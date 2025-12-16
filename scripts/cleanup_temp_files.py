"""
Small helper to remove common temporary files created while experimenting
with the Kalshi starter code.

This script is intentionally conservative and only targets a few known
paths. Adjust it for your own workflow as needed.
"""

from __future__ import annotations

import shutil
from pathlib import Path


def main() -> None:
  root = Path(__file__).resolve().parents[1]

  candidates = [
      root / ".pytest_cache",
      root / ".mypy_cache",
      root / "__pycache__",
  ]

  removed_any = False

  for path in candidates:
      if path.exists():
          print(f"Removing {path} ...")
          shutil.rmtree(path)
          removed_any = True

  if not removed_any:
      print("No known temporary directories found.")
  else:
      print("Cleanup finished.")


if __name__ == "__main__":
  main()
