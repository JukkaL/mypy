from typing import Generic, TypeVar
_T = TypeVar('_T')

class object:
    def __init__(self) -> None: pass

class type:
    def __init__(self, x: object) -> None: pass

# These are provided here for convenience.
class int:
    # Note: this is a simplification of the actual signature
    def __init__(self, x: object = ..., base: int = ...) -> None: pass
    def __add__(self, other: int) -> int: pass
    def __rmul__(self, other: int) -> int: pass
class float: pass

class str:
    def __add__(self, other: 'str') -> 'str': pass
class bytes: pass

class tuple(Generic[_T]): pass
class function: pass
class ellipsis: pass

# Definition of None is implicit
