More types
==========

This section introduces a few additional kinds of types, including :py:data:`~typing.NoReturn`,
:py:class:`~typing.NewType`, and types for async code. It also discusses
how to give functions more precise types using overloads. All of these are only
situationally useful, so feel free to skip this section and come back when you
have a need for some of them.

Here's a quick summary of what's covered here:

* :py:data:`~typing.NoReturn` lets you tell mypy that a function never returns normally.

* :py:class:`~typing.NewType` lets you define a variant of a type that is treated as a
  separate type by mypy but is identical to the original type at runtime.
  For example, you can have ``UserId`` as a variant of ``int`` that is
  just an ``int`` at runtime.

* :py:func:`@overload <typing.overload>` lets you define a function that can accept multiple distinct
  signatures. This is useful if you need to encode a relationship between the
  arguments and the return type that would be difficult to express normally.

* Async types let you type check programs using ``async`` and ``await``.

.. _noreturn:

The NoReturn type
*****************

Mypy provides support for functions that never return. For
example, a function that unconditionally raises an exception:

.. code-block:: python

   from typing import NoReturn

   def stop() -> NoReturn:
       raise Exception('no way')

Mypy will ensure that functions annotated as returning :py:data:`~typing.NoReturn`
truly never return, either implicitly or explicitly. Mypy will also
recognize that the code after calls to such functions is unreachable
and will behave accordingly:

.. code-block:: python

   def f(x: int) -> int:
       if x == 0:
           return x
       stop()
       return 'whatever works'  # No error in an unreachable block

In earlier Python versions you need to install ``typing_extensions`` using
pip to use :py:data:`~typing.NoReturn` in your code. Python 3 command line:

.. code-block:: text

    python3 -m pip install --upgrade typing-extensions

.. _newtypes:

NewTypes
********

There are situations where you may want to avoid programming errors by
creating simple derived classes that are only used to distinguish
certain values from base class instances. Example:

.. code-block:: python

    class UserId(int):
        pass

    def get_by_user_id(user_id: UserId):
        ...

However, this approach introduces some runtime overhead. To avoid this, the typing
module provides a helper object :py:class:`~typing.NewType` that creates simple unique types with
almost zero runtime overhead. Mypy will treat the statement
``Derived = NewType('Derived', Base)`` as being roughly equivalent to the following
definition:

.. code-block:: python

    class Derived(Base):
        def __init__(self, _x: Base) -> None:
            ...

However, at runtime, ``NewType('Derived', Base)`` will return a dummy callable that
simply returns its argument:

.. code-block:: python

    def Derived(_x):
        return _x

Mypy will require explicit casts from ``int`` where ``UserId`` is expected, while
implicitly casting from ``UserId`` where ``int`` is expected. Examples:

.. code-block:: python

    from typing import NewType

    UserId = NewType('UserId', int)

    def name_by_id(user_id: UserId) -> str:
        ...

    UserId('user')          # Fails type check

    name_by_id(42)          # Fails type check
    name_by_id(UserId(42))  # OK

    num: int = UserId(5) + 1

:py:class:`~typing.NewType` accepts exactly two arguments. The first argument must be a string literal
containing the name of the new type and must equal the name of the variable to which the new
type is assigned. The second argument must be a properly subclassable class, i.e.,
not a type construct like a :ref:`union type <union-types>`, etc.

The callable returned by :py:class:`~typing.NewType` accepts only one argument; this is equivalent to
supporting only one constructor accepting an instance of the base class (see above).
Example:

.. code-block:: python

    from typing import NewType

    class PacketId:
        def __init__(self, major: int, minor: int) -> None:
            self._major = major
            self._minor = minor

    TcpPacketId = NewType('TcpPacketId', PacketId)

    packet = PacketId(100, 100)
    tcp_packet = TcpPacketId(packet)  # OK

    tcp_packet = TcpPacketId(127, 0)  # Fails in type checker and at runtime

You cannot use :py:func:`isinstance` or :py:func:`issubclass` on the object returned by
:py:class:`~typing.NewType`, nor can you subclass an object returned by :py:class:`~typing.NewType`.

