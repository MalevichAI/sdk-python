from typing import Iterator, List
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Self
import itertools

class Task(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    id: str = Field(alias="taskId")
    appsDepends: List[str] = Field(alias="appsDepends", default_factory=list)
    tasksDepends: List[str] = Field(alias="tasksDepends", default_factory=list)
    synthetic: bool = Field(alias="synthetic", default=False)


    @classmethod
    def get(cls, id: str) -> Self:
        from malevich_coretools import get_task
        return cls(**get_task(id).model_dump())

    @classmethod
    def all(cls) -> Iterator[Self]:
        from malevich_coretools import get_pipelines

        task_ids = ().ids
        print(task_ids)
        total_tasks = len(task_ids)
        current, fetch_next, buffer = 0, 1, []
        while current < total_tasks:
            buffer = [cls.get(task_ids[i]) for i in range(current, min(current + fetch_next, total_tasks))]
            fetch_next *= 2
            yield from buffer
            current += fetch_next

