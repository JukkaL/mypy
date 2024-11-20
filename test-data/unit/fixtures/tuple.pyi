# Builtins stub used in tuple-related test cases.

import _typeshed
from typing import Iterable, Iterator, TypeVar, Generic, Sequence, Optional, overload, Tuple, Type

_T = TypeVar("_T")
_Tco = TypeVar('_Tco', covariant=True)

class object:
    def __init__(self) -> None: pass
    def __eq__(self, other: object) -> bool: pass

class type:
    def __init__(self, *a: object) -> None: pass
    def __call__(self, *a: object) -> object: pass
class tuple(Sequence[_Tco], Generic[_Tco]):
    def __new__(cls: Type[_T], iterable: Iterable[_Tco] = ...) -> _T: ...
    def __iter__(self) -> Iterator[_Tco]: pass
    def __contains__(self, item: object) -> bool: pass
    @overload
    def __getitem__(self, x: int) -> _Tco: pass
    @overload
    def __getitem__(self, x: slice) -> Tuple[_Tco, ...]: ...
    def __mul__(self, n: int) -> Tuple[_Tco, ...]: pass
    def __rmul__(self, n: int) -> Tuple[_Tco, ...]: pass
    def __add__(self, x: Tuple[_Tco, ...]) -> Tuple[_Tco, ...]: pass
    def count(self, obj: object) -> int: pass
class function:
    __name__: str
class ellipsis: pass
class classmethod: pass

# We need int and slice for indexing tuples.
class int:
    def __neg__(self) -> 'int': pass
    def __pos__(self) -> 'int': pass
class float: pass
class slice: pass
class bool(int): pass
class str: pass # For convenience
class bytes: pass
class bytearray: pass

class list(Sequence[_T], Generic[_T]):
    @overload
    def __getitem__(self, i: int) -> _T: ...
    @overload
    def __getitem__(self, s: slice) -> list[_T]: ...
    def __contains__(self, item: object) -> bool: ...
    def __iter__(self) -> Iterator[_T]: ...

def isinstance(x: object, t: type) -> bool: pass

class BaseException: pass

class dict: pass
