# Test stub for typing module that includes TypedDict related things.
#
# Use [typing fixtures/typing-typeddict.pyi] to use this instead of lib-stub/typing.pyi
# in a particular test case.
#
# Many of the definitions have special handling in the type checker, so they
# can just be initialized to anything.

from abc import ABCMeta

cast = 0
overload = 0
Any = 0
Union = 0
Optional = 0
TypeVar = 0
Generic = 0
Protocol = 0
Tuple = 0
Callable = 0
NamedTuple = 0
Final = 0
Literal = 0
TypedDict = 0
NoReturn = 0
Required = 0
NotRequired = 0

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)
V = TypeVar('V')

# Note: definitions below are different from typeshed, variances are declared
# to silence the protocol variance checks. Maybe it is better to use type: ignore?

class Sized(Protocol):
    def __len__(self) -> int: pass

class Iterable(Protocol[T_co]):
    def __iter__(self) -> 'Iterator[T_co]': pass

class Iterator(Iterable[T_co], Protocol):
    def __next__(self) -> T_co: pass

class Sequence(Iterable[T_co]):
    def __getitem__(self, n: Any) -> T_co: pass

class Mapping(Iterable[T], Generic[T, T_co], metaclass=ABCMeta):
    def __getitem__(self, key: T) -> T_co: pass
    @overload
    def get(self, k: T) -> Optional[T_co]: pass
    @overload
    def get(self, k: T, default: Union[T_co, V]) -> Union[T_co, V]: pass
    def values(self) -> Iterable[T_co]: pass  # Approximate return type
    def __len__(self) -> int: ...
    def __contains__(self, arg: object) -> int: pass

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