.. note::

    Unlike type aliases, :py:class:`~typing.NewType` will create an entirely new and
    unique type when used. The intended purpose of :py:class:`~typing.NewType` is to help you
    detect cases where you accidentally mixed together the old base type and the
    new derived type.

    For example, the following will successfully typecheck when using type
    aliases:

    .. code-block:: python

        UserId = int

        def name_by_id(user_id: UserId) -> str:
            ...

        name_by_id(3)  # ints and UserId are synonymous

    But a similar example using :py:class:`~typing.NewType` will not typecheck:

    .. code-block:: python

        from typing import NewType

        UserId = NewType('UserId', int)

        def name_by_id(user_id: UserId) -> str:
            ...

        name_by_id(3)  # int is not the same as UserId

.. _function-overloading:

Function overloading
********************

Sometimes the arguments and types in a function depend on each other
in ways that can't be captured with a :ref:`union types <union-types>`. For example, suppose
we want to write a function that can accept x-y coordinates. If we pass
in just a single x-y coordinate, we return a ``ClickEvent`` object. However,
if we pass in two x-y coordinates, we return a ``DragEvent`` object.

Our first attempt at writing this function might look like this:

.. code-block:: python

    def mouse_event(x1: int,
                    y1: int,
                    x2: int | None = None,
                    y2: int | None = None) -> ClickEvent | DragEvent:
        if x2 is None and y2 is None:
            return ClickEvent(x1, y1)
        elif x2 is not None and y2 is not None:
            return DragEvent(x1, y1, x2, y2)
        else:
            raise TypeError("Bad arguments")

While this function signature works, it's too loose: it implies ``mouse_event``
could return either object regardless of the number of arguments
we pass in. It also does not prohibit a caller from passing in the wrong
number of ints: mypy would treat calls like ``mouse_event(1, 2, 20)`` as being
valid, for example.

We can do better by using :pep:`overloading <484#function-method-overloading>`
which lets us give the same function multiple type annotations (signatures)
to more accurately describe the function's behavior:

.. code-block:: python

    from typing import overload

    # Overload *variants* for 'mouse_event'.
    # These variants give extra information to the type checker.
    # They are ignored at runtime.

    @overload
    def mouse_event(x1: int, y1: int) -> ClickEvent: ...
    @overload
    def mouse_event(x1: int, y1: int, x2: int, y2: int) -> DragEvent: ...

    # The actual *implementation* of 'mouse_event'.
    # The implementation contains the actual runtime logic.
    #
    # It may or may not have type hints. If it does, mypy
    # will check the body of the implementation against the
    # type hints.
    #
    # Mypy will also check and make sure the signature is
    # consistent with the provided variants.

    def mouse_event(x1: int,
                    y1: int,
                    x2: int | None = None,
                    y2: int | None = None) -> ClickEvent | DragEvent:
        if x2 is None and y2 is None:
            return ClickEvent(x1, y1)
        elif x2 is not None and y2 is not None:
            return DragEvent(x1, y1, x2, y2)
        else:
            raise TypeError("Bad arguments")

This allows mypy to understand calls to ``mouse_event`` much more precisely.
For example, mypy will understand that ``mouse_event(5, 25)`` will
always have a return type of ``ClickEvent`` and will report errors for
calls like ``mouse_event(5, 25, 2)``.

As another example, suppose we want to write a custom container class that
implements the :py:meth:`__getitem__ <object.__getitem__>` method (``[]`` bracket indexing). If this
method receives an integer we return a single item. If it receives a
``slice``, we return a :py:class:`~collections.abc.Sequence` of items.

We can precisely encode this relationship between the argument and the
return type by using overloads like so (Python 3.12 syntax):

.. code-block:: python

    from collections.abc import Sequence
    from typing import overload

    class MyList[T](Sequence[T]):
        @overload
        def __getitem__(self, index: int) -> T: ...

        @overload
        def __getitem__(self, index: slice) -> Sequence[T]: ...

        def __getitem__(self, index: int | slice) -> T | Sequence[T]:
            if isinstance(index, int):
                # Return a T here
            elif isinstance(index, slice):
                # Return a sequence of Ts here
            else:
                raise TypeError(...)

Here is the same example using the legacy syntax (Python 3.11 and earlier):

