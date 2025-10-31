from typing import Any, Callable, Iterable, Iterator
from malevich_coretools import Pipeline as CorePipeline, Processor, Result, get_task_runs
from typing_extensions import Self
import json
import hashlib

from malevich_sdk.core_api.exc import CoreApiNotFoundError
from malevich_sdk.core_api.operation import Operation
from malevich_sdk.utils import getid


class PipelineNotFoundError(CoreApiNotFoundError):
    def __init__(self, id: str) -> None:
        super().__init__(f"Pipeline {id} not found")
        self.id = id


class PipelineCursor:
    def __init__(self, predicate: Callable[['Pipeline'], bool]) -> None:
        self.__predicate = predicate

    def __iter__(self) -> Iterator['Pipeline']:
        from malevich_coretools import get_pipelines

        p_cursor = get_pipelines()
        for id in p_cursor.ids:
            pipeline = Pipeline.get(id)
            if self.__predicate(pipeline):
                yield pipeline


class PipelineOperations:
    def __init__(self, pipeline: 'Pipeline') -> None:
        self.pipeline = pipeline

    def active(self) -> Iterable[Operation]:
        active_ops = get_task_runs(self.pipeline.id)
        for id in active_ops.ids:
            yield Operation(id)


    def create(self, **config: dict[str, Any]) -> Operation:
        from malevich_coretools import pipeline_prepare, Cfg, create_cfg
        
        cfg_id = getid('cfg')
        create_cfg(cfg_id, Cfg())
        prepare_result = pipeline_prepare(self.pipeline.id, cfg_id)
        return Operation(prepare_result.operationId)


class Pipeline:
    id: str


    def hash(self) -> bytes:
        # Convert Processor objects to dictionaries for JSON serialization
        # Processor is a Pydantic model, use model_dump() to convert to dict
        processors_dict = {
            key: processor.model_dump()
            for key, processor in self.__processors.items()
        }
        return hashlib.sha256(json.dumps(processors_dict, sort_keys=True).encode()).digest()

    def __init__(self, id: str | None = None, *, processors: dict[str, Processor], result_map: dict[str, list[Result]] | None = None) -> None:
        self.__processors = processors
        self.__result_map = result_map
        self.id = id or self.hash().hex()

    @property
    def as_core_pipeline(self) -> CorePipeline:
        return CorePipeline(
            pipelineId=self.id,
            processors=self.__processors,
            results={
                key: [Result(name=self.hash().hex() + '_' + key)]
                for key in self.__processors.keys()
            },
        )

    @property
    def operations(self) -> PipelineOperations:
        return PipelineOperations(self)

    @classmethod
    def get(cls, id: str) -> Self:
        from malevich_coretools import get_pipeline
        
        try:
            pipeline = get_pipeline(id)
            return cls(processors=pipeline.processors, id=pipeline.pipelineId, result_map=pipeline.results)
        except Exception as e:
            raise PipelineNotFoundError(f"Pipeline {id} not found") from e

    @classmethod
    def upsert(cls, processors: dict[str, Processor]) -> Self:
        from malevich_coretools import create_pipeline

        pipeline = cls(processors=processors)
        try:
            return cls.get(pipeline.id)
        except PipelineNotFoundError:   
            create_pipeline(pipeline.id, processors=pipeline.as_core_pipeline.processors, results=pipeline.as_core_pipeline.results)
            return cls.get(pipeline.id)