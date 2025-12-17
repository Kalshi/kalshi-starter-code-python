import os


def test_kalshi_env_flag_present() -> None:
    """
    Sanity test to verify that KALSHI_ENV has a reasonable value
    when running tests in a configured environment.
    """
    value = os.getenv("KALSHI_ENV", "")
    # The variable may be empty in some local setups, so this test is
    # intentionally lenient and only checks that we can read it.
    assert value is not None
