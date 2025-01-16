.. _common_issues:

Common issues and solutions
===========================

This section has examples of cases when you need to update your code
to use static typing, and ideas for working around issues if mypy
doesn't work as expected. Statically typed code is often identical to
normal Python code (except for type annotations), but sometimes you need
to do things slightly differently.

.. _annotations_needed:

No errors reported for obviously wrong code
-------------------------------------------

There are several common reasons why obviously wrong code is not
flagged as an error.

**The function containing the error is not annotated.**

Functions that
do not have any annotations (neither for any argument nor for the
return type) are not type-checked, and even the most blatant type
errors (e.g. ``2 + 'a'``) pass silently.  The solution is to add
annotations. Where that isn't possible, functions without annotations
can be checked using :option:`--check-untyped-defs <mypy --check-untyped-defs>`.

Example:

.. code-block:: python

    def foo(a):
        return '(' + a.split() + ')'  # No error!

This gives no error even though ``a.split()`` is "obviously" a list
(the author probably meant ``a.strip()``).  The error is reported
once you add annotations:

.. code-block:: python

    def foo(a: str) -> str:
        return '(' + a.split() + ')'
    # error: Unsupported operand types for + ("str" and "list[str]")

If you don't know what types to add, you can use ``Any``, but beware:

**One of the values involved has type 'Any'.**

Extending the above
example, if we were to leave out the annotation for ``a``, we'd get
no error:

.. code-block:: python

    def foo(a) -> str:
        return '(' + a.split() + ')'  # No error!

The reason is that if the type of ``a`` is unknown, the type of
``a.split()`` is also unknown, so it is inferred as having type
``Any``, and it is no error to add a string to an ``Any``.

If you're having trouble debugging such situations,
:ref:`reveal_type() <reveal-type>` might come in handy.

Note that sometimes library stubs with imprecise type information
can be a source of ``Any`` values.

:py:meth:`__init__ <object.__init__>` **method has no annotated
arguments and no return type annotation.**

This is basically a combination of the two cases above, in that ``__init__``
without annotations can cause ``Any`` types leak into instance variables:

.. code-block:: python

    class Bad:
        def __init__(self):
            self.value = "asdf"
            1 + "asdf"  # No error!

    bad = Bad()
    bad.value + 1           # No error!
    reveal_type(bad)        # Revealed type is "__main__.Bad"
    reveal_type(bad.value)  # Revealed type is "Any"

    class Good:
        def __init__(self) -> None:  # Explicitly return None
            self.value = value


**Some imports may be silently ignored**.

A common source of unexpected ``Any`` values is the
:option:`--ignore-missing-imports <mypy --ignore-missing-imports>` flag.

When you use :option:`--ignore-missing-imports <mypy --ignore-missing-imports>`,
any imported module that cannot be found is silently replaced with ``Any``.

To help debug this, simply leave out
:option:`--ignore-missing-imports <mypy --ignore-missing-imports>`.
As mentioned in :ref:`fix-missing-imports`, setting ``ignore_missing_imports=True``
on a per-module basis will make bad surprises less likely and is highly encouraged.

Use of the :option:`--follow-imports=skip <mypy --follow-imports>` flags can also
cause problems. Use of these flags is strongly discouraged and only required in
relatively niche situations. See :ref:`follow-imports` for more information.

**mypy considers some of your code unreachable**.

See :ref:`unreachable` for more information.

**A function annotated as returning a non-optional type returns 'None'
and mypy doesn't complain**.

.. code-block:: python

    def foo() -> str:
        return None  # No error!

You may have disabled strict optional checking (see
:ref:`--no-strict-optional <no_strict_optional>` for more).

.. _silencing_checker:

Spurious errors and locally silencing the checker
-------------------------------------------------

You can use a ``# type: ignore`` comment to silence the type checker
on a particular line. For example, let's say our code is using
the C extension module ``frobnicate``, and there's no stub available.
Mypy will complain about this, as it has no information about the
module:

.. code-block:: python

    import frobnicate  # Error: No module "frobnicate"
    frobnicate.start()

You can add a ``# type: ignore`` comment to tell mypy to ignore this
error:

.. code-block:: python

    import frobnicate  # type: ignore
    frobnicate.start()  # Okay!

The second line is now fine, since the ignore comment causes the name
``frobnicate`` to get an implicit ``Any`` type.

.. note::

    You can use the form ``# type: ignore[<code>]`` to only ignore
    specific errors on the line. This way you are less likely to
    silence unexpected errors that are not safe to ignore, and this
    will also document what the purpose of the comment is.  See
    :ref:`error-codes` for more information.

.. note::

    The ``# type: ignore`` comment will only assign the implicit ``Any``
    type if mypy cannot find information about that particular module. So,
    if we did have a stub available for ``frobnicate`` then mypy would
    ignore the ``# type: ignore`` comment and typecheck the stub as usual.

Another option is to explicitly annotate values with type ``Any`` --
mypy will let you perform arbitrary operations on ``Any``
values. Sometimes there is no more precise type you can use for a
particular value, especially if you use dynamic Python features
such as :py:meth:`__getattr__ <object.__getattr__>`:

.. code-block:: python

   class Wrapper:
       ...
       def __getattr__(self, a: str) -> Any:
           return getattr(self._wrapped, a)

Finally, you can create a stub file (``.pyi``) for a file that
generates spurious errors. Mypy will only look at the stub file
and ignore the implementation, since stub files take precedence
over ``.py`` files.

Ignoring a whole file
---------------------

* To only ignore errors, use a top-level ``# mypy: ignore-errors`` comment instead.
* To only ignore errors with a specific error code, use a top-level
  ``# mypy: disable-error-code="..."`` comment. Example: ``# mypy: disable-error-code="truthy-bool, ignore-without-code"``
* To replace the contents of a module with ``Any``, use a per-module ``follow_imports = skip``.
  See :ref:`Following imports <follow-imports>` for details.

Note that a ``# type: ignore`` comment at the top of a module (before any statements,
including imports or docstrings) has the effect of ignoring the entire contents of the module.
This behaviour can be surprising and result in
"Module ... has no attribute ... [attr-defined]" errors.

Issues with code at runtime
---------------------------

Idiomatic use of type annotations can sometimes run up against what a given
version of Python considers legal code. These can result in some of the
following errors when trying to run your code:

* ``ImportError`` from circular imports
* ``NameError: name "X" is not defined`` from forward references
* ``TypeError: 'type' object is not subscriptable`` from types that are not generic at runtime
* ``ImportError`` or ``ModuleNotFoundError`` from use of stub definitions not available at runtime
* ``TypeError: unsupported operand type(s) for |: 'type' and 'type'`` from use of new syntax

For dealing with these, see :ref:`runtime_troubles`.

Mypy runs are slow
------------------

If your mypy runs feel slow, you should probably use the :ref:`mypy
daemon <mypy_daemon>`, which can speed up incremental mypy runtimes by
a factor of 10 or more. :ref:`Remote caching <remote-cache>` can
make cold mypy runs several times faster.

Types of empty collections
--------------------------

You often need to specify the type when you assign an empty list or
dict to a new variable, as mentioned earlier:

.. code-block:: python

   a: list[int] = []

Without the annotation mypy can't always figure out the
precise type of ``a``.

You can use a simple empty list literal in a dynamically typed function (as the
type of ``a`` would be implicitly ``Any`` and need not be inferred), if type
of the variable has been declared or inferred before, or if you perform a simple
modification operation in the same scope (such as ``append`` for a list):

.. code-block:: python

   a = []  # Okay because followed by append, inferred type list[int]
   for i in range(n):
       a.append(i * i)

However, in more complex cases an explicit type annotation can be
required (mypy will tell you this). Often the annotation can
make your code easier to understand, so it doesn't only help mypy but
everybody who is reading the code!

Redefinitions with incompatible types
-------------------------------------

Each name within a function only has a single 'declared' type. You can
reuse for loop indices etc., but if you want to use a variable with
multiple types within a single function, you may need to instead use
multiple variables (or maybe declare the variable with an ``Any`` type).

