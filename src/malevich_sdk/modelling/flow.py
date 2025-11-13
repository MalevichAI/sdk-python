from collections import defaultdict

from malevich_app import LocalRunner
from malevich_coretools import Processor, AlternativeArgument, base_settings, Pipeline as CorePipeline
from malevich_sdk.modelling.group import Group
from malevich_sdk.utils import parse_fn
from malevich_sdk.modelling.image import FunctionRef
from malevich_sdk.core_api.pipeline import Pipeline
from typing import Any
import json

class FlowGroup(Group):
    collection_name: str

    def __init__(self, name: str, collection_name: str, /, **kwargs: Any):
        self.name = name
        self.data = kwargs
        self.collection_name = collection_name
        
    @classmethod
    def from_group(cls, group: Group, collection_name: str) -> 'FlowGroup':
        return cls(group.name, collection_name, **group.data)

class FlowRef:
    def __init__(self, flow_id: str): 
        self.__flow_id = flow_id

    @property
    def flow_id(self) -> str:
        return self.__flow_id
    
class Flow:
    def __init__(self):
        self.__id_map = defaultdict(lambda: 0)
        self.__pipeline = CorePipeline(pipelineId='__temp__')
        self.__groups: dict[str, dict[str, FlowGroup]] = defaultdict(dict)


    def startwith(
        self, 
        name: str,
        /,
        *groups: Group, 
        function: FunctionRef | str, 
        config: dict[str, Any] | None = None,
        data: Any | None = None,
        memory_limit: int | None = None,
        cpu_limit: int | None = None,
        memory_request: int | None = None,
        cpu_request: int | None = None,
    ) -> 'FlowRef':
        function = parse_fn(function) if isinstance(function, str) else function
        if 'name' in self.__id_map:
            raise ValueError(f'"{name}" already exists in the flow')

        flow_id = name
        mapped_groups: list[FlowGroup] = []
        for group in groups:
            if not isinstance(group, Group):
                raise TypeError(
                    f"Positional arguments must be Group instances. "
                    f"Got {type(group).__name__} instead."
                )
            self.__id_map[group.name] += 1
            collection_name = f"{group.name}_{self.__id_map[group.name]}"
            mapped_groups.append(FlowGroup.from_group(group, collection_name))

        arguments = {
            group.name: AlternativeArgument(
                collectionName=group.collection_name,
            )
            for group in mapped_groups
        }


        if data:
            collection_name = f"__input__{self.__id_map['__input__']}"
            arguments['__input__'] = AlternativeArgument(
                collectionName=collection_name,
            )
            mapped_groups.append(FlowGroup(
                '__input__',
                collection_name,
                **data,
            ))

        for mapped_group in mapped_groups:
            self.__groups[flow_id][mapped_group.name] = mapped_group
        

        processor = Processor(
            image=function,
            processorId=function.processor_id,
            cfg=json.dumps(config or {}),
            arguments={
                group.name: AlternativeArgument(
                    collectionName=group.collection_name,
                )
                for group in mapped_groups
            },
            platformSettings=base_settings(
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
                memory_request=memory_request,
                cpu_request=cpu_request,
            )
        )

        self.__pipeline.processors[flow_id] = processor
        return FlowRef(flow_id)

    def add(
        self,
        name: str,
        /,
        function: FunctionRef | str,
        config: dict[str, Any] | None = None,
        memory_limit: int | None = None,
        cpu_limit: int | None = None,
        memory_request: int | None = None,
        cpu_request: int | None = None,
    ) -> 'FlowRef':
        function = parse_fn(function) if isinstance(function, str) else function
        if 'name' in self.__id_map:
            raise ValueError(f'"{name}" already exists in the flow')

        flow_id = name

        self.__pipeline.processors[flow_id] = Processor(
            image=function,
            processorId=function.processor_id,
            cfg=json.dumps(config or {}),
            arguments={},
            platformSettings=base_settings(
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
                memory_request=memory_request,
                cpu_request=cpu_request,
            )
        )
        return FlowRef(flow_id)

    def addflow(
        self,
        from_: FlowRef,
        to: str,
        in_: FlowRef,
    ) -> None:
        if not isinstance(from_, FlowRef):
            raise TypeError(
                f"`addflow` argument `from_` must be a FlowRef instance. "
                f"Got {type(from_).__name__} instead."
            )

        if not isinstance(in_, FlowRef):
            raise TypeError(
                f"`addflow` argument `in_` must be a FlowRef instance. "
                f"Got {type(in_).__name__} instead."
            )

        if to in self.__groups[in_.flow_id]:
            raise ValueError(
                f"`For processor {in_.flow_id} there is already a group set for {to}. "
            )

        if to in self.__pipeline.processors[in_.flow_id].arguments:
            raise ValueError(
                f"`For processor {in_.flow_id} there is already an argument set for {to}. "
            )

        self.__pipeline.processors[in_.flow_id].arguments[to] = AlternativeArgument(
            id=from_.flow_id,
        )

    def build(self) -> Pipeline:
        return Pipeline.from_core_pipeline(self.__pipeline)

    def upload_collections(self) -> dict[str, str]:
        """Upload collection data by creating documents.
        
        Creates a document for each group's data and returns a mapping
        of collection names to document references.
        
        Returns:
            Dict mapping collection names to document IDs (prefixed with '#')
        """
        from malevich_coretools import create_doc
        
        collections: dict[str, str] = {}
        
        # Iterate through all flow groups
        for flow_groups in self.__groups.values():
            for group in flow_groups.values():
                # Create a document for this group's data
                doc_id = create_doc(data=group.data)
                # Map collection name to document reference (with '#' prefix)
                collections[group.collection_name] = '#' + doc_id
        return collections

    def build_local_collections(self, runner: LocalRunner) -> dict[str, str]:
        collections: dict[str, str] = {}
        for flow_groups in self.__groups.values():
            for group in flow_groups.values():
                collection_id = runner.storage.data(group.data)
                collections[group.collection_name] = '#' + collection_id
        return collections