.. code-block:: python

    from collections.abc import Sequence
    from typing import TypeVar, overload

    T = TypeVar('T')

    class MyList(Sequence[T]):
        @overload
        def __getitem__(self, index: int) -> T: ...

        @overload
        def __getitem__(self, index: slice) -> Sequence[T]: ...

        def __getitem__(self, index: int | slice) -> T | Sequence[T]:
            if isinstance(index, int):
                # Return a T here
            elif isinstance(index, slice):
                # Return a sequence of Ts here
            else:
                raise TypeError(...)

.. note::

   If you just need to constrain a type variable to certain types or
   subtypes, you can use a :ref:`value restriction
   <type-variable-value-restriction>`.

The default values of a function's arguments don't affect its signature -- only
the absence or presence of a default value does. So in order to reduce
redundancy, it's possible to replace default values in overload definitions with
``...`` as a placeholder:

.. code-block:: python

    from typing import overload

    class M: ...

    @overload
    def get_model(model_or_pk: M, flag: bool = ...) -> M: ...
    @overload
    def get_model(model_or_pk: int, flag: bool = ...) -> M | None: ...

    def get_model(model_or_pk: int | M, flag: bool = True) -> M | None:
        ...


Runtime behavior
----------------

An overloaded function must consist of two or more overload *variants*
followed by an *implementation*. The variants and the implementations
must be adjacent in the code: think of them as one indivisible unit.

The variant bodies must all be empty; only the implementation is allowed
to contain code. This is because at runtime, the variants are completely
ignored: they're overridden by the final implementation function.

This means that an overloaded function is still an ordinary Python
function! There is no automatic dispatch handling and you must manually
handle the different types in the implementation (e.g. by using
``if`` statements and :py:func:`isinstance <isinstance>` checks).

If you are adding an overload within a stub file, the implementation
function should be omitted: stubs do not contain runtime logic.

.. note::

   While we can leave the variant body empty using the ``pass`` keyword,
   the more common convention is to instead use the ellipsis (``...``) literal.

Type checking calls to overloads
--------------------------------

When you call an overloaded function, mypy will infer the correct return
type by picking the best matching variant, after taking into consideration
both the argument types and arity. However, a call is never type
checked against the implementation. This is why mypy will report calls
like ``mouse_event(5, 25, 3)`` as being invalid even though it matches the
implementation signature.

If there are multiple equally good matching variants, mypy will select
the variant that was defined first. For example, consider the following
program:

.. code-block:: python

    # For Python 3.8 and below you must use `typing.List` instead of `list`. e.g.
    # from typing import List
    from typing import overload

    @overload
    def summarize(data: list[int]) -> float: ...

    @overload
    def summarize(data: list[str]) -> str: ...

    def summarize(data):
        if not data:
            return 0.0
        elif isinstance(data[0], int):
            # Do int specific code
        else:
            # Do str-specific code

    # What is the type of 'output'? float or str?
    output = summarize([])

The ``summarize([])`` call matches both variants: an empty list could
be either a ``list[int]`` or a ``list[str]``. In this case, mypy
will break the tie by picking the first matching variant: ``output``
will have an inferred type of ``float``. The implementer is responsible
for making sure ``summarize`` breaks ties in the same way at runtime.

However, there are two exceptions to the "pick the first match" rule.
First, if multiple variants match due to an argument being of type
``Any``, mypy will make the inferred type also be ``Any``:

.. code-block:: python

    dynamic_var: Any = some_dynamic_function()

    # output2 is of type 'Any'
    output2 = summarize(dynamic_var)

Second, if multiple variants match due to one or more of the arguments
being a union, mypy will make the inferred type be the union of the
matching variant returns:

.. code-block:: python

    some_list: list[int] | list[str]

    # output3 is of type 'float | str'
    output3 = summarize(some_list)

.. note::

   Due to the "pick the first match" rule, changing the order of your
   overload variants can change how mypy type checks your program.

   To minimize potential issues, we recommend that you:

   1. Make sure your overload variants are listed in the same order as
      the runtime checks (e.g. :py:func:`isinstance <isinstance>` checks) in your implementation.
   2. Order your variants and runtime checks from most to least specific.
      (See the following section for an example).

Type checking the variants
--------------------------

Mypy will perform several checks on your overload variant definitions
to ensure they behave as expected. First, mypy will check and make sure
that no overload variant is shadowing a subsequent one. For example,
consider the following function which adds together two ``Expression``
objects, and contains a special-case to handle receiving two ``Literal``
types:

