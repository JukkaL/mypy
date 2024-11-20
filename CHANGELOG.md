# Mypy Release Notes

## Next release

### Change to enum membership semantics

As per the updated [typing specification for enums](https://typing.readthedocs.io/en/latest/spec/enums.html#defining-members),
enum members must be left unannotated.

```python
class Pet(Enum):
    CAT = 1  # Member attribute
    DOG = 2  # Member attribute
    WOLF: int = 3  # New error: Enum members must be left unannotated

    species: str  # Considered a non-member attribute
```

In particular, the specification change can result in issues in type stubs (`.pyi` files), since
historically it was common to leave the value absent:

```python
# In a type stub (.pyi file)

class Pet(Enum):
    # Change in semantics: previously considered members, now non-member attributes
    CAT: int
    DOG: int

    # Mypy will now issue a warning if it detects this situation in type stubs:
    # > Detected enum "Pet" in a type stub with zero members.
    # > There is a chance this is due to a recent change in the semantics of enum membership.
    # > If so, use `member = value` to mark an enum member, instead of `member: type`

class Pet(Enum):
    # As per the specification, you should now do one of the following:
    DOG = 1  # Member attribute with value 1 and known type
    WOLF = cast(int, ...)  # Member attribute with unknown value but known type
    LION = ...  # Member attribute with unknown value and unknown type
```

Contributed by Terence Honles in PR [17207](https://github.com/python/mypy/pull/17207) and
Shantanu Jain in PR [18068](https://github.com/python/mypy/pull/18068).

## Mypy 1.13

We’ve just uploaded mypy 1.13 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)).
Mypy is a static type checker for Python. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

Note that unlike typical releases, Mypy 1.13 does not have any changes to type checking semantics
from 1.12.1.

### Improved performance

Mypy 1.13 contains several performance improvements. Users can expect mypy to be 5-20% faster.
In environments with long search paths (such as environments using many editable installs), mypy
can be significantly faster, e.g. 2.2x faster in the use case targeted by these improvements.

Mypy 1.13 allows use of the `orjson` library for handling the cache instead of the stdlib `json`,
for improved performance. You can ensure the presence of `orjson` using the `faster-cache` extra:

    python3 -m pip install -U mypy[faster-cache]

Mypy may depend on `orjson` by default in the future.

These improvements were contributed by Shantanu.

List of changes:
* Significantly speed up file handling error paths (Shantanu, PR [17920](https://github.com/python/mypy/pull/17920))
* Use fast path in modulefinder more often (Shantanu, PR [17950](https://github.com/python/mypy/pull/17950))
* Let mypyc optimise os.path.join (Shantanu, PR [17949](https://github.com/python/mypy/pull/17949))
* Make is_sub_path faster (Shantanu, PR [17962](https://github.com/python/mypy/pull/17962))
* Speed up stubs suggestions (Shantanu, PR [17965](https://github.com/python/mypy/pull/17965))
* Use sha1 for hashing (Shantanu, PR [17953](https://github.com/python/mypy/pull/17953))
* Use orjson instead of json, when available (Shantanu, PR [17955](https://github.com/python/mypy/pull/17955))
* Add faster-cache extra, test in CI (Shantanu, PR [17978](https://github.com/python/mypy/pull/17978))

### Acknowledgements
Thanks to all mypy contributors who contributed to this release:

- Shantanu Jain
- Jukka Lehtosalo

## Mypy 1.12

We’ve just uploaded mypy 1.12 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type
checker for Python. This release includes new features, performance improvements and bug fixes.
You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Support Python 3.12 Syntax for Generics (PEP 695)

Support for the new type parameter syntax introduced in Python 3.12 is now enabled by default,
documented, and no longer experimental. It was available through a feature flag in
mypy 1.11 as an experimental feature.

This example demonstrates the new syntax:

```python
# Generic function
def f[T](x: T) -> T: ...

reveal_type(f(1))  # Revealed type is 'int'

# Generic class
class C[T]:
    def __init__(self, x: T) -> None:
       self.x = x

c = C('a')
reveal_type(c.x)  # Revealed type is 'str'

# Type alias
type A[T] = C[list[T]]
```

For more information, refer to the [documentation](https://mypy.readthedocs.io/en/latest/generics.html).

These improvements are included:

 * Document Python 3.12 type parameter syntax (Jukka Lehtosalo, PR [17816](https://github.com/python/mypy/pull/17816))
 * Further documentation updates (Jukka Lehtosalo, PR [17826](https://github.com/python/mypy/pull/17826))
 * Allow Self return types with contravariance (Jukka Lehtosalo, PR [17786](https://github.com/python/mypy/pull/17786))
 * Enable new type parameter syntax by default (Jukka Lehtosalo, PR [17798](https://github.com/python/mypy/pull/17798))
 * Generate error if new-style type alias used as base class (Jukka Lehtosalo, PR [17789](https://github.com/python/mypy/pull/17789))
 * Inherit variance if base class has explicit variance (Jukka Lehtosalo, PR [17787](https://github.com/python/mypy/pull/17787))
 * Fix crash on invalid type var reference (Jukka Lehtosalo, PR [17788](https://github.com/python/mypy/pull/17788))
 * Fix covariance of frozen dataclasses (Jukka Lehtosalo, PR [17783](https://github.com/python/mypy/pull/17783))
 * Allow covariance with attribute that has "`_`" name prefix (Jukka Lehtosalo, PR [17782](https://github.com/python/mypy/pull/17782))
 * Support `Annotated[...]` in new-style type aliases (Jukka Lehtosalo, PR [17777](https://github.com/python/mypy/pull/17777))
 * Fix nested generic classes (Jukka Lehtosalo, PR [17776](https://github.com/python/mypy/pull/17776))
 * Add detection and error reporting for the use of incorrect expressions within the scope of a type parameter and a type alias (Kirill Podoprigora, PR [17560](https://github.com/python/mypy/pull/17560))

### Basic Support for Python 3.13

This release adds partial support for Python 3.13 features and compiled binaries for
Python 3.13. Mypyc now also supports Python 3.13.

In particular, these features are supported:
 * Various new stdlib features and changes (through typeshed stub improvements)
 * `typing.ReadOnly` (see below for more)
 * `typing.TypeIs` (added in mypy 1.10, [PEP 742](https://peps.python.org/pep-0742/))
 * Type parameter defaults when using the legacy syntax ([PEP 696](https://peps.python.org/pep-0696/))

These features are not supported yet:
 * `warnings.deprecated` ([PEP 702](https://peps.python.org/pep-0702/))
 * Type parameter defaults when using Python 3.12 type parameter syntax

### Mypyc Support for Python 3.13

Mypyc now supports Python 3.13. This was contributed by Marc Mueller, with additional
fixes by Jukka Lehtosalo. Free threaded Python 3.13 builds are not supported yet.

List of changes:

 * Add additional includes for Python 3.13 (Marc Mueller, PR [17506](https://github.com/python/mypy/pull/17506))
 * Add another include for Python 3.13 (Marc Mueller, PR [17509](https://github.com/python/mypy/pull/17509))
 * Fix ManagedDict functions for Python 3.13 (Marc Mueller, PR [17507](https://github.com/python/mypy/pull/17507))
 * Update mypyc test output for Python 3.13 (Marc Mueller, PR [17508](https://github.com/python/mypy/pull/17508))
 * Fix `PyUnicode` functions for Python 3.13 (Marc Mueller, PR [17504](https://github.com/python/mypy/pull/17504))
 * Fix `_PyObject_LookupAttrId` for Python 3.13 (Marc Mueller, PR [17505](https://github.com/python/mypy/pull/17505))
 * Fix `_PyList_Extend` for Python 3.13 (Marc Mueller, PR [17503](https://github.com/python/mypy/pull/17503))
 * Fix `gen_is_coroutine` for Python 3.13 (Marc Mueller, PR [17501](https://github.com/python/mypy/pull/17501))
 * Fix `_PyObject_FastCall` for Python 3.13 (Marc Mueller, PR [17502](https://github.com/python/mypy/pull/17502))
 * Avoid uses of `_PyObject_CallMethodOneArg` on 3.13 (Jukka Lehtosalo, PR [17526](https://github.com/python/mypy/pull/17526))
 * Don't rely on `_PyType_CalculateMetaclass` on 3.13 (Jukka Lehtosalo, PR [17525](https://github.com/python/mypy/pull/17525))
 * Don't use `_PyUnicode_FastCopyCharacters` on 3.13 (Jukka Lehtosalo, PR [17524](https://github.com/python/mypy/pull/17524))
 * Don't use `_PyUnicode_EQ` on 3.13, as it's no longer exported (Jukka Lehtosalo, PR [17523](https://github.com/python/mypy/pull/17523))

### Inferring Unions for Conditional Expressions

Mypy now always tries to infer a union type for a conditional expression if left and right
operand types are different. This results in more precise inferred types and lets mypy detect
more issues. Example:

```python
s = "foo" if cond() else 1
# Type of "s" is now "str | int" (it used to be "object")
```

Notably, if one of the operands has type `Any`, the type of a conditional expression is
now `<type> | Any`. Previously the inferred type was just `Any`. The new type essentially
indicates that the value can be of type `<type>`, and potentially of some (unknown) type.
Most operations performed on the result must also be valid for `<type>`.
Example where this is relevant:

```python
from typing import Any

def func(a: Any, b: bool) -> None:
    x = a if b else None
    # Type of x is "Any | None"
    print(x.y)  # Error: None has no attribute "y"
```

This feature was contributed by Ivan Levkivskyi (PR [17427](https://github.com/python/mypy/pull/17427)).

### ReadOnly Support for TypedDict (PEP 705)

You can now use `typing.ReadOnly` to specity TypedDict items as
read-only ([PEP 705](https://peps.python.org/pep-0705/)):

```python
from typing import TypedDict

# Or "from typing ..." on Python 3.13
from typing_extensions import ReadOnly

class TD(TypedDict):
    a: int
    b: ReadOnly[int]

d: TD = {"a": 1, "b": 2}
d["a"] = 3  # OK
d["b"] = 5  # Error: "b" is ReadOnly
```

This feature was contributed by Nikita Sobolev (PR [17644](https://github.com/python/mypy/pull/17644)).

### Python 3.8 End of Life Approaching

We are planning to drop support for Python 3.8 in the next mypy feature release or the
one after that. Python 3.8 reaches end of life in October 2024.

### Planned Changes to Defaults

We are planning to enable `--local-partial-types` by default in mypy 2.0. This will
often require at least minor code changes. This option is implicitly enabled by mypy
daemon, so this makes the behavior of daemon and non-daemon modes consistent.

We recommend that mypy users start using local partial types soon (or to explicitly disable
them) to prepare for the change.

This can also be configured in a mypy configuration file:

```
local_partial_types = True
```

For more information, refer to the
[documentation](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-local-partial-types).

### Documentation Updates

Mypy documentation now uses modern syntax variants and imports in many examples. Some
examples no longer work on Python 3.8, which is the earliest Python version that mypy supports.

Notably, `Iterable` and other protocols/ABCs are imported from `collections.abc` instead of
`typing`:
```python
from collections.abc import Iterable, Callable
```

Examples also avoid the upper-case aliases to built-in types: `list[str]` is used instead
of `List[str]`. The `X | Y` union type syntax introduced in Python 3.10 is also now prevalent.

List of documentation updates:

 * Document `--output=json` CLI option (Edgar Ramírez Mondragón, PR [17611](https://github.com/python/mypy/pull/17611))
 * Update various references to deprecated type aliases in docs (Jukka Lehtosalo, PR [17829](https://github.com/python/mypy/pull/17829))
 * Make "X | Y" union syntax more prominent in documentation (Jukka Lehtosalo, PR [17835](https://github.com/python/mypy/pull/17835))
 * Discuss upper bounds before self types in documentation (Jukka Lehtosalo, PR [17827](https://github.com/python/mypy/pull/17827))
 * Make changelog visible in mypy documentation (quinn-sasha, PR [17742](https://github.com/python/mypy/pull/17742))
 * List all incomplete features in `--enable-incomplete-feature` docs (sobolevn, PR [17633](https://github.com/python/mypy/pull/17633))
 * Remove the explicit setting of a pygments theme (Pradyun Gedam, PR [17571](https://github.com/python/mypy/pull/17571))
 * Document ReadOnly with TypedDict (Jukka Lehtosalo, PR [17905](https://github.com/python/mypy/pull/17905))
 * Document TypeIs (Chelsea Durazo, PR [17821](https://github.com/python/mypy/pull/17821))

### Experimental Inline TypedDict Syntax

Mypy now supports a non-standard, experimental syntax for defining anonymous TypedDicts.
Example:

```python
def func(n: str, y: int) -> {"name": str, "year": int}:
    return {"name": n, "year": y}
```

The feature is disabled by default. Use `--enable-incomplete-feature=InlineTypedDict` to
enable it. *We might remove this feature in a future release.*

This feature was contributed by Ivan Levkivskyi (PR [17457](https://github.com/python/mypy/pull/17457)).

### Stubgen Improvements

 * Fix crash on literal class-level keywords (sobolevn, PR [17663](https://github.com/python/mypy/pull/17663))
 * Stubgen add `--version` (sobolevn, PR [17662](https://github.com/python/mypy/pull/17662))
 * Fix `stubgen --no-analysis/--parse-only` docs (sobolevn, PR [17632](https://github.com/python/mypy/pull/17632))
 * Include keyword only args when generating signatures in stubgenc (Eric Mark Martin, PR [17448](https://github.com/python/mypy/pull/17448))
 * Add support for detecting `Literal` types when extracting types from docstrings (Michael Carlstrom, PR [17441](https://github.com/python/mypy/pull/17441))
 * Use `Generator` type var defaults (Sebastian Rittau, PR [17670](https://github.com/python/mypy/pull/17670))

### Stubtest Improvements
 * Add support for `cached_property` (Ali Hamdan, PR [17626](https://github.com/python/mypy/pull/17626))
 * Add `enable_incomplete_feature` validation to `stubtest` (sobolevn, PR [17635](https://github.com/python/mypy/pull/17635))
 * Fix error code handling in `stubtest` with `--mypy-config-file` (sobolevn, PR [17629](https://github.com/python/mypy/pull/17629))

### Other Notables Fixes and Improvements

 * Report error if using unsupported type parameter defaults (Jukka Lehtosalo, PR [17876](https://github.com/python/mypy/pull/17876))
 * Fix re-processing cross-reference in mypy daemon when node kind changes (Ivan Levkivskyi, PR [17883](https://github.com/python/mypy/pull/17883))
 * Don't use equality to narrow when value is IntEnum/StrEnum (Jukka Lehtosalo, PR [17866](https://github.com/python/mypy/pull/17866))
 * Don't consider None vs IntEnum comparison ambiguous (Jukka Lehtosalo, PR [17877](https://github.com/python/mypy/pull/17877))
 * Fix narrowing of IntEnum and StrEnum types (Jukka Lehtosalo, PR [17874](https://github.com/python/mypy/pull/17874))
 * Filter overload items based on self type during type inference (Jukka Lehtosalo, PR [17873](https://github.com/python/mypy/pull/17873))
 * Enable negative narrowing of union TypeVar upper bounds (Brian Schubert, PR [17850](https://github.com/python/mypy/pull/17850))
 * Fix issue with member expression formatting (Brian Schubert, PR [17848](https://github.com/python/mypy/pull/17848))
 * Avoid type size explosion when expanding types (Jukka Lehtosalo, PR [17842](https://github.com/python/mypy/pull/17842))
 * Fix negative narrowing of tuples in match statement (Brian Schubert, PR [17817](https://github.com/python/mypy/pull/17817))
 * Narrow falsey str/bytes/int to literal type (Brian Schubert, PR [17818](https://github.com/python/mypy/pull/17818))
 * Test against latest Python 3.13, make testing 3.14 easy (Shantanu, PR [17812](https://github.com/python/mypy/pull/17812))
 * Reject ParamSpec-typed callables calls with insufficient arguments (Stanislav Terliakov, PR [17323](https://github.com/python/mypy/pull/17323))
 * Fix crash when passing too many type arguments to generic base class accepting single ParamSpec (Brian Schubert, PR [17770](https://github.com/python/mypy/pull/17770))
 * Fix TypeVar upper bounds sometimes not being displayed in pretty callables (Brian Schubert, PR [17802](https://github.com/python/mypy/pull/17802))
 * Added error code for overlapping function signatures (Katrina Connors, PR [17597](https://github.com/python/mypy/pull/17597))
 * Check for `truthy-bool` in `not ...` unary expressions (sobolevn, PR [17773](https://github.com/python/mypy/pull/17773))
 * Add missing lines-covered and lines-valid attributes (Soubhik Kumar Mitra, PR [17738](https://github.com/python/mypy/pull/17738))
 * Fix another crash scenario with recursive tuple types (Ivan Levkivskyi, PR [17708](https://github.com/python/mypy/pull/17708))
 * Resolve TypeVar upper bounds in `functools.partial` (Shantanu, PR [17660](https://github.com/python/mypy/pull/17660))
 * Always reset binder when checking deferred nodes (Ivan Levkivskyi, PR [17643](https://github.com/python/mypy/pull/17643))
 * Fix crash on a callable attribute with single unpack (Ivan Levkivskyi, PR [17641](https://github.com/python/mypy/pull/17641))
 * Fix mismatched signature between checker plugin API and implementation (bzoracler, PR [17343](https://github.com/python/mypy/pull/17343))
 * Indexing a type also produces a GenericAlias (Shantanu, PR [17546](https://github.com/python/mypy/pull/17546))
 * Fix crash on self-type in callable protocol (Ivan Levkivskyi, PR [17499](https://github.com/python/mypy/pull/17499))
 * Fix crash on NamedTuple with method and error in function (Ivan Levkivskyi, PR [17498](https://github.com/python/mypy/pull/17498))
 * Add `__replace__` for dataclasses in 3.13 (Max Muoto, PR [17469](https://github.com/python/mypy/pull/17469))
 * Fix help message for `--no-namespace-packages` (Raphael Krupinski, PR [17472](https://github.com/python/mypy/pull/17472))
 * Fix typechecking for async generators (Danny Yang, PR [17452](https://github.com/python/mypy/pull/17452))
 * Fix strict optional handling in attrs plugin (Ivan Levkivskyi, PR [17451](https://github.com/python/mypy/pull/17451))
 * Allow mixing ParamSpec and TypeVarTuple in Generic (Ivan Levkivskyi, PR [17450](https://github.com/python/mypy/pull/17450))
 * Improvements to `functools.partial` of types (Shantanu, PR [17898](https://github.com/python/mypy/pull/17898))
 * Make ReadOnly TypedDict items covariant (Jukka Lehtosalo, PR [17904](https://github.com/python/mypy/pull/17904))
 * Fix union callees with `functools.partial` (Jukka Lehtosalo, PR [17903](https://github.com/python/mypy/pull/17903))
 * Improve handling of generic functions with `functools.partial` (Ivan Levkivskyi, PR [17925](https://github.com/python/mypy/pull/17925))

### Typeshed Updates

Please see [git log](https://github.com/python/typeshed/commits/main?after=91a58b07cdd807b1d965e04ba85af2adab8bf924+0&branch=main&path=stdlib) for full list of standard library typeshed stub changes.

### Mypy 1.12.1
 * Fix crash when showing partially analyzed type in error message (Ivan Levkivskyi, PR [17961](https://github.com/python/mypy/pull/17961))
 * Fix iteration over union (when self type is involved) (Shantanu, PR [17976](https://github.com/python/mypy/pull/17976))
 * Fix type object with type var default in union context (Jukka Lehtosalo, PR [17991](https://github.com/python/mypy/pull/17991))
 * Revert change to `os.path` stubs affecting use of `os.PathLike[Any]` (Shantanu, PR [17995](https://github.com/python/mypy/pull/17995))

### Acknowledgements
Thanks to all mypy contributors who contributed to this release:

- Ali Hamdan
- Anders Kaseorg
- Bénédikt Tran
- Brian Schubert
- bzoracler
- Chelsea Durazo
- Danny Yang
- Edgar Ramírez Mondragón
- Eric Mark Martin
- InSync
- Ivan Levkivskyi
- Jordandev678
- Katrina Connors
- Kirill Podoprigora
- Marc Mueller
- Max Muoto
- Max Murin
- Michael Carlstrom
- Michael I Chen
- Pradyun Gedam
- quinn-sasha
- Raphael Krupinski
- Sebastian Rittau
- Shantanu
- sobolevn
- Soubhik Kumar Mitra
- Stanislav Terliakov
- wyattscarpenter

I’d also like to thank my employer, Dropbox, for supporting mypy development.


## Mypy 1.11

We’ve just uploaded mypy 1.11 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Support Python 3.12 Syntax for Generics (PEP 695)

Mypy now supports the new type parameter syntax introduced in Python 3.12 ([PEP 695](https://peps.python.org/pep-0695/)).
This feature is still experimental and must be enabled with the `--enable-incomplete-feature=NewGenericSyntax` flag, or with `enable_incomplete_feature = NewGenericSyntax` in the mypy configuration file.
We plan to enable this by default in the next mypy feature release.

This example demonstrates the new syntax:

```python
# Generic function
def f[T](x: T) -> T: ...

reveal_type(f(1))  # Revealed type is 'int'

# Generic class
class C[T]:
    def __init__(self, x: T) -> None:
       self.x = x

c = C('a')
reveal_type(c.x)  # Revealed type is 'str'

# Type alias
type A[T] = C[list[T]]
```

This feature was contributed by Jukka Lehtosalo.


### Support for `functools.partial`

Mypy now type checks uses of `functools.partial`. Previously mypy would accept arbitrary arguments.

This example will now produce an error:

```python
from functools import partial

def f(a: int, b: str) -> None: ...

g = partial(f, 1)

# Argument has incompatible type "int"; expected "str"
g(11)
```

This feature was contributed by Shantanu (PR [16939](https://github.com/python/mypy/pull/16939)).


### Stricter Checks for Untyped Overrides

Past mypy versions didn't check if untyped methods were compatible with overridden methods. This would result in false negatives. Now mypy performs these checks when using `--check-untyped-defs`.

For example, this now generates an error if using `--check-untyped-defs`:

```python
class Base:
    def f(self, x: int = 0) -> None: ...

class Derived(Base):
    # Signature incompatible with "Base"
    def f(self): ...
```

This feature was contributed by Steven Troxler (PR [17276](https://github.com/python/mypy/pull/17276)).


### Type Inference Improvements

The new polymorphic inference algorithm introduced in mypy 1.5 is now used in more situations. This improves type inference involving generic higher-order functions, in particular.

This feature was contributed by Ivan Levkivskyi (PR [17348](https://github.com/python/mypy/pull/17348)).

Mypy now uses unions of tuple item types in certain contexts to enable more precise inferred types. Example:

```python
for x in (1, 'x'):
    # Previously inferred as 'object'
    reveal_type(x)  # Revealed type is 'int | str'
```

This was also contributed by Ivan Levkivskyi (PR [17408](https://github.com/python/mypy/pull/17408)).


### Improvements to Detection of Overlapping Overloads

The details of how mypy checks if two `@overload` signatures are unsafely overlapping were overhauled. This both fixes some false positives, and allows mypy to detect additional unsafe signatures.

This feature was contributed by Ivan Levkivskyi (PR [17392](https://github.com/python/mypy/pull/17392)).


### Better Support for Type Hints in Expressions

Mypy now allows more expressions that evaluate to valid type annotations in all expression contexts. The inferred types of these expressions are also sometimes more precise. Previously they were often `object`.

This example uses a union type that includes a callable type as an expression, and it no longer generates an error:

```python
from typing import Callable

print(Callable[[], int] | None)  # No error
```

This feature was contributed by Jukka Lehtosalo (PR [17404](https://github.com/python/mypy/pull/17404)).


### Mypyc Improvements

Mypyc now supports the new syntax for generics introduced in Python 3.12 (see above). Another notable improvement is signficantly faster basic operations on `int` values.

 * Support Python 3.12 syntax for generic functions and classes (Jukka Lehtosalo, PR [17357](https://github.com/python/mypy/pull/17357))
 * Support Python 3.12 type alias syntax (Jukka Lehtosalo, PR [17384](https://github.com/python/mypy/pull/17384))
 * Fix ParamSpec (Shantanu, PR [17309](https://github.com/python/mypy/pull/17309))
 * Inline fast paths of integer unboxing operations (Jukka Lehtosalo, PR [17266](https://github.com/python/mypy/pull/17266))
 * Inline tagged integer arithmetic and bitwise operations (Jukka Lehtosalo, PR [17265](https://github.com/python/mypy/pull/17265))
 * Allow specifying primitives as pure (Jukka Lehtosalo, PR [17263](https://github.com/python/mypy/pull/17263))


### Changes to Stubtest
 * Ignore `_ios_support` (Alex Waygood, PR [17270](https://github.com/python/mypy/pull/17270))
 * Improve support for Python 3.13 (Shantanu, PR [17261](https://github.com/python/mypy/pull/17261))


### Changes to Stubgen
 * Gracefully handle invalid `Optional` and recognize aliases to PEP 604 unions (Ali Hamdan, PR [17386](https://github.com/python/mypy/pull/17386))
 * Fix for Python 3.13 (Jelle Zijlstra, PR [17290](https://github.com/python/mypy/pull/17290))
 * Preserve enum value initialisers (Shantanu, PR [17125](https://github.com/python/mypy/pull/17125))


### Miscellaneous New Features
 * Add error format support and JSON output option via `--output json` (Tushar Sadhwani, PR [11396](https://github.com/python/mypy/pull/11396))
 * Support `enum.member` in Python 3.11+ (Nikita Sobolev, PR [17382](https://github.com/python/mypy/pull/17382))
 * Support `enum.nonmember` in Python 3.11+ (Nikita Sobolev, PR [17376](https://github.com/python/mypy/pull/17376))
 * Support `namedtuple.__replace__` in Python 3.13 (Shantanu, PR [17259](https://github.com/python/mypy/pull/17259))
 * Support `rename=True` in collections.namedtuple (Jelle Zijlstra, PR [17247](https://github.com/python/mypy/pull/17247))
 * Add support for `__spec__` (Shantanu, PR [14739](https://github.com/python/mypy/pull/14739))


### Changes to Error Reporting
 * Mention `--enable-incomplete-feature=NewGenericSyntax` in messages (Shantanu, PR [17462](https://github.com/python/mypy/pull/17462))
 * Do not report plugin-generated methods with `explicit-override` (sobolevn, PR [17433](https://github.com/python/mypy/pull/17433))
 * Use and display namespaces for function type variables (Ivan Levkivskyi, PR [17311](https://github.com/python/mypy/pull/17311))
 * Fix false positive for Final local scope variable in Protocol (GiorgosPapoutsakis, PR [17308](https://github.com/python/mypy/pull/17308))
 * Use Never in more messages, use ambiguous in join (Shantanu, PR [17304](https://github.com/python/mypy/pull/17304))
 * Log full path to config file in verbose output (dexterkennedy, PR [17180](https://github.com/python/mypy/pull/17180))
 * Added `[prop-decorator]` code for unsupported property decorators (#14461) (Christopher Barber, PR [16571](https://github.com/python/mypy/pull/16571))
 * Suppress second error message with `:=` and `[truthy-bool]` (Nikita Sobolev, PR [15941](https://github.com/python/mypy/pull/15941))
 * Generate error for assignment of functional Enum to variable of different name (Shantanu, PR [16805](https://github.com/python/mypy/pull/16805))
 * Fix error reporting on cached run after uninstallation of third party library (Shantanu, PR [17420](https://github.com/python/mypy/pull/17420))


### Fixes for Crashes
 * Fix daemon crash on invalid type in TypedDict (Ivan Levkivskyi, PR [17495](https://github.com/python/mypy/pull/17495))
 * Fix crash and bugs related to `partial()` (Ivan Levkivskyi, PR [17423](https://github.com/python/mypy/pull/17423))
 * Fix crash when overriding with unpacked TypedDict (Ivan Levkivskyi, PR [17359](https://github.com/python/mypy/pull/17359))
 * Fix crash on TypedDict unpacking for ParamSpec (Ivan Levkivskyi, PR [17358](https://github.com/python/mypy/pull/17358))
 * Fix crash involving recursive union of tuples (Ivan Levkivskyi, PR [17353](https://github.com/python/mypy/pull/17353))
 * Fix crash on invalid callable property override (Ivan Levkivskyi, PR [17352](https://github.com/python/mypy/pull/17352))
 * Fix crash on unpacking self in NamedTuple (Ivan Levkivskyi, PR [17351](https://github.com/python/mypy/pull/17351))
 * Fix crash on recursive alias with an optional type (Ivan Levkivskyi, PR [17350](https://github.com/python/mypy/pull/17350))
 * Fix crash on type comment inside generic definitions (Bénédikt Tran, PR [16849](https://github.com/python/mypy/pull/16849))


### Changes to Documentation
 * Use inline config in documentation for optional error codes (Shantanu, PR [17374](https://github.com/python/mypy/pull/17374))
 * Use lower-case generics in documentation (Seo Sanghyeon, PR [17176](https://github.com/python/mypy/pull/17176))
 * Add documentation for show-error-code-links (GiorgosPapoutsakis, PR [17144](https://github.com/python/mypy/pull/17144))
 * Update CONTRIBUTING.md to include commands for Windows (GiorgosPapoutsakis, PR [17142](https://github.com/python/mypy/pull/17142))


### Other Notable Improvements and Fixes
 * Fix ParamSpec inference against TypeVarTuple (Ivan Levkivskyi, PR [17431](https://github.com/python/mypy/pull/17431))
 * Fix explicit type for `partial` (Ivan Levkivskyi, PR [17424](https://github.com/python/mypy/pull/17424))
 * Always allow lambda calls (Ivan Levkivskyi, PR [17430](https://github.com/python/mypy/pull/17430))
 * Fix isinstance checks with PEP 604 unions containing None (Shantanu, PR [17415](https://github.com/python/mypy/pull/17415))
 * Fix self-referential upper bound in new-style type variables (Ivan Levkivskyi, PR [17407](https://github.com/python/mypy/pull/17407))
 * Consider overlap between instances and callables (Ivan Levkivskyi, PR [17389](https://github.com/python/mypy/pull/17389))
 * Allow new-style self-types in classmethods (Ivan Levkivskyi, PR [17381](https://github.com/python/mypy/pull/17381))
 * Fix isinstance with type aliases to PEP 604 unions (Shantanu, PR [17371](https://github.com/python/mypy/pull/17371))
 * Properly handle unpacks in overlap checks (Ivan Levkivskyi, PR [17356](https://github.com/python/mypy/pull/17356))
 * Fix type application for classes with generic constructors (Ivan Levkivskyi, PR [17354](https://github.com/python/mypy/pull/17354))
 * Update `typing_extensions` to >=4.6.0 to fix Python 3.12 error (Ben Brown, PR [17312](https://github.com/python/mypy/pull/17312))
 * Avoid "does not return" error in lambda (Shantanu, PR [17294](https://github.com/python/mypy/pull/17294))
 * Fix bug with descriptors in non-strict-optional mode (Max Murin, PR [17293](https://github.com/python/mypy/pull/17293))
 * Don’t leak unreachability from lambda body to surrounding scope (Anders Kaseorg, PR [17287](https://github.com/python/mypy/pull/17287))
 * Fix issues with non-ASCII characters on Windows (Alexander Leopold Shon, PR [17275](https://github.com/python/mypy/pull/17275))
 * Fix for type narrowing of negative integer literals (gilesgc, PR [17256](https://github.com/python/mypy/pull/17256))
 * Fix confusion between .py and .pyi files in mypy daemon (Valentin Stanciu, PR [17245](https://github.com/python/mypy/pull/17245))
 * Fix type of `tuple[X, Y]` expression (urnest, PR [17235](https://github.com/python/mypy/pull/17235))
 * Don't forget that a `TypedDict` was wrapped in `Unpack` after a `name-defined` error occurred (Christoph Tyralla, PR [17226](https://github.com/python/mypy/pull/17226))
 * Mark annotated argument as having an explicit, not inferred type (bzoracler, PR [17217](https://github.com/python/mypy/pull/17217))
 * Don't consider Enum private attributes as enum members (Ali Hamdan, PR [17182](https://github.com/python/mypy/pull/17182))
 * Fix Literal strings containing pipe characters (Jelle Zijlstra, PR [17148](https://github.com/python/mypy/pull/17148))


### Typeshed Updates

Please see [git log](https://github.com/python/typeshed/commits/main?after=6dda799d8ad1d89e0f8aad7ac41d2d34bd838ace+0&branch=main&path=stdlib) for full list of standard library typeshed stub changes.

### Mypy 1.11.1
 * Fix `RawExpressionType.accept` crash with `--cache-fine-grained` (Anders Kaseorg, PR [17588](https://github.com/python/mypy/pull/17588))
 * Fix PEP 604 isinstance caching (Shantanu, PR [17563](https://github.com/python/mypy/pull/17563))
 * Fix `typing.TypeAliasType` being undefined on python < 3.12 (Nikita Sobolev, PR [17558](https://github.com/python/mypy/pull/17558))
 * Fix `types.GenericAlias` lookup crash (Shantanu, PR [17543](https://github.com/python/mypy/pull/17543))

### Mypy 1.11.2
 * Alternative fix for a union-like literal string (Ivan Levkivskyi, PR [17639](https://github.com/python/mypy/pull/17639))
 * Unwrap `TypedDict` item types before storing (Ivan Levkivskyi, PR [17640](https://github.com/python/mypy/pull/17640))

### Acknowledgements
Thanks to all mypy contributors who contributed to this release:

- Alex Waygood
- Alexander Leopold Shon
- Ali Hamdan
- Anders Kaseorg
- Ben Brown
- Bénédikt Tran
- bzoracler
- Christoph Tyralla
- Christopher Barber
- dexterkennedy
- gilesgc
- GiorgosPapoutsakis
- Ivan Levkivskyi
- Jelle Zijlstra
- Jukka Lehtosalo
- Marc Mueller
- Matthieu Devlin
- Michael R. Crusoe
- Nikita Sobolev
- Seo Sanghyeon
- Shantanu
- sobolevn
- Steven Troxler
- Tadeu Manoel
- Tamir Duberstein
- Tushar Sadhwani
- urnest
- Valentin Stanciu

I’d also like to thank my employer, Dropbox, for supporting mypy development.


## Mypy 1.10

We’ve just uploaded mypy 1.10 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Support TypeIs (PEP 742)

Mypy now supports `TypeIs` ([PEP 742](https://peps.python.org/pep-0742/)), which allows
functions to narrow the type of a value, similar to `isinstance()`. Unlike `TypeGuard`,
`TypeIs` can narrow in both the `if` and `else` branches of an if statement:

```python
from typing_extensions import TypeIs

def is_str(s: object) -> TypeIs[str]:
    return isinstance(s, str)

def f(o: str | int) -> None:
    if is_str(o):
        # Type of o is 'str'
        ...
    else:
        # Type of o is 'int'
        ...
```

`TypeIs` will be added to the `typing` module in Python 3.13, but it
can be used on earlier Python versions by importing it from
`typing_extensions`.

This feature was contributed by Jelle Zijlstra (PR [16898](https://github.com/python/mypy/pull/16898)).

### Support TypeVar Defaults (PEP 696)

[PEP 696](https://peps.python.org/pep-0696/) adds support for type parameter defaults.
Example:

```python
from typing import Generic
from typing_extensions import TypeVar

T = TypeVar("T", default=int)

class C(Generic[T]):
   ...

x: C = ...
y: C[str] = ...
reveal_type(x)  # C[int], because of the default
reveal_type(y)  # C[str]
```

TypeVar defaults will be added to the `typing` module in Python 3.13, but they
can be used with earlier Python releases by importing `TypeVar` from
`typing_extensions`.

This feature was contributed by Marc Mueller (PR [16878](https://github.com/python/mypy/pull/16878)
and PR [16925](https://github.com/python/mypy/pull/16925)).

### Support TypeAliasType (PEP 695)
As part of the initial steps towards implementing [PEP 695](https://peps.python.org/pep-0695/), mypy now supports `TypeAliasType`.
`TypeAliasType` provides a backport of the new `type` statement in Python 3.12.

```python
type ListOrSet[T] = list[T] | set[T]
```

is equivalent to:

```python
T = TypeVar("T")
ListOrSet = TypeAliasType("ListOrSet", list[T] | set[T], type_params=(T,))
```

Example of use in mypy:

```python
from typing_extensions import TypeAliasType, TypeVar

NewUnionType = TypeAliasType("NewUnionType", int | str)
x: NewUnionType = 42
y: NewUnionType = 'a'
z: NewUnionType = object()  # error: Incompatible types in assignment (expression has type "object", variable has type "int | str")  [assignment]

T = TypeVar("T")
ListOrSet = TypeAliasType("ListOrSet", list[T] | set[T], type_params=(T,))
a: ListOrSet[int] = [1, 2]
b: ListOrSet[str] = {'a', 'b'}
c: ListOrSet[str] = 'test'  # error: Incompatible types in assignment (expression has type "str", variable has type "list[str] | set[str]")  [assignment]
```

`TypeAliasType` was added to the `typing` module in Python 3.12, but it can be used with earlier Python releases by importing from `typing_extensions`.

This feature was contributed by Ali Hamdan (PR [16926](https://github.com/python/mypy/pull/16926), PR [17038](https://github.com/python/mypy/pull/17038) and PR [17053](https://github.com/python/mypy/pull/17053))

### Detect Additional Unsafe Uses of super()

Mypy will reject unsafe uses of `super()` more consistently, when the target has a
trivial (empty) body. Example:

```python
class Proto(Protocol):
    def method(self) -> int: ...

class Sub(Proto):
    def method(self) -> int:
        return super().meth()  # Error (unsafe)
```

This feature was contributed by Shantanu (PR [16756](https://github.com/python/mypy/pull/16756)).

### Stubgen Improvements
- Preserve empty tuple annotation (Ali Hamdan, PR [16907](https://github.com/python/mypy/pull/16907))
- Add support for PEP 570 positional-only parameters (Ali Hamdan, PR [16904](https://github.com/python/mypy/pull/16904))
- Replace obsolete typing aliases with builtin containers (Ali Hamdan, PR [16780](https://github.com/python/mypy/pull/16780))
- Fix generated dataclass `__init__` signature (Ali Hamdan, PR [16906](https://github.com/python/mypy/pull/16906))

### Mypyc Improvements

- Provide an easier way to define IR-to-IR transforms (Jukka Lehtosalo, PR [16998](https://github.com/python/mypy/pull/16998))
- Implement lowering pass and add primitives for int (in)equality (Jukka Lehtosalo, PR [17027](https://github.com/python/mypy/pull/17027))
- Implement lowering for remaining tagged integer comparisons (Jukka Lehtosalo, PR [17040](https://github.com/python/mypy/pull/17040))
- Optimize away some bool/bit registers (Jukka Lehtosalo, PR [17022](https://github.com/python/mypy/pull/17022))
- Remangle redefined names produced by async with (Richard Si, PR [16408](https://github.com/python/mypy/pull/16408))
- Optimize TYPE_CHECKING to False at Runtime (Srinivas Lade, PR [16263](https://github.com/python/mypy/pull/16263))
- Fix compilation of unreachable comprehensions (Richard Si, PR [15721](https://github.com/python/mypy/pull/15721))
- Don't crash on non-inlinable final local reads (Richard Si, PR [15719](https://github.com/python/mypy/pull/15719))

### Documentation Improvements
- Import `TypedDict` from `typing` instead of `typing_extensions` (Riccardo Di Maio, PR [16958](https://github.com/python/mypy/pull/16958))
- Add missing `mutable-override` to section title (James Braza, PR [16886](https://github.com/python/mypy/pull/16886))

### Error Reporting Improvements

- Use lower-case generics more consistently in error messages (Jukka Lehtosalo, PR [17035](https://github.com/python/mypy/pull/17035))

### Other Notable Changes and Fixes
- Fix incorrect inferred type when accessing descriptor on union type (Matthieu Devlin, PR [16604](https://github.com/python/mypy/pull/16604))
- Fix crash when expanding invalid `Unpack` in a `Callable` alias (Ali Hamdan, PR [17028](https://github.com/python/mypy/pull/17028))
- Fix false positive when string formatting with string enum (roberfi, PR [16555](https://github.com/python/mypy/pull/16555))
- Narrow individual items when matching a tuple to a sequence pattern (Loïc Simon, PR [16905](https://github.com/python/mypy/pull/16905))
- Fix false positive from type variable within TypeGuard or TypeIs (Evgeniy Slobodkin, PR [17071](https://github.com/python/mypy/pull/17071))
- Improve `yield from` inference for unions of generators (Shantanu, PR [16717](https://github.com/python/mypy/pull/16717))
- Fix emulating hash method logic in `attrs` classes (Hashem, PR [17016](https://github.com/python/mypy/pull/17016))
- Add reverted typeshed commit that uses `ParamSpec` for `functools.wraps` (Tamir Duberstein, PR [16942](https://github.com/python/mypy/pull/16942))
- Fix type narrowing for `types.EllipsisType` (Shantanu, PR [17003](https://github.com/python/mypy/pull/17003))
- Fix single item enum match type exhaustion (Oskari Lehto, PR [16966](https://github.com/python/mypy/pull/16966))
- Improve type inference with empty collections (Marc Mueller, PR [16994](https://github.com/python/mypy/pull/16994))
- Fix override checking for decorated property (Shantanu, PR [16856](https://github.com/python/mypy/pull/16856))
- Fix narrowing on match with function subject (Edward Paget, PR [16503](https://github.com/python/mypy/pull/16503))
- Allow `+N` within `Literal[...]` (Spencer Brown, PR [16910](https://github.com/python/mypy/pull/16910))
- Experimental: Support TypedDict within `type[...]` (Marc Mueller, PR [16963](https://github.com/python/mypy/pull/16963))
- Experimtental: Fix issue with TypedDict with optional keys in `type[...]` (Marc Mueller, PR [17068](https://github.com/python/mypy/pull/17068))

### Typeshed Updates

Please see [git log](https://github.com/python/typeshed/commits/main?after=6dda799d8ad1d89e0f8aad7ac41d2d34bd838ace+0&branch=main&path=stdlib) for full list of standard library typeshed stub changes.

### Mypy 1.10.1

- Fix error reporting on cached run after uninstallation of third party library (Shantanu, PR [17420](https://github.com/python/mypy/pull/17420))

### Acknowledgements
Thanks to all mypy contributors who contributed to this release:

- Alex Waygood
- Ali Hamdan
- Edward Paget
- Evgeniy Slobodkin
- Hashem
- hesam
- Hugo van Kemenade
- Ihor
- James Braza
- Jelle Zijlstra
- jhance
- Jukka Lehtosalo
- Loïc Simon
- Marc Mueller
- Matthieu Devlin
- Michael R. Crusoe
- Nikita Sobolev
- Oskari Lehto
- Riccardo Di Maio
- Richard Si
- roberfi
- Roman Solomatin
- Sam Xifaras
- Shantanu
- Spencer Brown
- Srinivas Lade
- Tamir Duberstein
- youkaichao

I’d also like to thank my employer, Dropbox, for supporting mypy development.


## Mypy 1.9

We’ve just uploaded mypy 1.9 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Breaking Changes

Because the version of typeshed we use in mypy 1.9 doesn't support 3.7, neither does mypy 1.9. (Jared Hance, PR [16883](https://github.com/python/mypy/pull/16883))

We are planning to enable
[local partial types](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-local-partial-types) (enabled via the
`--local-partial-types` flag) later this year by default. This change
was announced years ago, but now it's finally happening. This is a
major backward-incompatible change, so we'll probably include it as
part of the upcoming mypy 2.0 release. This makes daemon and
non-daemon mypy runs have the same behavior by default.

Local partial types can also be enabled in the mypy config file:
```
local_partial_types = True
```

We are looking at providing a tool to make it easier to migrate
projects to use `--local-partial-types`, but it's not yet clear whether
this is practical. The migration usually involves adding some
explicit type annotations to module-level and class-level variables.

### Basic Support for Type Parameter Defaults (PEP 696)

This release contains new experimental support for type parameter
defaults ([PEP 696](https://peps.python.org/pep-0696)). Please try it
out! This feature was contributed by Marc Mueller.

Since this feature will be officially introduced in the next Python
feature release (3.13), you will need to import `TypeVar`, `ParamSpec`
or `TypeVarTuple` from `typing_extensions` to use defaults for now.

This example adapted from the PEP defines a default for `BotT`:
```python
from typing import Generic
from typing_extensions import TypeVar

class Bot: ...

BotT = TypeVar("BotT", bound=Bot, default=Bot)

class Context(Generic[BotT]):
    bot: BotT

class MyBot(Bot): ...

# type is Bot (the default)
reveal_type(Context().bot)
# type is MyBot
reveal_type(Context[MyBot]().bot)
```

### Type-checking Improvements
 * Fix missing type store for overloads (Marc Mueller, PR [16803](https://github.com/python/mypy/pull/16803))
 * Fix `'WriteToConn' object has no attribute 'flush'` (Charlie Denton, PR [16801](https://github.com/python/mypy/pull/16801))
 * Improve TypeAlias error messages (Marc Mueller, PR [16831](https://github.com/python/mypy/pull/16831))
 * Support narrowing unions that include `type[None]` (Christoph Tyralla, PR [16315](https://github.com/python/mypy/pull/16315))
 * Support TypedDict functional syntax as class base type (anniel-stripe, PR [16703](https://github.com/python/mypy/pull/16703))
 * Accept multiline quoted annotations (Shantanu, PR [16765](https://github.com/python/mypy/pull/16765))
 * Allow unary + in `Literal` (Jelle Zijlstra, PR [16729](https://github.com/python/mypy/pull/16729))
 * Substitute type variables in return type of static methods (Kouroche Bouchiat, PR [16670](https://github.com/python/mypy/pull/16670))
 * Consider TypeVarTuple to be invariant (Marc Mueller, PR [16759](https://github.com/python/mypy/pull/16759))
 * Add `alias` support to `field()` in `attrs` plugin (Nikita Sobolev, PR [16610](https://github.com/python/mypy/pull/16610))
 * Improve attrs hashability detection (Tin Tvrtković, PR [16556](https://github.com/python/mypy/pull/16556))

### Performance Improvements

 * Speed up finding function type variables (Jukka Lehtosalo, PR [16562](https://github.com/python/mypy/pull/16562))

### Documentation Updates

 * Document supported values for `--enable-incomplete-feature` in "mypy --help" (Froger David, PR [16661](https://github.com/python/mypy/pull/16661))
 * Update new type system discussion links (thomaswhaley, PR [16841](https://github.com/python/mypy/pull/16841))
 * Add missing class instantiation to cheat sheet (Aleksi Tarvainen, PR [16817](https://github.com/python/mypy/pull/16817))
 * Document how evil `--no-strict-optional` is (Shantanu, PR [16731](https://github.com/python/mypy/pull/16731))
 * Improve mypy daemon documentation note about local partial types (Makonnen Makonnen, PR [16782](https://github.com/python/mypy/pull/16782))
 * Fix numbering error (Stefanie Molin, PR [16838](https://github.com/python/mypy/pull/16838))
 * Various documentation improvements (Shantanu, PR [16836](https://github.com/python/mypy/pull/16836))

### Stubtest Improvements
 * Ignore private function/method parameters when they are missing from the stub (private parameter names start with a single underscore and have a default) (PR [16507](https://github.com/python/mypy/pull/16507))
 * Ignore a new protocol dunder (Alex Waygood, PR [16895](https://github.com/python/mypy/pull/16895))
 * Private parameters can be omitted (Sebastian Rittau, PR [16507](https://github.com/python/mypy/pull/16507))
 * Add support for setting enum members to "..." (Jelle Zijlstra, PR [16807](https://github.com/python/mypy/pull/16807))
 * Adjust symbol table logic (Shantanu, PR [16823](https://github.com/python/mypy/pull/16823))
 * Fix posisitional-only handling in overload resolution (Shantanu, PR [16750](https://github.com/python/mypy/pull/16750))

### Stubgen Improvements
 * Fix crash on star unpack of TypeVarTuple (Ali Hamdan, PR [16869](https://github.com/python/mypy/pull/16869))
 * Use PEP 604 unions everywhere (Ali Hamdan, PR [16519](https://github.com/python/mypy/pull/16519))
 * Do not ignore property deleter (Ali Hamdan, PR [16781](https://github.com/python/mypy/pull/16781))
 * Support type stub generation for `staticmethod` (WeilerMarcel, PR [14934](https://github.com/python/mypy/pull/14934))

### Acknowledgements

​Thanks to all mypy contributors who contributed to this release:

- Aleksi Tarvainen
- Alex Waygood
- Ali Hamdan
- anniel-stripe
- Charlie Denton
- Christoph Tyralla
- Dheeraj
- Fabian Keller
- Fabian Lewis
- Froger David
- Ihor
- Jared Hance
- Jelle Zijlstra
- Jukka Lehtosalo
- Kouroche Bouchiat
- Lukas Geiger
- Maarten Huijsmans
- Makonnen Makonnen
- Marc Mueller
- Nikita Sobolev
- Sebastian Rittau
- Shantanu
- Stefanie Molin
- Stephen Morton
- thomaswhaley
- Tin Tvrtković
- WeilerMarcel
- Wesley Collin Wright
- zipperer

I’d also like to thank my employer, Dropbox, for supporting mypy development.

## Mypy 1.8

We’ve just uploaded mypy 1.8 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Type-checking Improvements
 * Do not intersect types in isinstance checks if at least one is final (Christoph Tyralla, PR [16330](https://github.com/python/mypy/pull/16330))
 * Detect that `@final` class without `__bool__` cannot have falsey instances (Ilya Priven, PR [16566](https://github.com/python/mypy/pull/16566))
 * Do not allow `TypedDict` classes with extra keywords (Nikita Sobolev, PR [16438](https://github.com/python/mypy/pull/16438))
 * Do not allow class-level keywords for `NamedTuple` (Nikita Sobolev, PR [16526](https://github.com/python/mypy/pull/16526))
 * Make imprecise constraints handling more robust (Ivan Levkivskyi, PR [16502](https://github.com/python/mypy/pull/16502))
 * Fix strict-optional in extending generic TypedDict (Ivan Levkivskyi, PR [16398](https://github.com/python/mypy/pull/16398))
 * Allow type ignores of PEP 695 constructs (Shantanu, PR [16608](https://github.com/python/mypy/pull/16608))
 * Enable `type_check_only` support for `TypedDict` and `NamedTuple` (Nikita Sobolev, PR [16469](https://github.com/python/mypy/pull/16469))

### Performance Improvements
 * Add fast path to analyzing special form assignments (Jukka Lehtosalo, PR [16561](https://github.com/python/mypy/pull/16561))

### Improvements to Error Reporting
 * Don't show documentation links for plugin error codes (Ivan Levkivskyi, PR [16383](https://github.com/python/mypy/pull/16383))
 * Improve error messages for `super` checks and add more tests (Nikita Sobolev, PR [16393](https://github.com/python/mypy/pull/16393))
 * Add error code for mutable covariant override (Ivan Levkivskyi, PR [16399](https://github.com/python/mypy/pull/16399))

### Stubgen Improvements
 * Preserve simple defaults in function signatures (Ali Hamdan, PR [15355](https://github.com/python/mypy/pull/15355))
 * Include `__all__` in output (Jelle Zijlstra, PR [16356](https://github.com/python/mypy/pull/16356))
 * Fix stubgen regressions with pybind11 and mypy 1.7 (Chad Dombrova, PR [16504](https://github.com/python/mypy/pull/16504))

### Stubtest Improvements
 * Improve handling of unrepresentable defaults (Jelle Zijlstra, PR [16433](https://github.com/python/mypy/pull/16433))
 * Print more helpful errors if a function is missing from stub (Alex Waygood, PR [16517](https://github.com/python/mypy/pull/16517))
 * Support `@type_check_only` decorator (Nikita Sobolev, PR [16422](https://github.com/python/mypy/pull/16422))
 * Warn about missing `__del__` (Shantanu, PR [16456](https://github.com/python/mypy/pull/16456))
 * Fix crashes with some uses of `final` and `deprecated` (Shantanu, PR [16457](https://github.com/python/mypy/pull/16457))

### Fixes to Crashes
 * Fix crash with type alias to `Callable[[Unpack[Tuple[Any, ...]]], Any]` (Alex Waygood, PR [16541](https://github.com/python/mypy/pull/16541))
 * Fix crash on TypeGuard in `__call__` (Ivan Levkivskyi, PR [16516](https://github.com/python/mypy/pull/16516))
 * Fix crash on invalid enum in method (Ivan Levkivskyi, PR [16511](https://github.com/python/mypy/pull/16511))
 * Fix crash on unimported Any in TypedDict (Ivan Levkivskyi, PR [16510](https://github.com/python/mypy/pull/16510))

### Documentation Updates
 * Update soft-error-limit default value to -1 (Sveinung Gundersen, PR [16542](https://github.com/python/mypy/pull/16542))
 * Support Sphinx 7.x (Michael R. Crusoe, PR [16460](https://github.com/python/mypy/pull/16460))

### Other Notable Changes and Fixes
 * Allow mypy to output a junit file with per-file results (Matthew Wright, PR [16388](https://github.com/python/mypy/pull/16388))

### Typeshed Updates

Please see [git log](https://github.com/python/typeshed/commits/main?after=4a854366e03dee700109f8e758a08b2457ea2f51+0&branch=main&path=stdlib) for full list of standard library typeshed stub changes.

### Acknowledgements

​Thanks to all mypy contributors who contributed to this release:

- Alex Waygood
- Ali Hamdan
- Chad Dombrova
- Christoph Tyralla
- Ilya Priven
- Ivan Levkivskyi
- Jelle Zijlstra
- Jukka Lehtosalo
- Marcel Telka
- Matthew Wright
- Michael R. Crusoe
- Nikita Sobolev
- Ole Peder Brandtzæg
- robjhornby
- Shantanu
- Sveinung Gundersen
- Valentin Stanciu

I’d also like to thank my employer, Dropbox, for supporting mypy development.

Posted by Wesley Collin Wright

## Mypy 1.7

We’ve just uploaded mypy 1.7 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Using TypedDict for `**kwargs` Typing

Mypy now has support for using `Unpack[...]` with a TypedDict type to annotate `**kwargs` arguments enabled by default. Example:

```python
# Or 'from typing_extensions import ...'
from typing import TypedDict, Unpack

class Person(TypedDict):
    name: str
    age: int

def foo(**kwargs: Unpack[Person]) -> None:
    ...

foo(name="x", age=1)  # Ok
foo(name=1)  # Error
```

The definition of `foo` above is equivalent to the one below, with keyword-only arguments `name` and `age`:

```python
def foo(*, name: str, age: int) -> None:
    ...
```

Refer to [PEP 692](https://peps.python.org/pep-0692/) for more information. Note that unlike in the current version of the PEP, mypy always treats signatures with `Unpack[SomeTypedDict]` as equivalent to their expanded forms with explicit keyword arguments, and there aren't special type checking rules for TypedDict arguments.

This was contributed by Ivan Levkivskyi back in 2022 (PR [13471](https://github.com/python/mypy/pull/13471)).

### TypeVarTuple Support Enabled (Experimental)

Mypy now has support for variadic generics (TypeVarTuple) enabled by default, as an experimental feature. Refer to [PEP 646](https://peps.python.org/pep-0646/) for the details.

TypeVarTuple was implemented by Jared Hance and Ivan Levkivskyi over several mypy releases, with help from Jukka Lehtosalo.

Changes included in this release:

 * Fix handling of tuple type context with unpacks (Ivan Levkivskyi, PR [16444](https://github.com/python/mypy/pull/16444))
 * Handle TypeVarTuples when checking overload constraints (robjhornby, PR [16428](https://github.com/python/mypy/pull/16428))
 * Enable Unpack/TypeVarTuple support (Ivan Levkivskyi, PR [16354](https://github.com/python/mypy/pull/16354))
 * Fix crash on unpack call special-casing (Ivan Levkivskyi, PR [16381](https://github.com/python/mypy/pull/16381))
 * Some final touches for variadic types support (Ivan Levkivskyi, PR [16334](https://github.com/python/mypy/pull/16334))
 * Support PEP-646 and PEP-692 in the same callable (Ivan Levkivskyi, PR [16294](https://github.com/python/mypy/pull/16294))
 * Support new `*` syntax for variadic types (Ivan Levkivskyi, PR [16242](https://github.com/python/mypy/pull/16242))
 * Correctly handle variadic instances with empty arguments (Ivan Levkivskyi, PR [16238](https://github.com/python/mypy/pull/16238))
 * Correctly handle runtime type applications of variadic types (Ivan Levkivskyi, PR [16240](https://github.com/python/mypy/pull/16240))
 * Support variadic tuple packing/unpacking (Ivan Levkivskyi, PR [16205](https://github.com/python/mypy/pull/16205))
 * Better support for variadic calls and indexing (Ivan Levkivskyi, PR [16131](https://github.com/python/mypy/pull/16131))
 * Subtyping and inference of user-defined variadic types (Ivan Levkivskyi, PR [16076](https://github.com/python/mypy/pull/16076))
 * Complete type analysis of variadic types (Ivan Levkivskyi, PR [15991](https://github.com/python/mypy/pull/15991))

### New Way of Installing Mypyc Dependencies

If you want to install package dependencies needed by mypyc (not just mypy), you should now install `mypy[mypyc]` instead of just `mypy`:

```
python3 -m pip install -U 'mypy[mypyc]'
```

Mypy has many more users than mypyc, so always installing mypyc dependencies would often bring unnecessary dependencies.

This change was contributed by Shantanu (PR [16229](https://github.com/python/mypy/pull/16229)).

### New Rules for Re-exports

Mypy no longer considers an import such as `import a.b as b` as an explicit re-export. The old behavior was arguably inconsistent and surprising. This may impact some stub packages, such as older versions of `types-six`. You can change the import to `from a import b as b`, if treating the import as a re-export was intentional.

This change was contributed by Anders Kaseorg (PR [14086](https://github.com/python/mypy/pull/14086)).

### Improved Type Inference

The new type inference algorithm that was recently introduced to mypy (but was not enabled by default) is now enabled by default. It improves type inference of calls to generic callables where an argument is also a generic callable, in particular. You can use `--old-type-inference` to disable the new behavior.

The new algorithm can (rarely) produce different error messages, different error codes, or errors reported on different lines. This is more likely in cases where generic types were used incorrectly.

The new type inference algorithm was contributed by Ivan Levkivskyi. PR [16345](https://github.com/python/mypy/pull/16345) enabled it by default.

### Narrowing Tuple Types Using len()

Mypy now can narrow tuple types using `len()` checks. Example:

```python
def f(t: tuple[int, int] | tuple[int, int, int]) -> None:
    if len(t) == 2:
        a, b = t   # Ok
    ...
```

This feature was contributed by Ivan Levkivskyi (PR [16237](https://github.com/python/mypy/pull/16237)).

### More Precise Tuple Lengths (Experimental)

Mypy supports experimental, more precise checking of tuple type lengths through `--enable-incomplete-feature=PreciseTupleTypes`. Refer to the [documentation](https://mypy.readthedocs.io/en/latest/command_line.html#enabling-incomplete-experimental-features) for more information.

More generally, we are planning to use `--enable-incomplete-feature` to introduce experimental features that would benefit from community feedback.

This feature was contributed by Ivan Levkivskyi (PR [16237](https://github.com/python/mypy/pull/16237)).

### Mypy Changelog

We now maintain a [changelog](https://github.com/python/mypy/blob/master/CHANGELOG.md) in the mypy Git repository. It mirrors the contents of [mypy release blog posts](https://mypy-lang.blogspot.com/). We will continue to also publish release blog posts. In the future, release blog posts will be created based on the changelog near a release date.

This was contributed by Shantanu (PR [16280](https://github.com/python/mypy/pull/16280)).

### Mypy Daemon Improvements

 * Fix daemon crash caused by deleted submodule (Jukka Lehtosalo, PR [16370](https://github.com/python/mypy/pull/16370))
 * Fix file reloading in dmypy with --export-types (Ivan Levkivskyi, PR [16359](https://github.com/python/mypy/pull/16359))
 * Fix dmypy inspect on Windows (Ivan Levkivskyi, PR [16355](https://github.com/python/mypy/pull/16355))
 * Fix dmypy inspect for namespace packages (Ivan Levkivskyi, PR [16357](https://github.com/python/mypy/pull/16357))
 * Fix return type change to optional in generic function (Jukka Lehtosalo, PR [16342](https://github.com/python/mypy/pull/16342))
 * Fix daemon false positives related to module-level `__getattr__` (Jukka Lehtosalo, PR [16292](https://github.com/python/mypy/pull/16292))
 * Fix daemon crash related to ABCs (Jukka Lehtosalo, PR [16275](https://github.com/python/mypy/pull/16275))
 * Stream dmypy output instead of dumping everything at the end (Valentin Stanciu, PR [16252](https://github.com/python/mypy/pull/16252))
 * Make sure all dmypy errors are shown (Valentin Stanciu, PR [16250](https://github.com/python/mypy/pull/16250))

### Mypyc Improvements

 * Generate error on duplicate function definitions (Jukka Lehtosalo, PR [16309](https://github.com/python/mypy/pull/16309))
 * Don't crash on unreachable statements (Jukka Lehtosalo, PR [16311](https://github.com/python/mypy/pull/16311))
 * Avoid cyclic reference in nested functions (Jukka Lehtosalo, PR [16268](https://github.com/python/mypy/pull/16268))
 * Fix direct `__dict__` access on inner functions in new Python (Shantanu, PR [16084](https://github.com/python/mypy/pull/16084))
 * Make tuple packing and unpacking more efficient (Jukka Lehtosalo, PR [16022](https://github.com/python/mypy/pull/16022))

### Improvements to Error Reporting

 * Update starred expression error message to match CPython (Cibin Mathew, PR [16304](https://github.com/python/mypy/pull/16304))
 * Fix error code of "Maybe you forgot to use await" note (Jelle Zijlstra, PR [16203](https://github.com/python/mypy/pull/16203))
 * Use error code `[unsafe-overload]` for unsafe overloads, instead of `[misc]` (Randolf Scholz, PR [16061](https://github.com/python/mypy/pull/16061))
 * Reword the error message related to void functions (Albert Tugushev, PR [15876](https://github.com/python/mypy/pull/15876))
 * Represent bottom type as Never in messages (Shantanu, PR [15996](https://github.com/python/mypy/pull/15996))
 * Add hint for AsyncIterator incompatible return type (Ilya Priven, PR [15883](https://github.com/python/mypy/pull/15883))
 * Don't suggest stubs packages where the runtime package now ships with types (Alex Waygood, PR [16226](https://github.com/python/mypy/pull/16226))

### Performance Improvements

 * Speed up type argument checking (Jukka Lehtosalo, PR [16353](https://github.com/python/mypy/pull/16353))
 * Add fast path for checking self types (Jukka Lehtosalo, PR [16352](https://github.com/python/mypy/pull/16352))
 * Cache information about whether file is typeshed file (Jukka Lehtosalo, PR [16351](https://github.com/python/mypy/pull/16351))
 * Skip expensive `repr()` in logging call when not needed (Jukka Lehtosalo, PR [16350](https://github.com/python/mypy/pull/16350))

### Attrs and Dataclass Improvements

 * `dataclass.replace`: Allow transformed classes (Ilya Priven, PR [15915](https://github.com/python/mypy/pull/15915))
 * `dataclass.replace`: Fall through to typeshed signature (Ilya Priven, PR [15962](https://github.com/python/mypy/pull/15962))
 * Document `dataclass_transform` behavior (Ilya Priven, PR [16017](https://github.com/python/mypy/pull/16017))
 * `attrs`: Remove fields type check (Ilya Priven, PR [15983](https://github.com/python/mypy/pull/15983))
 * `attrs`, `dataclasses`: Don't enforce slots when base class doesn't (Ilya Priven, PR [15976](https://github.com/python/mypy/pull/15976))
 * Fix crash on dataclass field / property collision (Nikita Sobolev, PR [16147](https://github.com/python/mypy/pull/16147))

### Stubgen Improvements

 * Write stubs with utf-8 encoding (Jørgen Lind, PR [16329](https://github.com/python/mypy/pull/16329))
 * Fix missing property setter in semantic analysis mode (Ali Hamdan, PR [16303](https://github.com/python/mypy/pull/16303))
 * Unify C extension and pure python stub generators with object oriented design (Chad Dombrova, PR [15770](https://github.com/python/mypy/pull/15770))
 * Multiple fixes to the generated imports (Ali Hamdan, PR [15624](https://github.com/python/mypy/pull/15624))
 * Generate valid dataclass stubs (Ali Hamdan, PR [15625](https://github.com/python/mypy/pull/15625))

### Fixes to Crashes

 * Fix incremental mode crash on TypedDict in method (Ivan Levkivskyi, PR [16364](https://github.com/python/mypy/pull/16364))
 * Fix crash on star unpack in TypedDict (Ivan Levkivskyi, PR [16116](https://github.com/python/mypy/pull/16116))
 * Fix crash on malformed TypedDict in incremental mode (Ivan Levkivskyi, PR [16115](https://github.com/python/mypy/pull/16115))
 * Fix crash with report generation on namespace packages (Shantanu, PR [16019](https://github.com/python/mypy/pull/16019))
 * Fix crash when parsing error code config with typo (Shantanu, PR [16005](https://github.com/python/mypy/pull/16005))
 * Fix `__post_init__()` internal error (Ilya Priven, PR [16080](https://github.com/python/mypy/pull/16080))

### Documentation Updates

 * Make it easier to copy commands from README (Hamir Mahal, PR [16133](https://github.com/python/mypy/pull/16133))
 * Document and rename `[overload-overlap]` error code (Shantanu, PR [16074](https://github.com/python/mypy/pull/16074))
 * Document `--force-uppercase-builtins` and `--force-union-syntax` (Nikita Sobolev, PR [16049](https://github.com/python/mypy/pull/16049))
 * Document `force_union_syntax` and `force_uppercase_builtins` (Nikita Sobolev, PR [16048](https://github.com/python/mypy/pull/16048))
 * Document we're not tracking relationships between symbols (Ilya Priven, PR [16018](https://github.com/python/mypy/pull/16018))

### Other Notable Changes and Fixes

 * Propagate narrowed types to lambda expressions (Ivan Levkivskyi, PR [16407](https://github.com/python/mypy/pull/16407))
 * Avoid importing from `setuptools._distutils` (Shantanu, PR [16348](https://github.com/python/mypy/pull/16348))
 * Delete recursive aliases flags (Ivan Levkivskyi, PR [16346](https://github.com/python/mypy/pull/16346))
 * Properly use proper subtyping for callables (Ivan Levkivskyi, PR [16343](https://github.com/python/mypy/pull/16343))
 * Use upper bound as inference fallback more consistently (Ivan Levkivskyi, PR [16344](https://github.com/python/mypy/pull/16344))
 * Add `[unimported-reveal]` error code (Nikita Sobolev, PR [16271](https://github.com/python/mypy/pull/16271))
 * Add `|=` and `|` operators support for `TypedDict` (Nikita Sobolev, PR [16249](https://github.com/python/mypy/pull/16249))
 * Clarify variance convention for Parameters (Ivan Levkivskyi, PR [16302](https://github.com/python/mypy/pull/16302))
 * Correctly recognize `typing_extensions.NewType` (Ganden Schaffner, PR [16298](https://github.com/python/mypy/pull/16298))
 * Fix partially defined in the case of missing type maps (Shantanu, PR [15995](https://github.com/python/mypy/pull/15995))
 * Use SPDX license identifier (Nikita Sobolev, PR [16230](https://github.com/python/mypy/pull/16230))
 * Make `__qualname__` and `__module__` available in class bodies (Anthony Sottile, PR [16215](https://github.com/python/mypy/pull/16215))
 * stubtest: Hint when args in stub need to be keyword-only (Alex Waygood, PR [16210](https://github.com/python/mypy/pull/16210))
 * Tuple slice should not propagate fallback (Thomas Grainger, PR [16154](https://github.com/python/mypy/pull/16154))
 * Fix cases of type object handling for overloads (Shantanu, PR [16168](https://github.com/python/mypy/pull/16168))
 * Fix walrus interaction with empty collections (Ivan Levkivskyi, PR [16197](https://github.com/python/mypy/pull/16197))
 * Use type variable bound when it appears as actual during inference (Ivan Levkivskyi, PR [16178](https://github.com/python/mypy/pull/16178))
 * Use upper bounds as fallback solutions for inference (Ivan Levkivskyi, PR [16184](https://github.com/python/mypy/pull/16184))
 * Special-case type inference of empty collections (Ivan Levkivskyi, PR [16122](https://github.com/python/mypy/pull/16122))
 * Allow TypedDict unpacking in Callable types (Ivan Levkivskyi, PR [16083](https://github.com/python/mypy/pull/16083))
 * Fix inference for overloaded `__call__` with generic self (Shantanu, PR [16053](https://github.com/python/mypy/pull/16053))
 * Call dynamic class hook on generic classes (Petter Friberg, PR [16052](https://github.com/python/mypy/pull/16052))
 * Preserve implicitly exported types via attribute access (Shantanu, PR [16129](https://github.com/python/mypy/pull/16129))
 * Fix a stubtest bug (Alex Waygood)
 * Fix `tuple[Any, ...]` subtyping (Shantanu, PR [16108](https://github.com/python/mypy/pull/16108))
 * Lenient handling of trivial Callable suffixes (Ivan Levkivskyi, PR [15913](https://github.com/python/mypy/pull/15913))
 * Add `add_overloaded_method_to_class` helper for plugins (Nikita Sobolev, PR [16038](https://github.com/python/mypy/pull/16038))
 * Bundle `misc/proper_plugin.py` as a part of `mypy` (Nikita Sobolev, PR [16036](https://github.com/python/mypy/pull/16036))
 * Fix `case Any()` in match statement (DS/Charlie, PR [14479](https://github.com/python/mypy/pull/14479))
 * Make iterable logic more consistent (Shantanu, PR [16006](https://github.com/python/mypy/pull/16006))
 * Fix inference for properties with `__call__` (Shantanu, PR [15926](https://github.com/python/mypy/pull/15926))

### Typeshed Updates

Please see [git log](https://github.com/python/typeshed/commits/main?after=4a854366e03dee700109f8e758a08b2457ea2f51+0&branch=main&path=stdlib) for full list of standard library typeshed stub changes.

### Acknowledgements

Thanks to all mypy contributors who contributed to this release:

* Albert Tugushev
* Alex Waygood
* Ali Hamdan
* Anders Kaseorg
* Anthony Sottile
* Chad Dombrova
* Cibin Mathew
* dinaldoap
* DS/Charlie
* Eli Schwartz
* Ganden Schaffner
* Hamir Mahal
* Ihor
* Ikko Eltociear Ashimine
* Ilya Priven
* Ivan Levkivskyi
* Jelle Zijlstra
* Jukka Lehtosalo
* Jørgen Lind
* KotlinIsland
* Matt Bogosian
* Nikita Sobolev
* Petter Friberg
* Randolf Scholz
* Shantanu
* Thomas Grainger
* Valentin Stanciu

I’d also like to thank my employer, Dropbox, for supporting mypy development.

Posted by Jukka Lehtosalo

## Mypy 1.6

[Tuesday, 10 October 2023](https://mypy-lang.blogspot.com/2023/10/mypy-16-released.html)

We’ve just uploaded mypy 1.6 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Introduce Error Subcodes for Import Errors

Mypy now uses the error code import-untyped if an import targets an installed library that doesn’t support static type checking, and no stub files are available. Other invalid imports produce the import-not-found error code. They both are subcodes of the import error code, which was previously used for both kinds of import-related errors.

Use \--disable-error-code=import-untyped to only ignore import errors about installed libraries without stubs. This way mypy will still report errors about typos in import statements, for example.

If you use \--warn-unused-ignore or \--strict, mypy will complain if you use \# type: ignore\[import\] to ignore an import error. You are expected to use one of the more specific error codes instead. Otherwise, ignoring the import error code continues to silence both errors.

This feature was contributed by Shantanu (PR [15840](https://github.com/python/mypy/pull/15840), PR [14740](https://github.com/python/mypy/pull/14740)).

### Remove Support for Targeting Python 3.6 and Earlier

Running mypy with \--python-version 3.6, for example, is no longer supported. Python 3.6 hasn’t been properly supported by mypy for some time now, and this makes it explicit. This was contributed by Nikita Sobolev (PR [15668](https://github.com/python/mypy/pull/15668)).

### Selective Filtering of \--disallow-untyped-calls Targets

Using \--disallow-untyped-calls could be annoying when using libraries with missing type information, as mypy would generate many errors about code that uses the library. Now you can use \--untyped-calls-exclude=acme, for example, to disable these errors about calls targeting functions defined in the acme package. Refer to the [documentation](https://mypy.readthedocs.io/en/latest/command_line.html#cmdoption-mypy-untyped-calls-exclude) for more information.

This feature was contributed by Ivan Levkivskyi (PR [15845](https://github.com/python/mypy/pull/15845)).

### Improved Type Inference between Callable Types

Mypy now does a better job inferring type variables inside arguments of callable types. For example, this code fragment now type checks correctly:

```python
def f(c: Callable[[T, S], None]) -> Callable[[str, T, S], None]: ...
def g(*x: int) -> None: ...

reveal_type(f(g))  # Callable[[str, int, int], None]
```

This was contributed by Ivan Levkivskyi (PR [15910](https://github.com/python/mypy/pull/15910)).

### Don’t Consider None and TypeVar to Overlap in Overloads

Mypy now doesn’t consider an overload item with an argument type None to overlap with a type variable:

```python
@overload
def f(x: None) -> None: ..
@overload
def f(x: T) -> Foo[T]: ...
...
```

Previously mypy would generate an error about the definition of f above. This is slightly unsafe if the upper bound of T is object, since the value of the type variable could be None. We relaxed the rules a little, since this solves a common issue.

This feature was contributed by Ivan Levkivskyi (PR [15846](https://github.com/python/mypy/pull/15846)).

### Improvements to \--new-type-inference

The experimental new type inference algorithm (polymorphic inference) introduced as an opt-in feature in mypy 1.5 has several improvements:

*   Improve transitive closure computation during constraint solving (Ivan Levkivskyi, PR [15754](https://github.com/python/mypy/pull/15754))
*   Add support for upper bounds and values with \--new-type-inference (Ivan Levkivskyi, PR [15813](https://github.com/python/mypy/pull/15813))
*   Basic support for variadic types with \--new-type-inference (Ivan Levkivskyi, PR [15879](https://github.com/python/mypy/pull/15879))
*   Polymorphic inference: support for parameter specifications and lambdas (Ivan Levkivskyi, PR [15837](https://github.com/python/mypy/pull/15837))
*   Invalidate cache when adding \--new-type-inference (Marc Mueller, PR [16059](https://github.com/python/mypy/pull/16059))

**Note:** We are planning to enable \--new-type-inference by default in mypy 1.7. Please try this out and let us know if you encounter any issues.

### ParamSpec Improvements

*   Support self-types containing ParamSpec (Ivan Levkivskyi, PR [15903](https://github.com/python/mypy/pull/15903))
*   Allow “…” in Concatenate, and clean up ParamSpec literals (Ivan Levkivskyi, PR [15905](https://github.com/python/mypy/pull/15905))
*   Fix ParamSpec inference for callback protocols (Ivan Levkivskyi, PR [15986](https://github.com/python/mypy/pull/15986))
*   Infer ParamSpec constraint from arguments (Ivan Levkivskyi, PR [15896](https://github.com/python/mypy/pull/15896))
*   Fix crash on invalid type variable with ParamSpec (Ivan Levkivskyi, PR [15953](https://github.com/python/mypy/pull/15953))
*   Fix subtyping between ParamSpecs (Ivan Levkivskyi, PR [15892](https://github.com/python/mypy/pull/15892))

### Stubgen Improvements

*   Add option to include docstrings with stubgen (chylek, PR [13284](https://github.com/python/mypy/pull/13284))
*   Add required ... initializer to NamedTuple fields with default values (Nikita Sobolev, PR [15680](https://github.com/python/mypy/pull/15680))

### Stubtest Improvements

*   Fix \_\_mypy-replace false positives (Alex Waygood, PR [15689](https://github.com/python/mypy/pull/15689))
*   Fix edge case for bytes enum subclasses (Alex Waygood, PR [15943](https://github.com/python/mypy/pull/15943))
*   Generate error if typeshed is missing modules from the stdlib (Alex Waygood, PR [15729](https://github.com/python/mypy/pull/15729))
*   Fixes to new check for missing stdlib modules (Alex Waygood, PR [15960](https://github.com/python/mypy/pull/15960))
*   Fix stubtest enum.Flag edge case (Alex Waygood, PR [15933](https://github.com/python/mypy/pull/15933))

### Documentation Improvements

*   Do not advertise to create your own assert\_never helper (Nikita Sobolev, PR [15947](https://github.com/python/mypy/pull/15947))
*   Fix all the missing references found within the docs (Albert Tugushev, PR [15875](https://github.com/python/mypy/pull/15875))
*   Document await-not-async error code (Shantanu, PR [15858](https://github.com/python/mypy/pull/15858))
*   Improve documentation of disabling error codes (Shantanu, PR [15841](https://github.com/python/mypy/pull/15841))

### Other Notable Changes and Fixes

*   Make unsupported PEP 695 features (introduced in Python 3.12) give a reasonable error message (Shantanu, PR [16013](https://github.com/python/mypy/pull/16013))
*   Remove the \--py2 command-line argument (Marc Mueller, PR [15670](https://github.com/python/mypy/pull/15670))
*   Change empty tuple from tuple\[\] to tuple\[()\] in error messages (Nikita Sobolev, PR [15783](https://github.com/python/mypy/pull/15783))
*   Fix assert\_type failures when some nodes are deferred (Nikita Sobolev, PR [15920](https://github.com/python/mypy/pull/15920))
*   Generate error on unbound TypeVar with values (Nikita Sobolev, PR [15732](https://github.com/python/mypy/pull/15732))
*   Fix over-eager types-google-cloud-ndb suggestion (Shantanu, PR [15347](https://github.com/python/mypy/pull/15347))
*   Fix type narrowing of \== None and in (None,) conditions (Marti Raudsepp, PR [15760](https://github.com/python/mypy/pull/15760))
*   Fix inference for attrs.fields (Shantanu, PR [15688](https://github.com/python/mypy/pull/15688))
*   Make “await in non-async function” a non-blocking error and give it an error code (Gregory Santosa, PR [15384](https://github.com/python/mypy/pull/15384))
*   Add basic support for decorated overloads (Ivan Levkivskyi, PR [15898](https://github.com/python/mypy/pull/15898))
*   Fix TypeVar regression with self types (Ivan Levkivskyi, PR [15945](https://github.com/python/mypy/pull/15945))
*   Add \_\_match\_args\_\_ to dataclasses with no fields (Ali Hamdan, PR [15749](https://github.com/python/mypy/pull/15749))
*   Include stdout and stderr in dmypy verbose output (Valentin Stanciu, PR [15881](https://github.com/python/mypy/pull/15881))
*   Improve match narrowing and reachability analysis (Shantanu, PR [15882](https://github.com/python/mypy/pull/15882))
*   Support \_\_bool\_\_ with Literal in \--warn-unreachable (Jannic Warken, PR [15645](https://github.com/python/mypy/pull/15645))
*   Fix inheriting from generic @frozen attrs class (Ilya Priven, PR [15700](https://github.com/python/mypy/pull/15700))
*   Correctly narrow types for tuple\[type\[X\], ...\] (Nikita Sobolev, PR [15691](https://github.com/python/mypy/pull/15691))
*   Don't flag intentionally empty generators unreachable (Ilya Priven, PR [15722](https://github.com/python/mypy/pull/15722))
*   Add tox.ini to mypy sdist (Marcel Telka, PR [15853](https://github.com/python/mypy/pull/15853))
*   Fix mypyc regression with pretty (Shantanu, PR [16124](https://github.com/python/mypy/pull/16124))

### Typeshed Updates

Typeshed is now modular and distributed as separate PyPI packages for everything except the standard library stubs. Please see [git log](https://github.com/python/typeshed/commits/main?after=6a8d653a671925b0a3af61729ff8cf3f90c9c662+0&branch=main&path=stdlib) for full list of typeshed changes.

### Acknowledgements

Thanks to Max Murin, who did most of the release manager work for this release (I just did the final steps).

Thanks to all mypy contributors who contributed to this release:

*   Albert Tugushev
*   Alex Waygood
*   Ali Hamdan
*   chylek
*   EXPLOSION
*   Gregory Santosa
*   Ilya Priven
*   Ivan Levkivskyi
*   Jannic Warken
*   KotlinIsland
*   Marc Mueller
*   Marcel Johannesmann
*   Marcel Telka
*   Mark Byrne
*   Marti Raudsepp
*   Max Murin
*   Nikita Sobolev
*   Shantanu
*   Valentin Stanciu

Posted by Jukka Lehtosalo


## Mypy 1.5

[Thursday, 10 August 2023](https://mypy-lang.blogspot.com/2023/08/mypy-15-released.html)

We’ve just uploaded mypy 1.5 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, deprecations and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Drop Support for Python 3.7

Mypy no longer supports running with Python 3.7, which has reached end-of-life. This was contributed by Shantanu (PR [15566](https://github.com/python/mypy/pull/15566)).

### Optional Check to Require Explicit @override

If you enable the explicit-override error code, mypy will generate an error if a method override doesn’t use the @typing.override decorator (as discussed in [PEP 698](https://peps.python.org/pep-0698/#strict-enforcement-per-project)). This way mypy will detect accidentally introduced overrides. Example:

```python
# mypy: enable-error-code="explicit-override"

from typing_extensions import override

class C:
    def foo(self) -> None: pass
    def bar(self) -> None: pass

class D(C):
    # Error: Method "foo" is not using @override but is
    # overriding a method
    def foo(self) -> None:
        ...

    @override
    def bar(self) -> None:  # OK
        ...
```

You can enable the error code via \--enable-error-code=explicit-override on the mypy command line or enable\_error\_code = explicit-override in the mypy config file.

The override decorator will be available in typing in Python 3.12, but you can also use the backport from a recent version of `typing_extensions` on all supported Python versions.

This feature was contributed by Marc Mueller(PR [15512](https://github.com/python/mypy/pull/15512)).

### More Flexible TypedDict Creation and Update

Mypy was previously overly strict when type checking TypedDict creation and update operations. Though these checks were often technically correct, they sometimes triggered for apparently valid code. These checks have now been relaxed by default. You can enable stricter checking by using the new \--extra-checks flag.

Construction using the `**` syntax is now more flexible:

```python
from typing import TypedDict

class A(TypedDict):
    foo: int
    bar: int

class B(TypedDict):
    foo: int

a: A = {"foo": 1, "bar": 2}
b: B = {"foo": 3}
a2: A = { **a, **b}  # OK (previously an error)
```

You can also call update() with a TypedDict argument that contains a subset of the keys in the updated TypedDict:
```python
a.update(b)  # OK (previously an error)
```

This feature was contributed by Ivan Levkivskyi (PR [15425](https://github.com/python/mypy/pull/15425)).

### Deprecated Flag: \--strict-concatenate

The behavior of \--strict-concatenate is now included in the new \--extra-checks flag, and the old flag is deprecated.

### Optionally Show Links to Error Code Documentation

If you use \--show-error-code-links, mypy will add documentation links to (many) reported errors. The links are not shown for error messages that are sufficiently obvious, and they are shown once per error code only.

Example output:
```
a.py:1: error: Need type annotation for "foo" (hint: "x: List[<type>] = ...")  [var-annotated]
a.py:1: note: See https://mypy.rtfd.io/en/stable/_refs.html#code-var-annotated for more info
```
This was contributed by Ivan Levkivskyi (PR [15449](https://github.com/python/mypy/pull/15449)).

### Consistently Avoid Type Checking Unreachable Code

If a module top level has unreachable code, mypy won’t type check the unreachable statements. This is consistent with how functions behave. The behavior of \--warn-unreachable is also more consistent now.

This was contributed by Ilya Priven (PR [15386](https://github.com/python/mypy/pull/15386)).

### Experimental Improved Type Inference for Generic Functions

You can use \--new-type-inference to opt into an experimental new type inference algorithm. It fixes issues when calling a generic functions with an argument that is also a generic function, in particular. This current implementation is still incomplete, but we encourage trying it out and reporting bugs if you encounter regressions. We are planning to enable the new algorithm by default in a future mypy release.

This feature was contributed by Ivan Levkivskyi (PR [15287](https://github.com/python/mypy/pull/15287)).

### Partial Support for Python 3.12

Mypy and mypyc now support running on recent Python 3.12 development versions. Not all new Python 3.12 features are supported, and we don’t ship compiled wheels for Python 3.12 yet.

*   Fix ast warnings for Python 3.12 (Nikita Sobolev, PR [15558](https://github.com/python/mypy/pull/15558))
*   mypyc: Fix multiple inheritance with a protocol on Python 3.12 (Jukka Lehtosalo, PR [15572](https://github.com/python/mypy/pull/15572))
*   mypyc: Fix self-compilation on Python 3.12 (Jukka Lehtosalo, PR [15582](https://github.com/python/mypy/pull/15582))
*   mypyc: Fix 3.12 issue with pickling of instances with \_\_dict\_\_ (Jukka Lehtosalo, PR [15574](https://github.com/python/mypy/pull/15574))
*   mypyc: Fix i16 on Python 3.12 (Jukka Lehtosalo, PR [15510](https://github.com/python/mypy/pull/15510))
*   mypyc: Fix int operations on Python 3.12 (Jukka Lehtosalo, PR [15470](https://github.com/python/mypy/pull/15470))
*   mypyc: Fix generators on Python 3.12 (Jukka Lehtosalo, PR [15472](https://github.com/python/mypy/pull/15472))
*   mypyc: Fix classes with \_\_dict\_\_ on 3.12 (Jukka Lehtosalo, PR [15471](https://github.com/python/mypy/pull/15471))
*   mypyc: Fix coroutines on Python 3.12 (Jukka Lehtosalo, PR [15469](https://github.com/python/mypy/pull/15469))
*   mypyc: Don't use \_PyErr\_ChainExceptions on 3.12, since it's deprecated (Jukka Lehtosalo, PR [15468](https://github.com/python/mypy/pull/15468))
*   mypyc: Add Python 3.12 feature macro (Jukka Lehtosalo, PR [15465](https://github.com/python/mypy/pull/15465))

### Improvements to Dataclasses

*   Improve signature of dataclasses.replace (Ilya Priven, PR [14849](https://github.com/python/mypy/pull/14849))
*   Fix dataclass/protocol crash on joining types (Ilya Priven, PR [15629](https://github.com/python/mypy/pull/15629))
*   Fix strict optional handling in dataclasses (Ivan Levkivskyi, PR [15571](https://github.com/python/mypy/pull/15571))
*   Support optional types for custom dataclass descriptors (Marc Mueller, PR [15628](https://github.com/python/mypy/pull/15628))
*   Add `__slots__` attribute to dataclasses (Nikita Sobolev, PR [15649](https://github.com/python/mypy/pull/15649))
*   Support better \_\_post\_init\_\_ method signature for dataclasses (Nikita Sobolev, PR [15503](https://github.com/python/mypy/pull/15503))

### Mypyc Improvements

*   Support unsigned 8-bit native integer type: mypy\_extensions.u8 (Jukka Lehtosalo, PR [15564](https://github.com/python/mypy/pull/15564))
*   Support signed 16-bit native integer type: mypy\_extensions.i16 (Jukka Lehtosalo, PR [15464](https://github.com/python/mypy/pull/15464))
*   Define mypy\_extensions.i16 in stubs (Jukka Lehtosalo, PR [15562](https://github.com/python/mypy/pull/15562))
*   Document more unsupported features and update supported features (Richard Si, PR [15524](https://github.com/python/mypy/pull/15524))
*   Fix final NamedTuple classes (Richard Si, PR [15513](https://github.com/python/mypy/pull/15513))
*   Use C99 compound literals for undefined tuple values (Jukka Lehtosalo, PR [15453](https://github.com/python/mypy/pull/15453))
*   Don't explicitly assign NULL values in setup functions (Logan Hunt, PR [15379](https://github.com/python/mypy/pull/15379))

### Stubgen Improvements

*   Teach stubgen to work with complex and unary expressions (Nikita Sobolev, PR [15661](https://github.com/python/mypy/pull/15661))
*   Support ParamSpec and TypeVarTuple (Ali Hamdan, PR [15626](https://github.com/python/mypy/pull/15626))
*   Fix crash on non-str docstring (Ali Hamdan, PR [15623](https://github.com/python/mypy/pull/15623))

### Documentation Updates

*   Add documentation for additional error codes (Ivan Levkivskyi, PR [15539](https://github.com/python/mypy/pull/15539))
*   Improve documentation of type narrowing (Ilya Priven, PR [15652](https://github.com/python/mypy/pull/15652))
*   Small improvements to protocol documentation (Shantanu, PR [15460](https://github.com/python/mypy/pull/15460))
*   Remove confusing instance variable example in cheat sheet (Adel Atallah, PR [15441](https://github.com/python/mypy/pull/15441))

### Other Notable Fixes and Improvements

*   Constant fold additional unary and binary expressions (Richard Si, PR [15202](https://github.com/python/mypy/pull/15202))
*   Exclude the same special attributes from Protocol as CPython (Kyle Benesch, PR [15490](https://github.com/python/mypy/pull/15490))
*   Change the default value of the slots argument of attrs.define to True, to match runtime behavior (Ilya Priven, PR [15642](https://github.com/python/mypy/pull/15642))
*   Fix type of class attribute if attribute is defined in both class and metaclass (Alex Waygood, PR [14988](https://github.com/python/mypy/pull/14988))
*   Handle type the same as typing.Type in the first argument of classmethods (Erik Kemperman, PR [15297](https://github.com/python/mypy/pull/15297))
*   Fix \--find-occurrences flag (Shantanu, PR [15528](https://github.com/python/mypy/pull/15528))
*   Fix error location for class patterns (Nikita Sobolev, PR [15506](https://github.com/python/mypy/pull/15506))
*   Fix re-added file with errors in mypy daemon (Ivan Levkivskyi, PR [15440](https://github.com/python/mypy/pull/15440))
*   Fix dmypy run on Windows (Ivan Levkivskyi, PR [15429](https://github.com/python/mypy/pull/15429))
*   Fix abstract and non-abstract variant error for property deleter (Shantanu, PR [15395](https://github.com/python/mypy/pull/15395))
*   Remove special casing for "cannot" in error messages (Ilya Priven, PR [15428](https://github.com/python/mypy/pull/15428))
*   Add runtime `__slots__` attribute to attrs classes (Nikita Sobolev, PR [15651](https://github.com/python/mypy/pull/15651))
*   Add get\_expression\_type to CheckerPluginInterface (Ilya Priven, PR [15369](https://github.com/python/mypy/pull/15369))
*   Remove parameters that no longer exist from NamedTuple.\_make() (Alex Waygood, PR [15578](https://github.com/python/mypy/pull/15578))
*   Allow using typing.Self in `__all__` with an explicit @staticmethod decorator (Erik Kemperman, PR [15353](https://github.com/python/mypy/pull/15353))
*   Fix self types in subclass methods without Self annotation (Ivan Levkivskyi, PR [15541](https://github.com/python/mypy/pull/15541))
*   Check for abstract class objects in tuples (Nikita Sobolev, PR [15366](https://github.com/python/mypy/pull/15366))

### Typeshed Updates

Typeshed is now modular and distributed as separate PyPI packages for everything except the standard library stubs. Please see [git log](https://github.com/python/typeshed/commits/main?after=fc7d4722eaa54803926cee5730e1f784979c0531+0&branch=main&path=stdlib) for full list of typeshed changes.

### Acknowledgements

Thanks to all mypy contributors who contributed to this release:

*   Adel Atallah
*   Alex Waygood
*   Ali Hamdan
*   Erik Kemperman
*   Federico Padua
*   Ilya Priven
*   Ivan Levkivskyi
*   Jelle Zijlstra
*   Jared Hance
*   Jukka Lehtosalo
*   Kyle Benesch
*   Logan Hunt
*   Marc Mueller
*   Nikita Sobolev
*   Richard Si
*   Shantanu
*   Stavros Ntentos
*   Valentin Stanciu

Posted by Valentin Stanciu


## Mypy 1.4

[Tuesday, 20 June 2023](https://mypy-lang.blogspot.com/2023/06/mypy-140-released.html)

We’ve just uploaded mypy 1.4 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### The Override Decorator

Mypy can now ensure that when renaming a method, overrides are also renamed. You can explicitly mark a method as overriding a base class method by using the @typing.override decorator ([PEP 698](https://peps.python.org/pep-0698/)). If the method is then renamed in the base class while the method override is not, mypy will generate an error. The decorator will be available in typing in Python 3.12, but you can also use the backport from a recent version of `typing_extensions` on all supported Python versions.

This feature was contributed byThomas M Kehrenberg (PR [14609](https://github.com/python/mypy/pull/14609)).

### Propagating Type Narrowing to Nested Functions

Previously, type narrowing was not propagated to nested functions because it would not be sound if the narrowed variable changed between the definition of the nested function and the call site. Mypy will now propagate the narrowed type if the variable is not assigned to after the definition of the nested function:

```python
def outer(x: str | None = None) -> None:
    if x is None:
        x = calculate_default()
    reveal_type(x)  # "str" (narrowed)

    def nested() -> None:
        reveal_type(x)  # Now "str" (used to be "str | None")

    nested()
```

This may generate some new errors because asserts that were previously necessary may become tautological or no-ops.

This was contributed by Jukka Lehtosalo (PR [15133](https://github.com/python/mypy/pull/15133)).

### Narrowing Enum Values Using “==”

Mypy now allows narrowing enum types using the \== operator. Previously this was only supported when using the is operator. This makes exhaustiveness checking with enum types more usable, as the requirement to use the is operator was not very intuitive. In this example mypy can detect that the developer forgot to handle the value MyEnum.C in example

```python
from enum import Enum

class MyEnum(Enum):
    A = 0
    B = 1
    C = 2

def example(e: MyEnum) -> str:  # Error: Missing return statement
    if e == MyEnum.A:
        return 'x'
    elif e == MyEnum.B:
        return 'y'
```

Adding an extra elif case resolves the error:

```python
...
def example(e: MyEnum) -> str:  # No error -- all values covered
    if e == MyEnum.A:
        return 'x'
    elif e == MyEnum.B:
        return 'y'
    elif e == MyEnum.C:
        return 'z'
```

This change can cause false positives in test cases that have assert statements like assert o.x == SomeEnum.X when using \--strict-equality. Example:

```python
# mypy: strict-equality

from enum import Enum

class MyEnum(Enum):
    A = 0
    B = 1

class C:
    x: MyEnum
    ...

def test_something() -> None:
    c = C(...)
    assert c.x == MyEnum.A
    c.do_something_that_changes_x()
    assert c.x == MyEnum.B  # Error: Non-overlapping equality check
```

These errors can be ignored using \# type: ignore\[comparison-overlap\], or you can perform the assertion using a temporary variable as a workaround:

```python
...
def test_something() -> None:
    ...
    x = c.x
    assert x == MyEnum.A  # Does not narrow c.x
    c.do_something_that_changes_x()
    x = c.x
    assert x == MyEnum.B  # OK
```

This feature was contributed by Shantanu (PR [11521](https://github.com/python/mypy/pull/11521)).

### Performance Improvements

*   Speed up simplification of large union types and also fix a recursive tuple crash (Shantanu, PR [15128](https://github.com/python/mypy/pull/15128))
*   Speed up union subtyping (Shantanu, PR [15104](https://github.com/python/mypy/pull/15104))
*   Don't type check most function bodies when type checking third-party library code, or generally when ignoring errors (Jukka Lehtosalo, PR [14150](https://github.com/python/mypy/pull/14150))

### Improvements to Plugins

*   attrs.evolve: Support generics and unions (Ilya Konstantinov, PR [15050](https://github.com/python/mypy/pull/15050))
*   Fix ctypes plugin (Alex Waygood)

### Fixes to Crashes

*   Fix a crash when function-scope recursive alias appears as upper bound (Ivan Levkivskyi, PR [15159](https://github.com/python/mypy/pull/15159))
*   Fix crash on follow\_imports\_for\_stubs (Ivan Levkivskyi, PR [15407](https://github.com/python/mypy/pull/15407))
*   Fix stubtest crash in explicit init subclass (Shantanu, PR [15399](https://github.com/python/mypy/pull/15399))
*   Fix crash when indexing TypedDict with empty key (Shantanu, PR [15392](https://github.com/python/mypy/pull/15392))
*   Fix crash on NamedTuple as attribute (Ivan Levkivskyi, PR [15404](https://github.com/python/mypy/pull/15404))
*   Correctly track loop depth for nested functions/classes (Ivan Levkivskyi, PR [15403](https://github.com/python/mypy/pull/15403))
*   Fix crash on joins with recursive tuples (Ivan Levkivskyi, PR [15402](https://github.com/python/mypy/pull/15402))
*   Fix crash with custom ErrorCode subclasses (Marc Mueller, PR [15327](https://github.com/python/mypy/pull/15327))
*   Fix crash in dataclass protocol with self attribute assignment (Ivan Levkivskyi, PR [15157](https://github.com/python/mypy/pull/15157))
*   Fix crash on lambda in generic context with generic method in body (Ivan Levkivskyi, PR [15155](https://github.com/python/mypy/pull/15155))
*   Fix recursive type alias crash in make\_simplified\_union (Ivan Levkivskyi, PR [15216](https://github.com/python/mypy/pull/15216))

### Improvements to Error Messages

*   Use lower-case built-in collection types such as list\[…\] instead of List\[…\] in errors when targeting Python 3.9+ (Max Murin, PR [15070](https://github.com/python/mypy/pull/15070))
*   Use X | Y union syntax in error messages when targeting Python 3.10+ (Omar Silva, PR [15102](https://github.com/python/mypy/pull/15102))
*   Use type instead of Type in errors when targeting Python 3.9+ (Rohit Sanjay, PR [15139](https://github.com/python/mypy/pull/15139))
*   Do not show unused-ignore errors in unreachable code, and make it a real error code (Ivan Levkivskyi, PR [15164](https://github.com/python/mypy/pull/15164))
*   Don’t limit the number of errors shown by default (Rohit Sanjay, PR [15138](https://github.com/python/mypy/pull/15138))
*   Improver message for truthy functions (madt2709, PR [15193](https://github.com/python/mypy/pull/15193))
*   Output distinct types when type names are ambiguous (teresa0605, PR [15184](https://github.com/python/mypy/pull/15184))
*   Update message about invalid exception type in try (AJ Rasmussen, PR [15131](https://github.com/python/mypy/pull/15131))
*   Add explanation if argument type is incompatible because of an unsupported numbers type (Jukka Lehtosalo, PR [15137](https://github.com/python/mypy/pull/15137))
*   Add more detail to 'signature incompatible with supertype' messages for non-callables (Ilya Priven, PR [15263](https://github.com/python/mypy/pull/15263))

### Documentation Updates

*   Add \--local-partial-types note to dmypy docs (Alan Du, PR [15259](https://github.com/python/mypy/pull/15259))
*   Update getting started docs for mypyc for Windows (Valentin Stanciu, PR [15233](https://github.com/python/mypy/pull/15233))
*   Clarify usage of callables regarding type object in docs (Viicos, PR [15079](https://github.com/python/mypy/pull/15079))
*   Clarify difference between disallow\_untyped\_defs and disallow\_incomplete\_defs (Ilya Priven, PR [15247](https://github.com/python/mypy/pull/15247))
*   Use attrs and @attrs.define in documentation and tests (Ilya Priven, PR [15152](https://github.com/python/mypy/pull/15152))

### Mypyc Improvements

*   Fix unexpected TypeError for certain variables with an inferred optional type (Richard Si, PR [15206](https://github.com/python/mypy/pull/15206))
*   Inline math literals (Logan Hunt, PR [15324](https://github.com/python/mypy/pull/15324))
*   Support unpacking mappings in dict display (Richard Si, PR [15203](https://github.com/python/mypy/pull/15203))

### Changes to Stubgen

*   Do not remove Generic from base classes (Ali Hamdan, PR [15316](https://github.com/python/mypy/pull/15316))
*   Support yield from statements (Ali Hamdan, PR [15271](https://github.com/python/mypy/pull/15271))
*   Fix missing total from TypedDict class (Ali Hamdan, PR [15208](https://github.com/python/mypy/pull/15208))
*   Fix call-based namedtuple omitted from class bases (Ali Hamdan, PR [14680](https://github.com/python/mypy/pull/14680))
*   Support TypedDict alternative syntax (Ali Hamdan, PR [14682](https://github.com/python/mypy/pull/14682))
*   Make stubgen respect MYPY\_CACHE\_DIR (Henrik Bäärnhielm, PR [14722](https://github.com/python/mypy/pull/14722))
*   Fixes and simplifications (Ali Hamdan, PR [15232](https://github.com/python/mypy/pull/15232))

### Other Notable Fixes and Improvements

*   Fix nested async functions when using TypeVar value restriction (Jukka Lehtosalo, PR [14705](https://github.com/python/mypy/pull/14705))
*   Always allow returning Any from lambda (Ivan Levkivskyi, PR [15413](https://github.com/python/mypy/pull/15413))
*   Add foundation for TypeVar defaults (PEP 696) (Marc Mueller, PR [14872](https://github.com/python/mypy/pull/14872))
*   Update semantic analyzer for TypeVar defaults (PEP 696) (Marc Mueller, PR [14873](https://github.com/python/mypy/pull/14873))
*   Make dict expression inference more consistent (Ivan Levkivskyi, PR [15174](https://github.com/python/mypy/pull/15174))
*   Do not block on duplicate base classes (Nikita Sobolev, PR [15367](https://github.com/python/mypy/pull/15367))
*   Generate an error when both staticmethod and classmethod decorators are used (Juhi Chandalia, PR [15118](https://github.com/python/mypy/pull/15118))
*   Fix assert\_type behaviour with literals (Carl Karsten, PR [15123](https://github.com/python/mypy/pull/15123))
*   Fix match subject ignoring redefinitions (Vincent Vanlaer, PR [15306](https://github.com/python/mypy/pull/15306))
*   Support `__all__`.remove (Shantanu, PR [15279](https://github.com/python/mypy/pull/15279))

### Typeshed Updates

Typeshed is now modular and distributed as separate PyPI packages for everything except the standard library stubs. Please see [git log](https://github.com/python/typeshed/commits/main?after=877e06ad1cfd9fd9967c0b0340a86d0c23ea89ce+0&branch=main&path=stdlib) for full list of typeshed changes.

### Acknowledgements

Thanks to all mypy contributors who contributed to this release:

*   Adrian Garcia Badaracco
*   AJ Rasmussen
*   Alan Du
*   Alex Waygood
*   Ali Hamdan
*   Carl Karsten
*   dosisod
*   Ethan Smith
*   Gregory Santosa
*   Heather White
*   Henrik Bäärnhielm
*   Ilya Konstantinov
*   Ilya Priven
*   Ivan Levkivskyi
*   Juhi Chandalia
*   Jukka Lehtosalo
*   Logan Hunt
*   madt2709
*   Marc Mueller
*   Max Murin
*   Nikita Sobolev
*   Omar Silva
*   Özgür
*   Richard Si
*   Rohit Sanjay
*   Shantanu
*   teresa0605
*   Thomas M Kehrenberg
*   Tin Tvrtković
*   Tushar Sadhwani
*   Valentin Stanciu
*   Viicos
*   Vincent Vanlaer
*   Wesley Collin Wright
*   William Santosa
*   yaegassy

I’d also like to thank my employer, Dropbox, for supporting mypy development.

Posted by Jared Hance


## Mypy 1.3

[Wednesday, 10 May 2023](https://mypy-lang.blogspot.com/2023/05/mypy-13-released.html)

 We’ve just uploaded mypy 1.3 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Performance Improvements

*   Improve performance of union subtyping (Shantanu, PR [15104](https://github.com/python/mypy/pull/15104))
*   Add negative subtype caches (Ivan Levkivskyi, PR [14884](https://github.com/python/mypy/pull/14884))

### Stub Tooling Improvements

*   Stubtest: Check that the stub is abstract if the runtime is, even when the stub is an overloaded method (Alex Waygood, PR [14955](https://github.com/python/mypy/pull/14955))
*   Stubtest: Verify stub methods or properties are decorated with @final if they are decorated with @final at runtime (Alex Waygood, PR [14951](https://github.com/python/mypy/pull/14951))
*   Stubtest: Fix stubtest false positives with TypedDicts at runtime (Alex Waygood, PR [14984](https://github.com/python/mypy/pull/14984))
*   Stubgen: Support @functools.cached\_property (Nikita Sobolev, PR [14981](https://github.com/python/mypy/pull/14981))
*   Improvements to stubgenc (Chad Dombrova, PR [14564](https://github.com/python/mypy/pull/14564))

### Improvements to attrs

*   Add support for converters with TypeVars on generic attrs classes (Chad Dombrova, PR [14908](https://github.com/python/mypy/pull/14908))
*   Fix attrs.evolve on bound TypeVar (Ilya Konstantinov, PR [15022](https://github.com/python/mypy/pull/15022))

### Documentation Updates

*   Improve async documentation (Shantanu, PR [14973](https://github.com/python/mypy/pull/14973))
*   Improvements to cheat sheet (Shantanu, PR [14972](https://github.com/python/mypy/pull/14972))
*   Add documentation for bytes formatting error code (Shantanu, PR [14971](https://github.com/python/mypy/pull/14971))
*   Convert insecure links to use HTTPS (Marti Raudsepp, PR [14974](https://github.com/python/mypy/pull/14974))
*   Also mention overloads in async iterator documentation (Shantanu, PR [14998](https://github.com/python/mypy/pull/14998))
*   stubtest: Improve allowlist documentation (Shantanu, PR [15008](https://github.com/python/mypy/pull/15008))
*   Clarify "Using types... but not at runtime" (Jon Shea, PR [15029](https://github.com/python/mypy/pull/15029))
*   Fix alignment of cheat sheet example (Ondřej Cvacho, PR [15039](https://github.com/python/mypy/pull/15039))
*   Fix error for callback protocol matching against callable type object (Shantanu, PR [15042](https://github.com/python/mypy/pull/15042))

### Error Reporting Improvements

*   Improve bytes formatting error (Shantanu, PR [14959](https://github.com/python/mypy/pull/14959))

### Mypyc Improvements

*   Fix unions of bools and ints (Tomer Chachamu, PR [15066](https://github.com/python/mypy/pull/15066))

### Other Fixes and Improvements

*   Fix narrowing union types that include Self with isinstance (Christoph Tyralla, PR [14923](https://github.com/python/mypy/pull/14923))
*   Allow objects matching SupportsKeysAndGetItem to be unpacked (Bryan Forbes, PR [14990](https://github.com/python/mypy/pull/14990))
*   Check type guard validity for staticmethods (EXPLOSION, PR [14953](https://github.com/python/mypy/pull/14953))
*   Fix sys.platform when cross-compiling with emscripten (Ethan Smith, PR [14888](https://github.com/python/mypy/pull/14888))

### Typeshed Updates

Typeshed is now modular and distributed as separate PyPI packages for everything except the standard library stubs. Please see [git log](https://github.com/python/typeshed/commits/main?after=b0ed50e9392a23e52445b630a808153e0e256976+0&branch=main&path=stdlib) for full list of typeshed changes.

### Acknowledgements

Thanks to all mypy contributors who contributed to this release:

*   Alex Waygood
*   Amin Alaee
*   Bryan Forbes
*   Chad Dombrova
*   Charlie Denton
*   Christoph Tyralla
*   dosisod
*   Ethan Smith
*   EXPLOSION
*   Ilya Konstantinov
*   Ivan Levkivskyi
*   Jon Shea
*   Jukka Lehtosalo
*   KotlinIsland
*   Marti Raudsepp
*   Nikita Sobolev
*   Ondřej Cvacho
*   Shantanu
*   sobolevn
*   Tomer Chachamu
*   Yaroslav Halchenko

Posted by Wesley Collin Wright.


## Mypy 1.2

[Thursday, 6 April 2023](https://mypy-lang.blogspot.com/2023/04/mypy-12-released.html)

We’ve just uploaded mypy 1.2 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Improvements to Dataclass Transforms

*   Support implicit default for "init" parameter in field specifiers (Wesley Collin Wright and Jukka Lehtosalo, PR [15010](https://github.com/python/mypy/pull/15010))
*   Support descriptors in dataclass transform (Jukka Lehtosalo, PR [15006](https://github.com/python/mypy/pull/15006))
*   Fix frozen\_default in incremental mode (Wesley Collin Wright)
*   Fix frozen behavior for base classes with direct metaclasses (Wesley Collin Wright, PR [14878](https://github.com/python/mypy/pull/14878))

### Mypyc: Native Floats

Mypyc now uses a native, unboxed representation for values of type float. Previously these were heap-allocated Python objects. Native floats are faster and use less memory. Code that uses floating-point operations heavily can be several times faster when using native floats.

Various float operations and math functions also now have optimized implementations. Refer to the [documentation](https://mypyc.readthedocs.io/en/latest/float_operations.html) for a full list.

This can change the behavior of existing code that uses subclasses of float. When assigning an instance of a subclass of float to a variable with the float type, it gets implicitly converted to a float instance when compiled:

```python
from lib import MyFloat  # MyFloat ia a subclass of "float"

def example() -> None:
    x = MyFloat(1.5)
    y: float = x  # Implicit conversion from MyFloat to float
    print(type(y))  # float, not MyFloat
```

Previously, implicit conversions were applied to int subclasses but not float subclasses.

Also, int values can no longer be assigned to a variable with type float in compiled code, since these types now have incompatible representations. An explicit conversion is required:

```python
def example(n: int) -> None:
    a: float = 1  # Error: cannot assign "int" to "float"
    b: float = 1.0  # OK
    c: float = n  # Error
    d: float = float(n)  # OK
```

This restriction only applies to assignments, since they could otherwise narrow down the type of a variable from float to int. int values can still be implicitly converted to float when passed as arguments to functions that expect float values.

Note that mypyc still doesn’t support arrays of unboxed float values. Using list\[float\] involves heap-allocated float objects, since list can only store boxed values. Support for efficient floating point arrays is one of the next major planned mypyc features.

Related changes:

*   Use a native unboxed representation for floats (Jukka Lehtosalo, PR [14880](https://github.com/python/mypy/pull/14880))
*   Document native floats and integers (Jukka Lehtosalo, PR [14927](https://github.com/python/mypy/pull/14927))
*   Fixes to float to int conversion (Jukka Lehtosalo, PR [14936](https://github.com/python/mypy/pull/14936))

### Mypyc: Native Integers

Mypyc now supports signed 32-bit and 64-bit integer types in addition to the arbitrary-precision int type. You can use the types mypy\_extensions.i32 and mypy\_extensions.i64 to speed up code that uses integer operations heavily.

Simple example:
```python
from mypy_extensions import i64

def inc(x: i64) -> i64:
    return x + 1
```

Refer to the [documentation](https://mypyc.readthedocs.io/en/latest/using_type_annotations.html#native-integer-types) for more information. This feature was contributed by Jukka Lehtosalo.

### Other Mypyc Fixes and Improvements

*   Support iterating over a TypedDict (Richard Si, PR [14747](https://github.com/python/mypy/pull/14747))
*   Faster coercions between different tuple types (Jukka Lehtosalo, PR [14899](https://github.com/python/mypy/pull/14899))
*   Faster calls via type aliases (Jukka Lehtosalo, PR [14784](https://github.com/python/mypy/pull/14784))
*   Faster classmethod calls via cls (Jukka Lehtosalo, PR [14789](https://github.com/python/mypy/pull/14789))

### Fixes to Crashes

*   Fix crash on class-level import in protocol definition (Ivan Levkivskyi, PR [14926](https://github.com/python/mypy/pull/14926))
*   Fix crash on single item union of alias (Ivan Levkivskyi, PR [14876](https://github.com/python/mypy/pull/14876))
*   Fix crash on ParamSpec in incremental mode (Ivan Levkivskyi, PR [14885](https://github.com/python/mypy/pull/14885))

### Documentation Updates

*   Update adopting \--strict documentation for 1.0 (Shantanu, PR [14865](https://github.com/python/mypy/pull/14865))
*   Some minor documentation tweaks (Jukka Lehtosalo, PR [14847](https://github.com/python/mypy/pull/14847))
*   Improve documentation of top level mypy: disable-error-code comment (Nikita Sobolev, PR [14810](https://github.com/python/mypy/pull/14810))

### Error Reporting Improvements

*   Add error code to `typing_extensions` suggestion (Shantanu, PR [14881](https://github.com/python/mypy/pull/14881))
*   Add a separate error code for top-level await (Nikita Sobolev, PR [14801](https://github.com/python/mypy/pull/14801))
*   Don’t suggest two obsolete stub packages (Jelle Zijlstra, PR [14842](https://github.com/python/mypy/pull/14842))
*   Add suggestions for pandas-stubs and lxml-stubs (Shantanu, PR [14737](https://github.com/python/mypy/pull/14737))

### Other Fixes and Improvements

*   Multiple inheritance considers callable objects as subtypes of functions (Christoph Tyralla, PR [14855](https://github.com/python/mypy/pull/14855))
*   stubtest: Respect @final runtime decorator and enforce it in stubs (Nikita Sobolev, PR [14922](https://github.com/python/mypy/pull/14922))
*   Fix false positives related to type\[<type-var>\] (sterliakov, PR [14756](https://github.com/python/mypy/pull/14756))
*   Fix duplication of ParamSpec prefixes and properly substitute ParamSpecs (EXPLOSION, PR [14677](https://github.com/python/mypy/pull/14677))
*   Fix line number if `__iter__` is incorrectly reported as missing (Jukka Lehtosalo, PR [14893](https://github.com/python/mypy/pull/14893))
*   Fix incompatible overrides of overloaded generics with self types (Shantanu, PR [14882](https://github.com/python/mypy/pull/14882))
*   Allow SupportsIndex in slice expressions (Shantanu, PR [14738](https://github.com/python/mypy/pull/14738))
*   Support if statements in bodies of dataclasses and classes that use dataclass\_transform (Jacek Chałupka, PR [14854](https://github.com/python/mypy/pull/14854))
*   Allow iterable class objects to be unpacked (including enums) (Alex Waygood, PR [14827](https://github.com/python/mypy/pull/14827))
*   Fix narrowing for walrus expressions used in match statements (Shantanu, PR [14844](https://github.com/python/mypy/pull/14844))
*   Add signature for attr.evolve (Ilya Konstantinov, PR [14526](https://github.com/python/mypy/pull/14526))
*   Fix Any inference when unpacking iterators that don't directly inherit from typing.Iterator (Alex Waygood, PR [14821](https://github.com/python/mypy/pull/14821))
*   Fix unpack with overloaded `__iter__` method (Nikita Sobolev, PR [14817](https://github.com/python/mypy/pull/14817))
*   Reduce size of JSON data in mypy cache (dosisod, PR [14808](https://github.com/python/mypy/pull/14808))
*   Improve “used before definition” checks when a local definition has the same name as a global definition (Stas Ilinskiy, PR [14517](https://github.com/python/mypy/pull/14517))
*   Honor NoReturn as \_\_setitem\_\_ return type to mark unreachable code (sterliakov, PR [12572](https://github.com/python/mypy/pull/12572))

### Typeshed Updates

Typeshed is now modular and distributed as separate PyPI packages for everything except the standard library stubs. Please see [git log](https://github.com/python/typeshed/commits/main?after=a544b75320e97424d2d927605316383c755cdac0+0&branch=main&path=stdlib) for full list of typeshed changes.

### Acknowledgements

Thanks to all mypy contributors who contributed to this release:

*   Alex Waygood
*   Avasam
*   Christoph Tyralla
*   dosisod
*   EXPLOSION
*   Ilya Konstantinov
*   Ivan Levkivskyi
*   Jacek Chałupka
*   Jelle Zijlstra
*   Jukka Lehtosalo
*   Marc Mueller
*   Max Murin
*   Nikita Sobolev
*   Richard Si
*   Shantanu
*   Stas Ilinskiy
*   sterliakov
*   Wesley Collin Wright

Posted by Jukka Lehtosalo


## Mypy 1.1.1

[Monday, 6 March 2023](https://mypy-lang.blogspot.com/2023/03/mypy-111-released.html)

 We’ve just uploaded mypy 1.1.1 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### Support for `dataclass_transform``

This release adds full support for the dataclass\_transform decorator defined in [PEP 681](https://peps.python.org/pep-0681/#decorator-function-example). This allows decorators, base classes, and metaclasses that generate a \_\_init\_\_ method or other methods based on the properties of that class (similar to dataclasses) to have those methods recognized by mypy.

This was contributed by Wesley Collin Wright.

### Dedicated Error Code for Method Assignments

Mypy can’t safely check all assignments to methods (a form of monkey patching), so mypy generates an error by default. To make it easier to ignore this error, mypy now uses the new error code method-assign for this. By disabling this error code in a file or globally, mypy will no longer complain about assignments to methods if the signatures are compatible.

Mypy also supports the old error code assignment for these assignments to prevent a backward compatibility break. More generally, we can use this mechanism in the future if we wish to split or rename another existing error code without causing backward compatibility issues.

This was contributed by Ivan Levkivskyi (PR [14570](https://github.com/python/mypy/pull/14570)).

### Fixes to Crashes

*   Fix a crash on walrus in comprehension at class scope (Ivan Levkivskyi, PR [14556](https://github.com/python/mypy/pull/14556))
*   Fix crash related to value-constrained TypeVar (Shantanu, PR [14642](https://github.com/python/mypy/pull/14642))

### Fixes to Cache Corruption

*   Fix generic TypedDict/NamedTuple caching (Ivan Levkivskyi, PR [14675](https://github.com/python/mypy/pull/14675))

### Mypyc Fixes and Improvements

*   Raise "non-trait base must be first..." error less frequently (Richard Si, PR [14468](https://github.com/python/mypy/pull/14468))
*   Generate faster code for bool comparisons and arithmetic (Jukka Lehtosalo, PR [14489](https://github.com/python/mypy/pull/14489))
*   Optimize \_\_(a)enter\_\_/\_\_(a)exit\_\_ for native classes (Jared Hance, PR [14530](https://github.com/python/mypy/pull/14530))
*   Detect if attribute definition conflicts with base class/trait (Jukka Lehtosalo, PR [14535](https://github.com/python/mypy/pull/14535))
*   Support \_\_(r)divmod\_\_ dunders (Richard Si, PR [14613](https://github.com/python/mypy/pull/14613))
*   Support \_\_pow\_\_, \_\_rpow\_\_, and \_\_ipow\_\_ dunders (Richard Si, PR [14616](https://github.com/python/mypy/pull/14616))
*   Fix crash on star unpacking to underscore (Ivan Levkivskyi, PR [14624](https://github.com/python/mypy/pull/14624))
*   Fix iterating over a union of dicts (Richard Si, PR [14713](https://github.com/python/mypy/pull/14713))

### Fixes to Detecting Undefined Names (used-before-def)

*   Correctly handle walrus operator (Stas Ilinskiy, PR [14646](https://github.com/python/mypy/pull/14646))
*   Handle walrus declaration in match subject correctly (Stas Ilinskiy, PR [14665](https://github.com/python/mypy/pull/14665))

### Stubgen Improvements

Stubgen is a tool for automatically generating draft stubs for libraries.

*   Allow aliases below the top level (Chad Dombrova, PR [14388](https://github.com/python/mypy/pull/14388))
*   Fix crash with PEP 604 union in type variable bound (Shantanu, PR [14557](https://github.com/python/mypy/pull/14557))
*   Preserve PEP 604 unions in generated .pyi files (hamdanal, PR [14601](https://github.com/python/mypy/pull/14601))

### Stubtest Improvements

Stubtest is a tool for testing that stubs conform to the implementations.

*   Update message format so that it’s easier to go to error location (Avasam, PR [14437](https://github.com/python/mypy/pull/14437))
*   Handle name-mangling edge cases better (Alex Waygood, PR [14596](https://github.com/python/mypy/pull/14596))

### Changes to Error Reporting and Messages

*   Add new TypedDict error code typeddict-unknown-key (JoaquimEsteves, PR [14225](https://github.com/python/mypy/pull/14225))
*   Give arguments a more reasonable location in error messages (Max Murin, PR [14562](https://github.com/python/mypy/pull/14562))
*   In error messages, quote just the module's name (Ilya Konstantinov, PR [14567](https://github.com/python/mypy/pull/14567))
*   Improve misleading message about Enum() (Rodrigo Silva, PR [14590](https://github.com/python/mypy/pull/14590))
*   Suggest importing from `typing_extensions` if definition is not in typing (Shantanu, PR [14591](https://github.com/python/mypy/pull/14591))
*   Consistently use type-abstract error code (Ivan Levkivskyi, PR [14619](https://github.com/python/mypy/pull/14619))
*   Consistently use literal-required error code for TypedDicts (Ivan Levkivskyi, PR [14621](https://github.com/python/mypy/pull/14621))
*   Adjust inconsistent dataclasses plugin error messages (Wesley Collin Wright, PR [14637](https://github.com/python/mypy/pull/14637))
*   Consolidate literal bool argument error messages (Wesley Collin Wright, PR [14693](https://github.com/python/mypy/pull/14693))

### Other Fixes and Improvements

*   Check that type guards accept a positional argument (EXPLOSION, PR [14238](https://github.com/python/mypy/pull/14238))
*   Fix bug with in operator used with a union of Container and Iterable (Max Murin, PR [14384](https://github.com/python/mypy/pull/14384))
*   Support protocol inference for type\[T\] via metaclass (Ivan Levkivskyi, PR [14554](https://github.com/python/mypy/pull/14554))
*   Allow overlapping comparisons between bytes-like types (Shantanu, PR [14658](https://github.com/python/mypy/pull/14658))
*   Fix mypy daemon documentation link in README (Ivan Levkivskyi, PR [14644](https://github.com/python/mypy/pull/14644))

### Typeshed Updates

Typeshed is now modular and distributed as separate PyPI packages for everything except the standard library stubs. Please see [git log](https://github.com/python/typeshed/commits/main?after=5ebf892d0710a6e87925b8d138dfa597e7bb11cc+0&branch=main&path=stdlib) for full list of typeshed changes.

### Acknowledgements

Thanks to all mypy contributors who contributed to this release:

*   Alex Waygood
*   Avasam
*   Chad Dombrova
*   dosisod
*   EXPLOSION
*   hamdanal
*   Ilya Konstantinov
*   Ivan Levkivskyi
*   Jared Hance
*   JoaquimEsteves
*   Jukka Lehtosalo
*   Marc Mueller
*   Max Murin
*   Michael Lee
*   Michael R. Crusoe
*   Richard Si
*   Rodrigo Silva
*   Shantanu
*   Stas Ilinskiy
*   Wesley Collin Wright
*   Yilei "Dolee" Yang
*   Yurii Karabas

We’d also like to thank our employer, Dropbox, for funding the mypy core team.

Posted by Max Murin


## Mypy 1.0

[Monday, 6 February 2023](https://mypy-lang.blogspot.com/2023/02/mypy-10-released.html)

We’ve just uploaded mypy 1.0 to the Python Package Index ([PyPI](https://pypi.org/project/mypy/)). Mypy is a static type checker for Python. This release includes new features, performance improvements and bug fixes. You can install it as follows:

    python3 -m pip install -U mypy

You can read the full documentation for this release on [Read the Docs](http://mypy.readthedocs.io).

### New Release Versioning Scheme

Now that mypy reached 1.0, we’ll switch to a new versioning scheme. Mypy version numbers will be of form x.y.z.

Rules:

*   The major release number (x) is incremented if a feature release includes a significant backward incompatible change that affects a significant fraction of users.
*   The minor release number (y) is incremented on each feature release. Minor releases include updated stdlib stubs from typeshed.
*   The point release number (z) is incremented when there are fixes only.

Mypy doesn't use SemVer, since most minor releases have at least minor backward incompatible changes in typeshed, at the very least. Also, many type checking features find new legitimate issues in code. These are not considered backward incompatible changes, unless the number of new errors is very high.

Any significant backward incompatible change must be announced in the blog post for the previous feature release, before making the change. The previous release must also provide a flag to explicitly enable or disable the new behavior (whenever practical), so that users will be able to prepare for the changes and report issues. We should keep the feature flag for at least a few releases after we've switched the default.

See [”Release Process” in the mypy wiki](https://github.com/python/mypy/wiki/Release-Process) for more details and for the most up-to-date version of the versioning scheme.

### Performance Improvements

Mypy 1.0 is up to 40% faster than mypy 0.991 when type checking the Dropbox internal codebase. We also set up a daily job to measure the performance of the most recent development version of mypy to make it easier to track changes in performance.

Many optimizations contributed to this improvement:

*   Improve performance for errors on class with many attributes (Shantanu, PR [14379](https://github.com/python/mypy/pull/14379))
*   Speed up make\_simplified\_union (Jukka Lehtosalo, PR [14370](https://github.com/python/mypy/pull/14370))
*   Micro-optimize get\_proper\_type(s) (Jukka Lehtosalo, PR [14369](https://github.com/python/mypy/pull/14369))
*   Micro-optimize flatten\_nested\_unions (Jukka Lehtosalo, PR [14368](https://github.com/python/mypy/pull/14368))
*   Some semantic analyzer micro-optimizations (Jukka Lehtosalo, PR [14367](https://github.com/python/mypy/pull/14367))
*   A few miscellaneous micro-optimizations (Jukka Lehtosalo, PR [14366](https://github.com/python/mypy/pull/14366))
*   Optimization: Avoid a few uses of contextmanagers in semantic analyzer (Jukka Lehtosalo, PR [14360](https://github.com/python/mypy/pull/14360))
*   Optimization: Enable always defined attributes in Type subclasses (Jukka Lehtosalo, PR [14356](https://github.com/python/mypy/pull/14356))
*   Optimization: Remove expensive context manager in type analyzer (Jukka Lehtosalo, PR [14357](https://github.com/python/mypy/pull/14357))
*   subtypes: fast path for Union/Union subtype check (Hugues, PR [14277](https://github.com/python/mypy/pull/14277))
*   Micro-optimization: avoid Bogus\[int\] types that cause needless boxing (Jukka Lehtosalo, PR [14354](https://github.com/python/mypy/pull/14354))
*   Avoid slow error message logic if errors not shown to user (Jukka Lehtosalo, PR [14336](https://github.com/python/mypy/pull/14336))
*   Speed up the implementation of hasattr() checks (Jukka Lehtosalo, PR [14333](https://github.com/python/mypy/pull/14333))
*   Avoid the use of a context manager in hot code path (Jukka Lehtosalo, PR [14331](https://github.com/python/mypy/pull/14331))
*   Change various type queries into faster bool type queries (Jukka Lehtosalo, PR [14330](https://github.com/python/mypy/pull/14330))
*   Speed up recursive type check (Jukka Lehtosalo, PR [14326](https://github.com/python/mypy/pull/14326))
*   Optimize subtype checking by avoiding a nested function (Jukka Lehtosalo, PR [14325](https://github.com/python/mypy/pull/14325))
*   Optimize type parameter checks in subtype checking (Jukka Lehtosalo, PR [14324](https://github.com/python/mypy/pull/14324))
*   Speed up freshening type variables (Jukka Lehtosalo, PR [14323](https://github.com/python/mypy/pull/14323))
*   Optimize implementation of TypedDict types for \*\*kwds (Jukka Lehtosalo, PR [14316](https://github.com/python/mypy/pull/14316))

### Warn About Variables Used Before Definition

Mypy will now generate an error if you use a variable before it’s defined. This feature is enabled by default. By default mypy reports an error when it infers that a variable is always undefined.
```python
y = x  # E: Name "x" is used before definition [used-before-def]
x = 0
```
This feature was contributed by Stas Ilinskiy.

### Detect Possibly Undefined Variables (Experimental)

A new experimental possibly-undefined error code is now available that will detect variables that may be undefined:
```python
    if b:
        x = 0
    print(x)  # Error: Name "x" may be undefined [possibly-undefined]
```
The error code is disabled be default, since it can generate false positives.

This feature was contributed by Stas Ilinskiy.

### Support the “Self” Type

There is now a simpler syntax for declaring [generic self types](https://mypy.readthedocs.io/en/stable/generics.html#generic-methods-and-generic-self) introduced in [PEP 673](https://peps.python.org/pep-0673/): the Self type. You no longer have to define a type variable to use “self types”, and you can use them with attributes. Example from mypy documentation:
```python
from typing import Self

class Friend:
    other: Self | None = None

    @classmethod
    def make_pair(cls) -> tuple[Self, Self]:
        a, b = cls(), cls()
        a.other = b
        b.other = a
        return a, b

class SuperFriend(Friend):
    pass

# a and b have the inferred type "SuperFriend", not "Friend"
a, b = SuperFriend.make_pair()
```
The feature was introduced in Python 3.11. In earlier Python versions a backport of Self is available in `typing_extensions`.

This was contributed by Ivan Levkivskyi (PR [14041](https://github.com/python/mypy/pull/14041)).

### Support ParamSpec in Type Aliases

ParamSpec and Concatenate can now be used in type aliases. Example:
```python
from typing import ParamSpec, Callable

P = ParamSpec("P")
A = Callable[P, None]

def f(c: A[int, str]) -> None:
    c(1, "x")
```
This feature was contributed by Ivan Levkivskyi (PR [14159](https://github.com/python/mypy/pull/14159)).

### ParamSpec and Generic Self Types No Longer Experimental

Support for ParamSpec ([PEP 612](https://www.python.org/dev/peps/pep-0612/)) and generic self types are no longer considered experimental.

### Miscellaneous New Features

*   Minimal, partial implementation of dataclass\_transform ([PEP 681](https://peps.python.org/pep-0681/)) (Wesley Collin Wright, PR [14523](https://github.com/python/mypy/pull/14523))
*   Add basic support for `typing_extensions`.TypeVar (Marc Mueller, PR [14313](https://github.com/python/mypy/pull/14313))
*   Add \--debug-serialize option (Marc Mueller, PR [14155](https://github.com/python/mypy/pull/14155))
*   Constant fold initializers of final variables (Jukka Lehtosalo, PR [14283](https://github.com/python/mypy/pull/14283))
*   Enable Final instance attributes for attrs (Tin Tvrtković, PR [14232](https://github.com/python/mypy/pull/14232))
*   Allow function arguments as base classes (Ivan Levkivskyi, PR [14135](https://github.com/python/mypy/pull/14135))
*   Allow super() with mixin protocols (Ivan Levkivskyi, PR [14082](https://github.com/python/mypy/pull/14082))
*   Add type inference for dict.keys membership (Matthew Hughes, PR [13372](https://github.com/python/mypy/pull/13372))
*   Generate error for class attribute access if attribute is defined with `__slots__` (Harrison McCarty, PR [14125](https://github.com/python/mypy/pull/14125))
*   Support additional attributes in callback protocols (Ivan Levkivskyi, PR [14084](https://github.com/python/mypy/pull/14084))

### Fixes to Crashes

*   Fix crash on prefixed ParamSpec with forward reference (Ivan Levkivskyi, PR [14569](https://github.com/python/mypy/pull/14569))
*   Fix internal crash when resolving the same partial type twice (Shantanu, PR [14552](https://github.com/python/mypy/pull/14552))
*   Fix crash in daemon mode on new import cycle (Ivan Levkivskyi, PR [14508](https://github.com/python/mypy/pull/14508))
*   Fix crash in mypy daemon (Ivan Levkivskyi, PR [14497](https://github.com/python/mypy/pull/14497))
*   Fix crash on Any metaclass in incremental mode (Ivan Levkivskyi, PR [14495](https://github.com/python/mypy/pull/14495))
*   Fix crash in await inside comprehension outside function (Ivan Levkivskyi, PR [14486](https://github.com/python/mypy/pull/14486))
*   Fix crash in Self type on forward reference in upper bound (Ivan Levkivskyi, PR [14206](https://github.com/python/mypy/pull/14206))
*   Fix a crash when incorrect super() is used outside a method (Ivan Levkivskyi, PR [14208](https://github.com/python/mypy/pull/14208))
*   Fix crash on overriding with frozen attrs (Ivan Levkivskyi, PR [14186](https://github.com/python/mypy/pull/14186))
*   Fix incremental mode crash on generic function appearing in nested position (Ivan Levkivskyi, PR [14148](https://github.com/python/mypy/pull/14148))
*   Fix daemon crash on malformed NamedTuple (Ivan Levkivskyi, PR [14119](https://github.com/python/mypy/pull/14119))
*   Fix crash during ParamSpec inference (Ivan Levkivskyi, PR [14118](https://github.com/python/mypy/pull/14118))
*   Fix crash on nested generic callable (Ivan Levkivskyi, PR [14093](https://github.com/python/mypy/pull/14093))
*   Fix crashes with unpacking SyntaxError (Shantanu, PR [11499](https://github.com/python/mypy/pull/11499))
*   Fix crash on partial type inference within a lambda (Ivan Levkivskyi, PR [14087](https://github.com/python/mypy/pull/14087))
*   Fix crash with enums (Michael Lee, PR [14021](https://github.com/python/mypy/pull/14021))
*   Fix crash with malformed TypedDicts and disllow-any-expr (Michael Lee, PR [13963](https://github.com/python/mypy/pull/13963))

### Error Reporting Improvements

*   More helpful error for missing self (Shantanu, PR [14386](https://github.com/python/mypy/pull/14386))
*   Add error-code truthy-iterable (Marc Mueller, PR [13762](https://github.com/python/mypy/pull/13762))
*   Fix pluralization in error messages (KotlinIsland, PR [14411](https://github.com/python/mypy/pull/14411))

### Mypyc: Support Match Statement

Mypyc can now compile Python 3.10 match statements.

This was contributed by dosisod (PR [13953](https://github.com/python/mypy/pull/13953)).

### Other Mypyc Fixes and Improvements

*   Optimize int(x)/float(x)/complex(x) on instances of native classes (Richard Si, PR [14450](https://github.com/python/mypy/pull/14450))
*   Always emit warnings (Richard Si, PR [14451](https://github.com/python/mypy/pull/14451))
*   Faster bool and integer conversions (Jukka Lehtosalo, PR [14422](https://github.com/python/mypy/pull/14422))
*   Support attributes that override properties (Jukka Lehtosalo, PR [14377](https://github.com/python/mypy/pull/14377))
*   Precompute set literals for "in" operations and iteration (Richard Si, PR [14409](https://github.com/python/mypy/pull/14409))
*   Don't load targets with forward references while setting up non-extension class `__all__` (Richard Si, PR [14401](https://github.com/python/mypy/pull/14401))
*   Compile away NewType type calls (Richard Si, PR [14398](https://github.com/python/mypy/pull/14398))
*   Improve error message for multiple inheritance (Joshua Bronson, PR [14344](https://github.com/python/mypy/pull/14344))
*   Simplify union types (Jukka Lehtosalo, PR [14363](https://github.com/python/mypy/pull/14363))
*   Fixes to union simplification (Jukka Lehtosalo, PR [14364](https://github.com/python/mypy/pull/14364))
*   Fix for typeshed changes to Collection (Shantanu, PR [13994](https://github.com/python/mypy/pull/13994))
*   Allow use of enum.Enum (Shantanu, PR [13995](https://github.com/python/mypy/pull/13995))
*   Fix compiling on Arch Linux (dosisod, PR [13978](https://github.com/python/mypy/pull/13978))

### Documentation Improvements

*   Various documentation and error message tweaks (Jukka Lehtosalo, PR [14574](https://github.com/python/mypy/pull/14574))
*   Improve Generics documentation (Shantanu, PR [14587](https://github.com/python/mypy/pull/14587))
*   Improve protocols documentation (Shantanu, PR [14577](https://github.com/python/mypy/pull/14577))
*   Improve dynamic typing documentation (Shantanu, PR [14576](https://github.com/python/mypy/pull/14576))
*   Improve the Common Issues page (Shantanu, PR [14581](https://github.com/python/mypy/pull/14581))
*   Add a top-level TypedDict page (Shantanu, PR [14584](https://github.com/python/mypy/pull/14584))
*   More improvements to getting started documentation (Shantanu, PR [14572](https://github.com/python/mypy/pull/14572))
*   Move truthy-function documentation from “optional checks” to “enabled by default” (Anders Kaseorg, PR [14380](https://github.com/python/mypy/pull/14380))
*   Avoid use of implicit optional in decorator factory documentation (Tom Schraitle, PR [14156](https://github.com/python/mypy/pull/14156))
*   Clarify documentation surrounding install-types (Shantanu, PR [14003](https://github.com/python/mypy/pull/14003))
*   Improve searchability for module level type ignore errors (Shantanu, PR [14342](https://github.com/python/mypy/pull/14342))
*   Advertise mypy daemon in README (Ivan Levkivskyi, PR [14248](https://github.com/python/mypy/pull/14248))
*   Add link to error codes in README (Ivan Levkivskyi, PR [14249](https://github.com/python/mypy/pull/14249))
*   Document that report generation disables cache (Ilya Konstantinov, PR [14402](https://github.com/python/mypy/pull/14402))
*   Stop saying mypy is beta software (Ivan Levkivskyi, PR [14251](https://github.com/python/mypy/pull/14251))
*   Flycheck-mypy is deprecated, since its functionality was merged to Flycheck (Ivan Levkivskyi, PR [14247](https://github.com/python/mypy/pull/14247))
*   Update code example in "Declaring decorators" (ChristianWitzler, PR [14131](https://github.com/python/mypy/pull/14131))

### Stubtest Improvements

Stubtest is a tool for testing that stubs conform to the implementations.

*   Improve error message for `__all__`\-related errors (Alex Waygood, PR [14362](https://github.com/python/mypy/pull/14362))
*   Improve heuristics for determining whether global-namespace names are imported (Alex Waygood, PR [14270](https://github.com/python/mypy/pull/14270))
*   Catch BaseException on module imports (Shantanu, PR [14284](https://github.com/python/mypy/pull/14284))
*   Associate exported symbol error with `__all__` object\_path (Nikita Sobolev, PR [14217](https://github.com/python/mypy/pull/14217))
*   Add \_\_warningregistry\_\_ to the list of ignored module dunders (Nikita Sobolev, PR [14218](https://github.com/python/mypy/pull/14218))
*   If a default is present in the stub, check that it is correct (Jelle Zijlstra, PR [14085](https://github.com/python/mypy/pull/14085))

### Stubgen Improvements

Stubgen is a tool for automatically generating draft stubs for libraries.

*   Treat dlls as C modules (Shantanu, PR [14503](https://github.com/python/mypy/pull/14503))

### Other Notable Fixes and Improvements

*   Update stub suggestions based on recent typeshed changes (Alex Waygood, PR [14265](https://github.com/python/mypy/pull/14265))
*   Fix attrs protocol check with cache (Marc Mueller, PR [14558](https://github.com/python/mypy/pull/14558))
*   Fix strict equality check if operand item type has custom \_\_eq\_\_ (Jukka Lehtosalo, PR [14513](https://github.com/python/mypy/pull/14513))
*   Don't consider object always truthy (Jukka Lehtosalo, PR [14510](https://github.com/python/mypy/pull/14510))
*   Properly support union of TypedDicts as dict literal context (Ivan Levkivskyi, PR [14505](https://github.com/python/mypy/pull/14505))
*   Properly expand type in generic class with Self and TypeVar with values (Ivan Levkivskyi, PR [14491](https://github.com/python/mypy/pull/14491))
*   Fix recursive TypedDicts/NamedTuples defined with call syntax (Ivan Levkivskyi, PR [14488](https://github.com/python/mypy/pull/14488))
*   Fix type inference issue when a class inherits from Any (Shantanu, PR [14404](https://github.com/python/mypy/pull/14404))
*   Fix false positive on generic base class with six (Ivan Levkivskyi, PR [14478](https://github.com/python/mypy/pull/14478))
*   Don't read scripts without extensions as modules in namespace mode (Tim Geypens, PR [14335](https://github.com/python/mypy/pull/14335))
*   Fix inference for constrained type variables within unions (Christoph Tyralla, PR [14396](https://github.com/python/mypy/pull/14396))
*   Fix Unpack imported from typing (Marc Mueller, PR [14378](https://github.com/python/mypy/pull/14378))
*   Allow trailing commas in ini configuration of multiline values (Nikita Sobolev, PR [14240](https://github.com/python/mypy/pull/14240))
*   Fix false negatives involving Unions and generators or coroutines (Shantanu, PR [14224](https://github.com/python/mypy/pull/14224))
*   Fix ParamSpec constraint for types as callable (Vincent Vanlaer, PR [14153](https://github.com/python/mypy/pull/14153))
*   Fix type aliases with fixed-length tuples (Jukka Lehtosalo, PR [14184](https://github.com/python/mypy/pull/14184))
*   Fix issues with type aliases and new style unions (Jukka Lehtosalo, PR [14181](https://github.com/python/mypy/pull/14181))
*   Simplify unions less aggressively (Ivan Levkivskyi, PR [14178](https://github.com/python/mypy/pull/14178))
*   Simplify callable overlap logic (Ivan Levkivskyi, PR [14174](https://github.com/python/mypy/pull/14174))
*   Try empty context when assigning to union typed variables (Ivan Levkivskyi, PR [14151](https://github.com/python/mypy/pull/14151))
*   Improvements to recursive types (Ivan Levkivskyi, PR [14147](https://github.com/python/mypy/pull/14147))
*   Make non-numeric non-empty FORCE\_COLOR truthy (Shantanu, PR [14140](https://github.com/python/mypy/pull/14140))
*   Fix to recursive type aliases (Ivan Levkivskyi, PR [14136](https://github.com/python/mypy/pull/14136))
*   Correctly handle Enum name on Python 3.11 (Ivan Levkivskyi, PR [14133](https://github.com/python/mypy/pull/14133))
*   Fix class objects falling back to metaclass for callback protocol (Ivan Levkivskyi, PR [14121](https://github.com/python/mypy/pull/14121))
*   Correctly support self types in callable ClassVar (Ivan Levkivskyi, PR [14115](https://github.com/python/mypy/pull/14115))
*   Fix type variable clash in nested positions and in attributes (Ivan Levkivskyi, PR [14095](https://github.com/python/mypy/pull/14095))
*   Allow class variable as implementation for read only attribute (Ivan Levkivskyi, PR [14081](https://github.com/python/mypy/pull/14081))
*   Prevent warnings from causing dmypy to fail (Andrzej Bartosiński, PR [14102](https://github.com/python/mypy/pull/14102))
*   Correctly process nested definitions in mypy daemon (Ivan Levkivskyi, PR [14104](https://github.com/python/mypy/pull/14104))
*   Don't consider a branch unreachable if there is a possible promotion (Ivan Levkivskyi, PR [14077](https://github.com/python/mypy/pull/14077))
*   Fix incompatible overrides of overloaded methods in concrete subclasses (Shantanu, PR [14017](https://github.com/python/mypy/pull/14017))
*   Fix new style union syntax in type aliases (Jukka Lehtosalo, PR [14008](https://github.com/python/mypy/pull/14008))
*   Fix and optimise overload compatibility checking (Shantanu, PR [14018](https://github.com/python/mypy/pull/14018))
*   Improve handling of redefinitions through imports (Shantanu, PR [13969](https://github.com/python/mypy/pull/13969))
*   Preserve (some) implicitly exported types (Shantanu, PR [13967](https://github.com/python/mypy/pull/13967))

### Typeshed Updates

Typeshed is now modular and distributed as separate PyPI packages for everything except the standard library stubs. Please see [git log](https://github.com/python/typeshed/commits/main?after=ea0ae2155e8a04c9837903c3aff8dd5ad5f36ebc+0&branch=main&path=stdlib) for full list of typeshed changes.

### Acknowledgements

Thanks to all mypy contributors who contributed to this release:

*   Alessio Izzo
*   Alex Waygood
*   Anders Kaseorg
*   Andrzej Bartosiński
*   Avasam
*   ChristianWitzler
*   Christoph Tyralla
*   dosisod
*   Harrison McCarty
*   Hugo van Kemenade
*   Hugues
*   Ilya Konstantinov
*   Ivan Levkivskyi
*   Jelle Zijlstra
*   jhance
*   johnthagen
*   Jonathan Daniel
*   Joshua Bronson
*   Jukka Lehtosalo
*   KotlinIsland
*   Lakshay Bisht
*   Lefteris Karapetsas
*   Marc Mueller
*   Matthew Hughes
*   Michael Lee
*   Nick Drozd
*   Nikita Sobolev
*   Richard Si
*   Shantanu
*   Stas Ilinskiy
*   Tim Geypens
*   Tin Tvrtković
*   Tom Schraitle
*   Valentin Stanciu
*   Vincent Vanlaer

We’d also like to thank our employer, Dropbox, for funding the mypy core team.

Posted by Stas Ilinskiy

## Previous releases

For information about previous releases, refer to the posts at https://mypy-lang.blogspot.com/
