.. _error-code-list:

Error codes enabled by default
==============================

This section documents various errors codes that mypy can generate
with default options. See :ref:`error-codes` for general documentation
about error codes. :ref:`error-codes-optional` documents additional
error codes that you can enable.

.. _code-attr-defined:

Check that attribute exists [attr-defined]
------------------------------------------

Mypy checks that an attribute is defined in the target class or module
when using the dot operator. This applies to both getting and setting
an attribute. New attributes are defined by assignments in the class
body, or assignments to ``self.x`` in methods. These assignments don't
generate ``attr-defined`` errors.

Example:

.. code-block:: python

   class Resource:
       def __init__(self, name: str) -> None:
           self.name = name

   r = Resource('x')
   print(r.name)  # OK
   print(r.id)  # Error: "Resource" has no attribute "id"  [attr-defined]
   r.id = 5  # Error: "Resource" has no attribute "id"  [attr-defined]

This error code is also generated if an imported name is not defined
in the module in a ``from ... import`` statement (as long as the
target module can be found):

.. code-block:: python

    # Error: Module "os" has no attribute "non_existent"  [attr-defined]
    from os import non_existent

A reference to a missing attribute is given the ``Any`` type. In the
above example, the type of ``non_existent`` will be ``Any``, which can
be important if you silence the error.

.. _code-union-attr:

Check that attribute exists in each union item [union-attr]
-----------------------------------------------------------

If you access the attribute of a value with a union type, mypy checks
that the attribute is defined for *every* type in that
union. Otherwise the operation can fail at runtime. This also applies
to optional types.

Example:

.. code-block:: python

   from typing import Union

   class Cat:
       def sleep(self) -> None: ...
       def miaow(self) -> None: ...

   class Dog:
       def sleep(self) -> None: ...
       def follow_me(self) -> None: ...

   def func(animal: Union[Cat, Dog]) -> None:
       # OK: 'sleep' is defined for both Cat and Dog
       animal.sleep()
       # Error: Item "Cat" of "Union[Cat, Dog]" has no attribute "follow_me"  [union-attr]
       animal.follow_me()

You can often work around these errors by using ``assert isinstance(obj, ClassName)``
or ``assert obj is not None`` to tell mypy that you know that the type is more specific
than what mypy thinks.

.. _code-name-defined:

Check that name is defined [name-defined]
-----------------------------------------

Mypy expects that all references to names have a corresponding
definition in an active scope, such as an assignment, function
definition or an import. This can catch missing definitions, missing
imports, and typos.

This example accidentally calls ``sort()`` instead of :py:func:`sorted`:

.. code-block:: python

    x = sort([3, 2, 4])  # Error: Name "sort" is not defined  [name-defined]

.. _code-used-before-def:

Check that a variable is not used before it's defined [used-before-def]
-----------------------------------------------------------------------

Mypy will generate an error if a name is used before it's defined.
While the name-defined check will catch issues with names that are undefined,
it will not flag if a variable is used and then defined later in the scope.
used-before-def check will catch such cases.

Example:

.. code-block:: python

    print(x)  # Error: Name "x" is used before definition [used-before-def]
    x = 123

.. _code-call-arg:

Check arguments in calls [call-arg]
-----------------------------------

Mypy expects that the number and names of arguments match the called function.
Note that argument type checks have a separate error code ``arg-type``.

Example:

.. code-block:: python

    from typing import Sequence

    def greet(name: str) -> None:
         print('hello', name)

    greet('jack')  # OK
    greet('jill', 'jack')  # Error: Too many arguments for "greet"  [call-arg]

.. _code-arg-type:

Check argument types [arg-type]
-------------------------------

Mypy checks that argument types in a call match the declared argument
types in the signature of the called function (if one exists).

Example:

.. code-block:: python

    from typing import Optional

    def first(x: list[int]) -> Optional[int]:
        return x[0] if x else 0

    t = (5, 4)
    # Error: Argument 1 to "first" has incompatible type "tuple[int, int]";
    #        expected "list[int]"  [arg-type]
    print(first(t))

.. _code-call-overload:

