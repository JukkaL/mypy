# Minimal set of builtins required to work with Enums
from typing import TypeVar, Generic

T = TypeVar('T')

class object:
    def __init__(self): pass

class type: pass
class tuple(Generic[T]):
    def __getitem__(self, x: int) -> T: pass

class int: pass
class str: pass
class dict: pass
class ellipsis: pass
