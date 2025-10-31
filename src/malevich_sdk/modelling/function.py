"""Function processing helpers for logic functions.

This module provides helpers to process function parameters and handle
input arguments, input groups, and run context arguments.
"""

import asyncio
import contextlib
import inspect
import json
import pathlib
from typing import Any, AsyncContextManager, Callable, ContextManager, Generic, Literal, TypeAlias, TypeVar, Union, cast, TYPE_CHECKING

try:
    import humps
except ImportError:
    humps = None  # type: ignore

from pydantic import BaseModel, create_model, TypeAdapter


from malevich_app.square import processor, Context, Doc  # type: ignore

from malevich_sdk.modelling.arguments import (
    ArgumentSpecification,
    InputArgument,
    InputArgumentGroup,
    RunContext,
    no_default,
)
from malevich_sdk.utils import issubclass_safe

# Optional imports for runtime dependencies
if TYPE_CHECKING:
    # These would be imported when available
    pass

# Type aliases for input processing
InputMapType: TypeAlias = dict[
    str, 
    Union[
        dict[str, tuple[type[Any], Any]],       # For default inputs
        tuple[type[BaseModel], Any],            # For input groups
        tuple[type[Any], Any],                  # For file inputs
    ]
]

InputKind: TypeAlias = Literal['doc', 'file', 'multi_file', 'obj']


# Helper classes and functions
class EmptyModel(BaseModel): 
    """Empty model used as a placeholder."""
    pass


class Output(BaseModel):
    """Wrapper model for logic function outputs.
    
    This model wraps the output data from logic functions
    if the output is not a base model. It is necessary to
    provide a consistent interface for the platform.
    """
    data: Any


T = TypeVar('T')
class Wrapped(BaseModel, Generic[T]):
    """Wrapper model for generic data."""
    data: T


def _check_arguments(**kwargs: inspect.Parameter) -> None:
    """Validate function parameters to ensure they meet the requirements.
    
    Raises:
        NotImplementedError: If variadic or positional-only arguments are found.
    """
    for value in kwargs.values():
        if value.kind == inspect.Parameter.VAR_KEYWORD or value.kind == inspect.Parameter.VAR_POSITIONAL:
            raise NotImplementedError("Variadic arguments are not supported")
        if value.kind == inspect.Parameter.POSITIONAL_ONLY:
            raise NotImplementedError("Positional-only arguments are not supported")


def _make_pyd_schema(
    name: str,
    base: type[BaseModel] | None = None,
    module: str | None = None,
    /,
    **kwargs: tuple[type[Any], Any]
) -> type[BaseModel]:
    """Create a Pydantic model dynamically with the given fields.
    
    Args:
        name: Name of the model class
        base: Optional base class for the model
        module: Module name for the created model
        **kwargs: Field definitions as (type, default) tuples
        
    Returns:
        A new Pydantic model class
    """
    return create_model(
        name,
        __config__=None,
        __doc__=None,
        __base__=base,
        __module__=module or __name__,
        __validators__=None,
        __cls_kwargs__={},
        **kwargs
    )


def _output_model(
    name: str,
    annotation: Any
) -> type[BaseModel]:
    """Create a Pydantic model for wrapping function outputs.
    
    Args:
        name: Name for the output model class
        annotation: Type annotation for the data field
        
    Returns:
        A Pydantic model class with a single 'data' field
    """
    return create_model(
        name,
        data=(annotation, ...)
    )


