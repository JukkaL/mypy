.. _common_issues:

Common issues and solutions
===========================

This section has examples of cases when you need to update your code
to use static typing, and ideas for working around issues if mypy
doesn't work as expected. Statically typed code is often identical to
normal Python code (except for type annotations), but sometimes you need
to do things slightly differently.

Can't install mypy using pip
----------------------------

If installation fails, you've probably hit one of these issues:

* Mypy needs Python 3.5 or later to run.
* You may have to run pip like this:
  ``python3 -m pip install mypy``.

.. _annotations_needed:

No errors reported for obviously wrong code
-------------------------------------------

There are several common reasons why obviously wrong code is not
flagged as an error.

- **The function containing the error is not annotated.** Functions that
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
      # error: Unsupported operand types for + ("str" and List[str])

  If you don't know what types to add, you can use ``Any``, but beware:

- **One of the values involved has type 'Any'.** Extending the above
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

  Note that sometimes library stubs have imprecise type information,
  e.g. the :py:func:`pow` builtin returns ``Any`` (see `typeshed issue 285
  <https://github.com/python/typeshed/issues/285>`_ for the reason).

- :py:meth:`__init__ <object.__init__>` **method has no annotated
  arguments or return type annotation.** :py:meth:`__init__ <object.__init__>`
  is considered fully-annotated **if at least one argument is annotated**,
  while mypy will infer the return type as ``None``.
  The implication is that, for a :py:meth:`__init__ <object.__init__>` method
  that has no argument, you'll have to explicitly annotate the return type
  as ``None`` to type-check this :py:meth:`__init__ <object.__init__>` method:

  .. code-block:: python

      def foo(s: str) -> str:
          return s

      class A():
          def __init__(self, value: str): # Return type inferred as None, considered as typed method
              self.value = value
              foo(1) # error: Argument 1 to "foo" has incompatible type "int"; expected "str"

      class B():
          def __init__(self):  # No argument is annotated, considered as untyped method
              foo(1)  # No error!

      class C():
          def __init__(self) -> None:  # Must specify return type to type-check
              foo(1) # error: Argument 1 to "foo" has incompatible type "int"; expected "str"

- **Some imports may be silently ignored**.  Another source of
  unexpected ``Any`` values are the :option:`--ignore-missing-imports
  <mypy --ignore-missing-imports>` and :option:`--follow-imports=skip
  <mypy --follow-imports>` flags.  When you use :option:`--ignore-missing-imports <mypy --ignore-missing-imports>`,
  any imported module that cannot be found is silently replaced with
  ``Any``.  When using :option:`--follow-imports=skip <mypy --follow-imports>` the same is true for
  modules for which a ``.py`` file is found but that are not specified
  on the command line.  (If a ``.pyi`` stub is found it is always
  processed normally, regardless of the value of
  :option:`--follow-imports <mypy --follow-imports>`.)  To help debug the former situation (no
  module found at all) leave out :option:`--ignore-missing-imports <mypy --ignore-missing-imports>`; to get
  clarity about the latter use :option:`--follow-imports=error <mypy --follow-imports>`.  You can
  read up about these and other useful flags in :ref:`command-line`.

- **A function annotated as returning a non-optional type returns 'None'
  and mypy doesn't complain**.

  .. code-block:: python

      def foo() -> str:
          return None  # No error!

  You may have disabled strict optional checking (see
  :ref:`no_strict_optional` for more).

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

A ``# type: ignore`` comment at the top of a module (before any statements,
including imports or docstrings) has the effect of ignoring the *entire* module.

.. code-block:: python

    # type: ignore

    import foo

    foo.bar()

Ignoring a single class or function
-----------------------------------

A ``@typing.no_type_check`` decorator added to a class, method or function has the
effect of ignoring that class, method or function.

.. code-block:: python

    import typing
    
    @typing.no_type_check
    def foo() -> str:
       return None  # No error!

Unexpected errors about 'None' and/or 'Optional' types
------------------------------------------------------

Starting from mypy 0.600, mypy uses
:ref:`strict optional checking <strict_optional>` by default,
and the ``None`` value is not compatible with non-optional types.
It's easy to switch back to the older behavior where ``None`` was
compatible with arbitrary types (see :ref:`no_strict_optional`).
You can also fall back to this behavior if strict optional
checking would require a large number of ``assert foo is not None``
checks to be inserted, and you want to minimize the number
of code changes required to get a clean mypy run.

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

   a: List[int] = []

Without the annotation mypy can't always figure out the
precise type of ``a``.

You can use a simple empty list literal in a dynamically typed function (as the
type of ``a`` would be implicitly ``Any`` and need not be inferred), if type
of the variable has been declared or inferred before, or if you perform a simple
modification operation in the same scope (such as ``append`` for a list):

.. code-block:: python

   a = []  # Okay because followed by append, inferred type List[int]
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
multiple types within a single function, you may need to declare it
with the ``Any`` type.

.. code-block:: python

   def f() -> None:
       n = 1
       ...
       n = 'x'        # Type error: n has type int

.. note::

   This limitation could be lifted in a future mypy
   release.

Note that you can redefine a variable with a more *precise* or a more
concrete type. For example, you can redefine a sequence (which does
not support ``sort()``) as a list and sort it in-place:

.. code-block:: python

    def f(x: Sequence[int]) -> None:
        # Type of x is Sequence[int] here; we don't know the concrete type.
        x = list(x)
        # Type of x is List[int] here.
        x.sort()  # Okay!

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

   lst = [A(), A()]  # Inferred type is List[A]
   new_lst = [B(), B()]  # inferred type is List[B]
   lst = new_lst  # mypy will complain about this, because List is invariant

Possible strategies in such situations are:

* Use an explicit type annotation:

  .. code-block:: python

     new_lst: List[A] = [B(), B()]
     lst = new_lst  # OK

* Make a copy of the right hand side:

  .. code-block:: python

     lst = list(new_lst) # Also OK

* Use immutable collections as annotations whenever possible:

  .. code-block:: python

     def f_bad(x: List[A]) -> A:
         return x[0]
     f_bad(new_lst) # Fails

     def f_good(x: Sequence[A]) -> A:
         return x[0]
     f_good(new_lst) # OK

Declaring a supertype as variable type
--------------------------------------

Sometimes the inferred type is a subtype (subclass) of the desired
type. The type inference uses the first assignment to infer the type
of a name (assume here that ``Shape`` is the base class of both
``Circle`` and ``Triangle``):

.. code-block:: python

   shape = Circle()    # Infer shape to be Circle
   ...
   shape = Triangle()  # Type error: Triangle is not a Circle

You can just give an explicit type for the variable in cases such the
above example:

.. code-block:: python

   shape = Circle() # type: Shape   # The variable s can be any Shape,
                                    # not just Circle
   ...
   shape = Triangle()               # OK

Complex type tests
------------------

Mypy can usually infer the types correctly when using :py:func:`isinstance <isinstance>`
type tests, but for other kinds of checks you may need to add an
explicit type cast:

.. code-block:: python

   def f(o: object) -> None:
       if type(o) is int:
           o = cast(int, o)
           g(o + 1)    # This would be an error without the cast
           ...
       else:
           ...

.. note::

    Note that the :py:class:`object` type used in the above example is similar
    to ``Object`` in Java: it only supports operations defined for *all*
    objects, such as equality and :py:func:`isinstance`. The type ``Any``,
    in contrast, supports all operations, even if they may fail at
    runtime. The cast above would have been unnecessary if the type of
    ``o`` was ``Any``.

Mypy can't infer the type of ``o`` after the :py:class:`type() <type>` check
because it only knows about :py:func:`isinstance` (and the latter is better
style anyway).  We can write the above code without a cast by using
:py:func:`isinstance`:

.. code-block:: python

   def f(o: object) -> None:
       if isinstance(o, int):  # Mypy understands isinstance checks
           g(o + 1)        # Okay; type of o is inferred as int here
           ...

Type inference in mypy is designed to work well in common cases, to be
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
   if sys.version_info >= (3, 5):
       # Python 3.5+ specific definitions and imports
   elif sys.version_info[0] >= 3:
       # Python 3 specific definitions and imports
   else:
       # Python 2 specific definitions and imports

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
:py:data:`~typing.TYPE_CHECKING`, variables named ``MYPY``, and any variable
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
For example, to verify your code typechecks if were run using Python 2, pass
in :option:`--python-version 2.7 <mypy --python-version>` from the command line. Note that you do not need
to have Python 2.7 installed to perform this check.

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

   reveal_type((1, 'hello'))  # Revealed type is "Tuple[builtins.int, builtins.str]"

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

   from typing_extensions import Protocol

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

   from typing_extensions import Protocol

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
renaming the method, a work-around is to use an alias:

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
    sudo python3 -m pip install --upgrade .

Variables vs type aliases
-----------------------------------

Mypy has both type aliases and variables with types like ``Type[...]`` and it is important to know their difference.

1. Variables with type ``Type[...]`` should be created by assignments with an explicit type annotations:

.. code-block:: python

    class A: ...
    tp: Type[A] = A

2. Aliases are created by assignments without an explicit type:

.. code-block:: python

    class A: ...
    Alias = A

3. The difference is that aliases are completely known statically and can be used in type context (annotations):

.. code-block:: python

    class A: ...
    class B: ...

    if random() > 0.5:
        Alias = A
    else:
        Alias = B  # error: Cannot assign multiple types to name "Alias" without an explicit "Type[...]" annotation \
                   # error: Incompatible types in assignment (expression has type "Type[B]", variable has type "Type[A]")

    tp: Type[object]  # tp is a type variable
    if random() > 0.5:
        tp = A
    else:
        tp = B  # This is OK

    def fun1(x: Alias) -> None: ...  # This is OK
    def fun2(x: tp) -> None: ...  # error: Variable "__main__.tp" is not valid as a type

Incompatible overrides
------------------------------

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

    from typing import Sequence, List, Iterable

    class A:
        def test(self, t: Sequence[int]) -> Sequence[str]:
            ...

    class GeneralizedArgument(A):
        # A more general argument type is okay
        def test(self, t: Iterable[int]) -> Sequence[str]:  # OK
            ...

    class NarrowerArgument(A):
        # A more specific argument type isn't accepted
        def test(self, t: List[int]) -> Sequence[str]:  # Error
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
and hence mypy will not complain about the mis-typed code below
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

    def foo(x: Optional[int]) -> Callable[[], int]:
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
