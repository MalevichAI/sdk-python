from typing import Any, AsyncIterable, Iterable, Literal, Union
import json

from malevich_sdk.core_api.pipeline import Pipeline
from malevich_sdk.utils import getid, parse_fn
from malevich_sdk.modelling.image import FunctionRef
from malevich_coretools import (
    create_cfg,
    pipeline_prepare,
    task_run,
    Processor,
    Cfg,
    get_collections_by_group_name,
    create_doc,
    AlternativeArgument,
    get_run_main_pipeline_cfg,
)

# I make here iterable with an idea that we will
# optimize logs fetching in the future by enabling
# streaming responses. For now it is just a list
# disguised as an iterable.
def get_run_logs(run: 'Run', /) -> Iterable[str]:
    from malevich_coretools import logs

    app_logs = logs(run.operation_id, run.id)
    for log in app_logs.data[run.id].data:
        yield log.data


async def async_get_run_logs(run: 'Run', /) -> AsyncIterable[str]:
    from malevich_coretools import logs

    app_logs = await logs(run.operation_id, run.id, is_async=True)
    for log in app_logs.data[run.id].data:
        yield log.data

class RunResults:
    def __init__(self, run: 'Run') -> None:
        self.run = run

    def docs(self) -> list[dict[str, Any]]:
        from malevich_coretools import get_collections_by_group_name
        
        if self.run.pipeline_id is None:
            raise ValueError("You cannot obtain results from a run that is not associated with a pipeline (i.e. `pipeline_id` is not set)")
        
        pipeline = Pipeline.get(self.run.pipeline_id)
        results_map = pipeline.as_core_pipeline.results

        if '__main__' in results_map:
            result_def = next(iter(results_map['__main__']), None)
            if result_def is None:
                return []
            return [json.loads(doc.data) for doc in get_collections_by_group_name(result_def.name, self.run.operation_id, self.run.id).data[0].docs]
        else:
            return []

RunStatus = Literal['in_progress', 'completed', 'failed']

class Run:
    id: str
    operation_id: str
    pipeline_id: str | None = None

    def __init__(self, id: str, operation_id: str, pipeline_id: str | None = None) -> None:
        self.id = id
        self.operation_id = operation_id
        self.pipeline_id = pipeline_id

    @property
    def results(self) -> RunResults:
        return RunResults(self)

    def status(self) -> RunStatus:
        from malevich_coretools import get_run_status

        match (status := get_run_status(self.operation_id, self.id)):
            case 'in_progress' | 'running' | 'waiting':
                return 'in_progress'
            case _:
                raise ValueError(f"Unknown run status: {status}")


class Group:
    """Helper class to assemble InputGroups for the run function.
    
    Positional arguments passed to run() are assumed to be InputGroups
    with corresponding titles. Use Group() to assemble these groups.
    
    Args:
        name: The name of the InputGroup (corresponds to the function parameter name)
        **kwargs: Key-value pairs that make up the group's data
        
    Examples:
        ```python
        run(
            "some_function",
            config={},
            Group("from_address", city="Moscow", street="Main St"),
            Group("to_address", city="SPB", street="Nevsky"),
            threshold=0.5  # Goes to default group
        )
        ```
    """
    def __init__(self, name: str, /, **kwargs: Any) -> None:
        self.name = name
        self.data = kwargs


def run(
    __function: Union[str, FunctionRef],
    __config: dict[str, Any] | None = None,
    /,
    *groups: Any,
    **kwargs: Any,
) -> Run:
    """Run a function with the given configuration and inputs.
    
    Positional arguments are assumed to be InputGroups with corresponding titles.
    Use Group(name, /, **kwargs) to assemble groups. All other kwargs go to the default group.
    
    Args:
        __function: Function reference as string or FunctionRef object
        __config: Optional configuration dictionary
        *groups: Positional arguments that are Group instances (InputGroups)
        **kwargs: Keyword arguments that go to the default group
        
    Returns:
        Run object representing the execution
        
    Examples:
        ```python
        # With InputGroups
        run(
            "some_function",
            config={"setting": "value"},
            Group("from_address", city="Moscow", street="Main St"),
            Group("to_address", city="SPB", street="Nevsky"),
            threshold=0.5,  # Goes to default group
            max_items=100   # Goes to default group
        )
        ```
    """
    processor_key = '__main__'
    
    if isinstance(__function, str):
        fun_ref = parse_fn(__function)
    else:
        fun_ref = __function

    # Process positional Group arguments
    run_kwargs: dict[str, Any] = {}
    
    for group in groups:
        if not isinstance(group, Group):
            raise TypeError(
                f"Positional arguments must be Group instances. "
                f"Got {type(group).__name__} instead."
            )
        run_kwargs[group.name] = group.data
    
    # Add all other kwargs to the default group
    # Default group key is '__input__' based on the function processing logic
    if kwargs:
        run_kwargs['__input__'] = kwargs

    # Set up processor arguments: map each group name to its collection
    # Collection names will be generated by the pipeline system
    processor_arguments: dict[str, AlternativeArgument] = {}
    for group_name in run_kwargs.keys():
        processor_arguments[group_name] = AlternativeArgument(
            collectionName=group_name,
        )

    # Create and prepare the pipeline first to get the actual collection names
    pipeline = Pipeline.upsert(processors={
        processor_key: Processor(
            image=fun_ref,
            processorId=fun_ref.processor_id,
            cfg=json.dumps(__config or {}),
            arguments=processor_arguments,
        )
    })

    # Prepare the pipeline to get an operation
    active_operation = next(iter(pipeline.operations.active()), None)
    if active_operation is None:
        active_operation = pipeline.operations.create()
    active_operation.bind_pipeline(pipeline.id, verify=True)

    # Get the main pipeline configuration to fetch actual collection names
    # The pipeline system may generate/modify collection names during preparation
    pipeline_cfg = get_run_main_pipeline_cfg(active_operation.id)
    pipeline_id = pipeline_cfg.pipelineId
    
    # Get the prepared pipeline to access processor arguments with actual collection names
    prepared_pipeline = Pipeline.get(pipeline_id)
    
    # Extract collection names from processor arguments
    # The collection names are generated/modified by the pipeline system
    collection_name_map: dict[str, str] = {}
    main_processor = prepared_pipeline.as_core_pipeline.processors.get(processor_key)
    if main_processor and main_processor.arguments:
        for arg_name, arg_value in main_processor.arguments.items():
            if arg_value and hasattr(arg_value, 'collectionName') and arg_value.collectionName:
                collection_name_map[arg_name] = arg_value.collectionName

    # Prepare collections using the actual collection names from the pipeline
    collections: dict[str, str] = {}
    for group_name, group_data in run_kwargs.items():
        # Use the actual collection name from the pipeline, or fall back to group_name
        actual_collection_name = collection_name_map.get(group_name, group_name)
        # Create a document for each group/collection
        doc_id = create_doc(data=group_data)
        collections[actual_collection_name] = '#' + doc_id

    run = active_operation.runs.create(__config or {}, collections=collections)

    return run