Check calls to overloaded functions [call-overload]
---------------------------------------------------

When you call an overloaded function, mypy checks that at least one of
the signatures of the overload items match the argument types in the
call.

Example:

.. code-block:: python

   from typing import overload, Optional

   @overload
   def inc_maybe(x: None) -> None: ...

   @overload
   def inc_maybe(x: int) -> int: ...

   def inc_maybe(x: Optional[int]) -> Optional[int]:
        if x is None:
            return None
        else:
            return x + 1

   inc_maybe(None)  # OK
   inc_maybe(5)  # OK

   # Error: No overload variant of "inc_maybe" matches argument type "float"  [call-overload]
   inc_maybe(1.2)

.. _code-valid-type:

Check validity of types [valid-type]
------------------------------------

Mypy checks that each type annotation and any expression that
represents a type is a valid type. Examples of valid types include
classes, union types, callable types, type aliases, and literal types.
Examples of invalid types include bare integer literals, functions,
variables, and modules.

This example incorrectly uses the function ``log`` as a type:

.. code-block:: python

    def log(x: object) -> None:
        print('log:', repr(x))

    # Error: Function "t.log" is not valid as a type  [valid-type]
    def log_all(objs: list[object], f: log) -> None:
        for x in objs:
            f(x)

You can use :py:data:`~typing.Callable` as the type for callable objects:

.. code-block:: python

    from typing import Callable

    # OK
    def log_all(objs: list[object], f: Callable[[object], None]) -> None:
        for x in objs:
            f(x)

.. _code-metaclass:

Check the validity of a class's metaclass [metaclass]
-----------------------------------------------------

Mypy checks whether the metaclass of a class is valid. The metaclass
must be a subclass of ``type``. Further, the class hierarchy must yield
a consistent metaclass. For more details, see the
`Python documentation <https://docs.python.org/3.13/reference/datamodel.html#determining-the-appropriate-metaclass>`_

Note that mypy's metaclass checking is limited and may produce false-positives.
See also :ref:`limitations`.

Example with an error:

.. code-block:: python

    class GoodMeta(type):
        pass

    class BadMeta:
        pass

    class A1(metaclass=GoodMeta):  # OK
        pass

    class A2(metaclass=BadMeta):  # Error:  Metaclasses not inheriting from "type" are not supported  [metaclass]
        pass

.. _code-var-annotated:

Require annotation if variable type is unclear [var-annotated]
--------------------------------------------------------------

In some cases mypy can't infer the type of a variable without an
explicit annotation. Mypy treats this as an error. This typically
happens when you initialize a variable with an empty collection or
``None``.  If mypy can't infer the collection item type, mypy replaces
any parts of the type it couldn't infer with ``Any`` and generates an
error.

Example with an error:

.. code-block:: python

    class Bundle:
        def __init__(self) -> None:
            # Error: Need type annotation for "items"
            #        (hint: "items: list[<type>] = ...")  [var-annotated]
            self.items = []

    reveal_type(Bundle().items)  # list[Any]

To address this, we add an explicit annotation:

.. code-block:: python

    class Bundle:
        def __init__(self) -> None:
            self.items: list[str] = []  # OK

   reveal_type(Bundle().items)  # list[str]

.. _code-override:

Check validity of overrides [override]
--------------------------------------

Mypy checks that an overridden method or attribute is compatible with
the base class.  A method in a subclass must accept all arguments
that the base class method accepts, and the return type must conform
to the return type in the base class (Liskov substitution principle).

Argument types can be more general is a subclass (i.e., they can vary
contravariantly).  The return type can be narrowed in a subclass
(i.e., it can vary covariantly).  It's okay to define additional
arguments in a subclass method, as long all extra arguments have default
values or can be left out (``*args``, for example).

Example:

.. code-block:: python

   from typing import Optional, Union

   class Base:
       def method(self,
                  arg: int) -> Optional[int]:
           ...

   class Derived(Base):
       def method(self,
                  arg: Union[int, str]) -> int:  # OK
           ...

   class DerivedBad(Base):
       # Error: Argument 1 of "method" is incompatible with "Base"  [override]
       def method(self,
                  arg: bool) -> int:
           ...

