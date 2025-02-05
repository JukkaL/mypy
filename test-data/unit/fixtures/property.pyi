import typing

_T = typing.TypeVar('_T')

class object:
    def __init__(self) -> None: pass

class type:
    def __init__(self, x: typing.Any) -> None: pass

class function: pass

class property: pass  # Dummy definition
class classmethod: pass

class list(typing.Generic[_T]): pass
class dict: pass
class int: pass
class float: pass
class str: pass
class bytes: pass
class bool: pass
class ellipsis: pass

class tuple(typing.Generic[_T]): pass
