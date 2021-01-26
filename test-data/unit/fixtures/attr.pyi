# Builtins stub used to support @attr.s tests.
from typing import Union, overload

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

class str: pass
class unicode: pass
class ellipsis: pass
class tuple: pass
