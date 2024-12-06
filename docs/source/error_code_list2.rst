.. _error-codes-optional:

Error codes for optional checks
===============================

This section documents various errors codes that mypy generates only
if you enable certain options. See :ref:`error-codes` for general
documentation about error codes and their configuration.
:ref:`error-code-list` documents error codes that are enabled by default.

.. note::

   The examples in this section use :ref:`inline configuration
   <inline-config>` to specify mypy options. You can also set the same
   options by using a :ref:`configuration file <config-file>` or
   :ref:`command-line options <command-line>`.

.. _code-type-arg:

Check that type arguments exist [type-arg]
------------------------------------------

If you use :option:`--disallow-any-generics <mypy --disallow-any-generics>`, mypy requires that each generic
type has values for each type argument. For example, the types ``list`` or
``dict`` would be rejected. You should instead use types like ``list[int]`` or
``dict[str, int]``. Any omitted generic type arguments get implicit ``Any``
values. The type ``list`` is equivalent to ``list[Any]``, and so on.

Example:

.. code-block:: python

    # mypy: disallow-any-generics

    # Error: Missing type parameters for generic type "list"  [type-arg]
    def remove_dups(items: list) -> list:
        ...

.. _code-no-untyped-def:

Check that every function has an annotation [no-untyped-def]
------------------------------------------------------------

If you use :option:`--disallow-untyped-defs <mypy --disallow-untyped-defs>`, mypy requires that all functions
have annotations (either a Python 3 annotation or a type comment).

Example:

.. code-block:: python

    # mypy: disallow-untyped-defs

    def inc(x):  # Error: Function is missing a type annotation  [no-untyped-def]
        return x + 1

    def inc_ok(x: int) -> int:  # OK
        return x + 1

    class Counter:
         # Error: Function is missing a type annotation  [no-untyped-def]
         def __init__(self):
             self.value = 0

    class CounterOk:
         # OK: An explicit "-> None" is needed if "__init__" takes no arguments
         def __init__(self) -> None:
             self.value = 0

.. _code-redundant-cast:

Check that cast is not redundant [redundant-cast]
-------------------------------------------------

If you use :option:`--warn-redundant-casts <mypy --warn-redundant-casts>`, mypy will generate an error if the source
type of a cast is the same as the target type.

Example:

.. code-block:: python

    # mypy: warn-redundant-casts

    from typing import cast

    Count = int

    def example(x: Count) -> int:
        # Error: Redundant cast to "int"  [redundant-cast]
        return cast(int, x)

.. _code-redundant-self:

Check that methods do not have redundant Self annotations [redundant-self]
--------------------------------------------------------------------------

If a method uses the ``Self`` type in the return type or the type of a
non-self argument, there is no need to annotate the ``self`` argument
explicitly. Such annotations are allowed by :pep:`673` but are
redundant. If you enable this error code, mypy will generate an error if
there is a redundant ``Self`` type.

Example:

.. code-block:: python

   # mypy: enable-error-code="redundant-self"

   from typing import Self

   class C:
       # Error: Redundant "Self" annotation for the first method argument
       def copy(self: Self) -> Self:
           return type(self)()

.. _code-comparison-overlap:

Check that comparisons are overlapping [comparison-overlap]
-----------------------------------------------------------

If you use :option:`--strict-equality <mypy --strict-equality>`, mypy will generate an error if it
thinks that a comparison operation is always true or false. These are
often bugs. Sometimes mypy is too picky and the comparison can
actually be useful. Instead of disabling strict equality checking
everywhere, you can use ``# type: ignore[comparison-overlap]`` to
ignore the issue on a particular line only.

Example:

.. code-block:: python

    # mypy: strict-equality

    def is_magic(x: bytes) -> bool:
        # Error: Non-overlapping equality check (left operand type: "bytes",
        #        right operand type: "str")  [comparison-overlap]
        return x == 'magic'

We can fix the error by changing the string literal to a bytes
literal:

.. code-block:: python

    # mypy: strict-equality

    def is_magic(x: bytes) -> bool:
        return x == b'magic'  # OK

.. _code-no-untyped-call:

Check that no untyped functions are called [no-untyped-call]
------------------------------------------------------------

If you use :option:`--disallow-untyped-calls <mypy --disallow-untyped-calls>`, mypy generates an error when you
call an unannotated function in an annotated function.

Example:

.. code-block:: python

    # mypy: disallow-untyped-calls

    def do_it() -> None:
        # Error: Call to untyped function "bad" in typed context  [no-untyped-call]
        bad()

    def bad():
        ...

.. _code-no-any-return:

Check that function does not return Any value [no-any-return]
-------------------------------------------------------------

If you use :option:`--warn-return-any <mypy --warn-return-any>`, mypy generates an error if you return a
value with an ``Any`` type in a function that is annotated to return a
non-``Any`` value.

Example:

.. code-block:: python

    # mypy: warn-return-any

    def fields(s):
         return s.split(',')

    def first_field(x: str) -> str:
        # Error: Returning Any from function declared to return "str"  [no-any-return]
        return fields(x)[0]

.. _code-no-any-unimported:

Check that types have no Any components due to missing imports [no-any-unimported]
----------------------------------------------------------------------------------

If you use :option:`--disallow-any-unimported <mypy --disallow-any-unimported>`, mypy generates an error if a component of
a type becomes ``Any`` because mypy couldn't resolve an import. These "stealth"
``Any`` types can be surprising and accidentally cause imprecise type checking.

In this example, we assume that mypy can't find the module ``animals``, which means
that ``Cat`` falls back to ``Any`` in a type annotation:

.. code-block:: python

    # mypy: disallow-any-unimported

    from animals import Cat  # type: ignore

    # Error: Argument 1 to "feed" becomes "Any" due to an unfollowed import  [no-any-unimported]
    def feed(cat: Cat) -> None:
        ...

.. _code-unreachable:

Check that statement or expression is unreachable [unreachable]
---------------------------------------------------------------

If you use :option:`--warn-unreachable <mypy --warn-unreachable>`, mypy generates an error if it
thinks that a statement or expression will never be executed. In most cases, this is due to
incorrect control flow or conditional checks that are accidentally always true or false.

.. code-block:: python

    # mypy: warn-unreachable

    def example(x: int) -> None:
        # Error: Right operand of "or" is never evaluated  [unreachable]
        assert isinstance(x, int) or x == 'unused'

        return
        # Error: Statement is unreachable  [unreachable]
        print('unreachable')

.. _code-deprecated:

Check that imported or used feature is deprecated [deprecated]
--------------------------------------------------------------

If you use :option:`--enable-error-code deprecated <mypy --enable-error-code>`,
mypy generates an error if your code imports a deprecated feature explicitly with a
``from mod import depr`` statement or uses a deprecated feature imported otherwise or defined
locally.  Features are considered deprecated when decorated with ``warnings.deprecated``, as
specified in `PEP 702 <https://peps.python.org/pep-0702>`_.
Use the :option:`--report-deprecated-as-note <mypy --report-deprecated-as-note>` option to
turn all such errors into notes.

.. note::

    The ``warnings`` module provides the ``@deprecated`` decorator since Python 3.13.
    To use it with older Python versions, import it from ``typing_extensions`` instead.

Examples:

.. code-block:: python

    # mypy: report-deprecated-as-error

    # Error: abc.abstractproperty is deprecated: Deprecated, use 'property' with 'abstractmethod' instead
    from abc import abstractproperty

    from typing_extensions import deprecated

    @deprecated("use new_function")
    def old_function() -> None:
        print("I am old")

    # Error: __main__.old_function is deprecated: use new_function
    old_function()
    old_function()  # type: ignore[deprecated]


.. _code-redundant-expr:

Check that expression is redundant [redundant-expr]
---------------------------------------------------

If you use :option:`--enable-error-code redundant-expr <mypy --enable-error-code>`,
mypy generates an error if it thinks that an expression is redundant.

.. code-block:: python

    # mypy: enable-error-code="redundant-expr"

    def example(x: int) -> None:
        # Error: Left operand of "and" is always true  [redundant-expr]
        if isinstance(x, int) and x > 0:
            pass

        # Error: If condition is always true  [redundant-expr]
        1 if isinstance(x, int) else 0

        # Error: If condition in comprehension is always true  [redundant-expr]
        [i for i in range(x) if isinstance(i, int)]


.. _code-possibly-undefined:

Warn about variables that are defined only in some execution paths [possibly-undefined]
---------------------------------------------------------------------------------------

If you use :option:`--enable-error-code possibly-undefined <mypy --enable-error-code>`,
mypy generates an error if it cannot verify that a variable will be defined in
all execution paths. This includes situations when a variable definition
appears in a loop, in a conditional branch, in an except handler, etc. For
example:

.. code-block:: python

    # mypy: enable-error-code="possibly-undefined"

    from collections.abc import Iterable

    def test(values: Iterable[int], flag: bool) -> None:
        if flag:
            a = 1
        z = a + 1  # Error: Name "a" may be undefined [possibly-undefined]

        for v in values:
            b = v
        z = b + 1  # Error: Name "b" may be undefined [possibly-undefined]

.. _code-truthy-bool:

Check that expression is not implicitly true in boolean context [truthy-bool]
-----------------------------------------------------------------------------

Warn when the type of an expression in a boolean context does not
implement ``__bool__`` or ``__len__``. Unless one of these is
implemented by a subtype, the expression will always be considered
true, and there may be a bug in the condition.

As an exception, the ``object`` type is allowed in a boolean context.
Using an iterable value in a boolean context has a separate error code
(see below).

.. code-block:: python

    # mypy: enable-error-code="truthy-bool"

    class Foo:
        pass
    foo = Foo()
    # Error: "foo" has type "Foo" which does not implement __bool__ or __len__ so it could always be true in boolean context
    if foo:
         ...

.. _code-truthy-iterable:

Check that iterable is not implicitly true in boolean context [truthy-iterable]
-------------------------------------------------------------------------------

Generate an error if a value of type ``Iterable`` is used as a boolean
condition, since ``Iterable`` does not implement ``__len__`` or ``__bool__``.

Example:

.. code-block:: python

    from collections.abc import Iterable

    def transform(items: Iterable[int]) -> list[int]:
        # Error: "items" has type "Iterable[int]" which can always be true in boolean context. Consider using "Collection[int]" instead.  [truthy-iterable]
        if not items:
            return [42]
        return [x + 1 for x in items]

If ``transform`` is called with a ``Generator`` argument, such as
``int(x) for x in []``, this function would not return ``[42]`` unlike
what might be intended. Of course, it's possible that ``transform`` is
only called with ``list`` or other container objects, and the ``if not
items`` check is actually valid. If that is the case, it is
recommended to annotate ``items`` as ``Collection[int]`` instead of
``Iterable[int]``.

.. _code-ignore-without-code:

Check that ``# type: ignore`` include an error code [ignore-without-code]
-------------------------------------------------------------------------

Warn when a ``# type: ignore`` comment does not specify any error codes.
This clarifies the intent of the ignore and ensures that only the
expected errors are silenced.

Example:

.. code-block:: python

    # mypy: enable-error-code="ignore-without-code"

    class Foo:
        def __init__(self, name: str) -> None:
            self.name = name

    f = Foo('foo')

    # This line has a typo that mypy can't help with as both:
    # - the expected error 'assignment', and
    # - the unexpected error 'attr-defined'
    # are silenced.
    # Error: "type: ignore" comment without error code (consider "type: ignore[attr-defined]" instead)
    f.nme = 42  # type: ignore

    # This line warns correctly about the typo in the attribute name
    # Error: "Foo" has no attribute "nme"; maybe "name"?
    f.nme = 42  # type: ignore[assignment]

.. _code-unused-awaitable:

Check that awaitable return value is used [unused-awaitable]
------------------------------------------------------------

If you use :option:`--enable-error-code unused-awaitable <mypy --enable-error-code>`,
mypy generates an error if you don't use a returned value that defines ``__await__``.

Example:

.. code-block:: python

    # mypy: enable-error-code="unused-awaitable"

    import asyncio

    async def f() -> int: ...

    async def g() -> None:
        # Error: Value of type "Task[int]" must be used
        #        Are you missing an await?
        asyncio.create_task(f())

You can assign the value to a temporary, otherwise unused variable to
silence the error:

.. code-block:: python

    async def g() -> None:
        _ = asyncio.create_task(f())  # No error

.. _code-unused-ignore:

Check that ``# type: ignore`` comment is used [unused-ignore]
-------------------------------------------------------------

If you use :option:`--enable-error-code unused-ignore <mypy --enable-error-code>`,
or :option:`--warn-unused-ignores <mypy --warn-unused-ignores>`
mypy generates an error if you don't use a ``# type: ignore`` comment, i.e. if
there is a comment, but there would be no error generated by mypy on this line
anyway.

Example:

.. code-block:: python

    # Use "mypy --warn-unused-ignores ..."

    def add(a: int, b: int) -> int:
        # Error: unused "type: ignore" comment
        return a + b  # type: ignore

Note that due to a specific nature of this comment, the only way to selectively
silence it, is to include the error code explicitly. Also note that this error is
not shown if the ``# type: ignore`` is not used due to code being statically
unreachable (e.g. due to platform or version checks).

Example:

.. code-block:: python

    # Use "mypy --warn-unused-ignores ..."

    import sys

    try:
        # The "[unused-ignore]" is needed to get a clean mypy run
        # on both Python 3.8, and 3.9 where this module was added
        import graphlib  # type: ignore[import,unused-ignore]
    except ImportError:
        pass

    if sys.version_info >= (3, 9):
        # The following will not generate an error on either
        # Python 3.8, or Python 3.9
        42 + "testing..."  # type: ignore

.. _code-explicit-override:

Check that ``@override`` is used when overriding a base class method [explicit-override]
----------------------------------------------------------------------------------------

If you use :option:`--enable-error-code explicit-override <mypy --enable-error-code>`
mypy generates an error if you override a base class method without using the
``@override`` decorator. An error will not be emitted for overrides of ``__init__``
or ``__new__``. See `PEP 698 <https://peps.python.org/pep-0698/#strict-enforcement-per-project>`_.

.. note::

    Starting with Python 3.12, the ``@override`` decorator can be imported from ``typing``.
    To use it with older Python versions, import it from ``typing_extensions`` instead.

Example:

.. code-block:: python

    # mypy: enable-error-code="explicit-override"

    from typing import override

    class Parent:
        def f(self, x: int) -> None:
            pass

        def g(self, y: int) -> None:
            pass


    class Child(Parent):
        def f(self, x: int) -> None:  # Error: Missing @override decorator
            pass

        @override
        def g(self, y: int) -> None:
            pass

.. _code-mutable-override:

Check that overrides of mutable attributes are safe [mutable-override]
----------------------------------------------------------------------

`mutable-override` will enable the check for unsafe overrides of mutable attributes.
For historical reasons, and because this is a relatively common pattern in Python,
this check is not enabled by default. The example below is unsafe, and will be
flagged when this error code is enabled:

.. code-block:: python

    from typing import Any

    class C:
        x: float
        y: float
        z: float

    class D(C):
        x: int  # Error: Covariant override of a mutable attribute
                # (base class "C" defined the type as "float",
                # expression has type "int")  [mutable-override]
        y: float  # OK
        z: Any  # OK

    def f(c: C) -> None:
        c.x = 1.1
    d = D()
    f(d)
    d.x >> 1  # This will crash at runtime, because d.x is now float, not an int

.. _code-unimported-reveal:

Check that ``reveal_type`` is imported from typing or typing_extensions [unimported-reveal]
-------------------------------------------------------------------------------------------

Mypy used to have ``reveal_type`` as a special builtin
that only existed during type-checking.
In runtime it fails with expected ``NameError``,
which can cause real problem in production, hidden from mypy.

But, in Python3.11 :py:func:`typing.reveal_type` was added.
``typing_extensions`` ported this helper to all supported Python versions.

Now users can actually import ``reveal_type`` to make the runtime code safe.

.. note::

    Starting with Python 3.11, the ``reveal_type`` function can be imported from ``typing``.
    To use it with older Python versions, import it from ``typing_extensions`` instead.

.. code-block:: python

    # mypy: enable-error-code="unimported-reveal"

    x = 1
    reveal_type(x)  # Note: Revealed type is "builtins.int" \
                    # Error: Name "reveal_type" is not defined

Correct usage:

.. code-block:: python

    # mypy: enable-error-code="unimported-reveal"
    from typing import reveal_type   # or `typing_extensions`

    x = 1
    # This won't raise an error:
    reveal_type(x)  # Note: Revealed type is "builtins.int"

When this code is enabled, using ``reveal_locals`` is always an error,
because there's no way one can import it.

.. _code-narrowed-type-not-subtype:

Check that ``TypeIs`` narrows types [narrowed-type-not-subtype]
---------------------------------------------------------------

:pep:`742` requires that when ``TypeIs`` is used, the narrowed
type must be a subtype of the original type::

    from typing_extensions import TypeIs

    def f(x: int) -> TypeIs[str]:  # Error, str is not a subtype of int
        ...

    def g(x: object) -> TypeIs[str]:  # OK
        ...
