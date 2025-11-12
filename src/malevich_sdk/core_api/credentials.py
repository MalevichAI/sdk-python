from contextlib import contextmanager
from malevich_coretools.abstract import AUTH as CoreAuth


@contextmanager
def with_credentials(auth: CoreAuth):
    """Sets credentials for the current context"""

    from malevich_coretools.secondary.config import Config
    old_auth = Config.CORE_USERNAME, Config.CORE_PASSWORD
    Config.CORE_USERNAME = auth[0] # type: ignore
    Config.CORE_PASSWORD = auth[1] # type: ignore
    try:
        yield auth
    finally:
        Config.CORE_USERNAME = old_auth[0] # type: ignore
        Config.CORE_PASSWORD = old_auth[1] # type: ignore


@contextmanager
def with_user(username: str):
    """Automatically load and set credentials from UserCredentialsStore.
    
    This context manager:
    1. Loads credentials from the store (or environment variables)
    2. Validates that host is already set (requires with_connection to be used first)
    3. Sets the credentials for the current context
    
    Raises:
        RuntimeError: If host is not set (with_connection must be called first)
        RuntimeError: If no credentials are found in store or environment
    
    Example:
        ```python
        from malevich_sdk.core_api.connection import with_connection
        from malevich_sdk.core_api.credentials import with_user
        
        with with_connection("https://core.mtp.group"):
            with with_user():
                # Credentials automatically loaded from store
                ...
        ```
    """
    from malevich_coretools.secondary.config import Config
    from malevich_sdk.usp.credstore import UserCredentialsStore
    
    # Check if host is already set
    if not Config.HOST_PORT or Config.HOST_PORT == "":
        raise RuntimeError(
            "Host is not set. Please use with_connection() before with_user(). "
            "Example: with with_connection('https://core.mtp.group'): with with_user(): ..."
        )
    
    # Load credentials from store
    core_creds = UserCredentialsStore().get_core_credentials(username=username)
    
    if not core_creds:
        raise RuntimeError(
            "No credentials found. Please add credentials using: "
            "malevich-sdk creds add core <username> <password> "
            "or set environment variables: MALEVICH_USER, MALEVICH_PASSWORD"
        )
    
    # Save old credentials
    old_auth = Config.CORE_USERNAME, Config.CORE_PASSWORD
    
    # Set new credentials
    Config.CORE_USERNAME = core_creds.user # type: ignore
    Config.CORE_PASSWORD = core_creds.password # type: ignore
    
    try:
        yield (core_creds.user, core_creds.password)
    finally:
        # Restore old credentials
        Config.CORE_USERNAME = old_auth[0] # type: ignore
        Config.CORE_PASSWORD = old_auth[1] # type: ignore