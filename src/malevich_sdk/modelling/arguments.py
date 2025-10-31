"""Input argument processing for logic functions.

This module provides functions to define and configure input arguments for logic functions.
It supports three main types of input arguments:

1. **Plain Arguments** (`Input`): Simple arguments with optional metadata like grouping,
   default values, titles, and descriptions.

2. **Grouped Arguments** (`InputGroup`): Complex Pydantic model arguments that maintain
   their structure as nested objects rather than being flattened.

3. **File Arguments** (`File`): Specialized arguments for handling file inputs, supporting
   both single and multiple file modes.

4. **Run Context** (`RunContext`): Helper to request a context object in logic functions.
"""

import pathlib
from typing import Any, Literal, TypeVar, Union, overload
from malevich_app.square import Context
from pydantic import BaseModel

T = TypeVar("T", bound=Any)
T_Model = TypeVar("T_Model", bound=BaseModel)


class ArgumentSpecification(BaseModel):
    """Specification holds important data about the arguments"""

    model_config = {'extra': 'allow'}
    """General function (logic) argument specification."""

    default: Any | None = None
    """Default value of the argument (should be necessarily serializable to JSON)."""

    required: bool = True
    """Whether the argument is required.
    
    If `False`, the argument is optional and default value is used. Otherwise,
    default value is ignored.
    """

    title: str | None = None
    """Title of the argument. Appears in the API documentation."""

    description: str | None = None
    """Description of the argument. Appears in the API documentation."""

    group: str = '$default'
    """Group of the argument.
    
    This is internal attribute that hints Malevich platform. When
    different groups are used, they will as different keys in the input body.

    For example, 
    def foo(x: int = Input())
    """

    file_mode: Literal['single', 'multi', 'obj'] | None = None
    """Whether the argument is a file.
    
    If `True`, the argument is a file and will be handled as a file. If `multi`,
    the argument is a list of files and will be handled as a list of files.
    """


class NoDefault:
    """Sentinel class to indicate no default value is provided.
    
    This class is used internally to distinguish between a default value of None
    and the absence of any default value, which makes an argument required.
    """
    pass


no_default: NoDefault = NoDefault()


class InputArgument(BaseModel):
    """Base class for input argument specifications.
    
    Contains the argument specification that defines how the argument
    should be handled in the processing pipeline.
    """
    specification: ArgumentSpecification


class InputArgumentGroup(InputArgument):
    """Represents a grouped input argument for complex objects.
    
    This class is used for Pydantic models and file inputs that should be
    treated as a single cohesive unit rather than having their fields
    flattened into individual arguments. This maintains the structure
    and typing of complex objects in the input specification.
    
    Used by:
        - InputGroup() for Pydantic model arguments
        - File() for file input arguments
    """
    pass


# Type stubs for file return types - these would need to be defined elsewhere
# or imported from the appropriate location when actually used
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    class RemoteFile:
        path: pathlib.Path

    class RemoteFiles:
        paths: list[RemoteFile]

    class RemoteObjectFile:
        path: pathlib.Path
else:
    # Runtime placeholders - these should be imported from the actual location when used
    RemoteFile = None
    RemoteFiles = None
    RemoteObjectFile = None


