from typing import Generic, Sequence, TypeVar

_T = TypeVar('_T')
_U = TypeVar('_U')

class object:
    def __init__(self) -> None: pass
    def __eq__(self, o: object) -> bool: pass
    def __ne__(self, o: object) -> bool: pass

class type: pass
class ellipsis: pass
class tuple(Generic[_T]): pass
class int: pass
class float: pass
class str: pass
class bool(int): pass
class dict(Generic[_T, _U]): pass
class list(Generic[_T], Sequence[_T]): pass
class function: pass
class classmethod: pass
property = object()