.. code-block:: python

    from typing import overload

    class Expression:
        # ...snip...

    class Literal(Expression):
        # ...snip...

    # Warning -- the first overload variant shadows the second!

    @overload
    def add(left: Expression, right: Expression) -> Expression: ...

    @overload
    def add(left: Literal, right: Literal) -> Literal: ...

    def add(left: Expression, right: Expression) -> Expression:
        # ...snip...

While this code snippet is technically type-safe, it does contain an
anti-pattern: the second variant will never be selected! If we try calling
``add(Literal(3), Literal(4))``, mypy will always pick the first variant
and evaluate the function call to be of type ``Expression``, not ``Literal``.
This is because ``Literal`` is a subtype of ``Expression``, which means
the "pick the first match" rule will always halt after considering the
first overload.

Because having an overload variant that can never be matched is almost
certainly a mistake, mypy will report an error. To fix the error, we can
either 1) delete the second overload or 2) swap the order of the overloads:

.. code-block:: python

    # Everything is ok now -- the variants are correctly ordered
    # from most to least specific.

    @overload
    def add(left: Literal, right: Literal) -> Literal: ...

    @overload
    def add(left: Expression, right: Expression) -> Expression: ...

    def add(left: Expression, right: Expression) -> Expression:
        # ...snip...

Mypy will also type check the different variants and flag any overloads
that have inherently unsafely overlapping variants. For example, consider
the following unsafe overload definition:

.. code-block:: python

    from typing import overload

    @overload
    def unsafe_func(x: int) -> int: ...

    @overload
    def unsafe_func(x: object) -> str: ...

    def unsafe_func(x: object) -> int | str:
        if isinstance(x, int):
            return 42
        else:
            return "some string"

On the surface, this function definition appears to be fine. However, it will
result in a discrepancy between the inferred type and the actual runtime type
when we try using it like so:

.. code-block:: python

    some_obj: object = 42
    unsafe_func(some_obj) + " danger danger"  # Type checks, yet crashes at runtime!

Since ``some_obj`` is of type :py:class:`object`, mypy will decide that ``unsafe_func``
must return something of type ``str`` and concludes the above will type check.
But in reality, ``unsafe_func`` will return an int, causing the code to crash
at runtime!

To prevent these kinds of issues, mypy will detect and prohibit inherently unsafely
overlapping overloads on a best-effort basis. Two variants are considered unsafely
overlapping when both of the following are true:

1. All of the arguments of the first variant are potentially compatible with the second.
2. The return type of the first variant is *not* compatible with (e.g. is not a
   subtype of) the second.

So in this example, the ``int`` argument in the first variant is a subtype of
the ``object`` argument in the second, yet the ``int`` return type is not a subtype of
``str``. Both conditions are true, so mypy will correctly flag ``unsafe_func`` as
being unsafe.

Note that in cases where you ignore the overlapping overload error, mypy will usually
still infer the types you expect at callsites.

However, mypy will not detect *all* unsafe uses of overloads. For example,
suppose we modify the above snippet so it calls ``summarize`` instead of
``unsafe_func``:

.. code-block:: python

    some_list: list[str] = []
    summarize(some_list) + "danger danger"  # Type safe, yet crashes at runtime!

We run into a similar issue here. This program type checks if we look just at the
annotations on the overloads. But since ``summarize(...)`` is designed to be biased
towards returning a float when it receives an empty list, this program will actually
crash during runtime.

The reason mypy does not flag definitions like ``summarize`` as being potentially
unsafe is because if it did, it would be extremely difficult to write a safe
overload. For example, suppose we define an overload with two variants that accept
types ``A`` and ``B`` respectively. Even if those two types were completely unrelated,
the user could still potentially trigger a runtime error similar to the ones above by
passing in a value of some third type ``C`` that inherits from both ``A`` and ``B``.

Thankfully, these types of situations are relatively rare. What this does mean,
however, is that you should exercise caution when designing or using an overloaded
function that can potentially receive values that are an instance of two seemingly
unrelated types.


Type checking the implementation
--------------------------------

The body of an implementation is type-checked against the
type hints provided on the implementation. For example, in the
``MyList`` example up above, the code in the body is checked with
argument list ``index: int | slice`` and a return type of
``T | Sequence[T]``. If there are no annotations on the
implementation, then the body is not type checked. If you want to
force mypy to check the body anyways, use the :option:`--check-untyped-defs <mypy --check-untyped-defs>`
flag (:ref:`more details here <untyped-definitions-and-calls>`).

