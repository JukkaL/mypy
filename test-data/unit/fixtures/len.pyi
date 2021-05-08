from typing import Tuple, TypeVar, Generic, Union, Any, Type, Sequence
from typing_extensions import Protocol

T = TypeVar('T')

class object:
    def __init__(self) -> None: pass

class type:
    def __init__(self, x) -> None: pass

class tuple(Generic[T]):
    def __len__(self) -> int: pass

class list(Sequence[T]): pass

class function: pass

class Sized(Protocol):
    def __len__(self) -> int: pass

def len(__obj: Sized) -> int: ...
def isinstance(x: object, t: Union[Type[object], Tuple[Type[object], ...]]) -> bool: pass

class int:
    def __add__(self, other: 'int') -> 'int': pass
    def __eq__(self, other: 'int') -> 'bool': pass
    def __ne__(self, other: 'int') -> 'bool': pass
    def __lt__(self, n: 'int') -> 'bool': pass
    def __gt__(self, n: 'int') -> 'bool': pass
    def __le__(self, n: 'int') -> 'bool': pass
    def __ge__(self, n: 'int') -> 'bool': pass
class float: pass
class bool(int): pass
class str:
    def __add__(self, other: 'str') -> 'str': pass
    def __len__(self) -> int: pass
class ellipsis: pass
