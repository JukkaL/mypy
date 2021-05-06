# builtins stub with non-generic primitive types
from typing import Generic, TypeVar, Sequence, Iterator, Mapping, Iterable
T = TypeVar('T')
V = TypeVar('V')

class object:
    def __init__(self) -> None: pass
    def __str__(self) -> str: pass
    def __eq__(self, other: object) -> bool: pass
    def __ne__(self, other: object) -> bool: pass

class type:
    def __init__(self, x) -> None: pass

class int:
    # Note: this is a simplification of the actual signature
    def __init__(self, x: object = ..., base: int = ...) -> None: pass
    def __add__(self, i: int) -> int: pass
    def __rmul__(self, x: int) -> int: pass
class float:
    def __float__(self) -> float: pass
class complex: pass
class bool(int): pass
class str(Sequence[str]):
    def __add__(self, s: str) -> str: pass
    def __iter__(self) -> Iterator[str]: pass
    def __contains__(self, other: object) -> bool: pass
    def __getitem__(self, item: int) -> str: pass
    def format(self, *args, **kwargs) -> str: pass
class bytes(Sequence[int]):
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
class tuple(Generic[T]): pass
class list(Sequence[T]):
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