def Input(
    default: T | NoDefault = no_default,
    /,
    group: str | None = None,
    **kwargs: Any,
) -> T:
    """Define an input argument for a logic function with metadata.

    This function creates a plain input argument that is passed as-is in the input body.
    It allows you to specify grouping, default values, titles, descriptions, and other
    argument characteristics that control how the argument appears in the API and how
    it's organized in the input structure.

    Args:
        default: Default value for the argument. If no_default, the argument
                becomes required. The default value must be JSON serializable.
        group: Group name for the argument. Arguments with the same group
               will be organized together in the input structure. Defaults to '$default'.
        **kwargs: Additional arguments passed to ArgumentSpecification
                 (title, description, required, etc.)

    Returns:
        An InputArgument instance that carries the argument metadata

    Examples:
        Basic Usage:
        ```python
        @logic()
        def process_data(
            threshold: float = Input(0.5),  # Optional with default
            max_items: int = Input()        # Required argument
        ) -> list:
            return [x for x in range(max_items) if x > threshold]
        ```

        Grouped Arguments:
        ```python
        @logic()
        def process_files(
            source_file: str = Input(group="files"),
            target_file: str = Input(group="files"),
            max_size: int = Input(group="limits"),
            timeout: float = Input(group="limits")
        ) -> str:
            # Arguments will be grouped as:
            # {
            #   "files": {"source_file": "...", "target_file": "..."},
            #   "limits": {"max_size": 100, "timeout": 30.0}
            # }
            return f"Processed {source_file} to {target_file}"
        ```

        With Additional Metadata:
        ```python
        @logic()
        def analyze_text(
            text: str = Input(
                title="Input Text",
                description="The text to analyze"
            ),
            language: str = Input(
                default="en",
                title="Language Code",
                description="ISO language code for text analysis"
            )
        ) -> dict:
            return {"text": text, "language": language, "length": len(text)}
        ```

    Input Structure:
        Plain arguments create a flat or grouped structure in the input body:
        
        .. code-block:: json
            {
                "threshold": 0.5,              // Default group argument
                "files": {                     // Custom group
                    "source_file": "input.txt",
                    "target_file": "output.txt"
                },
                "limits": {                    // Another custom group
                    "max_size": 1000,
                    "timeout": 30.0
                }
            }

    Note:
        - Plain arguments are passed directly to the logic function without transformation
        - Arguments without Input() default to the '$default' group
        - The group parameter organizes related arguments together
        - Default values make arguments optional; no default makes them required
        - All default values must be JSON serializable
    """
    return InputArgument(
        specification=ArgumentSpecification.model_validate(
            {
                **kwargs,
                'default': default if default is not no_default else None,
                'required': default is no_default,
                # FIXME: $default appears here, refactor will require changing it in both places
                'group': group or kwargs.get('group', '$default'),
            }
        )
    ) # type: ignore


def InputGroup(
    default: T_Model | NoDefault = no_default,
    /,
    **kwargs: Any,
) -> T_Model:
    """Define a complex input argument as a separate grouped object.

    This function is used when you want to accept a complex Pydantic model
    as a single grouped input rather than flattening its fields into
    individual arguments. This is particularly useful for organizing
    related parameters and avoiding flat argument lists.

    Args:
        default: Default instance of the model. If no_default, the argument
                becomes required.
        **kwargs: Additional arguments passed to ArgumentSpecification

    Returns:
        An InputArgumentGroup instance that treats the model as a single unit

    Examples:
        Without InputGroup (flat structure):
        ```python
        @logic()
        def process_config(
            host: str = Input(),
            port: int = Input(),
            username: str = Input(),
            password: str = Input(),
            timeout: float = Input(30.0)
        ) -> str:
            return f"Connected to {host}:{port}"

        # Results in flat input structure:
        # {
        #     "host": "localhost",
        #     "port": 5432,
        #     "username": "admin",
        #     "password": "secret",
        #     "timeout": 30.0
        # }
        ```

        With InputGroup (nested structure):
        ```python
        class DatabaseConfig(BaseModel):
            host: str
            port: int
            username: str
            password: str
            timeout: float = 30.0

        @logic()
        def process_config(
            config: DatabaseConfig = InputGroup()
        ) -> str:
            return f"Connected to {config.host}:{config.port}"

        # Results in nested input structure:
        # {
        #     "config": {
        #         "host": "localhost",
        #         "port": 5432,
        #         "username": "admin",
        #         "password": "secret",
        #         "timeout": 30.0
        #     }
        # }
        ```

        Multiple Input Groups:
        ```python
        class DatabaseConfig(BaseModel):
            host: str
            port: int
            credentials: str

        class ProcessingOptions(BaseModel):
            batch_size: int = 100
            parallel: bool = True
            timeout: float = 300.0

        @logic()
        def batch_process(
            db_config: DatabaseConfig = InputGroup(),
            options: ProcessingOptions = InputGroup()
        ) -> str:
            # Input structure:
            # {
            #     "db_config": {"host": "...", "port": 5432, "credentials": "..."},
            #     "options": {"batch_size": 100, "parallel": true, "timeout": 300.0}
            # }
            return f"Processing with {options.batch_size} batch size"
        ```

        Optional Input Groups:
        ```python
        class AdvancedSettings(BaseModel):
            cache_size: int = 1000
            debug_mode: bool = False

        @logic()
        def process_data(
            data: str = Input(),
            settings: AdvancedSettings = InputGroup(
                default=AdvancedSettings()  # Provides default instance
            )
        ) -> str:
            cache_info = f"cache: {settings.cache_size}" if settings else "no cache"
            return f"Processed {data} with {cache_info}"
        ```

    Benefits:
        - Organizes related parameters into logical groups
        - Maintains strong typing with Pydantic models
        - Reduces argument list length for complex configurations
        - Enables reuse of configuration models across functions
        - Provides better API structure for external consumers

    Note:
        - The input argument must be annotated with a BaseModel subclass
        - All model fields become part of the grouped input structure
        - Field defaults in the model are preserved
        - Validation is handled by the Pydantic model
    """
    return InputArgumentGroup(
        specification=ArgumentSpecification.model_validate(
            {
                **kwargs,
                'default': default if default is not no_default else None,
                'required': default is no_default,
            }
        )
    ) # type: ignore

