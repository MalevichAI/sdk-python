import pathlib
import tempfile
import os
from typing import Literal
from contextlib import contextmanager
from malevich_app.square import OBJ

class File:
    def __init__(self, path: pathlib.Path | str):
        self.core_path = pathlib.Path(path)
        _, self.physical_path = tempfile.mkstemp()

    def __del__(self):
        os.remove(self.physical_path)

    @contextmanager
    def open(self, mode: Literal['r', 'w', 'rb', 'wb'] = 'rb'):
        fp = open(self.physical_path, mode)
        yield fp
        fp.close()

    @property
    def path(self) -> pathlib.Path:
        return self.physical_path

    def read(self) -> bytes:
        with self.open('rb') as fp:
            return fp.read()

    def write(self, data: bytes):
        with self.open('wb') as fp:
            fp.write(data)

    def __str__(self):
        return self.core_path.as_posix()
    
    def __repr__(self): 
        return f"File(path={self.core_path.as_posix()})"