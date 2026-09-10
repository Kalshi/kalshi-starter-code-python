"""HTTP and WebSocket clients for the Kalshi trade API.

Authentication uses an RSA key pair. Every request carries the API key ID, a
Unix-millisecond timestamp, and an RSA-PSS/SHA-256 signature computed over the
concatenation ``timestamp + method + path``. The signed path must not include
the query string, which is why it is stripped in :meth:`request_headers`.
"""

import base64
import json
import time
from enum import Enum
from typing import Any, Dict, Optional, Tuple

import requests
import websockets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Default socket timeout applied to every HTTP request, as (connect, read)
# seconds. Without an explicit timeout, ``requests`` blocks forever: a stalled
# server or a silently dropped connection hangs the calling thread with no
# recovery path.
DEFAULT_TIMEOUT: Tuple[float, float] = (5.0, 30.0)

# Retry policy for transient transport and server-side failures. POST is
# deliberately excluded from the retried methods because order placement and
# cancellation are not safe to replay blindly.
RETRY_TOTAL = 3
RETRY_BACKOFF_FACTOR = 0.5
RETRY_STATUS_FORCELIST = (429, 500, 502, 503, 504)

# Minimum spacing between two consecutive API calls, in seconds.
RATE_LIMIT_INTERVAL_SECONDS = 0.1


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
    ):
        """Initializes the client with the provided API key and private key.

        Args:
            key_id: Your Kalshi API key ID.
            private_key: Your RSA private key.
            environment: The API environment to use (DEMO or PROD).

        Raises:
            ValueError: If ``key_id`` is empty, if ``private_key`` is missing,
                or if ``environment`` is not a known :class:`Environment`.
        """
        if not key_id:
            raise ValueError(
                "key_id must be a non-empty string; check that the "
                "DEMO_KEYID / PROD_KEYID environment variable is set"
            )
        if private_key is None:
            raise ValueError("private_key must be a loaded RSA private key")

        self.key_id = key_id
        self.private_key = private_key
        self.environment = environment

        # Monotonic clock rather than wall-clock time: it never jumps backwards
        # on an NTP correction or a DST transition, so the rate limiter can
        # neither be pushed into an unbounded sleep nor be tricked into skipping
        # its delay entirely.
        self.last_api_call = time.monotonic()

        if self.environment == Environment.DEMO:
            self.HTTP_BASE_URL = "https://demo-api.kalshi.co"
            self.WS_BASE_URL = "wss://demo-api.kalshi.co"
        elif self.environment == Environment.PROD:
            self.HTTP_BASE_URL = "https://api.elections.kalshi.com"
            self.WS_BASE_URL = "wss://api.elections.kalshi.com"
        else:
            raise ValueError(f"Invalid environment: {environment!r}")


    def request_headers(self, method: str, path: str) -> Dict[str, str]:
        """Generates the required authentication headers for API requests.

        Args:
            method: HTTP method, for example ``"GET"``. Normalised to upper case
                so that the signed string always matches what the server
                recomputes.
            path: Request path, optionally including a query string.

        Returns:
            The four headers the Kalshi API requires, plus the JSON content type.
        """
        timestamp_str = str(int(time.time() * 1000))

        # Sign the path only. Everything from the first "?" onwards is excluded,
        # because the Kalshi signature specification covers the path component
        # and not the query string.
        path_without_query = path.split("?", 1)[0]

        msg_string = timestamp_str + method.upper() + path_without_query
        signature = self.sign_pss_text(msg_string)

        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }

    def sign_pss_text(self, text: str) -> str:
        """Signs ``text`` with RSA-PSS/SHA-256 and base64-encodes the result.

        Raises:
            ValueError: If the key cannot produce a signature, for example
                because it is too short for a SHA-256 digest plus salt, or
                because the object passed in is not an RSA private key.
        """
        message = text.encode("utf-8")
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
        except (ValueError, TypeError) as exc:
            # ``sign`` raises ValueError for an unusable key/padding combination
            # and TypeError when the object is not an RSA private key. It never
            # raises InvalidSignature, which is verification-only, so the
            # previous handler for it could never fire. The original exception is
            # chained so the root cause stays visible in the traceback.
            raise ValueError("RSA-PSS signing failed") from exc
        return base64.b64encode(signature).decode("utf-8")