The variants must also also be compatible with the implementation
type hints. In the ``MyList`` example, mypy will check that the
parameter type ``int`` and the return type ``T`` are compatible with
``int | slice`` and ``T | Sequence`` for the
first variant. For the second variant it verifies the parameter
type ``slice`` and the return type ``Sequence[T]`` are compatible
with ``int | slice`` and ``T | Sequence``.

.. note::

   The overload semantics documented above are new as of mypy 0.620.

   Previously, mypy used to perform type erasure on all overload variants. For
   example, the ``summarize`` example from the previous section used to be
   illegal because ``list[str]`` and ``list[int]`` both erased to just ``list[Any]``.
   This restriction was removed in mypy 0.620.

   Mypy also previously used to select the best matching variant using a different
   algorithm. If this algorithm failed to find a match, it would default to returning
   ``Any``. The new algorithm uses the "pick the first match" rule and will fall back
   to returning ``Any`` only if the input arguments also contain ``Any``.


Conditional overloads
---------------------

Sometimes it is useful to define overloads conditionally.
Common use cases include types that are unavailable at runtime or that
only exist in a certain Python version. All existing overload rules still apply.
For example, there must be at least two overloads.

.. note::

    Mypy can only infer a limited number of conditions.
    Supported ones currently include :py:data:`~typing.TYPE_CHECKING`, ``MYPY``,
    :ref:`version_and_platform_checks`, :option:`--always-true <mypy --always-true>`,
    and :option:`--always-false <mypy --always-false>` values.

.. code-block:: python

    from typing import TYPE_CHECKING, Any, overload

    if TYPE_CHECKING:
        class A: ...
        class B: ...


    if TYPE_CHECKING:
        @overload
        def func(var: A) -> A: ...

        @overload
        def func(var: B) -> B: ...

    def func(var: Any) -> Any:
        return var


    reveal_type(func(A()))  # Revealed type is "A"

.. code-block:: python

    # flags: --python-version 3.10
    import sys
    from typing import Any, overload

    class A: ...
    class B: ...
    class C: ...
    class D: ...


    if sys.version_info < (3, 7):
        @overload
        def func(var: A) -> A: ...

    elif sys.version_info >= (3, 10):
        @overload
        def func(var: B) -> B: ...

    else:
        @overload
        def func(var: C) -> C: ...

    @overload
    def func(var: D) -> D: ...

    def func(var: Any) -> Any:
        return var


    reveal_type(func(B()))  # Revealed type is "B"
    reveal_type(func(C()))  # No overload variant of "func" matches argument type "C"
        # Possible overload variants:
        #     def func(var: B) -> B
        #     def func(var: D) -> D
        # Revealed type is "Any"


.. note::

    In the last example, mypy is executed with
    :option:`--python-version 3.10 <mypy --python-version>`.
    Therefore, the condition ``sys.version_info >= (3, 10)`` will match and
    the overload for ``B`` will be added.
    The overloads for ``A`` and ``C`` are ignored!
    The overload for ``D`` is not defined conditionally and thus is also added.

When mypy cannot infer a condition to be always ``True`` or always ``False``,
an error is emitted.

.. code-block:: python

    from typing import Any, overload

    class A: ...
    class B: ...


    def g(bool_var: bool) -> None:
        if bool_var:  # Condition can't be inferred, unable to merge overloads
            @overload
            def func(var: A) -> A: ...

            @overload
            def func(var: B) -> B: ...

        def func(var: Any) -> Any: ...

        reveal_type(func(A()))  # Revealed type is "Any"


.. _advanced_self:

Advanced uses of self-types
***************************

Normally, mypy doesn't require annotations for the first arguments of instance and
class methods. However, they may be needed to have more precise static typing
for certain programming patterns.

Restricted methods in generic classes
-------------------------------------

In generic classes some methods may be allowed to be called only
for certain values of type arguments (Python 3.12 syntax):

.. code-block:: python

   class Tag[T]:
       item: T

       def uppercase_item(self: Tag[str]) -> str:
           return self.item.upper()

   def label(ti: Tag[int], ts: Tag[str]) -> None:
       ti.uppercase_item()  # E: Invalid self argument "Tag[int]" to attribute function
                            # "uppercase_item" with type "Callable[[Tag[str]], str]"
       ts.uppercase_item()  # This is OK