.. _code-return:

Check that function returns a value [return]
--------------------------------------------

If a function has a non-``None`` return type, mypy expects that the
function always explicitly returns a value (or raises an exception).
The function should not fall off the end of the function, since this
is often a bug.

Example:

.. code-block:: python

    # Error: Missing return statement  [return]
    def show(x: int) -> int:
        print(x)

    # Error: Missing return statement  [return]
    def pred1(x: int) -> int:
        if x > 0:
            return x - 1

    # OK
    def pred2(x: int) -> int:
        if x > 0:
            return x - 1
        else:
            raise ValueError('not defined for zero')

.. _code-empty-body:

Check that functions don't have empty bodies outside stubs [empty-body]
-----------------------------------------------------------------------

This error code is similar to the ``[return]`` code but is emitted specifically
for functions and methods with empty bodies (if they are annotated with
non-trivial return type). Such a distinction exists because in some contexts
an empty body can be valid, for example for an abstract method or in a stub
file. Also old versions of mypy used to unconditionally allow functions with
empty bodies, so having a dedicated error code simplifies cross-version
compatibility.

Note that empty bodies are allowed for methods in *protocols*, and such methods
are considered implicitly abstract:

.. code-block:: python

   from abc import abstractmethod
   from typing import Protocol

   class RegularABC:
       @abstractmethod
       def foo(self) -> int:
           pass  # OK
       def bar(self) -> int:
           pass  # Error: Missing return statement  [empty-body]

   class Proto(Protocol):
       def bar(self) -> int:
           pass  # OK

.. _code-return-value:

Check that return value is compatible [return-value]
----------------------------------------------------

Mypy checks that the returned value is compatible with the type
signature of the function.

Example:

.. code-block:: python

   def func(x: int) -> str:
       # Error: Incompatible return value type (got "int", expected "str")  [return-value]
       return x + 1

.. _code-assignment:

Check types in assignment statement [assignment]
------------------------------------------------

Mypy checks that the assigned expression is compatible with the
assignment target (or targets).

Example:

.. code-block:: python

    class Resource:
        def __init__(self, name: str) -> None:
            self.name = name

    r = Resource('A')

    r.name = 'B'  # OK

    # Error: Incompatible types in assignment (expression has type "int",
    #        variable has type "str")  [assignment]
    r.name = 5

.. _code-method-assign:

Check that assignment target is not a method [method-assign]
------------------------------------------------------------

In general, assigning to a method on class object or instance (a.k.a.
monkey-patching) is ambiguous in terms of types, since Python's static type
system cannot express the difference between bound and unbound callable types.
Consider this example:

.. code-block:: python

   class A:
       def f(self) -> None: pass
       def g(self) -> None: pass

   def h(self: A) -> None: pass

   A.f = h  # Type of h is Callable[[A], None]
   A().f()  # This works
   A.f = A().g  # Type of A().g is Callable[[], None]
   A().f()  # ...but this also works at runtime

To prevent the ambiguity, mypy will flag both assignments by default. If this
error code is disabled, mypy will treat the assigned value in all method assignments as unbound,
so only the second assignment will still generate an error.

.. note::

    This error code is a subcode of the more general ``[assignment]`` code.

.. _code-type-var:

Check type variable values [type-var]
-------------------------------------

Mypy checks that value of a type variable is compatible with a value
restriction or the upper bound type.

Example:

.. code-block:: python

    from typing import TypeVar

    T1 = TypeVar('T1', int, float)

    def add(x: T1, y: T1) -> T1:
        return x + y

    add(4, 5.5)  # OK

    # Error: Value of type variable "T1" of "add" cannot be "str"  [type-var]
    add('x', 'y')

.. _code-operator:

Check uses of various operators [operator]
------------------------------------------

Mypy checks that operands support a binary or unary operation, such as
``+`` or ``~``. Indexing operations are so common that they have their
own error code ``index`` (see below).

Example:

.. code-block:: python

   # Error: Unsupported operand types for + ("int" and "str")  [operator]
   1 + 'x'

.. _code-index:

Check indexing operations [index]
---------------------------------

Mypy checks that the indexed value in indexing operation such as
``x[y]`` supports indexing, and that the index expression has a valid
type.

Example:

.. code-block:: python

   a = {'x': 1, 'y': 2}

   a['x']  # OK

   # Error: Invalid index type "int" for "dict[str, int]"; expected type "str"  [index]
   print(a[1])

   # Error: Invalid index type "bytes" for "dict[str, int]"; expected type "str"  [index]
   a[b'x'] = 4

.. _code-list-item:

Check list items [list-item]
----------------------------

When constructing a list using ``[item, ...]``, mypy checks that each item
is compatible with the list type that is inferred from the surrounding
context.

Example:

.. code-block:: python

    # Error: List item 0 has incompatible type "int"; expected "str"  [list-item]
    a: list[str] = [0]

.. _code-dict-item:

Check dict items [dict-item]
----------------------------

When constructing a dictionary using ``{key: value, ...}`` or ``dict(key=value, ...)``,
mypy checks that each key and value is compatible with the dictionary type that is
inferred from the surrounding context.

Example:

.. code-block:: python

    # Error: Dict entry 0 has incompatible type "str": "str"; expected "str": "int"  [dict-item]
    d: dict[str, int] = {'key': 'value'}

.. _code-typeddict-item:

Check TypedDict items [typeddict-item]
--------------------------------------

When constructing a TypedDict object, mypy checks that each key and value is compatible
with the TypedDict type that is inferred from the surrounding context.

When getting a TypedDict item, mypy checks that the key
exists. When assigning to a TypedDict, mypy checks that both the
key and the value are valid.

Example:

.. code-block:: python

    from typing import TypedDict

    class Point(TypedDict):
        x: int
        y: int

    # Error: Incompatible types (expression has type "float",
    #        TypedDict item "x" has type "int")  [typeddict-item]
    p: Point = {'x': 1.2, 'y': 4}

.. _code-typeddict-unknown-key:

Check TypedDict Keys [typeddict-unknown-key]
--------------------------------------------

When constructing a TypedDict object, mypy checks whether the
definition contains unknown keys, to catch invalid keys and
misspellings. On the other hand, mypy will not generate an error when
a previously constructed TypedDict value with extra keys is passed
to a function as an argument, since TypedDict values support
structural subtyping ("static duck typing") and the keys are assumed
to have been validated at the point of construction. Example:

.. code-block:: python

    from typing import TypedDict

    class Point(TypedDict):
        x: int
        y: int

    class Point3D(Point):
        z: int

    def add_x_coordinates(a: Point, b: Point) -> int:
        return a["x"] + b["x"]

    a: Point = {"x": 1, "y": 4}
    b: Point3D = {"x": 2, "y": 5, "z": 6}

    add_x_coordinates(a, b)  # OK

    # Error: Extra key "z" for TypedDict "Point"  [typeddict-unknown-key]
    add_x_coordinates(a, {"x": 1, "y": 4, "z": 5})

Setting a TypedDict item using an unknown key will also generate this
error, since it could be a misspelling:

.. code-block:: python

    a: Point = {"x": 1, "y": 2}
    # Error: Extra key "z" for TypedDict "Point"  [typeddict-unknown-key]
    a["z"] = 3

Reading an unknown key will generate the more general (and serious)
``typeddict-item`` error, which is likely to result in an exception at
runtime:

.. code-block:: python

    a: Point = {"x": 1, "y": 2}
    # Error: TypedDict "Point" has no key "z"  [typeddict-item]
    _ = a["z"]

.. note::

    This error code is a subcode of the wider ``[typeddict-item]`` code.

.. _code-has-type:

Check that type of target is known [has-type]
---------------------------------------------

Mypy sometimes generates an error when it hasn't inferred any type for
a variable being referenced. This can happen for references to
variables that are initialized later in the source file, and for
references across modules that form an import cycle. When this
happens, the reference gets an implicit ``Any`` type.

In this example the definitions of ``x`` and ``y`` are circular:

.. code-block:: python

   class Problem:
       def set_x(self) -> None:
           # Error: Cannot determine type of "y"  [has-type]
           self.x = self.y

       def set_y(self) -> None:
           self.y = self.x

To work around this error, you can add an explicit type annotation to
the target variable or attribute. Sometimes you can also reorganize
the code so that the definition of the variable is placed earlier than
the reference to the variable in a source file. Untangling cyclic
imports may also help.

We add an explicit annotation to the ``y`` attribute to work around
the issue:

.. code-block:: python

   class Problem:
       def set_x(self) -> None:
           self.x = self.y  # OK

       def set_y(self) -> None:
           self.y: int = self.x  # Added annotation here

.. _code-import:

Check for an issue with imports [import]
----------------------------------------

Mypy generates an error if it can't resolve an `import` statement.
This is a parent error code of `import-not-found` and `import-untyped`

See :ref:`ignore-missing-imports` for how to work around these errors.

.. _code-import-not-found:

Check that import target can be found [import-not-found]
--------------------------------------------------------

Mypy generates an error if it can't find the source code or a stub file
for an imported module.

Example:

.. code-block:: python

    # Error: Cannot find implementation or library stub for module named "m0dule_with_typo"  [import-not-found]
    import m0dule_with_typo

See :ref:`ignore-missing-imports` for how to work around these errors.

.. _code-import-untyped:

Check that import target can be found [import-untyped]
--------------------------------------------------------

Mypy generates an error if it can find the source code for an imported module,
but that module does not provide type annotations (via :ref:`PEP 561 <installed-packages>`).

Example:

.. code-block:: python

    # Error: Library stubs not installed for "bs4"  [import-untyped]
    import bs4
    # Error: Skipping analyzing "no_py_typed": module is installed, but missing library stubs or py.typed marker  [import-untyped]
    import no_py_typed

In some cases, these errors can be fixed by installing an appropriate
stub package. See :ref:`ignore-missing-imports` for more details.

.. _code-no-redef:

Check that each name is defined once [no-redef]
-----------------------------------------------

Mypy may generate an error if you have multiple definitions for a name
in the same namespace.  The reason is that this is often an error, as
the second definition may overwrite the first one. Also, mypy often
can't be able to determine whether references point to the first or
the second definition, which would compromise type checking.

If you silence this error, all references to the defined name refer to
the *first* definition.

Example:

.. code-block:: python

   class A:
       def __init__(self, x: int) -> None: ...

   class A:  # Error: Name "A" already defined on line 1  [no-redef]
       def __init__(self, x: str) -> None: ...

   # Error: Argument 1 to "A" has incompatible type "str"; expected "int"
   #        (the first definition wins!)
   A('x')

.. _code-func-returns-value:

Check that called function returns a value [func-returns-value]
---------------------------------------------------------------

Mypy reports an error if you call a function with a ``None``
return type and don't ignore the return value, as this is
usually (but not always) a programming error.

In this example, the ``if f()`` check is always false since ``f``
returns ``None``:

.. code-block:: python

   def f() -> None:
       ...

   # OK: we don't do anything with the return value
   f()

   # Error: "f" does not return a value (it only ever returns None)  [func-returns-value]
   if f():
        print("not false")

.. _code-abstract:

Check instantiation of abstract classes [abstract]
--------------------------------------------------

Mypy generates an error if you try to instantiate an abstract base
class (ABC). An abstract base class is a class with at least one
abstract method or attribute. (See also :py:mod:`abc` module documentation)

Sometimes a class is made accidentally abstract, often due to an
unimplemented abstract method. In a case like this you need to provide
an implementation for the method to make the class concrete
(non-abstract).

Example:

.. code-block:: python

    from abc import ABCMeta, abstractmethod

    class Persistent(metaclass=ABCMeta):
        @abstractmethod
        def save(self) -> None: ...

    class Thing(Persistent):
        def __init__(self) -> None:
            ...

        ...  # No "save" method

    # Error: Cannot instantiate abstract class "Thing" with abstract attribute "save"  [abstract]
    t = Thing()

.. _code-type-abstract:

Safe handling of abstract type object types [type-abstract]
-----------------------------------------------------------

