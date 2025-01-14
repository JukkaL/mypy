# More complete stub for typing module.
#
# Use [typing fixtures/typing-full.pyi] to use this instead of lib-stub/typing.pyi
# in a particular test case.
#
# Many of the definitions have special handling in the type checker, so they
# can just be initialized to anything.

from abc import abstractmethod, ABCMeta

class GenericMeta(type): pass

class _SpecialForm:
    def __getitem__(self, index: Any) -> Any: ...
    def __or__(self, other): ...
    def __ror__(self, other): ...
class TypeVar:
    def __init__(self, name, *args, bound=None): ...
    def __or__(self, other): ...
class ParamSpec: ...
class TypeVarTuple: ...

def cast(t, o): ...
def assert_type(o, t): ...
overload = 0
Any = object()
Optional = 0
Generic = 0
Protocol = 0
Tuple = 0
_promote = 0
Type = 0
no_type_check = 0
ClassVar = 0
Final = 0
TypedDict = 0
NoReturn = 0
NewType = 0
Self = 0
Unpack = 0
Callable: _SpecialForm
Union: _SpecialForm
Literal: _SpecialForm

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
T_contra = TypeVar('T_contra', contravariant=True)
U = TypeVar('U')
V = TypeVar('V')
S = TypeVar('S')

def final(x: T) -> T: ...

class NamedTuple(tuple[Any, ...]): ...

# Note: definitions below are different from typeshed, variances are declared
# to silence the protocol variance checks. Maybe it is better to use type: ignore?

@runtime_checkable
class Hashable(Protocol, metaclass=ABCMeta):
    @abstractmethod
    def __hash__(self) -> int: pass

@runtime_checkable
class Container(Protocol[T_co]):
    @abstractmethod
    # Use int because bool isn't in the default test builtins
    def __contains__(self, arg: object) -> int: pass

@runtime_checkable
class Sized(Protocol):
    @abstractmethod
    def __len__(self) -> int: pass

@runtime_checkable
class Iterable(Protocol[T_co]):
    @abstractmethod
    def __iter__(self) -> 'Iterator[T_co]': pass

@runtime_checkable
class Iterator(Iterable[T_co], Protocol):
    @abstractmethod
    def __next__(self) -> T_co: pass

class Generator(Iterator[T], Generic[T, U, V]):
    @abstractmethod
    def send(self, value: U) -> T: pass

    @abstractmethod
    def throw(self, typ: Any, val: Any=None, tb: Any=None) -> None: pass

    @abstractmethod
    def close(self) -> None: pass

    @abstractmethod
    def __iter__(self) -> 'Generator[T, U, V]': pass

class AsyncGenerator(AsyncIterator[T], Generic[T, U]):
    @abstractmethod
    def __anext__(self) -> Awaitable[T]: pass

    @abstractmethod
    def asend(self, value: U) -> Awaitable[T]: pass

    @abstractmethod
    def athrow(self, typ: Any, val: Any=None, tb: Any=None) -> Awaitable[T]: pass

    @abstractmethod
    def aclose(self) -> Awaitable[T]: pass

    @abstractmethod
    def __aiter__(self) -> 'AsyncGenerator[T, U]': pass

@runtime_checkable
class Awaitable(Protocol[T]):
    @abstractmethod
    def __await__(self) -> Generator[Any, Any, T]: pass

class AwaitableGenerator(Generator[T, U, V], Awaitable[V], Generic[T, U, V, S], metaclass=ABCMeta):
    pass

class Coroutine(Awaitable[V], Generic[T, U, V]):
    @abstractmethod
    def send(self, value: U) -> T: pass

    @abstractmethod
    def throw(self, typ: Any, val: Any=None, tb: Any=None) -> None: pass

    @abstractmethod
    def close(self) -> None: pass

@runtime_checkable
class AsyncIterable(Protocol[T]):
    @abstractmethod
    def __aiter__(self) -> 'AsyncIterator[T]': pass

@runtime_checkable
class AsyncIterator(AsyncIterable[T], Protocol):
    def __aiter__(self) -> 'AsyncIterator[T]': return self
    @abstractmethod
    def __anext__(self) -> Awaitable[T]: pass

class Sequence(Iterable[T_co], Container[T_co]):
    @abstractmethod
    def __getitem__(self, n: Any) -> T_co: pass

class MutableSequence(Sequence[T]):
    @abstractmethod
    def __setitem__(self, n: Any, o: T) -> None: pass

class Mapping(Iterable[T], Generic[T, T_co], metaclass=ABCMeta):
    def keys(self) -> Iterable[T]: pass  # Approximate return type
    def __getitem__(self, key: T) -> T_co: pass
    @overload
    def get(self, k: T) -> Optional[T_co]: pass
    @overload
    def get(self, k: T, default: Union[T_co, V]) -> Union[T_co, V]: pass
    def values(self) -> Iterable[T_co]: pass  # Approximate return type
    def __len__(self) -> int: ...
    def __contains__(self, arg: object) -> int: pass

class MutableMapping(Mapping[T, U], metaclass=ABCMeta):
    def __setitem__(self, k: T, v: U) -> None: pass

class SupportsInt(Protocol):
    def __int__(self) -> int: pass

class SupportsFloat(Protocol):
    def __float__(self) -> float: pass

class SupportsAbs(Protocol[T_co]):
    def __abs__(self) -> T_co: pass

def runtime_checkable(cls: T) -> T:
    return cls

class ContextManager(Generic[T_co]):
    def __enter__(self) -> T_co: pass
    # Use Any because not all the precise types are in the fixtures.
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> Any: pass

TYPE_CHECKING = 1

# Fallback type for all typed dicts (does not exist at runtime).
class _TypedDict(Mapping[str, object]):
    # Needed to make this class non-abstract. It is explicitly declared abstract in
    # typeshed, but we don't want to import abc here, as it would slow down the tests.
    def __iter__(self) -> Iterator[str]: ...
    def copy(self: T) -> T: ...
    # Using NoReturn so that only calls using the plugin hook can go through.
    def setdefault(self, k: NoReturn, default: object) -> object: ...
    # Mypy expects that 'default' has a type variable type.
    def pop(self, k: NoReturn, default: T = ...) -> object: ...
    def update(self: T, __m: T) -> None: ...
    def __delitem__(self, k: NoReturn) -> None: ...

def dataclass_transform(
    *,
    eq_default: bool = ...,
    order_default: bool = ...,
    kw_only_default: bool = ...,
    field_specifiers: tuple[type[Any] | Callable[..., Any], ...] = ...,
    **kwargs: Any,
) -> Callable[[T], T]: ...
def override(__arg: T) -> T: ...

def get_args(tp: T) -> T: ...

# Was added in 3.11
def reveal_type(__obj: T) -> T: ...

# Only exists in type checking time:
def type_check_only(__func_or_class: T) -> T: ...

# Was added in 3.12
@final
class TypeAliasType:
    def __init__(
        self, name: str, value: Any, *, type_params: Tuple[Union[TypeVar, ParamSpec, TypeVarTuple], ...] = ()
    ) -> None: ...

    def __or__(self, other: Any) -> Any: ...
    def __ror__(self, other: Any) -> Any: ...