def process_function_arguments(
    parameters: dict[str, inspect.Parameter],
    default_input_key: str = '__input__',
) -> tuple[
    dict[str, Any],  # input_map
    dict[str, InputKind],  # input_kinds
    bool,  # has_context
    type[BaseModel] | None,  # context_model
]:
    """Process function parameters to extract input argument specifications.
    
    This function processes function parameters and identifies Input, InputGroup,
    and RunContext arguments. It builds the input map and input kinds
    dictionaries that are used for runtime type validation.
    
    Args:
        parameters: Function parameters from inspect.signature()
        default_input_key: Key to use for default input group
        
    Returns:
        Tuple containing:
        - input_map: Mapping of input keys to their type specifications
        - input_kinds: Mapping of input keys to their kind (only 'doc' supported)
        - has_context: Whether the function requires a context argument
        - context_model: The context model type if has_context is True
    """
    input_map: InputMapType = {}
    input_kinds: dict[str, InputKind] = {}
    has_context = False
    context_model: type[BaseModel] | None = None
    
    for key, value in parameters.items():
        if key == 'self' or key == 'cls':
            continue
            
        match (argument_value := value.default):
            case InputArgumentGroup():
                # Handle grouped input arguments (only doc mode)
                input_key = key
                argument_value.specification.group = key
                fm = argument_value.specification.file_mode
                
                # Only support doc mode (no file mode)
                if fm is not None:
                    raise ValueError(f"File mode is not supported in this implementation. Use doc mode only.")
                
                if not issubclass_safe(value.annotation, BaseModel):
                    raise ValueError(f"Input argument group `{key}` must be a Pydantic model")
                
                default_value = argument_value.specification.default
                no_default_value = default_value is no_default
                input_map[input_key] = (value.annotation, ... if no_default_value else default_value)
                input_kinds[input_key] = 'doc'
                        
            case InputArgument():
                # Handle individual input arguments
                input_key = default_input_key
                if input_key not in input_map:
                    input_map[input_key] = {}
                input_kinds[input_key] = 'doc'
                
                # Handle inspect.Signature.empty to avoid JSON serialization issues
                default_value = argument_value.specification.default
                no_default_value = default_value is no_default
                
                input_map[input_key][key] = (value.annotation, ... if no_default_value else default_value) # type: ignore
                argument_value.specification.group = default_input_key
                
            case RunContext(model=model):
                # Handle execution context
                has_context = True
                context_model = model
                
            case _:
                # Handle default parameters (no Input/InputGroup wrapper)
                input_key = default_input_key
                if input_key not in input_map:
                    input_map[input_key] = {}
                input_kinds[input_key] = 'doc'
                
                # Handle inspect.Signature.empty to avoid JSON serialization issues
                default_value = value.default
                no_default_value = default_value is inspect.Signature.empty
                
                input_map[input_key][key] = (value.annotation, ... if no_default_value else default_value) # type: ignore
    
    return input_map, input_kinds, has_context, context_model


def unwrap_function_inputs(
    map: InputMapType,
    kinds: dict[str, InputKind],
    **kwargs: Any,
) -> dict[str, Any]:
    """Unwrap Doc inputs into individual arguments using TypeAdapter for validation.
    
    This simplified implementation only handles doc inputs and uses TypeAdapter
    for direct validation without creating extra schemas.
        
    Args:
        map: Mapping of argument names to their type specifications
        kinds: Mapping of argument names to their kind (only 'doc' is supported)
        dependency_keys: List of argument names that are dependencies
        **kwargs: Doc objects containing the grouped inputs
        
    Returns:
        Dictionary of individual arguments with validated types.
    """
    inputs: dict[str, Any] = {}
    
    for key, value in map.items():
        # Skip if not provided
        if key not in kwargs:
            continue
        
        # Only handle doc inputs
        if kinds.get(key) != 'doc':
            raise ValueError(f"Only 'doc' input kind is supported, got '{kinds.get(key)}' for key '{key}'")
        
        if isinstance(value, dict):
            # Handle default input group: dict of field_name -> (type, default)
            doc_value = kwargs[key]
            if not isinstance(doc_value, Doc):
                raise ValueError(f"Expected Doc for input '{key}', got {type(doc_value)}")
            
            # Extract data from Doc
            doc_data = doc_value.dict()
            
            # Validate each field using TypeAdapter
            for field_name, (field_type, field_default) in value.items():
                field_value = doc_data.get(field_name)
                
                # Use TypeAdapter for validation
                try:
                    adapter = TypeAdapter(field_type)
                    inputs[field_name] = adapter.validate_python(field_value)
                except Exception as e:
                    raise ValueError(f"Failed to validate field '{field_name}' with type {field_type}: {e}")
        
        else:
            # Handle single input group: (type, default)
            doc_value = kwargs[key]
            if not isinstance(doc_value, Doc):
                raise ValueError(f"Expected Doc for input '{key}', got {type(doc_value)}")
            
            model_type, _ = value
            
            # Extract data from Doc and validate using TypeAdapter
            try:
                adapter = TypeAdapter(model_type)
                inputs[key] = adapter.validate_python(doc_value.dict())
            except Exception as e:
                raise ValueError(f"Failed to validate input '{key}' with type {model_type}: {e}")
    
    return inputs


# Placeholder for Logic class - would be defined elsewhere or imported
class Function(BaseModel):
    """Represents a logical processing unit.
    
    Simplified version without dependency management.
    """
    id: str
    arguments: dict[str, Any]
    input_schema: dict[str, Any]
    output_schema: str
    output_model_name: str | None = None
    return_file_mode: Literal['single', 'multi', 'obj'] | None = None
    results_wrapped: bool = False
    tags: dict[str, Any] = {}
    stub_remote_class: str | None = None
    stub_imports: list[str] | None = None
    stub_schemas: list[str] | None = None


# Placeholder for PlainLogicInput - would be defined elsewhere
class PlainLogicInput(BaseModel):
    """Plain logic input specification."""
    specification: ArgumentSpecification
    kind: str
    json_schema: str | None = None
    key: str
    type: str = 'plain'