Mypy always allows instantiating (calling) type objects typed as ``Type[t]``,
even if it is not known that ``t`` is non-abstract, since it is a common
pattern to create functions that act as object factories (custom constructors).
Therefore, to prevent issues described in the above section, when an abstract
type object is passed where ``Type[t]`` is expected, mypy will give an error.
Example:

.. code-block:: python

   from abc import ABCMeta, abstractmethod
   from typing import List, Type, TypeVar

   class Config(metaclass=ABCMeta):
       @abstractmethod
       def get_value(self, attr: str) -> str: ...

   T = TypeVar("T")
   def make_many(typ: Type[T], n: int) -> List[T]:
       return [typ() for _ in range(n)]  # This will raise if typ is abstract

   # Error: Only concrete class can be given where "Type[Config]" is expected [type-abstract]
   make_many(Config, 5)

.. _code-safe-super:

Check that call to an abstract method via super is valid [safe-super]
---------------------------------------------------------------------

Abstract methods often don't have any default implementation, i.e. their
bodies are just empty. Calling such methods in subclasses via ``super()``
will cause runtime errors, so mypy prevents you from doing so:

.. code-block:: python

   from abc import abstractmethod
   class Base:
       @abstractmethod
       def foo(self) -> int: ...
   class Sub(Base):
       def foo(self) -> int:
           return super().foo() + 1  # error: Call to abstract method "foo" of "Base" with
                                     # trivial body via super() is unsafe  [safe-super]
   Sub().foo()  # This will crash at runtime.

Mypy considers the following as trivial bodies: a ``pass`` statement, a literal
ellipsis ``...``, a docstring, and a ``raise NotImplementedError`` statement.

.. _code-valid-newtype:

Check the target of NewType [valid-newtype]
-------------------------------------------

The target of a :py:class:`~typing.NewType` definition must be a class type. It can't
be a union type, ``Any``, or various other special types.

You can also get this error if the target has been imported from a
module whose source mypy cannot find, since any such definitions are
treated by mypy as values with ``Any`` types. Example:

.. code-block:: python

   from typing import NewType

   # The source for "acme" is not available for mypy
   from acme import Entity  # type: ignore

   # Error: Argument 2 to NewType(...) must be subclassable (got "Any")  [valid-newtype]
   UserEntity = NewType('UserEntity', Entity)

To work around the issue, you can either give mypy access to the sources
for ``acme`` or create a stub file for the module.  See :ref:`ignore-missing-imports`
for more information.

.. _code-exit-return:

Check the return type of __exit__ [exit-return]
-----------------------------------------------

If mypy can determine that :py:meth:`__exit__ <object.__exit__>` always returns ``False``, mypy
checks that the return type is *not* ``bool``.  The boolean value of
the return type affects which lines mypy thinks are reachable after a
``with`` statement, since any :py:meth:`__exit__ <object.__exit__>` method that can return
``True`` may swallow exceptions. An imprecise return type can result
in mysterious errors reported near ``with`` statements.

To fix this, use either ``typing.Literal[False]`` or
``None`` as the return type. Returning ``None`` is equivalent to
returning ``False`` in this context, since both are treated as false
values.

Example:

.. code-block:: python

   class MyContext:
       ...
       def __exit__(self, exc, value, tb) -> bool:  # Error
           print('exit')
           return False

This produces the following output from mypy:

.. code-block:: text

   example.py:3: error: "bool" is invalid as return type for "__exit__" that always returns False
   example.py:3: note: Use "typing_extensions.Literal[False]" as the return type or change it to
       "None"
   example.py:3: note: If return type of "__exit__" implies that it may return True, the context
       manager may swallow exceptions

You can use ``Literal[False]`` to fix the error:

.. code-block:: python

   from typing import Literal

   class MyContext:
       ...
       def __exit__(self, exc, value, tb) -> Literal[False]:  # OK
           print('exit')
           return False

You can also use ``None``:

.. code-block:: python

   class MyContext:
       ...
       def __exit__(self, exc, value, tb) -> None:  # Also OK
           print('exit')

.. _code-name-match:

Check that naming is consistent [name-match]
--------------------------------------------

