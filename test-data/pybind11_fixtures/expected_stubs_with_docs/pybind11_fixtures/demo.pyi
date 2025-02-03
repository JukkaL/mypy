from typing import ClassVar, overload

PI: float
__version__: str

class Point:
    class AngleUnit:
        """Members:

        radian

        degree
        """

        __members__: ClassVar[dict] = ...  # read-only
        """__members__(arg0: handle) -> dict"""
        __entries: ClassVar[dict] = ...
        degree: ClassVar[Point.AngleUnit] = ...
        radian: ClassVar[Point.AngleUnit] = ...
        def __init__(self, value: int) -> None:
            """__init__(self: pybind11_fixtures.demo.Point.AngleUnit, value: int) -> None"""
        def __eq__(self, other: object) -> bool:
            """__eq__(self: object, other: object) -> bool"""
        def __hash__(self) -> int:
            """__hash__(self: object) -> int"""
        def __index__(self) -> int:
            """__index__(self: pybind11_fixtures.demo.Point.AngleUnit) -> int"""
        def __int__(self) -> int:
            """__int__(self: pybind11_fixtures.demo.Point.AngleUnit) -> int"""
        def __ne__(self, other: object) -> bool:
            """__ne__(self: object, other: object) -> bool"""
        @property
        def name(self) -> str:
            """name(self: handle) -> str

            name(self: handle) -> str
            """
        @property
        def value(self) -> int:
            """(arg0: pybind11_fixtures.demo.Point.AngleUnit) -> int"""

    class LengthUnit:
        """Members:

        mm

        pixel

        inch
        """

        __members__: ClassVar[dict] = ...  # read-only
        """__members__(arg0: handle) -> dict"""
        __entries: ClassVar[dict] = ...
        inch: ClassVar[Point.LengthUnit] = ...
        mm: ClassVar[Point.LengthUnit] = ...
        pixel: ClassVar[Point.LengthUnit] = ...
        def __init__(self, value: int) -> None:
            """__init__(self: pybind11_fixtures.demo.Point.LengthUnit, value: int) -> None"""
        def __eq__(self, other: object) -> bool:
            """__eq__(self: object, other: object) -> bool"""
        def __hash__(self) -> int:
            """__hash__(self: object) -> int"""
        def __index__(self) -> int:
            """__index__(self: pybind11_fixtures.demo.Point.LengthUnit) -> int"""
        def __int__(self) -> int:
            """__int__(self: pybind11_fixtures.demo.Point.LengthUnit) -> int"""
        def __ne__(self, other: object) -> bool:
            """__ne__(self: object, other: object) -> bool"""
        @property
        def name(self) -> str:
            """name(self: handle) -> str

            name(self: handle) -> str
            """
        @property
        def value(self) -> int:
            """(arg0: pybind11_fixtures.demo.Point.LengthUnit) -> int"""
    angle_unit: ClassVar[Point.AngleUnit] = ...
    """(arg0: object) -> pybind11_fixtures.demo.Point.AngleUnit"""
    length_unit: ClassVar[Point.LengthUnit] = ...
    """(arg0: object) -> pybind11_fixtures.demo.Point.LengthUnit"""
    x_axis: ClassVar[Point] = ...  # read-only
    """(arg0: object) -> pybind11_fixtures.demo.Point"""
    y_axis: ClassVar[Point] = ...  # read-only
    """(arg0: object) -> pybind11_fixtures.demo.Point"""
    origin: ClassVar[Point] = ...
    x: float
    """some docstring
    (self: pybind11_fixtures.demo.Point) -> float
    """
    y: float
    """(arg0: pybind11_fixtures.demo.Point) -> float"""
    @overload
    def __init__(self) -> None:
        """__init__(*args, **kwargs)
        Overloaded function.

        1. __init__(self: pybind11_fixtures.demo.Point) -> None

        2. __init__(self: pybind11_fixtures.demo.Point, x: float, y: float) -> None
        """
    @overload
    def __init__(self, x: float, y: float) -> None:
        """__init__(*args, **kwargs)
        Overloaded function.

        1. __init__(self: pybind11_fixtures.demo.Point) -> None

        2. __init__(self: pybind11_fixtures.demo.Point, x: float, y: float) -> None
        """
    def as_list(self) -> list[float]:
        """as_list(self: pybind11_fixtures.demo.Point) -> List[float]"""
    @overload
    def distance_to(self, x: float, y: float) -> float:
        """distance_to(*args, **kwargs)
        Overloaded function.

        1. distance_to(self: pybind11_fixtures.demo.Point, x: float, y: float) -> float

        2. distance_to(self: pybind11_fixtures.demo.Point, other: pybind11_fixtures.demo.Point) -> float
        """
    @overload
    def distance_to(self, other: Point) -> float:
        """distance_to(*args, **kwargs)
        Overloaded function.

        1. distance_to(self: pybind11_fixtures.demo.Point, x: float, y: float) -> float

        2. distance_to(self: pybind11_fixtures.demo.Point, other: pybind11_fixtures.demo.Point) -> float
        """
    @property
    def length(self) -> float:
        """(arg0: pybind11_fixtures.demo.Point) -> float"""

def answer() -> int:
    '''answer() -> int

    answer docstring, with end quote"
    '''
def midpoint(left: float, right: float) -> float:
    """midpoint(left: float, right: float) -> float"""
def sum(arg0: int, arg1: int) -> int:
    '''sum(arg0: int, arg1: int) -> int

    multiline docstring test, edge case quotes """\'\'\'
    '''
def weighted_midpoint(left: float, right: float, alpha: float = ...) -> float:
    """weighted_midpoint(left: float, right: float, alpha: float = 0.5) -> float"""
