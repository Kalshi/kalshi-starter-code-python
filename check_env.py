```py
"""
Simple helper to verify that environment variables required for
Kalshi starter code are present.

Usage:
    python check_env.py
"""

import os
import textwrap


REQUIRED_VARS = [
    "KALSHI_API_KEY",
    "KALSHI_API_SECRET",
    "KALSHI_ENV",  # e.g. "demo" or "prod"
]


def main() -> None:
    print("Checking Kalshi environment variables...\n")

    missing = []
    for name in REQUIRED_VARS:
        value = os.getenv(name)
        if value:
            print(f"✅ {name} is set (hidden)")
        else:
            print(f"⚠️ {name} is NOT set")
            missing.append(name)

    if missing:
        print("\nSome variables are missing:")
        for name in missing:
            print(f"  - {name}")
          
        print(
            "\nYou can export them before running the starter code, e.g.:\n"
        )
        example = textwrap.dedent(
            """
            export KALSHI_API_KEY=your_api_key_here
            export KALSHI_API_SECRET=your_secret_here
            export KALSHI_ENV=demo
            """
        ).strip()
        print(example)
    else:
      print("\nAll required variables appear to be set. ✅")


if __name__ == "__main__":
    main()
