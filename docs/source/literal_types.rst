Literal types and Enums
=======================

.. _literal_types:

Literal types
-------------

Literal types let you indicate that an expression is equal to some specific
primitive value. For example, if we annotate a variable with type ``Literal["foo"]``,
mypy will understand that variable is not only of type ``str``, but is also
equal to specifically the string ``"foo"``.

This feature is primarily useful when annotating functions that behave
differently based on the exact value the caller provides. For example,
suppose we have a function ``fetch_data(...)`` that returns ``bytes`` if the
first argument is ``True``, and ``str`` if it's ``False``. We can construct a
precise type signature for this function using ``Literal[...]`` and overloads:

.. code-block:: python

    from typing import overload, Union, Literal

    # The first two overloads use Literal[...] so we can
    # have precise return types:

    @overload
    def fetch_data(raw: Literal[True]) -> bytes: ...
    @overload
    def fetch_data(raw: Literal[False]) -> str: ...

    # The last overload is a fallback in case the caller
    # provides a regular bool:

    @overload
    def fetch_data(raw: bool) -> Union[bytes, str]: ...

    def fetch_data(raw: bool) -> Union[bytes, str]:
        # Implementation is omitted
        ...

    reveal_type(fetch_data(True))        # Revealed type is "bytes"
    reveal_type(fetch_data(False))       # Revealed type is "str"

    # Variables declared without annotations will continue to have an
    # inferred type of 'bool'.

    variable = True
    reveal_type(fetch_data(variable))    # Revealed type is "Union[bytes, str]"

.. note::

    The examples in this page import ``Literal`` as well as ``Final`` and
    ``TypedDict`` from the ``typing`` module. These types were added to
    ``typing`` in Python 3.8, but are also available for use in Python
    3.4 - 3.7 via the ``typing_extensions`` package.

Parameterizing Literals
***********************

Literal types may contain one or more literal bools, ints, strs, bytes, and
enum values. However, literal types **cannot** contain arbitrary expressions:
types like ``Literal[my_string.trim()]``, ``Literal[x > 3]``, or ``Literal[3j + 4]``
are all illegal.

Literals containing two or more values are equivalent to the union of those values.
So, ``Literal[-3, b"foo", MyEnum.A]`` is equivalent to
``Union[Literal[-3], Literal[b"foo"], Literal[MyEnum.A]]``. This makes writing more
complex types involving literals a little more convenient.

Literal types may also contain ``None``. Mypy will treat ``Literal[None]`` as being
equivalent to just ``None``. This means that ``Literal[4, None]``,
``Literal[4] | None``, and ``Optional[Literal[4]]`` are all equivalent.

Literals may also contain aliases to other literal types. For example, the
following program is legal:

.. code-block:: python

    PrimaryColors = Literal["red", "blue", "yellow"]
    SecondaryColors = Literal["purple", "green", "orange"]
    AllowedColors = Literal[PrimaryColors, SecondaryColors]

    def paint(color: AllowedColors) -> None: ...

    paint("red")        # Type checks!
    paint("turquoise")  # Does not type check

Literals may not contain any other kind of type or expression. This means doing
``Literal[my_instance]``, ``Literal[Any]``, ``Literal[3.14]``, or
``Literal[{"foo": 2, "bar": 5}]`` are all illegal.

Declaring literal variables
***************************

You must explicitly add an annotation to a variable to declare that it has
a literal type:

.. code-block:: python

    a: Literal[19] = 19
    reveal_type(a)          # Revealed type is "Literal[19]"

In order to preserve backwards-compatibility, variables without this annotation
are **not** assumed to be literals:

.. code-block:: python

    b = 19
    reveal_type(b)          # Revealed type is "int"

If you find repeating the value of the variable in the type hint to be tedious,
you can instead change the variable to be ``Final`` (see :ref:`final_attrs`):

.. code-block:: python

    from typing import Final, Literal

    def expects_literal(x: Literal[19]) -> None: pass

    c: Final = 19

    reveal_type(c)          # Revealed type is "Literal[19]?"
    expects_literal(c)      # ...and this type checks!