This pattern also allows matching on nested types in situations where the type
argument is itself generic (Python 3.12 syntax):

.. code-block:: python

   from collections.abc import Sequence

   class Storage[T]:
       def __init__(self, content: T) -> None:
           self._content = content

       def first_chunk[S](self: Storage[Sequence[S]]) -> S:
           return self._content[0]

   page: Storage[list[str]]
   page.first_chunk()  # OK, type is "str"

   Storage(0).first_chunk()  # Error: Invalid self argument "Storage[int]" to attribute function
                             # "first_chunk" with type "Callable[[Storage[Sequence[S]]], S]"

Finally, one can use overloads on self-type to express precise types of
some tricky methods (Python 3.12 syntax):

.. code-block:: python

   from collections.abc import Callable
   from typing import overload

   class Tag[T]:
       @overload
       def export(self: Tag[str]) -> str: ...
       @overload
       def export(self, converter: Callable[[T], str]) -> str: ...

       def export(self, converter=None):
           if isinstance(self.item, str):
               return self.item
           return converter(self.item)

In particular, an :py:meth:`~object.__init__` method overloaded on self-type
may be useful to annotate generic class constructors where type arguments
depend on constructor parameters in a non-trivial way, see e.g. :py:class:`~subprocess.Popen`.

Mixin classes
-------------

Using host class protocol as a self-type in mixin methods allows
more code re-usability for static typing of mixin classes. For example,
one can define a protocol that defines common functionality for
host classes instead of adding required abstract methods to every mixin:

.. code-block:: python

   class Lockable(Protocol):
       @property
       def lock(self) -> Lock: ...

   class AtomicCloseMixin:
       def atomic_close(self: Lockable) -> int:
           with self.lock:
               # perform actions

   class AtomicOpenMixin:
       def atomic_open(self: Lockable) -> int:
           with self.lock:
               # perform actions

   class File(AtomicCloseMixin, AtomicOpenMixin):
       def __init__(self) -> None:
           self.lock = Lock()

   class Bad(AtomicCloseMixin):
       pass

   f = File()
   b: Bad
   f.atomic_close()  # OK
   b.atomic_close()  # Error: Invalid self type for "atomic_close"

Note that the explicit self-type is *required* to be a protocol whenever it
is not a supertype of the current class. In this case mypy will check the validity
of the self-type only at the call site.

Precise typing of alternative constructors
------------------------------------------

Some classes may define alternative constructors. If these
classes are generic, self-type allows giving them precise
signatures (Python 3.12 syntax):

.. code-block:: python

   from typing import Self

   class Base[T]:
       def __init__(self, item: T) -> None:
           self.item = item

       @classmethod
       def make_pair(cls, item: T) -> tuple[Self, Self]:
           return cls(item), cls(item)

   class Sub[T](Base[T]):
       ...

   pair = Sub.make_pair('yes')  # Type is "tuple[Sub[str], Sub[str]]"
   bad = Sub[int].make_pair('no')  # Error: Argument 1 to "make_pair" of "Base"
                                   # has incompatible type "str"; expected "int"

.. _async-and-await:

Typing async/await
******************

Mypy lets you type coroutines that use the ``async/await`` syntax.
For more information regarding coroutines, see :pep:`492` and the
`asyncio documentation <python:library/asyncio>`_.

Functions defined using ``async def`` are typed similar to normal functions.
The return type annotation should be the same as the type of the value you
expect to get back when ``await``-ing the coroutine.

.. code-block:: python

   import asyncio

   async def format_string(tag: str, count: int) -> str:
       return f'T-minus {count} ({tag})'

   async def countdown(tag: str, count: int) -> str:
       while count > 0:
           my_str = await format_string(tag, count)  # type is inferred to be str
           print(my_str)
           await asyncio.sleep(0.1)
           count -= 1
       return "Blastoff!"

   asyncio.run(countdown("Millennium Falcon", 5))

The result of calling an ``async def`` function *without awaiting* will
automatically be inferred to be a value of type
:py:class:`Coroutine[Any, Any, T] <collections.abc.Coroutine>`, which is a subtype of
:py:class:`Awaitable[T] <collections.abc.Awaitable>`:

