from pydantic import BaseModel
from malevich_coretools import JsonImage

class FunctionRef(JsonImage):
    processor_id: str