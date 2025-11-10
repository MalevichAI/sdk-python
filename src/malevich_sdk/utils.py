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

    # Try pattern with ref=$uuid
    match = re.match(r'^(?P<function_name>[^:]+)::\$(?P<ref>[a-f0-9-]+)$', fun_ref)
    if match:
        return FunctionRef(
            processor_id=match.group('function_name'),
            user=None,
            token=None,
            ref=f"${match.group('ref')}",
            tag='',
            syncRef=True,
        )

    # Try pattern with user:password@registry/image:tag (e.g., user:token@ghcr.io/org/repo:tag)
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
        return FunctionRef(
            processor_id=match.group('function_name'),
            user=match.group('user'),
            token=match.group('password'),
            ref=ref_with_tag,
            tag='',
            syncRef=True,
        )

    # Try pattern with user:password/ (legacy Docker Hub format)
    match = re.match(r'^(?P<function_name>[^:]+)::(?P<user>[^:]+):(?P<password>[^/]+)/(?P<image_ref>[^:]+):(?P<tag>[^@]+)(?:@(?P<digest>sha256:[a-f0-9]+))?$', fun_ref)
    if match:
        # Include tag (and digest if present) in ref string
        tag_part = match.group('tag')
        if match.group('digest'):
            ref_with_tag = f"{match.group('image_ref')}:{tag_part}@{match.group('digest')}"
        else:
            ref_with_tag = f"{match.group('image_ref')}:{tag_part}"
        return FunctionRef(
            processor_id=match.group('function_name'),
            user=match.group('user'),
            token=match.group('password'),
            ref=ref_with_tag,
            tag='',
            syncRef=True,
        )
    
    # Try pattern without user:password/ (just image_ref:tag@digest)
    match = re.match(r'^(?P<function_name>[^:]+)::(?P<image_ref>[^:]+):(?P<tag>[^@]+)(?:@(?P<digest>sha256:[a-f0-9]+))?$', fun_ref)
    if match:
        # Include tag (and digest if present) in ref string
        tag_part = match.group('tag')
        if match.group('digest'):
            ref_with_tag = f"{match.group('image_ref')}:{tag_part}@{match.group('digest')}"
        else:
            ref_with_tag = f"{match.group('image_ref')}:{tag_part}"
        return FunctionRef(
            processor_id=match.group('function_name'),
            user=None,
            token=None,
            ref=ref_with_tag,
            tag='',
            syncRef=True,
        )
    
    raise ValueError(f"Invalid function reference: {fun_ref}")