@overload
def File(
    type: Literal['single'] = 'single',
    **kwargs: Any,
) -> RemoteFile:
    pass

@overload
def File(
    type: Literal['multi'],
    **kwargs: Any,
) -> RemoteFiles:
    pass

@overload
def File(
    type: Literal['obj'],
    **kwargs: Any,
) -> RemoteObjectFile:
    pass

def File(
    type: Literal['single', 'multi', 'obj'] = 'single',
    **kwargs: Any,
) -> Union[RemoteFile, RemoteFiles, RemoteObjectFile]:
    """Define a file input argument for logic functions.
    
    This function creates a specialized input argument for handling file inputs.
    It supports both single file and multiple file modes, automatically handling
    the underlying file_mode specification.
    
    Args:
        type: File type - 'single' for single file, 'multi' for multiple files,
             'obj' for object file. Defaults to 'single'.
        **kwargs: Additional arguments passed to ArgumentSpecification
                 (title, description, default, required, etc.)
    
    Returns:
        An InputArgumentGroup configured for file handling that will be typed
        as pathlib.Path (single file) or list[pathlib.Path] (multiple files)
    
    Examples:
        Single File Input:
        ```python
        @logic()
        def process_document(
            input_file: pathlib.Path = File(),
            output_dir: pathlib.Path = File(
                title="Output Directory",
                description="Directory where processed files will be saved"
            )
        ) -> str:
            return f"Processing {input_file.name}"
        ```
        
        Multiple Files Input:
        ```python
        @logic()
        def batch_process(
            source_files: list[pathlib.Path] = File(type='multi'),
            config_file: pathlib.Path = File()
        ) -> list[str]:
            return [f"Processed {f.name}" for f in source_files]
        ```
        
        Optional File with Default:
        ```python
        @logic()
        def generate_report(
            data_file: pathlib.Path = File(),
            template_file: pathlib.Path = File(
                default="/templates/default.html",
                title="Report Template",
                description="HTML template for report generation"
            )
        ) -> str:
            return f"Generated report using {template_file.name}"
        ```
        
        Required vs Optional Files:
        ```python
        @logic()
        def convert_files(
            input_files: list[pathlib.Path] = File(
                type='multi',
                title="Input Files",
                description="Files to convert"
            ),
            output_format: str = Input(default="pdf"),
            logo_file: pathlib.Path = File(
                required=False,  # Optional file
                title="Company Logo",
                description="Optional logo to include in converted files"
            )
        ) -> list[str]:
            return [f"Converted {f.name} to {output_format}" for f in input_files]
        ```
    
    File Handling:
        - Files are represented as pathlib.Path objects for better path manipulation
        - The file_mode is automatically set to 'single' or 'multi' based on the type parameter
        - File validation and existence checks are handled by the processing pipeline
        - Both absolute and relative paths are supported depending on the execution context
    
    Note:
        - File arguments are treated as grouped inputs internally
        - The actual file handling (upload, validation, etc.) is managed by the execution environment
        - Multiple files are always provided as a list, even if only one file is uploaded
    """
    kwargs['file_mode'] = type
    return InputGroup(**kwargs) # type: ignore


# RunContext helper
T_Context = TypeVar("T_Context", bound=BaseModel)


class Config(BaseModel):
    """Default configuration model for RunContext."""
    model_config = {'extra': 'allow'}


class RunContext:
    """Use this function to request a context to be passed to the logic function.
    
    .. code-block:: python
        @logic()
        def foo(context: Context = RunContext()) -> None:
            pass
            
    Args:
        model: Optional BaseModel subclass to use as the context configuration model.
               Defaults to Config if not provided.
    """    
    def __new__(
        cls, 
        model: type[T_Context] = Config
    ) -> 'Context[T_Context]':
        obj = super().__new__(cls)
        obj.model = model
        return obj # type: ignore

    def __init__(
        self,
        model: type[T_Context] = Config
    ) -> None:
        self.model = model
