"""Utility functions for modelling."""

from typing import Any
import uuid

from malevich_sdk.modelling.image import FunctionRef


def issubclass_safe(cls: Any, base: type[Any] | tuple[type[Any], ...]) -> bool:
    """Checks if a class is a subclass of given base classes
    
    Same as `issubclass` but does not fail if `cls` is not a type. However,
    does not provide static type hints (after using `issubclass_safe` the
    type of the arguments does not change as it does with `issubclass`).

    Args:
        cls: Any object to check
        base: The base class or tuple of base classes to check against.

    Returns:
        True if `cls` is a subclass of `base`, False otherwise.
    """
    if isinstance(cls, type):
        if issubclass(cls, base):
            return True
        else:
            return False
    else:
        return False


def getid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"   

def parse_fn(fun_ref: str, /) -> FunctionRef:
    import re
    # FunctionName::$uuid (ref pattern)
    # OR FunctionName::user:password@registry/image_ref:tag@digest
    # OR FunctionName::user:password/image_ref:tag@digest
    # OR FunctionName::image_ref:tag@digest (without auth)
    # Note: digest must be SHA256 format (sha256:...), not simple strings like "latest"

    function_ref = None

    # Try pattern with ref=$uuid
    match = re.match(r'^(?P<function_name>[^:]+)::\$(?P<ref>[a-f0-9-]+)$', fun_ref)
    if match:
        function_ref = FunctionRef(
            processor_id=match.group('function_name'),
            user=None,
            token=None,
            ref=f"${match.group('ref')}",
            tag='',
            syncRef=True,
        )

    # Try pattern with user:password@registry/image:tag (e.g., user:token@ghcr.io/org/repo:tag)
    if not function_ref:
        match = re.match(r'^(?P<function_name>[^:]+)::(?P<user>[^:]+):(?P<password>[^@]+)@(?P<registry>[^/]+)/(?P<image_path>.+?):(?P<tag>[^@]+)(?:@(?P<digest>sha256:[a-f0-9]+))?$', fun_ref)
        if match:
            # Include registry, full image path and tag (and digest if present)
            tag_part = match.group('tag')
            registry = match.group('registry')
            image_path = match.group('image_path')
            if match.group('digest'):
                ref_with_tag = f"{registry}/{image_path}:{tag_part}@{match.group('digest')}"
            else:
                ref_with_tag = f"{registry}/{image_path}:{tag_part}"
            function_ref = FunctionRef(
                processor_id=match.group('function_name'),
                user=match.group('user'),
                token=match.group('password'),
                ref=ref_with_tag,
                tag='',
                syncRef=True,
            )

    # Try pattern with user:password/ (legacy Docker Hub format)
    if not function_ref:
        match = re.match(r'^(?P<function_name>[^:]+)::(?P<user>[^:]+):(?P<password>[^/]+)/(?P<image_ref>[^:]+):(?P<tag>[^@]+)(?:@(?P<digest>sha256:[a-f0-9]+))?$', fun_ref)
        if match:
            # Include tag (and digest if present) in ref string
            tag_part = match.group('tag')
            if match.group('digest'):
                ref_with_tag = f"{match.group('image_ref')}:{tag_part}@{match.group('digest')}"
            else:
                ref_with_tag = f"{match.group('image_ref')}:{tag_part}"
            function_ref = FunctionRef(
                processor_id=match.group('function_name'),
                user=match.group('user'),
                token=match.group('password'),
                ref=ref_with_tag,
                tag='',
                syncRef=True,
            )
    
    # Try pattern without user:password/ (just image_ref:tag@digest)
    if not function_ref:
        match = re.match(r'^(?P<function_name>[^:]+)::(?P<image_ref>[^:]+):(?P<tag>[^@]+)(?:@(?P<digest>sha256:[a-f0-9]+))?$', fun_ref)
        if match:
            # Include tag (and digest if present) in ref string
            tag_part = match.group('tag')
            if match.group('digest'):
                ref_with_tag = f"{match.group('image_ref')}:{tag_part}@{match.group('digest')}"
            else:
                ref_with_tag = f"{match.group('image_ref')}:{tag_part}"
            function_ref = FunctionRef(
                processor_id=match.group('function_name'),
                user=None,
                token=None,
                ref=ref_with_tag,
                tag='',
                syncRef=True,
            )
    
    # Try pattern without :: (just function name for local execution)
    if not function_ref:
        match = re.match(r'^(?P<function_name>[a-zA-Z_][a-zA-Z0-9_]*)$', fun_ref)
        if match:
            function_ref = FunctionRef(
                processor_id=match.group('function_name'),
                user=None,
                token=None,
                ref='',
                tag='',
                syncRef=False,
            )
    
    if not function_ref:
        raise ValueError(f"Invalid function reference: {fun_ref}")
    
    # If credentials are not embedded, try to resolve from user-space
    # using longest prefix matching
    if function_ref.user is None or function_ref.token is None:
        try:
            from malevich_sdk.usp.credstore import UserCredentialsStore
            store = UserCredentialsStore()
            
            # Find credentials with longest prefix match
            all_image_creds = store.get_all_image_credentials()
            best_match = None
            longest_prefix_len = 0
            
            for cred in all_image_creds:
                if function_ref.ref.startswith(cred.ref):
                    if len(cred.ref) > longest_prefix_len:
                        best_match = cred
                        longest_prefix_len = len(cred.ref)
            
            if best_match:
                function_ref.user = best_match.user
                function_ref.token = best_match.token
        except Exception:
            # If credential resolution fails, continue without credentials
            # This allows the function to work even if credstore is not available
            pass
    
    return function_ref