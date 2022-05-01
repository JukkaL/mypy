from Queue import Queue
from typing import Any

families: list[None]

class Connection(object):
    _in: Any
    _out: Any
    recv: Any
    recv_bytes: Any
    send: Any
    send_bytes: Any
    def __init__(self, _in, _out) -> None: ...
    def close(self) -> None: ...
    def poll(self, timeout=...) -> Any: ...

class Listener(object):
    _backlog_queue: Queue[Any] | None
    address: Any
    def __init__(self, address=..., family=..., backlog=...) -> None: ...
    def accept(self) -> Connection: ...
    def close(self) -> None: ...

def Client(address) -> Connection: ...
def Pipe(duplex=...) -> tuple[Connection, Connection]: ...
