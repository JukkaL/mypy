# builtins stub used in NotImplemented related cases.
from typing import Any, Iterable, Mapping, Generic, TypeVar, cast

Tco = TypeVar('Tco', covariant=True)
T = TypeVar('T')
S = TypeVar('S')

class object:
    def __init__(self) -> None: pass
    def __eq__(self, o: object) -> bool: pass
    def __ne__(self, o: object) -> bool: pass

class dict(Iterable[T], Mapping[T, S], Generic[T, S]): pass
class tuple(Iterable[Tco], Generic[Tco]): pass
class type: pass
class function: pass
class bool: pass
class int: pass
class str: pass
class Sequence_str: pass  # Sequence[str] for testing __dir__
NotImplemented = cast(Any, None)