If you do not provide an explicit type in the ``Final``, the type of ``c`` becomes
*context-sensitive*: mypy will basically try "substituting" the original assigned
value whenever it's used before performing type checking. This is why the revealed
type of ``c`` is ``Literal[19]?``: the question mark at the end reflects this
context-sensitive nature.

For example, mypy will type check the above program almost as if it were written like so:

.. code-block:: python

    from typing import Final, Literal

    def expects_literal(x: Literal[19]) -> None: pass

    reveal_type(19)
    expects_literal(19)

This means that while changing a variable to be ``Final`` is not quite the same thing
as adding an explicit ``Literal[...]`` annotation, it often leads to the same effect
in practice.

The main cases where the behavior of context-sensitive vs true literal types differ are
when you try using those types in places that are not explicitly expecting a ``Literal[...]``.
For example, compare and contrast what happens when you try appending these types to a list:

.. code-block:: python

    from typing import Final, Literal

    a: Final = 19
    b: Literal[19] = 19

    # Mypy will choose to infer list[int] here.
    list_of_ints = []
    list_of_ints.append(a)
    reveal_type(list_of_ints)  # Revealed type is "list[int]"

    # But if the variable you're appending is an explicit Literal, mypy
    # will infer list[Literal[19]].
    list_of_lits = []
    list_of_lits.append(b)
    reveal_type(list_of_lits)  # Revealed type is "list[Literal[19]]"


Intelligent indexing
********************

We can use Literal types to more precisely index into structured heterogeneous
types such as tuples, NamedTuples, and TypedDicts. This feature is known as
*intelligent indexing*.

For example, when we index into a tuple using some int, the inferred type is
normally the union of the tuple item types. However, if we want just the type
corresponding to some particular index, we can use Literal types like so:

.. code-block:: python

    from typing import TypedDict

    tup = ("foo", 3.4)

    # Indexing with an int literal gives us the exact type for that index
    reveal_type(tup[0])  # Revealed type is "str"

    # But what if we want the index to be a variable? Normally mypy won't
    # know exactly what the index is and so will return a less precise type:
    int_index = 0
    reveal_type(tup[int_index])  # Revealed type is "Union[str, float]"

    # But if we use either Literal types or a Final int, we can gain back
    # the precision we originally had:
    lit_index: Literal[0] = 0
    fin_index: Final = 0
    reveal_type(tup[lit_index])  # Revealed type is "str"
    reveal_type(tup[fin_index])  # Revealed type is "str"

    # We can do the same thing with with TypedDict and str keys:
    class MyDict(TypedDict):
        name: str
        main_id: int
        backup_id: int

    d: MyDict = {"name": "Saanvi", "main_id": 111, "backup_id": 222}
    name_key: Final = "name"
    reveal_type(d[name_key])  # Revealed type is "str"

    # You can also index using unions of literals
    id_key: Literal["main_id", "backup_id"]
    reveal_type(d[id_key])    # Revealed type is "int"

.. _tagged_unions:

Tagged unions
*************

When you have a union of types, you can normally discriminate between each type
in the union by using ``isinstance`` checks. For example, if you had a variable ``x`` of
type ``Union[int, str]``, you could write some code that runs only if ``x`` is an int
by doing ``if isinstance(x, int): ...``.

However, it is not always possible or convenient to do this. For example, it is not
possible to use ``isinstance`` to distinguish between two different TypedDicts since
at runtime, your variable will simply be just a dict.

Instead, what you can do is *label* or *tag* your TypedDicts with a distinct Literal
type. Then, you can discriminate between each kind of TypedDict by checking the label:

.. code-block:: python

    from typing import Literal, TypedDict, Union

    class NewJobEvent(TypedDict):
        tag: Literal["new-job"]
        job_name: str
        config_file_path: str

    class CancelJobEvent(TypedDict):
        tag: Literal["cancel-job"]
        job_id: int

    Event = Union[NewJobEvent, CancelJobEvent]

    def process_event(event: Event) -> None:
        # Since we made sure both TypedDicts have a key named 'tag', it's
        # safe to do 'event["tag"]'. This expression normally has the type
        # Literal["new-job", "cancel-job"], but the check below will narrow
        # the type to either Literal["new-job"] or Literal["cancel-job"].
        #
        # This in turns narrows the type of 'event' to either NewJobEvent
        # or CancelJobEvent.
        if event["tag"] == "new-job":
            print(event["job_name"])
        else:
            print(event["job_id"])

While this feature is mostly useful when working with TypedDicts, you can also
use the same technique with regular objects, tuples, or namedtuples.

Similarly, tags do not need to be specifically str Literals: they can be any type
you can normally narrow within ``if`` statements and the like. For example, you
could have your tags be int or Enum Literals or even regular classes you narrow
using ``isinstance()`` (Python 3.12 syntax):

.. code-block:: python

    class Wrapper[T]:
        def __init__(self, inner: T) -> None:
            self.inner = inner

    def process(w: Wrapper[int] | Wrapper[str]) -> None:
        # Doing `if isinstance(w, Wrapper[int])` does not work: isinstance requires
        # that the second argument always be an *erased* type, with no generics.
        # This is because generics are a typing-only concept and do not exist at
        # runtime in a way `isinstance` can always check.
        #
        # However, we can side-step this by checking the type of `w.inner` to
        # narrow `w` itself:
        if isinstance(w.inner, int):
            reveal_type(w)  # Revealed type is "Wrapper[int]"
        else:
            reveal_type(w)  # Revealed type is "Wrapper[str]"

This feature is sometimes called "sum types" or "discriminated union types"
in other programming languages.

Exhaustiveness checking
***********************

You may want to check that some code covers all possible
``Literal`` or ``Enum`` cases. Example:

.. code-block:: python

  from typing import Literal

  PossibleValues = Literal['one', 'two']

  def validate(x: PossibleValues) -> bool:
      if x == 'one':
          return True
      elif x == 'two':
          return False
      raise ValueError(f'Invalid value: {x}')

  assert validate('one') is True
  assert validate('two') is False

In the code above, it's easy to make a mistake. You can
add a new literal value to ``PossibleValues`` but forget
to handle it in the ``validate`` function:

.. code-block:: python

  PossibleValues = Literal['one', 'two', 'three']

Mypy won't catch that ``'three'`` is not covered.  If you want mypy to
perform an exhaustiveness check, you need to update your code to use an
``assert_never()`` check:

.. code-block:: python

  from typing import Literal
  from typing_extensions import assert_never

  PossibleValues = Literal['one', 'two']

  def validate(x: PossibleValues) -> bool:
      if x == 'one':
          return True
      elif x == 'two':
          return False
      assert_never(x)

Now if you add a new value to ``PossibleValues`` but don't update ``validate``,
mypy will spot the error:

.. code-block:: python

  PossibleValues = Literal['one', 'two', 'three']

  def validate(x: PossibleValues) -> bool:
      if x == 'one':
          return True
      elif x == 'two':
          return False
      # Error: Argument 1 to "assert_never" has incompatible type "Literal['three']";
      # expected "NoReturn"
      assert_never(x)

If runtime checking against unexpected values is not needed, you can
leave out the ``assert_never`` call in the above example, and mypy
will still generate an error about function ``validate`` returning
without a value:

.. code-block:: python

  PossibleValues = Literal['one', 'two', 'three']

  # Error: Missing return statement
  def validate(x: PossibleValues) -> bool:
      if x == 'one':
          return True
      elif x == 'two':
          return False

For the sake of brevity, you can use the ``in`` operator in combination with
list, set, or tuple expressions (lists, sets, or tuples created "on the fly"):

.. code-block:: python

  PossibleValues = Literal['one', 'two', 'three']

  def validate(x: PossibleValues) -> bool:
      if x in ['one']:
          return True
      elif x in ('two', 'three'):
          return False

Exhaustiveness checking is also supported for match statements (Python 3.10 and later):

