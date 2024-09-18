.. _metaclasses:

Metaclasses
===========

A :ref:`metaclass <python:metaclasses>` is a class that describes
the construction and behavior of other classes, similarly to how classes
describe the construction and behavior of objects.
The default metaclass is :py:class:`type`, but it's possible to use other metaclasses.
Metaclasses allows one to create "a different kind of class", such as
:py:class:`~enum.Enum`\s, :py:class:`~typing.NamedTuple`\s and singletons.

Mypy has some special understanding of :py:class:`~abc.ABCMeta` and ``EnumMeta``.

.. _defining:

Defining a metaclass
********************

.. code-block:: python

    class M(type):
        pass

    class A(metaclass=M):
        pass

.. _examples:

Metaclass usage example
***********************

Mypy supports the lookup of attributes in the metaclass:

.. code-block:: python

    from typing import Type, TypeVar, ClassVar
    T = TypeVar('T')

    class M(type):
        count: ClassVar[int] = 0

        def make(cls: Type[T]) -> T:
            M.count += 1
            return cls()

    class A(metaclass=M):
        pass

    a: A = A.make()  # make() is looked up at M; the result is an object of type A
    print(A.count)

    class B(A):
        pass

    b: B = B.make()  # metaclasses are inherited
    print(B.count + " objects were created")  # Error: Unsupported operand types for + ("int" and "str")

.. _limitations:

Gotchas and limitations of metaclass support
********************************************

Note that metaclasses pose some requirements on the inheritance structure,
so it's better not to combine metaclasses and class hierarchies:

.. code-block:: python

    class M1(type): pass
    class M2(type): pass

    class A1(metaclass=M1): pass
    class A2(metaclass=M2): pass

    class B1(A1, metaclass=M2): pass  # Mypy Error: metaclass conflict
    # At runtime the above definition raises an exception
    # TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases

    class B12(A1, A2): pass  # Mypy Error: metaclass conflict

    # This can be solved via a common metaclass subtype:
    class CorrectMeta(M1, M2): pass
    class B2(A1, A2, metaclass=CorrectMeta): pass  # OK, runtime is also OK

* Mypy does not understand dynamically-computed metaclasses,
  such as ``class A(metaclass=f()): ...``
* Mypy does not and cannot understand arbitrary metaclass code.
* Mypy only recognizes subclasses of :py:class:`type` as potential metaclasses.

For some builtin types, mypy assumes that their metaclass is :py:class:`abc.ABCMeta`
even if it's :py:class:`type`. In those cases, you can either

* use :py:class:`abc.ABCMeta` instead of :py:class:`type` as the
  superclass of your metaclass if that works in your use case,
* mute the error with ``# type: ignore[metaclass]``, or
* compute the metaclass' superclass dynamically, which mypy doesn't understand
  so it will also need to be muted.

.. code-block:: python

    import abc

    assert type(tuple) is type  # metaclass of tuple is type

    # the problem:
    class M0(type): pass
    class A0(tuple, metaclass=M1): pass  # Mypy Error: metaclass conflict

    # option 1: use ABCMeta instead of type
    class M1(abc.ABCMeta): pass
    class A1(tuple, metaclass=M1): pass

    # option 2: mute the error
    class M2(type): pass
    class A2(tuple, metaclass=M2): pass  # type: ignore[metaclass]

    # option 3: compute the metaclass dynamically
    class M3(type(tuple)): pass  # type: ignore[metaclass]
    class A3(tuple, metaclass=M3): pass
