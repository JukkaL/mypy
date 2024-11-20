.. _type-narrowing:

Type narrowing
==============

This section is dedicated to several type narrowing
techniques which are supported by mypy.

Type narrowing is when you convince a type checker that a broader type is actually more specific, for instance, that an object of type ``Shape`` is actually of the narrower type ``Square``.


Type narrowing expressions
--------------------------

The simplest way to narrow a type is to use one of the supported expressions:

- :py:func:`isinstance` like in :code:`isinstance(obj, float)` will narrow ``obj`` to have ``float`` type
- :py:func:`issubclass` like in :code:`issubclass(cls, MyClass)` will narrow ``cls`` to be ``Type[MyClass]``
- :py:class:`type` like in :code:`type(obj) is int` will narrow ``obj`` to have ``int`` type
- :py:func:`callable` like in :code:`callable(obj)` will narrow object to callable type
- :code:`obj is not None` will narrow object to its :ref:`non-optional form <strict_optional>`

Type narrowing is contextual. For example, based on the condition, mypy will narrow an expression only within an ``if`` branch:

.. code-block:: python

  def function(arg: object):
      if isinstance(arg, int):
          # Type is narrowed within the ``if`` branch only
          reveal_type(arg)  # Revealed type: "builtins.int"
      elif isinstance(arg, str) or isinstance(arg, bool):
          # Type is narrowed differently within this ``elif`` branch:
          reveal_type(arg)  # Revealed type: "builtins.str | builtins.bool"

          # Subsequent narrowing operations will narrow the type further
          if isinstance(arg, bool):
              reveal_type(arg)  # Revealed type: "builtins.bool"

      # Back outside of the ``if`` statement, the type isn't narrowed:
      reveal_type(arg)  # Revealed type: "builtins.object"

Mypy understands the implications ``return`` or exception raising can have
for what type an object could be:

.. code-block:: python

  def function(arg: int | str):
      if isinstance(arg, int):
          return

      # `arg` can't be `int` at this point:
      reveal_type(arg)  # Revealed type: "builtins.str"

We can also use ``assert`` to narrow types in the same context:

.. code-block:: python

  def function(arg: Any):
      assert isinstance(arg, int)
      reveal_type(arg)  # Revealed type: "builtins.int"

.. note::

  With :option:`--warn-unreachable <mypy --warn-unreachable>`
  narrowing types to some impossible state will be treated as an error.

  .. code-block:: python

     def function(arg: int):
         # error: Subclass of "int" and "str" cannot exist:
         # would have incompatible method signatures
         assert isinstance(arg, str)

         # error: Statement is unreachable
         print("so mypy concludes the assert will always trigger")

  Without ``--warn-unreachable`` mypy will simply not check code it deems to be
  unreachable. See :ref:`unreachable` for more information.

  .. code-block:: python

     x: int = 1
     assert isinstance(x, str)
     reveal_type(x)  # Revealed type is "builtins.int"
     print(x + '!')  # Typechecks with `mypy`, but fails in runtime.


issubclass
~~~~~~~~~~

Mypy can also use :py:func:`issubclass`
for better type inference when working with types and metaclasses:

.. code-block:: python

   class MyCalcMeta(type):
       @classmethod
       def calc(cls) -> int:
           ...

   def f(o: object) -> None:
       t = type(o)  # We must use a variable here
       reveal_type(t)  # Revealed type is "builtins.type"

       if issubclass(t, MyCalcMeta):  # `issubclass(type(o), MyCalcMeta)` won't work
           reveal_type(t)  # Revealed type is "Type[MyCalcMeta]"
           t.calc()  # Okay

callable
~~~~~~~~

Mypy knows what types are callable and which ones are not during type checking.
So, we know what ``callable()`` will return. For example:

.. code-block:: python

  from collections.abc import Callable

  x: Callable[[], int]

  if callable(x):
      reveal_type(x)  # N: Revealed type is "def () -> builtins.int"
  else:
      ...  # Will never be executed and will raise error with `--warn-unreachable`

The ``callable`` function can even split union types into
callable and non-callable parts:

.. code-block:: python

  from collections.abc import Callable

  x: int | Callable[[], int]

  if callable(x):
      reveal_type(x)  # N: Revealed type is "def () -> builtins.int"
  else:
      reveal_type(x)  # N: Revealed type is "builtins.int"

