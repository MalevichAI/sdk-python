from contextlib import contextmanager


@contextmanager
def with_connection(url: str):
    """Sets credentials for the current context"""
    
    from malevich_coretools.secondary.config import Config

    if not url.endswith("/"):
        url += "/"

    old_url = Config.HOST_PORT # type: ignore
    Config.HOST_PORT = url # type: ignore
    try:
        yield
    finally:
        Config.HOST_PORT = old_url # type: ignore