.. code-block:: python

  def validate(x: PossibleValues) -> bool:
      match x:
          case 'one':
              return True
          case 'two':
              return False
      assert_never(x)


Limitations
***********

Mypy will not understand expressions that use variables of type ``Literal[..]``
on a deep level. For example, if you have a variable ``a`` of type ``Literal[3]``
and another variable ``b`` of type ``Literal[5]``, mypy will infer that
``a + b`` has type ``int``, **not** type ``Literal[8]``.

The basic rule is that literal types are treated as just regular subtypes of
whatever type the parameter has. For example, ``Literal[3]`` is treated as a
subtype of ``int`` and so will inherit all of ``int``'s methods directly. This
means that ``Literal[3].__add__`` accepts the same arguments and has the same
return type as ``int.__add__``.


Enums
-----

Mypy has special support for :py:class:`enum.Enum` and its subclasses:
:py:class:`enum.IntEnum`, :py:class:`enum.Flag`, :py:class:`enum.IntFlag`,
and :py:class:`enum.StrEnum`.

.. code-block:: python

  from enum import Enum

  class Direction(Enum):
      up = 'up'
      down = 'down'

  reveal_type(Direction.up)  # Revealed type is "Literal[Direction.up]?"
  reveal_type(Direction.down)  # Revealed type is "Literal[Direction.down]?"

You can use enums to annotate types as you would expect:

.. code-block:: python

  class Movement:
      def __init__(self, direction: Direction, speed: float) -> None:
          self.direction = direction
          self.speed = speed

  Movement(Direction.up, 5.0)  # ok
  Movement('up', 5.0)  # E: Argument 1 to "Movement" has incompatible type "str"; expected "Direction"

Exhaustiveness checking
***********************

Similar to ``Literal`` types, ``Enum`` supports exhaustiveness checking.
Let's start with a definition:

.. code-block:: python

  from enum import Enum
  from typing import NoReturn
  from typing_extensions import assert_never

  class Direction(Enum):
      up = 'up'
      down = 'down'

Now, let's use an exhaustiveness check:

.. code-block:: python

  def choose_direction(direction: Direction) -> None:
      if direction is Direction.up:
          reveal_type(direction)  # N: Revealed type is "Literal[Direction.up]"
          print('Going up!')
          return
      elif direction is Direction.down:
          print('Down')
          return
      # This line is never reached
      assert_never(direction)

If we forget to handle one of the cases, mypy will generate an error:

.. code-block:: python

  def choose_direction(direction: Direction) -> None:
      if direction == Direction.up:
          print('Going up!')
          return
      assert_never(direction)  # E: Argument 1 to "assert_never" has incompatible type "Direction"; expected "NoReturn"

Exhaustiveness checking is also supported for match statements (Python 3.10 and later).

Extra Enum checks
*****************

Mypy also tries to support special features of ``Enum``
the same way Python's runtime does:

- Any ``Enum`` class with values is implicitly :ref:`final <final_attrs>`.
  This is what happens in CPython:

  .. code-block:: python

    >>> class AllDirection(Direction):
    ...     left = 'left'
    ...     right = 'right'
    Traceback (most recent call last):
      ...
    TypeError: AllDirection: cannot extend enumeration 'Direction'

  Mypy also catches this error:

  .. code-block:: python

    class AllDirection(Direction):  # E: Cannot inherit from final class "Direction"
        left = 'left'
        right = 'right'

- All ``Enum`` fields are implicitly ``final`` as well.

  .. code-block:: python

    Direction.up = '^'  # E: Cannot assign to final attribute "up"

- All field names are checked to be unique.

  .. code-block:: python

     class Some(Enum):
        x = 1
        x = 2  # E: Attempted to reuse member name "x" in Enum definition "Some"

- Base classes have no conflicts and mixin types are correct.

  .. code-block:: python

    class WrongEnum(str, int, enum.Enum):
        # E: Only a single data type mixin is allowed for Enum subtypes, found extra "int"
        ...

    class MixinAfterEnum(enum.Enum, Mixin): # E: No base classes are allowed after "enum.Enum"
        ...
