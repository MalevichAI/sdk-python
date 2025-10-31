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