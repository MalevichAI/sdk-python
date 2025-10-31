import json
from typing import TYPE_CHECKING, Any

from malevich_coretools import get_run_main_pipeline_cfg
from malevich_coretools.funcs.funcs import get_run_mainPipelineCfg
from malevich_sdk.utils import getid

if TYPE_CHECKING:
    from malevich_sdk.core_api.run import Run

class OperationRuns:
    def __init__(self, operation: 'Operation') -> None:
        self.operation = operation

    def create(self, config: dict[str, Any], /, collections: dict[str, str] | None = None, **kwargs: Any) -> 'Run':
        from malevich_coretools import task_run, create_cfg, Cfg
        from malevich_sdk.core_api.run import Run
        
        cfg_id = getid('cfg')
        run_id = getid('run')

        create_cfg(cfg_id, Cfg(
            collections=collections or {},
            app_cfg_extension={
                '$__main__': json.dumps({**config})
            }
        ))
        task_run(self.operation.id, cfg_id, run_id=run_id)
        return Run(run_id, self.operation.id, self.operation.pipeline_id)

class Operation:
    id: str
    pipeline_id: str | None = None

    def __init__(self, id: str, pipeline_id: str | None = None) -> None:
        self.pipeline_id = pipeline_id
        self.id = id

    def bind_pipeline(self, pipeline_id: str, /, verify: bool = False) -> None:
        if verify:
            try:
                info = get_run_main_pipeline_cfg(self.id)
                if info.pipelineId != pipeline_id:
                    raise ValueError(f"Operation {self.id} is not associated with pipeline {pipeline_id}")
            except Exception as e:
                raise ValueError(f"Operation {self.id} is not associated with any pipeline") from e

        self.pipeline_id = pipeline_id

    @property
    def runs(self) -> OperationRuns:
        return OperationRuns(self)

    