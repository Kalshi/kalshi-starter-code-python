"""Example entry point for the Kalshi starter client.

Reads the API key ID and the private key path from the environment, fetches the
account balance over HTTP, then opens a WebSocket subscription. The work is
inside ``main()`` so that importing this module has no side effects: the previous
version issued a network call and blocked on a WebSocket at import time.
"""

import asyncio
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dotenv import load_dotenv

from clients import Environment, KalshiHttpClient, KalshiWebSocketClient

# Toggle the environment here. DEMO is the default so that a misconfigured run
# cannot place real orders against the production exchange.
ENV = Environment.DEMO


def load_credentials(env: Environment) -> tuple:
    """Resolves the key ID and private key for ``env`` from the environment.

    Returns:
        A ``(key_id, private_key)`` tuple.

    Raises:
        RuntimeError: If either environment variable is unset, or if the key
            file is missing or cannot be parsed. The variable names are named
            explicitly; the key material itself is never echoed.
    """
    prefix = "DEMO" if env == Environment.DEMO else "PROD"
    key_id_var = f"{prefix}_KEYID"
    key_file_var = f"{prefix}_KEYFILE"

    key_id = os.getenv(key_id_var)
    key_file = os.getenv(key_file_var)

    # Check both variables before touching the filesystem. Previously a missing
    # KEYFILE reached ``open(None, "rb")``, which raises TypeError rather than
    # FileNotFoundError, so the friendly "Private key file not found" message
    # could never be reached and the operator saw an opaque type error instead.
    required = ((key_id_var, key_id), (key_file_var, key_file))
    missing = [name for name, value in required if not value]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            f"Copy .env.example to .env and fill it in."
        )

    try:
        with open(key_file, "rb") as handle:
            private_key = serialization.load_pem_private_key(
                handle.read(),
                password=None,  # Provide the password if your key is encrypted.
            )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Private key file not found at the path given by {key_file_var}"
        ) from exc
    except (ValueError, TypeError) as exc:
        # ValueError covers malformed PEM and an encrypted key with no password;
        # TypeError covers a password supplied for an unencrypted key. The
        # message deliberately omits the file contents so key material is never
        # written to logs.
        raise RuntimeError(
            f"Could not parse the private key referenced by {key_file_var}: "
            f"{type(exc).__name__}"
        ) from exc

    if not isinstance(private_key, rsa.RSAPrivateKey):
        # Kalshi request signing is RSA-PSS only. Failing here produces a clear
        # message instead of a confusing signature rejection from the server.
        raise RuntimeError(
            f"The key referenced by {key_file_var} is a "
            f"{type(private_key).__name__}, but an RSA private key is required."
        )

    return key_id, private_key


def main() -> None:
    """Fetches the balance over HTTP, then streams ticker updates."""
    load_dotenv()
    key_id, private_key = load_credentials(ENV)

    # The context manager closes the pooled HTTP connections on the way out,
    # including when get_balance raises.
    with KalshiHttpClient(
        key_id=key_id,
        private_key=private_key,
        environment=ENV,
    ) as client:
        balance = client.get_balance()
        print("Balance:", balance)

    ws_client = KalshiWebSocketClient(
        key_id=key_id,
        private_key=private_key,
        environment=ENV,
    )

    try:
        asyncio.run(ws_client.connect())
    except KeyboardInterrupt:
        # Ctrl-C during a long-lived subscription is an ordinary way to stop,
        # not a failure, so exit quietly instead of dumping a traceback.
        print("Interrupted; closing WebSocket.")


if __name__ == "__main__":
    main()