.. code-block:: python

   def f() -> None:
       n = 1
       ...
       n = 'x'  # error: Incompatible types in assignment (expression has type "str", variable has type "int")

.. note::

   Using the :option:`--allow-redefinition <mypy --allow-redefinition>`
   flag can suppress this error in several cases.

Note that you can redefine a variable with a more *precise* or a more
concrete type. For example, you can redefine a sequence (which does
not support ``sort()``) as a list and sort it in-place:

.. code-block:: python

    def f(x: Sequence[int]) -> None:
        # Type of x is Sequence[int] here; we don't know the concrete type.
        x = list(x)
        # Type of x is list[int] here.
        x.sort()  # Okay!

See :ref:`type-narrowing` for more information.

.. _variance:

Invariance vs covariance
------------------------

Most mutable generic collections are invariant, and mypy considers all
user-defined generic classes invariant by default
(see :ref:`variance-of-generics` for motivation). This could lead to some
unexpected errors when combined with type inference. For example:

.. code-block:: python

   class A: ...
   class B(A): ...

   lst = [A(), A()]  # Inferred type is list[A]
   new_lst = [B(), B()]  # inferred type is list[B]
   lst = new_lst  # mypy will complain about this, because List is invariant

Possible strategies in such situations are:

* Use an explicit type annotation:

  .. code-block:: python

     new_lst: list[A] = [B(), B()]
     lst = new_lst  # OK

* Make a copy of the right hand side:

  .. code-block:: python

     lst = list(new_lst) # Also OK

* Use immutable collections as annotations whenever possible:

  .. code-block:: python

     def f_bad(x: list[A]) -> A:
         return x[0]
     f_bad(new_lst) # Fails

     def f_good(x: Sequence[A]) -> A:
         return x[0]
     f_good(new_lst) # OK

Declaring a supertype as variable type
--------------------------------------

Sometimes the inferred type is a subtype (subclass) of the desired
type. The type inference uses the first assignment to infer the type
of a name:

.. code-block:: python

   class Shape: ...
   class Circle(Shape): ...
   class Triangle(Shape): ...

   shape = Circle()    # mypy infers the type of shape to be Circle
   shape = Triangle()  # error: Incompatible types in assignment (expression has type "Triangle", variable has type "Circle")

You can just give an explicit type for the variable in cases such the
above example:

.. code-block:: python

   shape: Shape = Circle()  # The variable s can be any Shape, not just Circle
   shape = Triangle()       # OK

Complex type tests
------------------

Mypy can usually infer the types correctly when using :py:func:`isinstance <isinstance>`,
:py:func:`issubclass <issubclass>`,
or ``type(obj) is some_class`` type tests,
and even :ref:`user-defined type guards <type-guards>`,
but for other kinds of checks you may need to add an
explicit type cast:

.. code-block:: python

  from collections.abc import Sequence
  from typing import cast

  def find_first_str(a: Sequence[object]) -> str:
      index = next((i for i, s in enumerate(a) if isinstance(s, str)), -1)
      if index < 0:
          raise ValueError('No str found')

      found = a[index]  # Has type "object", despite the fact that we know it is "str"
      return cast(str, found)  # We need an explicit cast to make mypy happy

Alternatively, you can use an ``assert`` statement together with some
of the supported type inference techniques:

.. code-block:: python

  def find_first_str(a: Sequence[object]) -> str:
      index = next((i for i, s in enumerate(a) if isinstance(s, str)), -1)
      if index < 0:
          raise ValueError('No str found')

      found = a[index]  # Has type "object", despite the fact that we know it is "str"
      assert isinstance(found, str)  # Now, "found" will be narrowed to "str"
      return found  # No need for the explicit "cast()" anymore

.. note::

    Note that the :py:class:`object` type used in the above example is similar
    to ``Object`` in Java: it only supports operations defined for *all*
    objects, such as equality and :py:func:`isinstance`. The type ``Any``,
    in contrast, supports all operations, even if they may fail at
    runtime. The cast above would have been unnecessary if the type of
    ``o`` was ``Any``.

.. note::

   You can read more about type narrowing techniques :ref:`here <type-narrowing>`.