.. _casts:

Casts
-----

Mypy supports type casts that are usually used to coerce a statically
typed value to a subtype. Unlike languages such as Java or C#,
however, mypy casts are only used as hints for the type checker, and they
don't perform a runtime type check. Use the function :py:func:`~typing.cast`
to perform a cast:

.. code-block:: python

   from typing import cast

   o: object = [1]
   x = cast(list[int], o)  # OK
   y = cast(list[str], o)  # OK (cast performs no actual runtime check)

To support runtime checking of casts such as the above, we'd have to check
the types of all list items, which would be very inefficient for large lists.
Casts are used to silence spurious
type checker warnings and give the type checker a little help when it can't
quite understand what is going on.

.. note::

   You can use an assertion if you want to perform an actual runtime check:

   .. code-block:: python

      def foo(o: object) -> None:
          print(o + 5)  # Error: can't add 'object' and 'int'
          assert isinstance(o, int)
          print(o + 5)  # OK: type of 'o' is 'int' here

You don't need a cast for expressions with type ``Any``, or when
assigning to a variable with type ``Any``, as was explained earlier.
You can also use ``Any`` as the cast target type -- this lets you perform
any operations on the result. For example:

.. code-block:: python

    from typing import cast, Any

    x = 1
    x.whatever()  # Type check error
    y = cast(Any, x)
    y.whatever()  # Type check OK (runtime error)


.. _type-guards:

User-Defined Type Guards
------------------------

Mypy supports User-Defined Type Guards (:pep:`647`).

A type guard is a way for programs to influence conditional
type narrowing employed by a type checker based on runtime checks.

Basically, a ``TypeGuard`` is a "smart" alias for a ``bool`` type.
Let's have a look at the regular ``bool`` example:

.. code-block:: python

  def is_str_list(val: list[object]) -> bool:
    """Determines whether all objects in the list are strings"""
    return all(isinstance(x, str) for x in val)

  def func1(val: list[object]) -> None:
      if is_str_list(val):
          reveal_type(val)  # Reveals list[object]
          print(" ".join(val)) # Error: incompatible type

The same example with ``TypeGuard``:

.. code-block:: python

  from typing import TypeGuard  # use `typing_extensions` for Python 3.9 and below

  def is_str_list(val: list[object]) -> TypeGuard[list[str]]:
      """Determines whether all objects in the list are strings"""
      return all(isinstance(x, str) for x in val)

  def func1(val: list[object]) -> None:
      if is_str_list(val):
          reveal_type(val)  # list[str]
          print(" ".join(val)) # ok

How does it work? ``TypeGuard`` narrows the first function argument (``val``)
to the type specified as the first type parameter (``list[str]``).

.. note::

  Narrowing is
  `not strict <https://www.python.org/dev/peps/pep-0647/#enforcing-strict-narrowing>`_.
  For example, you can narrow ``str`` to ``int``:

  .. code-block:: python

    def f(value: str) -> TypeGuard[int]:
        return True

  Note: since strict narrowing is not enforced, it's easy
  to break type safety.

  However, there are many ways a determined or uninformed developer can
  subvert type safety -- most commonly by using cast or Any.
  If a Python developer takes the time to learn about and implement
  user-defined type guards within their code,
  it is safe to assume that they are interested in type safety
  and will not write their type guard functions in a way
  that will undermine type safety or produce nonsensical results.

Generic TypeGuards
~~~~~~~~~~~~~~~~~~

``TypeGuard`` can also work with generic types (Python 3.12 syntax):

.. code-block:: python

  from typing import TypeGuard  # use `typing_extensions` for `python<3.10`

  def is_two_element_tuple[T](val: tuple[T, ...]) -> TypeGuard[tuple[T, T]]:
      return len(val) == 2

  def func(names: tuple[str, ...]):
      if is_two_element_tuple(names):
          reveal_type(names)  # tuple[str, str]
      else:
          reveal_type(names)  # tuple[str, ...]

TypeGuards with parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~

Type guard functions can accept extra arguments (Python 3.12 syntax):

