# Builtins stub used to support @attr.s tests.
from typing import Union, overload, Sequence, Generic, TypeVar, Iterable, \
    Tuple, Iterator


class object:
    def __init__(self) -> None: pass
    def __eq__(self, o: object) -> bool: pass
    def __ne__(self, o: object) -> bool: pass

class type: pass
class bytes: pass
class function: pass
class bool: pass
class float: pass
class int:
    @overload
    def __init__(self, x: Union[str, bytes, int] = ...) -> None: ...
    @overload
    def __init__(self, x: Union[str, bytes], base: int) -> None: ...
class complex:
    @overload
    def __init__(self, real: float = ..., im: float = ...) -> None: ...
    @overload
    def __init__(self, real: str = ...) -> None: ...

Tco = TypeVar('Tco', covariant=True)

class tuple(Sequence[Tco], Generic[Tco]):
    @overload
    def __init__(self) -> None: pass
    @overload
    def __init__(self, x: Iterable[Tco]) -> None: pass
    def __iter__(self) -> Iterator[Tco]: pass
    def __contains__(self, item: object) -> bool: pass
    def __getitem__(self, x: int) -> Tco: pass
    def __rmul__(self, n: int) -> Tuple[Tco, ...]: pass
    def __add__(self, x: Tuple[Tco, ...]) -> Tuple[Tco, ...]: pass
    def count(self, obj: object) -> int: pass

T = TypeVar('T')

class list(Sequence[T], Generic[T]): pass

class str: pass
class unicode: pass
class ellipsis: pass
