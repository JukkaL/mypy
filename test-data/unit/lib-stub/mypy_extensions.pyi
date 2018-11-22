# NOTE: Requires fixtures/dict.pyi
from typing import Dict, Type, TypeVar, Optional, Any, Generic, Mapping
import sys

_T = TypeVar('_T')
_U = TypeVar('_U')


def Arg(type: _T = ..., name: Optional[str] = ...) -> _T: ...

def DefaultArg(type: _T = ..., name: Optional[str] = ...) -> _T: ...

def NamedArg(type: _T = ..., name: Optional[str] = ...) -> _T: ...

def DefaultNamedArg(type: _T = ..., name: Optional[str] = ...) -> _T: ...

def VarArg(type: _T = ...) -> _T: ...

def KwArg(type: _T = ...) -> _T: ...


# Fallback type for all typed dicts (does not exist at runtime)
class _TypedDict(Mapping[str, object]):
    def copy(self: _T) -> _T: ...
    def setdefault(self, k: str, default: object) -> object: ...
    def pop(self, k: str, default: _T = ...) -> object: ...
    def update(self, __m: Mapping[str, object]) -> None: ...
    if sys.version_info[0] == 2:
        def has_key(self) -> bool: ...
    def __delitem__(self, k: str) -> None: ...

def TypedDict(typename: str, fields: Dict[str, Type[_T]], *, total: Any = ...) -> Type[dict]: ...

# This is intended as a class decorator, but mypy rejects abstract classes
# when a Type[_T] is expected, so we can't give it the type we want
def trait(cls: Any) -> Any: ...

class NoReturn: pass

class FlexibleAlias(Generic[_T, _U]): ...
