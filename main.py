import asyncio
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from dotenv import load_dotenv

from clients import Environment, KalshiHttpClient, KalshiWebSocketClient


def load_private_key(key_file_path: str, password: Optional[str] = None) -> RSAPrivateKey:
    """Load an RSA private key from a PEM file without printing key material."""
    path = Path(key_file_path).expanduser()
    try:
        key_bytes = path.read_bytes()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Private key file not found: {path}") from exc
    except OSError as exc:
        raise OSError(f"Unable to read the private key file: {path}") from exc

    try:
        # SECURITY FIX: Securely load the private key, supporting encrypted PEM passwords, 
        # without ever printing or leaking the key material to stdout/logs.
        private_key = serialization.load_pem_private_key(
            key_bytes,
            password=password.encode("utf-8") if password else None,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("The private key file is invalid or has the wrong password.") from exc

    if not isinstance(private_key, RSAPrivateKey):
        raise TypeError("The configured private key must be an RSA private key.")
    return private_key


def build_configuration() -> tuple[Environment, str, str, Optional[str]]:
    """Read and validate the environment-specific Kalshi configuration."""
    # SECURITY FIX: Configuration is now strictly environment-driven and validated.
    environment_name = os.getenv("KALSHI_ENV", "demo").lower()
    try:
        environment = Environment(environment_name)
    except ValueError as exc:
        raise ValueError("KALSHI_ENV must be either 'demo' or 'prod'.") from exc

    prefix = "DEMO" if environment is Environment.DEMO else "PROD"
    key_id = os.getenv(f"{prefix}_KEYID")
    key_file = os.getenv(f"{prefix}_KEYFILE")
    key_password = os.getenv(f"{prefix}_KEY_PASSWORD")
    if not key_id or not key_file:
        raise RuntimeError(
            f"{prefix}_KEYID and {prefix}_KEYFILE must be set in the environment."
        )
    return environment, key_id, key_file, key_password


def main() -> None:
    """Fetch the account balance and start the ticker WebSocket example."""
    load_dotenv()
    environment, key_id, key_file, key_password = build_configuration()
    private_key = load_private_key(key_file, key_password)

    http_client = KalshiHttpClient(
        key_id=key_id,
        private_key=private_key,
        environment=environment,
    )
    try:
        print("Balance:", http_client.get_balance())
    finally:
        # QUALITY FIX: Ensure deterministic cleanup of the HTTP connection pool.
        http_client.close()

    websocket_client = KalshiWebSocketClient(
        key_id=key_id,
        private_key=private_key,
        environment=environment,
    )
    asyncio.run(websocket_client.connect())


# QUALITY FIX: Protected the entry point to ensure safe module imports without 
# accidental side effects or API requests during initialization.
if __name__ == "__main__":
    main()