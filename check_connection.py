import os
from clients import get_authenticated_client  # adjust if the helper name differs


def main() -> None:
    """
    Simple helper that verifies we can reach the Kalshi API
    using the current environment configuration.
    """
    client = get_authenticated_client()
    try:
        status = client.get_exchange_status()
    except Exception as exc:  # pragma: no cover - helper script
        print("Failed to reach Kalshi API:")
        print(repr(exc))
        raise SystemExit(1)

    print("Kalshi exchange status response:")
    print(status)


if __name__ == "__main__":
    main()