.. code-block:: python

   my_coroutine = countdown("Millennium Falcon", 5)
   reveal_type(my_coroutine)  # Revealed type is "typing.Coroutine[Any, Any, builtins.str]"

.. _async-iterators:

Asynchronous iterators
----------------------

If you have an asynchronous iterator, you can use the
:py:class:`~collections.abc.AsyncIterator` type in your annotations:

.. code-block:: python

   from collections.abc import AsyncIterator
   from typing import Optional
   import asyncio

   class arange:
       def __init__(self, start: int, stop: int, step: int) -> None:
           self.start = start
           self.stop = stop
           self.step = step
           self.count = start - step

       def __aiter__(self) -> AsyncIterator[int]:
           return self

       async def __anext__(self) -> int:
           self.count += self.step
           if self.count == self.stop:
               raise StopAsyncIteration
           else:
               return self.count

   async def run_countdown(tag: str, countdown: AsyncIterator[int]) -> str:
       async for i in countdown:
           print(f'T-minus {i} ({tag})')
           await asyncio.sleep(0.1)
       return "Blastoff!"

   asyncio.run(run_countdown("Serenity", arange(5, 0, -1)))

Async generators (introduced in :pep:`525`) are an easy way to create
async iterators:

.. code-block:: python

   from collections.abc import AsyncGenerator
   from typing import Optional
   import asyncio

   # Could also type this as returning AsyncIterator[int]
   async def arange(start: int, stop: int, step: int) -> AsyncGenerator[int, None]:
       current = start
       while (step > 0 and current < stop) or (step < 0 and current > stop):
           yield current
           current += step

   asyncio.run(run_countdown("Battlestar Galactica", arange(5, 0, -1)))

One common confusion is that the presence of a ``yield`` statement in an
``async def`` function has an effect on the type of the function:

.. code-block:: python

   from collections.abc import AsyncIterator

   async def arange(stop: int) -> AsyncIterator[int]:
       # When called, arange gives you an async iterator
       # Equivalent to Callable[[int], AsyncIterator[int]]
       i = 0
       while i < stop:
           yield i
           i += 1

   async def coroutine(stop: int) -> AsyncIterator[int]:
       # When called, coroutine gives you something you can await to get an async iterator
       # Equivalent to Callable[[int], Coroutine[Any, Any, AsyncIterator[int]]]
       return arange(stop)

   async def main() -> None:
       reveal_type(arange(5))  # Revealed type is "typing.AsyncIterator[builtins.int]"
       reveal_type(coroutine(5))  # Revealed type is "typing.Coroutine[Any, Any, typing.AsyncIterator[builtins.int]]"

       await arange(5)  # Error: Incompatible types in "await" (actual type "AsyncIterator[int]", expected type "Awaitable[Any]")
       reveal_type(await coroutine(5))  # Revealed type is "typing.AsyncIterator[builtins.int]"

This can sometimes come up when trying to define base classes, Protocols or overloads:

.. code-block:: python

    from collections.abc import AsyncIterator
    from typing import Protocol, overload

    class LauncherIncorrect(Protocol):
        # Because launch does not have yield, this has type
        # Callable[[], Coroutine[Any, Any, AsyncIterator[int]]]
        # instead of
        # Callable[[], AsyncIterator[int]]
        async def launch(self) -> AsyncIterator[int]:
            raise NotImplementedError

    class LauncherCorrect(Protocol):
        def launch(self) -> AsyncIterator[int]:
            raise NotImplementedError

    class LauncherAlsoCorrect(Protocol):
        async def launch(self) -> AsyncIterator[int]:
            raise NotImplementedError
            if False:
                yield 0

    # The type of the overloads is independent of the implementation.
    # In particular, their type is not affected by whether or not the
    # implementation contains a `yield`.
    # Use of `def`` makes it clear the type is Callable[..., AsyncIterator[int]],
    # whereas with `async def` it would be Callable[..., Coroutine[Any, Any, AsyncIterator[int]]]
    @overload
    def launch(*, count: int = ...) -> AsyncIterator[int]: ...
    @overload
    def launch(*, time: float = ...) -> AsyncIterator[int]: ...

    async def launch(*, count: int = 0, time: float = 0) -> AsyncIterator[int]:
        # The implementation of launch is an async generator and contains a yield
        yield 0
