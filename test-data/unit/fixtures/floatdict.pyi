from typing import TypeVar, Generic, Iterable, Iterator, Mapping, Tuple, overload, Optional, Union

T = TypeVar('T')
KT = TypeVar('KT')
VT = TypeVar('VT')

Any = 0

class object:
    def __init__(self) -> None: pass

class type:
    def __init__(self, x: Any) -> None: pass

class str:
    def __add__(self, other: 'str') -> 'str': pass
    def __rmul__(self, n: int) -> str: ...

class bytes: pass

class tuple(Generic[T]): pass
class slice: pass
class function: pass

class ellipsis: pass

class list(Iterable[T], Generic[T]):
    @overload
    def __init__(self) -> None: pass
    @overload
    def __init__(self, x: Iterable[T]) -> None: pass
    def __iter__(self) -> Iterator[T]: pass
    def __add__(self, x: list[T]) -> list[T]: pass
    def __mul__(self, x: int) -> list[T]: pass
    def __getitem__(self, x: int) -> T: pass
    def append(self, x: T) -> None: pass
    def extend(self, x: Iterable[T]) -> None: pass

class dict(Mapping[KT, VT], Generic[KT, VT]):
    @overload
    def __init__(self, **kwargs: VT) -> None: pass
    @overload
    def __init__(self, arg: Iterable[Tuple[KT, VT]], **kwargs: VT) -> None: pass
    def __setitem__(self, k: KT, v: VT) -> None: pass
    def __getitem__(self, k: KT) -> VT: pass
    def __iter__(self) -> Iterator[KT]: pass
    def update(self, a: Mapping[KT, VT]) -> None: pass
    @overload
    def get(self, k: KT) -> Optional[VT]: pass
    @overload
    def get(self, k: KT, default: Union[KT, T]) -> Union[VT, T]: pass


class int:
    def __float__(self) -> float: ...
    def __int__(self) -> int: ...
    def __mul__(self, x: int) -> int: ...
    def __rmul__(self, x: int) -> int: ...
    def __truediv__(self, x: int) -> int: ...
    def __rtruediv__(self, x: int) -> int: ...

class float:
    def __float__(self) -> float: ...
    def __int__(self) -> int: ...
    def __mul__(self, x: float) -> float: ...
    def __rmul__(self, x: float) -> float: ...
    def __truediv__(self, x: float) -> float: ...
    def __rtruediv__(self, x: float) -> float: ...