class KalshiHttpClient(KalshiBaseClient):
    """Client for handling HTTP connections to the Kalshi API."""

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
        timeout: Tuple[float, float] = DEFAULT_TIMEOUT,
    ):
        """Initializes the HTTP client.

        Args:
            key_id: Your Kalshi API key ID.
            private_key: Your RSA private key.
            environment: The API environment to use (DEMO or PROD).
            timeout: ``(connect, read)`` timeout in seconds for every request.
        """
        super().__init__(key_id, private_key, environment)
        self.host = self.HTTP_BASE_URL
        self.timeout = timeout
        self.exchange_url = "/trade-api/v2/exchange"
        self.markets_url = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"

        # One pooled session keeps TLS connections warm across calls and carries
        # the retry policy. Only GET and DELETE are replayed on a transient
        # failure; replaying POST could duplicate an order.
        self.session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=RETRY_TOTAL,
                backoff_factor=RETRY_BACKOFF_FACTOR,
                status_forcelist=RETRY_STATUS_FORCELIST,
                allowed_methods=frozenset({"GET", "DELETE"}),
                # Let ``raise_if_bad_response`` surface the final status so the
                # caller keeps seeing a requests.HTTPError with a real response
                # body attached, rather than a urllib3 MaxRetryError.
                raise_on_status=False,
            )
        )
        self.session.mount("https://", adapter)

    def close(self) -> None:
        """Releases the pooled HTTP connections held by this client."""
        self.session.close()

    def __enter__(self) -> "KalshiHttpClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


    def rate_limit(self) -> None:
        """Built-in rate limiter to prevent exceeding API rate limits.

        Sleeps only the time still outstanding before the next call is allowed.
        The previous implementation slept the full 100 ms threshold even when
        99 ms had already elapsed, which roughly halved achievable throughput.
        """
        elapsed = time.monotonic() - self.last_api_call
        if elapsed < RATE_LIMIT_INTERVAL_SECONDS:
            time.sleep(RATE_LIMIT_INTERVAL_SECONDS - elapsed)
        self.last_api_call = time.monotonic()

    def raise_if_bad_response(self, response: requests.Response) -> None:
        """Raises an HTTPError if the response status code indicates an error."""
        # A successful status is 200-299 inclusive. The previous
        # ``range(200, 299)`` membership test excluded 299, so a 299 response
        # would have been reported as a failure.
        if not 200 <= response.status_code < 300:
            response.raise_for_status()

    def post(self, path: str, body: dict) -> Any:
        """Performs an authenticated POST request to the Kalshi API."""
        self.rate_limit()
        response = self.session.post(
            self.host + path,
            json=body,
            headers=self.request_headers("POST", path),
            timeout=self.timeout,
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Performs an authenticated GET request to the Kalshi API.

        ``params`` defaults to ``None`` rather than ``{}``: a mutable default is
        created once at function-definition time and shared by every call, so
        any caller that mutated it would corrupt all subsequent requests.
        """
        self.rate_limit()
        response = self.session.get(
            self.host + path,
            headers=self.request_headers("GET", path),
            params=params or {},
            timeout=self.timeout,
        )
        self.raise_if_bad_response(response)
        return response.json()

    def delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Performs an authenticated DELETE request to the Kalshi API."""
        self.rate_limit()
        response = self.session.delete(
            self.host + path,
            headers=self.request_headers("DELETE", path),
            params=params or {},
            timeout=self.timeout,
        )
        self.raise_if_bad_response(response)
        return response.json()


    def get_balance(self) -> Dict[str, Any]:
        """Retrieves the account balance."""
        return self.get(self.portfolio_url + "/balance")

    def get_exchange_status(self) -> Dict[str, Any]:
        """Retrieves the exchange status."""
        return self.get(self.exchange_url + "/status")

    def get_trades(
        self,
        ticker: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        max_ts: Optional[int] = None,
        min_ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params = {
            "ticker": ticker,
            "limit": limit,
            "cursor": cursor,
            "max_ts": max_ts,
            "min_ts": min_ts,
        }
        # Drop unset filters so the query string only carries what the caller
        # actually asked for.
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.markets_url + "/trades", params=params)


class KalshiWebSocketClient(KalshiBaseClient):
    """Client for handling WebSocket connections to the Kalshi API."""

    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.DEMO,
    ):
        super().__init__(key_id, private_key, environment)
        self.ws: Optional[Any] = None
        self.url_suffix = "/trade-api/ws/v2"
        self.message_id = 1  # Add counter for message IDs

    async def connect(self) -> None:
        """Establishes a WebSocket connection using authentication."""
        host = self.WS_BASE_URL + self.url_suffix
        auth_headers = self.request_headers("GET", self.url_suffix)
        # ping_interval / ping_timeout make a half-open connection detectable:
        # without keepalive pings a silently dropped TCP session looks identical
        # to an idle one and the consumer waits forever for the next message.
        async with websockets.connect(
            host,
            additional_headers=auth_headers,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ) as websocket:
            self.ws = websocket
            try:
                await self.on_open()
                await self.handler()
            finally:
                # Clear the reference on the way out so a later send cannot be
                # attempted on a closed socket.
                self.ws = None


    async def on_open(self) -> None:
        """Callback when WebSocket connection is opened."""
        print("WebSocket connection opened.")
        await self.subscribe_to_tickers()

    async def subscribe_to_tickers(self) -> None:
        """Subscribe to ticker updates for all markets."""
        if self.ws is None:
            raise RuntimeError("subscribe_to_tickers called before connect()")
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {"channels": ["ticker"]},
        }
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def handler(self) -> None:
        """Handle incoming messages."""
        if self.ws is None:
            raise RuntimeError("handler called before connect()")
        try:
            async for message in self.ws:
                await self.on_message(message)
        except websockets.ConnectionClosed as exc:
            await self.on_close(exc.code, exc.reason)
        except Exception as exc:
            # Report the failure, then re-raise. Swallowing it here made every
            # unexpected error look like a clean shutdown: ``connect()`` returned
            # normally and the caller had no way to distinguish a closed stream
            # from a crashed consumer.
            await self.on_error(exc)
            raise

    async def on_message(self, message: Any) -> None:
        """Callback for handling incoming messages."""
        print("Received message:", message)

    async def on_error(self, error: Exception) -> None:
        """Callback for handling errors."""
        print("WebSocket error:", error)

    async def on_close(
        self, close_status_code: Optional[int], close_msg: Optional[str]
    ) -> None:
        """Callback when WebSocket connection is closed."""
        print(
            "WebSocket connection closed with code:",
            close_status_code,
            "and message:",
            close_msg,
        )

