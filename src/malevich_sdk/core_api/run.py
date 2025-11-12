import pathlib
import tempfile
import uuid
import aiofiles
from typing import Any, AsyncIterable, Coroutine, Iterable, Literal, Union, overload
import json

from malevich_app import LocalRunner, cfg_translate, pipeline_translate

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
from malevich_sdk.modelling.flow import Flow
from malevich_sdk.modelling.group import Group

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

class RunFileResult:
    def __init__(self, path: str) -> None:
        self._core_path = path
        self._physical_path = None
        
    async def downloadto_async(self, path: pathlib.Path) -> None:
        from malevich_coretools import get_collection_object

        objbytes = await get_collection_object(self._core_path, is_async=True)
        if not path.exists():
            if '.' in path.name:
                path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

        async with aiofiles.open(path, 'wb') as f:
            await f.write(objbytes)

class RunNamedResult:
    def __init__(self, run: 'Run', name: str) -> None:
        self.run = run
        self.name = name

    def docs(self) -> list[dict[str, Any]]:
        from malevich_coretools import get_collections_by_group_name
        
        return [json.loads(doc.data) for doc in get_collections_by_group_name(self.name, self.run.operation_id, self.run.id).data[0].docs]

    def file(self) -> RunFileResult:
        from malevich_coretools import get_collections_by_group_name
        
        docs = self.docs()
        if len(docs) != 1:
            raise ValueError(f"Could not parse results as file, expected the collection to contain exactly one document, got {len(docs)}")
        path = docs[0].get('path')
        if path is None:
            raise ValueError(f"Could not parse results as file, expected the document to contain a `path` field, available fields: {docs[0].keys()}")
        return RunFileResult(path=path)

class RunResults:
    def __init__(self, run: 'Run') -> None:
        self.run = run
        self.__terminal_result_id = None
        
    def __getitem__(self, name: str) -> RunNamedResult:
        return RunNamedResult(self.run, name)

    def __get_terminal_result_id(self) -> str:
        if self.run.pipeline_id is None:
            raise ValueError("You cannot obtain results from a run that is not associated with a pipeline (i.e. `pipeline_id` is not set)")
        
        pipeline = Pipeline.get(self.run.pipeline_id)
        terminals = pipeline.terminals()
        if len(terminals) != 1:
            raise ValueError(f"Could not retrieve results automatically as pipeline has {len(terminals)} terminal processors,"
            " use `.results[name]` to access the result of a certain flow element")

        terminal_processor_name = next(iter(terminals.keys()))
        if self.__terminal_result_id is None:
            self.__terminal_result_id = pipeline.as_core_pipeline.results[terminal_processor_name][0].name
        return self.__terminal_result_id

    def docs(self) -> list[dict[str, Any]]:

        return RunNamedResult(self.run, self.__get_terminal_result_id()).docs()

    def file(self) -> RunFileResult:
        return RunNamedResult(self.run, self.__get_terminal_result_id()).file()

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


class LocalRunResults:
    def __init__(self, run: 'LocalRun') -> None:
        self.run = run
        self.__terminal_result_id = None

    def __getitem__(self, name: str) -> RunNamedResult: ...

    def __get_terminal_result_id(self) -> str:
        if self.run.pipeline is None:
            raise ValueError("You cannot obtain results from a run that is not associated with a pipeline (i.e. `pipeline_id` is not set)")
        
        pipeline = self.run.pipeline
        terminals = pipeline.terminals()
        if len(terminals) != 1:
            raise ValueError(f"Could not retrieve results automatically as pipeline has {len(terminals)} terminal processors,"
            " use `.results[name]` to access the result of a certain flow element")

        terminal_processor_name = next(iter(terminals.keys()))
        if self.__terminal_result_id is None:
            self.__terminal_result_id = pipeline.as_core_pipeline.results[terminal_processor_name][0].name
        return self.__terminal_result_id 
       
    def docs(self) -> list[dict[str, Any]]:
        path = pathlib.Path.joinpath(
            *map(pathlib.Path, [
                getattr(self.run.runner, '_LocalRunner__local_settings').results_dir,
                self.run.operation_id,
                self.run.id,
                self.__get_terminal_result_id(),
                '0.json'
            ])
        )

        with open(path, 'r') as f:
            return json.load(f)

    def file(self) -> RunFileResult:
        raise NotImplementedError("Local runs do not support file results")

