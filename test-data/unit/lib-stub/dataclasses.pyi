from typing import Any, Callable, Generic, Mapping, Optional, TypeVar, overload, Type, Dict, List, Tuple

_T = TypeVar('_T')

class InitVar(Generic[_T]):
    ...


@overload
def asdict(obj: Any) -> Dict[str, Any]: ...
@overload
def asdict(obj: Any, *, dict_factory: Callable[[List[Tuple[str, Any]]], _T]) -> _T: ...

@overload
def dataclass(_cls: Type[_T]) -> Type[_T]: ...

@overload
def dataclass(*, init: bool = ..., repr: bool = ..., eq: bool = ..., order: bool = ...,
    unsafe_hash: bool = ..., frozen: bool = ...) -> Callable[[Type[_T]], Type[_T]]: ...


@overload
def field(*, default: _T,
    init: bool = ..., repr: bool = ..., hash: Optional[bool] = ..., compare: bool = ...,
    metadata: Optional[Mapping[str, Any]] = ...) -> _T: ...

@overload
def field(*, default_factory: Callable[[], _T],
    init: bool = ..., repr: bool = ..., hash: Optional[bool] = ..., compare: bool = ...,
    metadata: Optional[Mapping[str, Any]] = ...) -> _T: ...

@overload
def field(*,
    init: bool = ..., repr: bool = ..., hash: Optional[bool] = ..., compare: bool = ...,
    metadata: Optional[Mapping[str, Any]] = ...) -> Any: ...