def function(
    id: str | None = None,
    tags: dict[str, Any] | None = None,
    instance: Any | None = None,
    instance_factory: Callable[[], Any] | None = None,
    cls: type[Any] | None = None,
    cls_factory: Callable[[], type[Any]] | None = None,
    stub_remote_class: str | None = None,
    stub_imports: list[str] | None = None,
    stub_schemas: list[str] | None = None,
    *args: Any,
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], Function]:
    """Decorator to create a logic function.
    
    This decorator processes a function and creates a Logic object that
    encapsulates the function's input/output specifications.
    
    Args:
        id: Unique identifier for the logic function. Defaults to function name.
        in_separate_thread: Whether to run in a separate thread.
        tags: Additional tags for the logic function.
        instance: Instance to use for instance methods.
        instance_factory: Factory function to create instance.
        cls: Class to use for class methods.
        cls_factory: Factory function to create class.
        stub_remote_class: Remote class name for stub generation.
        stub_imports: Imports for stub generation.
        stub_schemas: Schemas for stub generation.
        async_context_managers: Async context managers to use.
        sync_context_managers: Sync context managers to use.
        
    Returns:
        A decorator function that returns a Logic object.
    """
    def decorator(fn: Callable[..., Any]) -> Function:
        nonlocal tags, instance, cls, instance_factory, cls_factory

        # Analyze the function signature
        is_coroutine = asyncio.iscoroutinefunction(fn)
        is_async_generator = inspect.isasyncgenfunction(fn)
        signature = inspect.signature(fn)
        parameters = signature.parameters
        return_annotation = signature.return_annotation
        default_input_key = '__input__'

        if return_annotation is inspect.Signature.empty:
            raise ValueError(
                f"Could not infer return annotation for logic function `{fn.__name__}`. "
                "Please specify the return annotation explicitly."
            )
        
        for parameter in parameters.values():
            if parameter.name == 'self' or parameter.name == 'cls':
                continue
            if parameter.annotation is inspect.Signature.empty:
                # Try to infer annotation from RunContext default value
                if isinstance(parameter.default, RunContext):
                    # Annotation will be inferred from RunContext.model in process_function_arguments
                    continue
                raise ValueError(
                    f"Could not infer annotation for argument `{parameter.name}` of logic function `{fn.__name__}`. "
                    "Please specify the annotation explicitly."
                )

        _check_arguments(**parameters)

        instance_method = any(
            key == 'self' and parameter.default is inspect.Signature.empty
            for key, parameter in parameters.items()
        )

        cls_method = any(
            key == 'cls' and parameter.default is inspect.Signature.empty
            for key, parameter in parameters.items()
        )

        if cls_method and cls is None and cls_factory is None:
            raise ValueError(f"Logic function `{fn.__name__}` is a class method, but neither `cls` nor `cls_factory` is provided")

        if instance_method and instance is None and instance_factory is None:
            raise ValueError(f"Logic function `{fn.__name__}` is an instance method, but neither `instance` nor `instance_factory` is provided")

        if cls_method and cls_factory is not None:
            cls = cls_factory()

        if instance_method and instance_factory is not None:
            instance = instance_factory()

        tags = {
            **(tags or {}),
            "sdk.function=true": "",
        }

        # Determine return file mode (simplified - would check file output types)
        return_file_mode: Literal['single', 'multi', 'obj'] | None = None

        # Determine output model
        if issubclass_safe(return_annotation, BaseModel):
            output_model = return_annotation
            output_model_name = return_annotation.__name__
        else:
            output_model_name = (humps.pascalize(fn.__name__) + "Output" if humps else fn.__name__.title() + "Output")
            output_model = _output_model(
                output_model_name,
                return_annotation
            )

        # Process function parameters using helper
        input_map, input_kinds, has_context, context_model = process_function_arguments(
            dict(parameters),  # Convert MappingProxyType to dict
            default_input_key
        )

        # Create logic object
        fn_object = Function(
            id=id or fn.__name__,
            arguments={},
            input_schema={},
            output_schema=json.dumps(output_model.model_json_schema()),
            output_model_name=output_model_name,
            return_file_mode=return_file_mode,
            results_wrapped=not issubclass_safe(return_annotation, BaseModel),
            tags=tags,
            stub_remote_class=stub_remote_class,
            stub_imports=stub_imports,
            stub_schemas=stub_schemas,
        )

        # Process arguments and populate logic_object.arguments (simplified - no file mode)
        for key, value in parameters.items():
            if key == 'self' or key == 'cls':
                continue
                
            match (argument_value := value.default):
                case InputArgumentGroup():
                    if argument_value.specification.file_mode is not None:
                        raise ValueError(f"File mode is not supported in this implementation")
                    
                    fn_object.arguments[key] = PlainLogicInput(
                        specification=argument_value.specification,
                        kind='schema',
                        json_schema=json.dumps(value.annotation.model_json_schema()),
                        key=key,
                    )
                case InputArgument():
                    is_schema = issubclass_safe(value.annotation, BaseModel)
                    fn_object.arguments[key] = PlainLogicInput(
                        specification=argument_value.specification,
                        kind='schema' if is_schema else 'primitive',
                        json_schema=json.dumps(value.annotation.model_json_schema()) if is_schema else None,
                        key=key,
                    )
                case _:
                    # Handle default parameters
                    default_value = value.default
                    is_schema = issubclass_safe(value.annotation, BaseModel)
                    fn_object.arguments[key] = PlainLogicInput(
                        specification=ArgumentSpecification(
                            group=default_input_key,
                            required=default_value is inspect.Signature.empty,
                        ),
                        key=key,
                        kind='schema' if is_schema else 'primitive',
                        json_schema=None,
                    )

        # Build a simple input schema for documentation (no actual schema creation needed for runtime)
        # We'll use TypeAdapter at runtime instead
        fn_object.input_schema = {}
        tags['sdk.logic'] = fn_object.model_dump_json()

        # Create wrapper function and apply processor decorator
        # Build annotations dict for the wrapper
        # The wrapper must have context: Context as first parameter
        annotations: dict[str, Any] = {}
        # Context parameter from executor (first parameter)
        annotations['context'] = Context[context_model] if context_model is not None else Context[Any]
        
        # Add other parameters based on input_map (simplified - would need proper Doc/OBJ types)
        # For now, just map them as Any
        for key in input_map.keys():
            if key != '__input__':  # Skip default input key
                annotations[key] = Any
        
        # Create i_to_key mapping for args
        i_to_key: dict[int, str] = dict(enumerate(annotations.keys()))
        
        # Create a wrapper function that accepts context: Context as first parameter
        # and replaces RunContext defaults with the actual Context object
        if is_async_generator:
            async def fn_wrapper(context: Any, *args: Any, **kwargs: Any) -> Any:
                """Wrapper function for processor decorator."""
                # Map positional args to parameter names (skip context which is at index 0)
                inputs: dict[str, Any] = {
                    i_to_key[i]: v
                    for i, v in enumerate(args, start=1)  # Start from 1 to skip context
                    if i_to_key[i] != 'context'
                }
                
                # Prepare kwargs for the original function
                kwargs_dict = unwrap_function_inputs(
                    input_map,
                    input_kinds,
                    **inputs,
                )
                
                # Replace RunContext defaults with actual Context object
                if has_context:
                    kwargs_dict['context'] = context
                
                # Call the original function
                async for item in fn(**kwargs_dict):
                    yield item
        elif is_coroutine:
            async def fn_wrapper(context: Any, *args: Any, **kwargs: Any) -> Any:
                """Wrapper function for processor decorator."""
                # Map positional args to parameter names (skip context which is at index 0)
                inputs: dict[str, Any] = {
                    i_to_key[i]: v
                    for i, v in enumerate(args, start=1)  # Start from 1 to skip context
                    if i_to_key[i] != 'context'
                }
                
                # Prepare kwargs for the original function
                kwargs_dict = unwrap_function_inputs(
                    input_map,
                    input_kinds,
                    **inputs,
                )
                
                # Replace RunContext defaults with actual Context object
                if has_context:
                    kwargs_dict['context'] = context
                
                # Call the original function
                return await fn(**kwargs_dict)
        else:
            def fn_wrapper(context: Any, *args: Any, **kwargs: Any) -> Any:
                """Wrapper function for processor decorator."""
                # Map positional args to parameter names (skip context which is at index 0)
                inputs: dict[str, Any] = {
                    i_to_key[i]: v
                    for i, v in enumerate(args, start=1)  # Start from 1 to skip context
                    if i_to_key[i] != 'context'
                }
                
                # Prepare kwargs for the original function
                kwargs_dict = unwrap_function_inputs(
                    input_map,
                    input_kinds,
                    **inputs,
                )
                
                # Replace RunContext defaults with actual Context object
                if has_context:
                    kwargs_dict['context'] = context
                
                # Call the original function
                return fn(**kwargs_dict)
        
    
        # Set function attributes for processor decorator
        setattr(fn_wrapper, "__annotations", annotations)
        setattr(fn_wrapper, "__argcount", len(annotations))
        setattr(fn_wrapper, "__varnames", list(annotations.keys()))
        setattr(fn_wrapper, "__name__", fn.__name__)
        setattr(fn_wrapper, "__module__", fn.__module__)
        
        # Apply processor decorator
        processor_decorator: Any = processor(
            id=id or fn.__name__,
            is_stream=is_async_generator,
            cpu_bound=False,  # function decorator doesn't have in_separate_thread parameter
            tags=tags,
        )
        _ = processor_decorator(fn_wrapper)

        return fn_object

    return decorator