class LocalRun(Run):
    pipeline: Pipeline | None = None
    def __init__(self, runner: LocalRunner, id: str, operation_id: str, pipeline_id: str | None = None, pipeline: Pipeline | None = None) -> None:
        super().__init__(id, operation_id, pipeline_id)
        self.runner = runner
        self.pipeline = pipeline

    @property
    def results(self) -> LocalRunResults:
        return LocalRunResults(self)



def _run_flow_remote(flow: Flow) -> Run:
    from malevich_coretools import get_run_main_pipeline_cfg
   
    pipeline = Pipeline.upsert(flow.build())

    active_operation = pipeline.operations.create()
    active_operation.bind_pipeline(pipeline.id, verify=True)

    # Get the main pipeline configuration to fetch actual collection names
    # The pipeline system may generate/modify collection names during preparation
    pipeline_cfg = get_run_main_pipeline_cfg(active_operation.id)
    pipeline_id = pipeline_cfg.pipelineId
    
    # Get the prepared pipeline to access processor arguments with actual collection names
    prepared_pipeline = Pipeline.get(pipeline_id)
    
    collections = flow.upload_collections()

    run = active_operation.runs.create({}, collections=collections)

    return run


async def _run_flow_local(flow: Flow, imports: list[str]) -> Run:
    from malevich_app import LocalRunner, LocalRunStruct

    results_dir = pathlib.Path.home() / '.malevich' / 'local_runner' / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    mount_path = pathlib.Path.home() / '.malevich' / 'mnt'
    mount_path.mkdir(parents=True, exist_ok=True)
    mount_path_obj = pathlib.Path.home() / '.malevich' / 'mnt_obj'
    mount_path_obj.mkdir(parents=True, exist_ok=True)

    runner = LocalRunner(
        local_settings=LocalRunStruct(
            import_dirs=imports,
            mount_path=str(mount_path),
            mount_path_obj=str(mount_path_obj),
            results_dir=str(results_dir),
        ),
    )
    flow_pipeline = flow.build()
    pipeline = pipeline_translate(flow_pipeline.as_core_pipeline, secret_keys={})
    cfg = cfg_translate(Cfg(
        collections=flow.build_local_collections(runner)
    ))

    operation_id = await runner.prepare(pipeline, cfg)
    run_id = str(uuid.uuid4())
    await runner.run(operation_id, run_id, cfg)
    await runner.stop(operation_id, run_id)
    return LocalRun(runner, run_id, operation_id, pipeline=flow_pipeline)

@overload
def runflow(flow: Flow, /, local: Literal[True], imports: list[str]) -> Run: ...
@overload
def runflow(flow: Flow) -> Run: ...
def runflow(flow: Flow, /, local: bool = True, imports: list[str] = []) -> Run:
    match local:
        case True: return _run_flow_local(flow, imports)
        case False: return _run_flow_remote(flow)
  


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
    flow = Flow()       
    _ = flow.startwith('__main__', __function, __config, *groups, data=kwargs)
    return runflow(flow)

def runlocal(
    __function: Union[str, FunctionRef],
    __config: dict[str, Any] | None = None,
    imports: list[str] = [],
    /,
    *groups: Any,
    **kwargs: Any,
) -> Coroutine[Any, Any, Run]:
    flow = Flow()
    _ = flow.startwith('__main__', __function, __config, *groups, data=kwargs or {})
    return runflow(flow, local=True, imports=imports)