The definition of a named tuple or a TypedDict must be named
consistently when using the call-based syntax. Example:

.. code-block:: python

    from typing import NamedTuple

    # Error: First argument to namedtuple() should be "Point2D", not "Point"
    Point2D = NamedTuple("Point", [("x", int), ("y", int)])

.. _code-literal-required:

Check that literal is used where expected [literal-required]
------------------------------------------------------------

There are some places where only a (string) literal value is expected for
the purposes of static type checking, for example a ``TypedDict`` key, or
a ``__match_args__`` item. Providing a ``str``-valued variable in such contexts
will result in an error. Note that in many cases you can also use ``Final``
or ``Literal`` variables. Example:

.. code-block:: python

   from typing import Final, Literal, TypedDict

   class Point(TypedDict):
       x: int
       y: int

   def test(p: Point) -> None:
       X: Final = "x"
       p[X]  # OK

       Y: Literal["y"] = "y"
       p[Y]  # OK

       key = "x"  # Inferred type of key is `str`
       # Error: TypedDict key must be a string literal;
       #   expected one of ("x", "y")  [literal-required]
       p[key]

.. _code-no-overload-impl:

Check that overloaded functions have an implementation [no-overload-impl]
-------------------------------------------------------------------------

Overloaded functions outside of stub files must be followed by a non overloaded
implementation.

.. code-block:: python

   from typing import overload

   @overload
   def func(value: int) -> int:
       ...

   @overload
   def func(value: str) -> str:
       ...

   # presence of required function below is checked
   def func(value):
       pass  # actual implementation

.. _code-unused-coroutine:

Check that coroutine return value is used [unused-coroutine]
------------------------------------------------------------

Mypy ensures that return values of async def functions are not
ignored, as this is usually a programming error, as the coroutine
won't be executed at the call site.

.. code-block:: python

   async def f() -> None:
       ...

   async def g() -> None:
       f()  # Error: missing await
       await f()  # OK

You can work around this error by assigning the result to a temporary,
otherwise unused variable:

.. code-block:: python

       _ = f()  # No error

.. _code-top-level-await:

Warn about top level await expressions [top-level-await]
--------------------------------------------------------

This error code is separate from the general ``[syntax]`` errors, because in
some environments (e.g. IPython) a top level ``await`` is allowed. In such
environments a user may want to use ``--disable-error-code=top-level-await``,
that allows to still have errors for other improper uses of ``await``, for
example:

.. code-block:: python

   async def f() -> None:
       ...

   top = await f()  # Error: "await" outside function  [top-level-await]

.. _code-await-not-async:

Warn about await expressions used outside of coroutines [await-not-async]
-------------------------------------------------------------------------

``await`` must be used inside a coroutine.

.. code-block:: python

   async def f() -> None:
       ...

   def g() -> None:
       await f()  # Error: "await" outside coroutine ("async def")  [await-not-async]

.. _code-assert-type:

Check types in assert_type [assert-type]
----------------------------------------

The inferred type for an expression passed to ``assert_type`` must match
the provided type.

.. code-block:: python

   from typing_extensions import assert_type

   assert_type([1], list[int])  # OK

   assert_type([1], list[str])  # Error

.. _code-truthy-function:

Check that function isn't used in boolean context [truthy-function]
-------------------------------------------------------------------

Functions will always evaluate to true in boolean contexts.

.. code-block:: python

    def f():
        ...

    if f:  # Error: Function "Callable[[], Any]" could always be true in boolean context  [truthy-function]
        pass

.. _code-str-format:

Check that string formatting/interpolation is type-safe [str-format]
--------------------------------------------------------------------

Mypy will check that f-strings, ``str.format()`` calls, and ``%`` interpolations
are valid (when corresponding template is a literal string). This includes
checking number and types of replacements, for example:

.. code-block:: python

    # Error: Cannot find replacement for positional format specifier 1 [str-format]
    "{} and {}".format("spam")
    "{} and {}".format("spam", "eggs")  # OK
    # Error: Not all arguments converted during string formatting [str-format]
    "{} and {}".format("spam", "eggs", "cheese")

    # Error: Incompatible types in string interpolation
    # (expression has type "float", placeholder has type "int") [str-format]
    "{:d}".format(3.14)

