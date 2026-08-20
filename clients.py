import base64
import json
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Mapping, Optional

import requests
import websockets
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"


class KalshiBaseClient:
    """Base client class for interacting with the Kalshi API."""

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ) -> None:
        """Initialize the client with an API key, private key, and environment."""
        if not key_id:
            raise ValueError("The Kalshi API key ID must not be empty.")

        self.key_id = key_id
        self.private_key = private_key
        self.environment = environment
        self.last_api_call = 0.0

        if self.environment == Environment.DEMO:
            self.http_base_url = "https://demo-api.kalshi.co"
            self.ws_base_url = "wss://demo-api.kalshi.co"
        elif self.environment == Environment.PROD:
            self.http_base_url = "https://api.elections.kalshi.com"
            self.ws_base_url = "wss://api.elections.kalshi.com"
        else:
            raise ValueError("Invalid environment")

    def request_headers(self, method: str, path: str) -> Dict[str, str]:
        """Generate the required authentication headers for an API request."""
        current_time_milliseconds = int(time.time() * 1000)
        timestamp_str = str(current_time_milliseconds)
        request_path = path.split("?", 1)[0]
        message = timestamp_str + method + request_path
        signature = self.sign_pss_text(message)

        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }

    def sign_pss_text(self, text: str) -> str:
        """Sign text with RSA-PSS and return a base64-encoded signature."""
        try:
            signature = self.private_key.sign(
                text.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
        except (InvalidSignature, ValueError) as exc:
            raise ValueError("RSA-PSS signing failed") from exc
        return base64.b64encode(signature).decode("utf-8")


class KalshiHttpClient(KalshiBaseClient):
    """Client for handling authenticated HTTP connections to the Kalshi API."""

    # SECURITY FIX: Added explicit bounds for network I/O timeouts to prevent indefinite hangs.
    REQUEST_TIMEOUT_SECONDS = 10.0
    RATE_LIMIT_SECONDS = 0.1

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ) -> None:
        super().__init__(key_id, private_key, environment)
        # QUALITY FIX: Use requests.Session() to pool connections and improve performance.
        self.session = requests.Session()
        self.host = self.http_base_url
        self.exchange_url = "/trade-api/v2/exchange"
        self.markets_url = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self.session.close()

    def rate_limit(self) -> None:
        """Wait until the minimum interval between API calls has elapsed."""
        # SECURITY FIX: Use time.monotonic() instead of wall-clock time for reliable, linear rate limiting.
        now = time.monotonic()
        remaining = self.RATE_LIMIT_SECONDS - (now - self.last_api_call)
        if remaining > 0:
            time.sleep(remaining)
        self.last_api_call = time.monotonic()

    @staticmethod
    def raise_if_bad_response(response: requests.Response) -> None:
        """Raise an HTTPError when the response status code indicates failure."""
        response.raise_for_status()

    def post(self, path: str, body: Mapping[str, Any]) -> Any:
        """Perform an authenticated POST request to the Kalshi API."""
        self.rate_limit()
        response = self.session.post(
            self.host + path,
            json=dict(body),
            headers=self.request_headers("POST", path),
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        self.raise_if_bad_response(response)
        return response.json()

    # SECURITY FIX: Replaced mutable default arguments (e.g., params={}) with immutable Optional[Mapping]
    def get(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """Perform an authenticated GET request to the Kalshi API."""
        self.rate_limit()
        response = self.session.get(
            self.host + path,
            headers=self.request_headers("GET", path),
            params=dict(params) if params is not None else None,
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        self.raise_if_bad_response(response)
        return response.json()

    # SECURITY FIX: Replaced mutable default arguments with immutable Optional[Mapping]
    def delete(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """Perform an authenticated DELETE request to the Kalshi API."""
        self.rate_limit()
        response = self.session.delete(
            self.host + path,
            headers=self.request_headers("DELETE", path),
            params=dict(params) if params is not None else None,
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get_balance(self) -> Dict[str, Any]:
        """Retrieve the account balance."""
        return self.get(self.portfolio_url + "/balance")

    def get_exchange_status(self) -> Dict[str, Any]:
        """Retrieve the exchange status."""
        return self.get(self.exchange_url + "/status")

    def get_trades(
        self,
        ticker: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        max_ts: Optional[int] = None,
        min_ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieve trades using the supplied filters."""
        params = {
            "ticker": ticker,
            "limit": limit,
            "cursor": cursor,
            "max_ts": max_ts,
            "min_ts": min_ts,
        }
        return self.get(
            self.markets_url + "/trades",
            params={key: value for key, value in params.items() if value is not None},
        )


class KalshiWebSocketClient(KalshiBaseClient):
    """Client for handling authenticated WebSocket connections to Kalshi."""

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ) -> None:
        super().__init__(key_id, private_key, environment)
        self.ws: Optional[Any] = None
        self.url_suffix = "/trade-api/ws/v2"
        self.message_id = 1

    async def connect(self) -> None:
        """Establish and handle an authenticated WebSocket connection."""
        host = self.ws_base_url + self.url_suffix
        auth_headers = self.request_headers("GET", self.url_suffix)
        
        # QUALITY FIX: Enforced bounded open/close timeouts for the WebSocket connection.
        async with websockets.connect(
            host,
            additional_headers=auth_headers,
            open_timeout=10,
            close_timeout=10,
        ) as websocket:
            self.ws = websocket
            try:
                await self.on_open()
                await self.handler()
            finally:
                # QUALITY FIX: Guaranteed cleanup of the connection state.
                self.ws = None

    async def on_open(self) -> None:
        """Handle a successful WebSocket connection."""
        print("WebSocket connection opened.")
        await self.subscribe_to_tickers()

    async def subscribe_to_tickers(self) -> None:
        """Subscribe to ticker updates for all markets."""
        if self.ws is None:
            raise RuntimeError("The WebSocket is not connected.")

        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {"channels": ["ticker"]},
        }
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def handler(self) -> None:
        """Handle incoming messages and surface unexpected failures."""
        if self.ws is None:
            raise RuntimeError("The WebSocket is not connected.")

        try:
            async for message in self.ws:
                await self.on_message(message)
        except websockets.ConnectionClosed as error:
            await self.on_close(error.code, error.reason)
        except Exception as error:
            await self.on_error(error)
            # QUALITY FIX: Re-raise unexpected exceptions to ensure detached failures are observable.
            raise

    async def on_message(self, message: str) -> None:
        """Handle an incoming WebSocket message."""
        print("Received message:", message)

    async def on_error(self, error: Exception) -> None:
        """Handle a WebSocket error without exposing credentials."""
        print("WebSocket error:", error)

    async def on_close(self, close_status_code: int, close_msg: str) -> None:
        """Handle a closed WebSocket connection."""
        print(
            "WebSocket connection closed with code:",
            close_status_code,
            "and message:",
            close_msg,
        )