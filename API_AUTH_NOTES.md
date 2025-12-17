# API Authentication Notes

This file complements the main README and highlights a few practical
points about API authentication for the Kalshi starter code.

## Environment variables

The starter expects the following variables to be set:

- `KALSHI_API_KEY`
- `KALSHI_API_SECRET`
- `KALSHI_ENV` (`demo` or `prod`)

Use `env.sample` as a template and copy it to `.env` for local usage.

## Demo vs production

- `demo` is intended for testing and experimentation.
- `prod` is the live environment for real trading.

Make sure your credentials and environment variable values match the
environment you intend to use.

## Handling credentials

- Do not commit `.env` files or credentials to version control.
- Prefer environment variables or secret management solutions provided
  by your deployment platform.
- Rotate credentials if you suspect they may have been exposed.

## Error handling

If you encounter authentication-related errors:

- re-check the values of `KALSHI_API_KEY` and `KALSHI_API_SECRET`,
- confirm that `KALSHI_ENV` is set correctly,
- inspect the error messages returned by the client for additional
  hints.