.. code-block:: python

  from typing import TypeGuard  # use `typing_extensions` for `python<3.10`

  def is_set_of[T](val: set[Any], type: type[T]) -> TypeGuard[set[T]]:
      return all(isinstance(x, type) for x in val)

  items: set[Any]
  if is_set_of(items, str):
      reveal_type(items)  # set[str]

TypeGuards as methods
~~~~~~~~~~~~~~~~~~~~~

A method can also serve as a ``TypeGuard``:

.. code-block:: python

  class StrValidator:
      def is_valid(self, instance: object) -> TypeGuard[str]:
          return isinstance(instance, str)

  def func(to_validate: object) -> None:
      if StrValidator().is_valid(to_validate):
          reveal_type(to_validate)  # Revealed type is "builtins.str"

.. note::

  Note, that ``TypeGuard``
  `does not narrow <https://www.python.org/dev/peps/pep-0647/#narrowing-of-implicit-self-and-cls-parameters>`_
  types of ``self`` or ``cls`` implicit arguments.

  If narrowing of ``self`` or ``cls`` is required,
  the value can be passed as an explicit argument to a type guard function:

  .. code-block:: python

    class Parent:
        def method(self) -> None:
            reveal_type(self)  # Revealed type is "Parent"
            if is_child(self):
                reveal_type(self)  # Revealed type is "Child"

    class Child(Parent):
        ...

    def is_child(instance: Parent) -> TypeGuard[Child]:
        return isinstance(instance, Child)

Assignment expressions as TypeGuards
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes you might need to create a new variable and narrow it
to some specific type at the same time.
This can be achieved by using ``TypeGuard`` together
with `:= operator <https://docs.python.org/3/whatsnew/3.8.html#assignment-expressions>`_.

.. code-block:: python

  from typing import TypeGuard  # use `typing_extensions` for `python<3.10`

  def is_float(a: object) -> TypeGuard[float]:
      return isinstance(a, float)

  def main(a: object) -> None:
      if is_float(x := a):
          reveal_type(x)  # N: Revealed type is 'builtins.float'
          reveal_type(a)  # N: Revealed type is 'builtins.object'
      reveal_type(x)  # N: Revealed type is 'builtins.object'
      reveal_type(a)  # N: Revealed type is 'builtins.object'

What happens here?

1. We create a new variable ``x`` and assign a value of ``a`` to it
2. We run ``is_float()`` type guard on ``x``
3. It narrows ``x`` to be ``float`` in the ``if`` context and does not touch ``a``

.. note::

  The same will work with ``isinstance(x := a, float)`` as well.

Limitations
-----------

Mypy's analysis is limited to individual symbols and it will not track
relationships between symbols. For example, in the following code
it's easy to deduce that if :code:`a` is None then :code:`b` must not be,
therefore :code:`a or b` will always be an instance of :code:`C`,
but Mypy will not be able to tell that:

.. code-block:: python

    class C:
        pass

    def f(a: C | None, b: C | None) -> C:
        if a is not None or b is not None:
            return a or b  # Incompatible return value type (got "C | None", expected "C")
        return C()

Tracking these sort of cross-variable conditions in a type checker would add significant complexity
and performance overhead.

You can use an ``assert`` to convince the type checker, override it with a :ref:`cast <casts>`
or rewrite the function to be slightly more verbose:

.. code-block:: python

    def f(a: C | None, b: C | None) -> C:
        if a is not None:
            return a
        elif b is not None:
            return b
        return C()


.. _typeis:

TypeIs
------

Mypy supports TypeIs (:pep:`742`).

A `TypeIs narrowing function <https://typing.readthedocs.io/en/latest/spec/narrowing.html#typeis>`_
allows you to define custom type checks that can narrow the type of a variable
in `both the if and else <https://docs.python.org/3.13/library/typing.html#typing.TypeIs>`_
branches of a conditional, similar to how the built-in isinstance() function works.

TypeIs is new in Python 3.13 — for use in older Python versions, use the backport
from `typing_extensions <https://typing-extensions.readthedocs.io/en/latest/>`_

Consider the following example using TypeIs:

.. code-block:: python

    from typing import TypeIs

    def is_str(x: object) -> TypeIs[str]:
        return isinstance(x, str)

    def process(x: int | str) -> None:
        if is_str(x):
            reveal_type(x)  # Revealed type is 'str'
            print(x.upper())  # Valid: x is str
        else:
            reveal_type(x)  # Revealed type is 'int'
            print(x + 1)  # Valid: x is int

In this example, the function is_str is a type narrowing function
that returns TypeIs[str]. When used in an if statement, x is narrowed
to str in the if branch and to int in the else branch.

Key points:


- The function must accept at least one positional argument.

- The return type is annotated as ``TypeIs[T]``, where ``T`` is the type you
  want to narrow to.

- The function must return a ``bool`` value.

- In the ``if`` branch (when the function returns ``True``), the type of the
  argument is narrowed to the intersection of its original type and ``T``.

- In the ``else`` branch (when the function returns ``False``), the type of
  the argument is narrowed to the intersection of its original type and the
  complement of ``T``.


TypeIs vs TypeGuard
~~~~~~~~~~~~~~~~~~~

While both TypeIs and TypeGuard allow you to define custom type narrowing
functions, they differ in important ways:

- **Type narrowing behavior**: TypeIs narrows the type in both the if and else branches,
  whereas TypeGuard narrows only in the if branch.

- **Compatibility requirement**: TypeIs requires that the narrowed type T be
  compatible with the input type of the function. TypeGuard does not have this restriction.

- **Type inference**: With TypeIs, the type checker may infer a more precise type by
  combining existing type information with T.

Here's an example demonstrating the behavior with TypeGuard:

.. code-block:: python

    from typing import TypeGuard, reveal_type

    def is_str(x: object) -> TypeGuard[str]:
        return isinstance(x, str)

    def process(x: int | str) -> None:
        if is_str(x):
            reveal_type(x)  # Revealed type is "builtins.str"
            print(x.upper())  # ok: x is str
        else:
            reveal_type(x)  # Revealed type is "Union[builtins.int, builtins.str]"
            print(x + 1)  # ERROR: Unsupported operand types for + ("str" and "int")  [operator]

Generic TypeIs
~~~~~~~~~~~~~~

``TypeIs`` functions can also work with generic types:

.. code-block:: python

    from typing import TypeVar, TypeIs

    T = TypeVar('T')

    def is_two_element_tuple(val: tuple[T, ...]) -> TypeIs[tuple[T, T]]:
        return len(val) == 2

    def process(names: tuple[str, ...]) -> None:
        if is_two_element_tuple(names):
            reveal_type(names)  # Revealed type is 'tuple[str, str]'
        else:
            reveal_type(names)  # Revealed type is 'tuple[str, ...]'


TypeIs with Additional Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
TypeIs functions can accept additional parameters beyond the first.
The type narrowing applies only to the first argument.

.. code-block:: python

    from typing import Any, TypeVar, reveal_type, TypeIs

    T = TypeVar('T')

    def is_instance_of(val: Any, typ: type[T]) -> TypeIs[T]:
        return isinstance(val, typ)

    def process(x: Any) -> None:
        if is_instance_of(x, int):
            reveal_type(x)  # Revealed type is 'int'
            print(x + 1)  # ok
        else:
            reveal_type(x)  # Revealed type is 'Any'

TypeIs in Methods
~~~~~~~~~~~~~~~~~

A method can also serve as a ``TypeIs`` function. Note that in instance or
class methods, the type narrowing applies to the second parameter
(after ``self`` or ``cls``).

.. code-block:: python

    class Validator:
        def is_valid(self, instance: object) -> TypeIs[str]:
            return isinstance(instance, str)

        def process(self, to_validate: object) -> None:
            if Validator().is_valid(to_validate):
                reveal_type(to_validate)  # Revealed type is 'str'
                print(to_validate.upper())  # ok: to_validate is str


Assignment Expressions with TypeIs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use the assignment expression operator ``:=`` with ``TypeIs`` to create a new variable and narrow its type simultaneously.

.. code-block:: python

    from typing import TypeIs, reveal_type

    def is_float(x: object) -> TypeIs[float]:
        return isinstance(x, float)

    def main(a: object) -> None:
        if is_float(x := a):
            reveal_type(x)  # Revealed type is 'float'
            # x is narrowed to float in this block
            print(x + 1.0)
