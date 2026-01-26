import sys
from importlib.util import find_spec
from pathlib import Path


REQUIRED_MODULES = [
    "requests",
    "cryptography",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    missing_files = []
    for required in ["requirements.txt", "main.py", "clients.py"]:
        if not (root / required).exists():
            missing_files.append(required)

    missing_modules = [m for m in REQUIRED_MODULES if find_spec(m) is None]

    print("Kalshi starter setup check")
    print(f"Python: {sys.version.split()[0]}")

    if missing_files:
        print("\nMissing required files:")
        for f in missing_files:
            print(f"- {f}")

    if missing_modules:
        print("\nMissing Python packages (install with pip):")
        for m in missing_modules:
            print(f"- {m}")

    if not missing_files and not missing_modules:
        print("\nOK: basic project files and dependencies look good.")
        return 0

    print("\nNOT OK: please fix issues above and re-run this script.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
