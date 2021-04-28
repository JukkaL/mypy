# Builtins stub used to support *args, **kwargs.

from typing import TypeVar, Generic, Iterable, Sequence, Tuple, Dict, Any, overload, Mapping

Tco = TypeVar('Tco', covariant=True)
T = TypeVar('T')
S = TypeVar('S')

class object:
    def __init__(self) -> None: pass
    def __eq__(self, o: object) -> bool: pass
    def __ne__(self, o: object) -> bool: pass

class type:
    @overload
    def __init__(self, o: object) -> None: pass
    @overload
    def __init__(self, name: str, bases: Tuple[type, ...], dict: Dict[str, Any]) -> None: pass
    def __call__(self, *args: Any, **kwargs: Any) -> Any: pass

class tuple(Iterable[Tco], Generic[Tco]): pass

class dict(Iterable[T], Mapping[T, S], Generic[T, S]): pass

class list(Generic[T], Sequence[T]): pass

class int:
    def __eq__(self, o: object) -> bool: pass
class str: pass
class bool: pass
class function: pass
class ellipsis: pass
