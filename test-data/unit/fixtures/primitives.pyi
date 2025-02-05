# builtins stub with non-generic primitive types
import _typeshed
from typing import Generic, TypeVar, Sequence, Iterator, Mapping, Iterable, Tuple, Union

T = TypeVar('T')
V = TypeVar('V')

class object:
    def __init__(self) -> None: pass
    def __str__(self) -> str: pass
    def __eq__(self, other: object) -> bool: pass
    def __ne__(self, other: object) -> bool: pass

class type:
    def __init__(self, x: object) -> None: pass

class int:
    # Note: this is a simplification of the actual signature
    def __init__(self, x: object = ..., base: int = ...) -> None: pass
    def __add__(self, i: int) -> int: pass
    def __rmul__(self, x: int) -> int: pass
    def __bool__(self) -> bool: pass
class float:
    def __float__(self) -> float: pass
    def __add__(self, x: float) -> float: pass
    def hex(self) -> str: pass
class complex:
    def __add__(self, x: complex) -> complex: pass
class bool(int): pass
class str(Sequence[str]):
    def __add__(self, s: str) -> str: pass
    def __iter__(self) -> Iterator[str]: pass
    def __contains__(self, other: object) -> bool: pass
    def __getitem__(self, item: int) -> str: pass
    def format(self, *args: object, **kwargs: object) -> str: pass
class bytes(Sequence[int]):
    def __add__(self, x: bytes) -> bytes: pass
    def __iter__(self) -> Iterator[int]: pass
    def __contains__(self, other: object) -> bool: pass
    def __getitem__(self, item: int) -> int: pass
class bytearray(Sequence[int]):
    def __init__(self, x: bytes) -> None: pass
    def __iter__(self) -> Iterator[int]: pass
    def __contains__(self, other: object) -> bool: pass
    def __getitem__(self, item: int) -> int: pass
class memoryview(Sequence[int]):
    def __init__(self, x: bytes) -> None: pass
    def __iter__(self) -> Iterator[int]: pass
    def __contains__(self, other: object) -> bool: pass
    def __getitem__(self, item: int) -> int: pass
class tuple(Generic[T]):
    def __contains__(self, other: object) -> bool: pass
class list(Sequence[T]):
    def append(self, v: T) -> None: pass
    def __iter__(self) -> Iterator[T]: pass
    def __contains__(self, other: object) -> bool: pass
    def __getitem__(self, item: int) -> T: pass
class dict(Mapping[T, V]):
    def __iter__(self) -> Iterator[T]: pass
class set(Iterable[T]):
    def __iter__(self) -> Iterator[T]: pass
class frozenset(Iterable[T]):
    def __iter__(self) -> Iterator[T]: pass
class function: pass
class ellipsis: pass

class range(Sequence[int]):
    def __init__(self, __x: int, __y: int = ..., __z: int = ...) -> None: pass
    def count(self, value: int) -> int: pass
    def index(self, value: int) -> int: pass
    def __getitem__(self, i: int) -> int: pass
    def __iter__(self) -> Iterator[int]: pass
    def __contains__(self, other: object) -> bool: pass

def isinstance(x: object, t: Union[type, Tuple]) -> bool: pass