.. _code-str-bytes-safe:

Check for implicit bytes coercions [str-bytes-safe]
-------------------------------------------------------------------

Warn about cases where a bytes object may be converted to a string in an unexpected manner.

.. code-block:: python

    b = b"abc"

    # Error: If x = b'abc' then f"{x}" or "{}".format(x) produces "b'abc'", not "abc".
    # If this is desired behavior, use f"{x!r}" or "{!r}".format(x).
    # Otherwise, decode the bytes [str-bytes-safe]
    print(f"The alphabet starts with {b}")

    # Okay
    print(f"The alphabet starts with {b!r}")  # The alphabet starts with b'abc'
    print(f"The alphabet starts with {b.decode('utf-8')}")  # The alphabet starts with abc

.. _code-overload-overlap:

Check that overloaded functions don't overlap [overload-overlap]
----------------------------------------------------------------

Warn if multiple ``@overload`` variants overlap in potentially unsafe ways.
This guards against the following situation:

.. code-block:: python

    from typing import overload

    class A: ...
    class B(A): ...

    @overload
    def foo(x: B) -> int: ...  # Error: Overloaded function signatures 1 and 2 overlap with incompatible return types  [overload-overlap]
    @overload
    def foo(x: A) -> str: ...
    def foo(x): ...

    def takes_a(a: A) -> str:
        return foo(a)

    a: A = B()
    value = takes_a(a)
    # mypy will think that value is a str, but it could actually be an int
    reveal_type(value) # Revealed type is "builtins.str"


Note that in cases where you ignore this error, mypy will usually still infer the
types you expect.

See :ref:`overloading <function-overloading>` for more explanation.

.. _code-annotation-unchecked:

Notify about an annotation in an unchecked function [annotation-unchecked]
--------------------------------------------------------------------------

Sometimes a user may accidentally omit an annotation for a function, and mypy
will not check the body of this function (unless one uses
:option:`--check-untyped-defs <mypy --check-untyped-defs>` or
:option:`--disallow-untyped-defs <mypy --disallow-untyped-defs>`). To avoid
such situations go unnoticed, mypy will show a note, if there are any type
annotations in an unchecked function:

.. code-block:: python

    def test_assignment():  # "-> None" return annotation is missing
        # Note: By default the bodies of untyped functions are not checked,
        # consider using --check-untyped-defs [annotation-unchecked]
        x: int = "no way"

Note that mypy will still exit with return code ``0``, since such behaviour is
specified by :pep:`484`.

.. _code-prop-decorator:

Decorator preceding property not supported [prop-decorator]
-----------------------------------------------------------

Mypy does not yet support analysis of decorators that precede the property
decorator. If the decorator does not preserve the declared type of the property,
mypy will not infer the correct type for the declaration. If the decorator cannot
be moved after the ``@property`` decorator, then you must use a type ignore
comment:

.. code-block:: python

    class MyClass:
        @special  # type: ignore[prop-decorator]
        @property
        def magic(self) -> str:
            return "xyzzy"

.. note::

    For backward compatibility, this error code is a subcode of the generic ``[misc]`` code.

.. _code-syntax:

Report syntax errors [syntax]
-----------------------------

If the code being checked is not syntactically valid, mypy issues a
syntax error. Most, but not all, syntax errors are *blocking errors*:
they can't be ignored with a ``# type: ignore`` comment.

.. _code-misc:

Miscellaneous checks [misc]
---------------------------

Mypy performs numerous other, less commonly failing checks that don't
have specific error codes. These use the ``misc`` error code. Other
than being used for multiple unrelated errors, the ``misc`` error code
is not special. For example, you can ignore all errors in this
category by using ``# type: ignore[misc]`` comment. Since these errors
are not expected to be common, it's unlikely that you'll see two
*different* errors with the ``misc`` code on a single line -- though
this can certainly happen once in a while.

.. note::

    Future mypy versions will likely add new error codes for some errors
    that currently use the ``misc`` error code.
