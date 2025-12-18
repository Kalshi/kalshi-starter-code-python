#!/usr/bin/env bash
set -euo pipefail

if command -v black >/dev/null 2>&1; then
  echo "Running black..."
  black .
else
  echo "black is not installed, skipping formatting."
fi

if command -v ruff >/dev/null 2>&1; then
  echo "Running ruff..."
  ruff check .
else
  echo "ruff is not installed, skipping linting."
fi