Type inference in Mypy is designed to work well in common cases, to be
predictable and to let the type checker give useful error
messages. More powerful type inference strategies often have complex
and difficult-to-predict failure modes and could result in very
confusing error messages. The tradeoff is that you as a programmer
sometimes have to give the type checker a little help.

.. _version_and_platform_checks:

Python version and system platform checks
-----------------------------------------

Mypy supports the ability to perform Python version checks and platform
checks (e.g. Windows vs Posix), ignoring code paths that won't be run on
the targeted Python version or platform. This allows you to more effectively
typecheck code that supports multiple versions of Python or multiple operating
systems.

More specifically, mypy will understand the use of :py:data:`sys.version_info` and
:py:data:`sys.platform` checks within ``if/elif/else`` statements. For example:

.. code-block:: python

   import sys

   # Distinguishing between different versions of Python:
   if sys.version_info >= (3, 13):
       # Python 3.13+ specific definitions and imports
   else:
       # Other definitions and imports

   # Distinguishing between different operating systems:
   if sys.platform.startswith("linux"):
       # Linux-specific code
   elif sys.platform == "darwin":
       # Mac-specific code
   elif sys.platform == "win32":
       # Windows-specific code
   else:
       # Other systems

As a special case, you can also use one of these checks in a top-level
(unindented) ``assert``; this makes mypy skip the rest of the file.
Example:

.. code-block:: python

   import sys

   assert sys.platform != 'win32'

   # The rest of this file doesn't apply to Windows.

Some other expressions exhibit similar behavior; in particular,
:py:data:`~typing.TYPE_CHECKING`, variables named ``MYPY`` or ``TYPE_CHECKING``, and any variable
whose name is passed to :option:`--always-true <mypy --always-true>` or :option:`--always-false <mypy --always-false>`.
(However, ``True`` and ``False`` are not treated specially!)

.. note::

   Mypy currently does not support more complex checks, and does not assign
   any special meaning when assigning a :py:data:`sys.version_info` or :py:data:`sys.platform`
   check to a variable. This may change in future versions of mypy.

By default, mypy will use your current version of Python and your current
operating system as default values for :py:data:`sys.version_info` and
:py:data:`sys.platform`.

To target a different Python version, use the :option:`--python-version X.Y <mypy --python-version>` flag.
For example, to verify your code typechecks if were run using Python 3.8, pass
in :option:`--python-version 3.8 <mypy --python-version>` from the command line. Note that you do not need
to have Python 3.8 installed to perform this check.

To target a different operating system, use the :option:`--platform PLATFORM <mypy --platform>` flag.
For example, to verify your code typechecks if it were run in Windows, pass
in :option:`--platform win32 <mypy --platform>`. See the documentation for :py:data:`sys.platform`
for examples of valid platform parameters.

.. _reveal-type:

Displaying the type of an expression
------------------------------------

You can use ``reveal_type(expr)`` to ask mypy to display the inferred
static type of an expression. This can be useful when you don't quite
understand how mypy handles a particular piece of code. Example:

.. code-block:: python

   reveal_type((1, 'hello'))  # Revealed type is "tuple[builtins.int, builtins.str]"

You can also use ``reveal_locals()`` at any line in a file
to see the types of all local variables at once. Example:

.. code-block:: python

   a = 1
   b = 'one'
   reveal_locals()
   # Revealed local types are:
   #     a: builtins.int
   #     b: builtins.str
.. note::

   ``reveal_type`` and ``reveal_locals`` are only understood by mypy and
   don't exist in Python. If you try to run your program, you'll have to
   remove any ``reveal_type`` and ``reveal_locals`` calls before you can
   run your code. Both are always available and you don't need to import
   them.

.. _silencing-linters:

Silencing linters
-----------------

In some cases, linters will complain about unused imports or code. In
these cases, you can silence them with a comment after type comments, or on
the same line as the import:

.. code-block:: python

   # to silence complaints about unused imports
   from typing import List  # noqa
   a = None  # type: List[int]


To silence the linter on the same line as a type comment
put the linter comment *after* the type comment:

.. code-block:: python

    a = some_complex_thing()  # type: ignore  # noqa

Covariant subtyping of mutable protocol members is rejected
-----------------------------------------------------------

Mypy rejects this because this is potentially unsafe.
Consider this example:

.. code-block:: python

   from typing import Protocol

   class P(Protocol):
       x: float

   def fun(arg: P) -> None:
       arg.x = 3.14

   class C:
       x = 42
   c = C()
   fun(c)  # This is not safe
   c.x << 5  # Since this will fail!

To work around this problem consider whether "mutating" is actually part
of a protocol. If not, then one can use a :py:class:`@property <property>` in
the protocol definition:

.. code-block:: python

   from typing import Protocol

   class P(Protocol):
       @property
       def x(self) -> float:
          pass

   def fun(arg: P) -> None:
       ...

   class C:
       x = 42
   fun(C())  # OK

Dealing with conflicting names
------------------------------

Suppose you have a class with a method whose name is the same as an
imported (or built-in) type, and you want to use the type in another
method signature.  E.g.:

.. code-block:: python

   class Message:
       def bytes(self):
           ...
       def register(self, path: bytes):  # error: Invalid type "mod.Message.bytes"
           ...

The third line elicits an error because mypy sees the argument type
``bytes`` as a reference to the method by that name.  Other than
renaming the method, a workaround is to use an alias:

.. code-block:: python

   bytes_ = bytes
   class Message:
       def bytes(self):
           ...
       def register(self, path: bytes_):
           ...

Using a development mypy build
------------------------------

You can install the latest development version of mypy from source. Clone the
`mypy repository on GitHub <https://github.com/python/mypy>`_, and then run
``pip install`` locally:

.. code-block:: text

    git clone https://github.com/python/mypy.git
    cd mypy
    python3 -m pip install --upgrade .

To install a development version of mypy that is mypyc-compiled, see the
instructions at the `mypyc wheels repo <https://github.com/mypyc/mypy_mypyc-wheels>`_.

Variables vs type aliases
-------------------------

Mypy has both *type aliases* and variables with types like ``type[...]``. These are
subtly different, and it's important to understand how they differ to avoid pitfalls.

1. A variable with type ``type[...]`` is defined using an assignment with an
   explicit type annotation:

   .. code-block:: python

     class A: ...
     tp: type[A] = A

2. You can define a type alias using an assignment without an explicit type annotation
   at the top level of a module:

   .. code-block:: python

     class A: ...
     Alias = A

   You can also use ``TypeAlias`` (:pep:`613`) to define an *explicit type alias*:

   .. code-block:: python

     from typing import TypeAlias  # "from typing_extensions" in Python 3.9 and earlier

     class A: ...
     Alias: TypeAlias = A

   You should always use ``TypeAlias`` to define a type alias in a class body or
   inside a function.

The main difference is that the target of an alias is precisely known statically, and this
means that they can be used in type annotations and other *type contexts*. Type aliases
can't be defined conditionally (unless using
:ref:`supported Python version and platform checks <version_and_platform_checks>`):

   .. code-block:: python

     class A: ...
     class B: ...

     if random() > 0.5:
         Alias = A
     else:
         # error: Cannot assign multiple types to name "Alias" without an
         # explicit "Type[...]" annotation
         Alias = B

     tp: type[object]  # "tp" is a variable with a type object value
     if random() > 0.5:
         tp = A
     else:
         tp = B  # This is OK

     def fun1(x: Alias) -> None: ...  # OK
     def fun2(x: tp) -> None: ...  # Error: "tp" is not valid as a type

Incompatible overrides
----------------------

It's unsafe to override a method with a more specific argument type,
as it violates the `Liskov substitution principle
<https://stackoverflow.com/questions/56860/what-is-an-example-of-the-liskov-substitution-principle>`_.
For return types, it's unsafe to override a method with a more general
return type.

Other incompatible signature changes in method overrides, such as
adding an extra required parameter, or removing an optional parameter,
will also generate errors. The signature of a method in a subclass
should accept all valid calls to the base class method. Mypy
treats a subclass as a subtype of the base class. An instance of a
subclass is valid everywhere where an instance of the base class is
valid.

This example demonstrates both safe and unsafe overrides:

.. code-block:: python

    from collections.abc import Sequence, Iterable

    class A:
        def test(self, t: Sequence[int]) -> Sequence[str]:
            ...

    class GeneralizedArgument(A):
        # A more general argument type is okay
        def test(self, t: Iterable[int]) -> Sequence[str]:  # OK
            ...

    class NarrowerArgument(A):
        # A more specific argument type isn't accepted
        def test(self, t: list[int]) -> Sequence[str]:  # Error
            ...

    class NarrowerReturn(A):
        # A more specific return type is fine
        def test(self, t: Sequence[int]) -> List[str]:  # OK
            ...

    class GeneralizedReturn(A):
        # A more general return type is an error
        def test(self, t: Sequence[int]) -> Iterable[str]:  # Error
            ...

You can use ``# type: ignore[override]`` to silence the error. Add it
to the line that generates the error, if you decide that type safety is
not necessary:

.. code-block:: python

    class NarrowerArgument(A):
        def test(self, t: List[int]) -> Sequence[str]:  # type: ignore[override]
            ...

.. _unreachable:

Unreachable code
----------------

Mypy may consider some code as *unreachable*, even if it might not be
immediately obvious why.  It's important to note that mypy will *not*
type check such code. Consider this example:

.. code-block:: python

    class Foo:
        bar: str = ''

    def bar() -> None:
        foo: Foo = Foo()
        return
        x: int = 'abc'  # Unreachable -- no error

It's easy to see that any statement after ``return`` is unreachable,
and hence mypy will not complain about the mistyped code below
it. For a more subtle example, consider this code:

.. code-block:: python

    class Foo:
        bar: str = ''

    def bar() -> None:
        foo: Foo = Foo()
        assert foo.bar is None
        x: int = 'abc'  # Unreachable -- no error

Again, mypy will not report any errors. The type of ``foo.bar`` is
``str``, and mypy reasons that it can never be ``None``.  Hence the
``assert`` statement will always fail and the statement below will
never be executed.  (Note that in Python, ``None`` is not an empty
reference but an object of type ``None``.)

In this example mypy will go on to check the last line and report an
error, since mypy thinks that the condition could be either True or
False:

.. code-block:: python

    class Foo:
        bar: str = ''

    def bar() -> None:
        foo: Foo = Foo()
        if not foo.bar:
            return
        x: int = 'abc'  # Reachable -- error

If you use the :option:`--warn-unreachable <mypy --warn-unreachable>` flag, mypy will generate
an error about each unreachable code block.

Narrowing and inner functions
-----------------------------

Because closures in Python are late-binding (https://docs.python-guide.org/writing/gotchas/#late-binding-closures),
mypy will not narrow the type of a captured variable in an inner function.
This is best understood via an example:

.. code-block:: python

    def foo(x: int | None) -> Callable[[], int]:
        if x is None:
            x = 5
        print(x + 1)  # mypy correctly deduces x must be an int here
        def inner() -> int:
            return x + 1  # but (correctly) complains about this line

        x = None  # because x could later be assigned None
        return inner

    inner = foo(5)
    inner()  # this will raise an error when called

To get this code to type check, you could assign ``y = x`` after ``x`` has been
narrowed, and use ``y`` in the inner function, or add an assert in the inner
function.

.. _incorrect-self:

Incorrect use of ``Self``
-------------------------

``Self`` is not the type of the current class; it's a type variable with upper
bound of the current class. That is, it represents the type of the current class
or of potential subclasses.

.. code-block:: python

    from typing import Self

    class Foo:
        @classmethod
        def constructor(cls) -> Self:
            # Instead, either call cls() or change the annotation to -> Foo
            return Foo()  # error: Incompatible return value type (got "Foo", expected "Self")

    class Bar(Foo):
        ...

    reveal_type(Foo.constructor())  # note: Revealed type is "Foo"
    # In the context of the subclass Bar, the Self return type promises
    # that the return value will be Bar
    reveal_type(Bar.constructor())  # note: Revealed type is "Bar"
