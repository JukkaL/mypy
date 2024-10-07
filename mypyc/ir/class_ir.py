"""Intermediate representation of classes."""

from __future__ import annotations

from typing import List, NamedTuple

from mypyc.common import PROPSET_PREFIX, JsonDict
from mypyc.ir.func_ir import FuncDecl, FuncIR, FuncSignature
from mypyc.ir.ops import DeserMaps, Value
from mypyc.ir.rtypes import RInstance, RType, deserialize_type
from mypyc.namegen import NameGenerator, exported_name

# Some notes on the vtable layout: Each concrete class has a vtable
# that contains function pointers for its methods. So that subclasses
# may be efficiently used when their parent class is expected, the
# layout of child vtables must be an extension of their base class's
# vtable.
#
# This makes multiple inheritance tricky, since obviously we cannot be
# an extension of multiple parent classes. We solve this by requiring
# all but one parent to be "traits", which we can operate on in a
# somewhat less efficient way. For each trait implemented by a class,
# we generate a separate vtable for the methods in that trait.
# We then store an array of (trait type, trait vtable) pointers alongside
# a class's main vtable. When we want to call a trait method, we
# (at runtime!) search the array of trait vtables to find the correct one,
# then call through it.
# Trait vtables additionally need entries for attribute getters and setters,
# since they can't always be in the same location.
#
# To keep down the number of indirections necessary, we store the
# array of trait vtables in the memory *before* the class vtable, and
# search it backwards.  (This is a trick we can only do once---there
# are only two directions to store data in---but I don't think we'll
# need it again.)
# There are some tricks we could try in the future to store the trait
# vtables inline in the trait table (which would cut down one indirection),
# but this seems good enough for now.
#
# As an example:
# Imagine that we have a class B that inherits from a concrete class A
# and traits T1 and T2, and that A has methods foo() and
# bar() and B overrides bar() with a more specific type.
# Then B's vtable will look something like:
#
#      T1 type object
#      ptr to B's T1 trait vtable
#      T2 type object
#      ptr to B's T2 trait vtable
# -> | A.foo
#    | Glue function that converts between A.bar's type and B.bar
#      B.bar
#      B.baz
#
# The arrow points to the "start" of the vtable (what vtable pointers
# point to) and the bars indicate which parts correspond to the parent
# class A's vtable layout.
#
# Classes that allow interpreted code to subclass them also have a
# "shadow vtable" that contains implementations that delegate to
# making a pycall, so that overridden methods in interpreted children
# will be called. (A better strategy could dynamically generate these
# vtables based on which methods are overridden in the children.)

# Descriptions of method and attribute entries in class vtables.
# The 'cls' field is the class that the method/attr was defined in,
# which might be a parent class.
# The 'shadow_method', if present, contains the method that should be
# placed in the class's shadow vtable (if it has one).


class VTableMethod(NamedTuple):
    cls: "ClassIR"  # noqa: UP037
    name: str
    method: FuncIR
    shadow_method: FuncIR | None


VTableEntries = List[VTableMethod]


class ClassIR:
    """Intermediate representation of a class.

    This also describes the runtime structure of native instances.
    """

    def __init__(
        self,
        name: str,
        module_name: str,
        is_trait: bool = False,
        is_generated: bool = False,
        is_abstract: bool = False,
        is_ext_class: bool = True,
        is_final_class: bool = False,
    ) -> None:
        self.name = name
        self.module_name = module_name
        self.is_trait = is_trait
        self.is_generated = is_generated
        self.is_abstract = is_abstract
        self.is_ext_class = is_ext_class
        self.is_final_class = is_final_class
        # An augmented class has additional methods separate from what mypyc generates.
        # Right now the only one is dataclasses.
        self.is_augmented = False
        # Does this inherit from a Python class?
        self.inherits_python = False
        # Do instances of this class have __dict__?
        self.has_dict = False
        # Do we allow interpreted subclasses? Derived from a mypyc_attr.
        self.allow_interpreted_subclasses = False
        # Does this class need getseters to be generated for its attributes? (getseters are also
        # added if is_generated is False)
        self.needs_getseters = False
        # Is this class declared as serializable (supports copy.copy
        # and pickle) using @mypyc_attr(serializable=True)?
        #
        # Additionally, any class with this attribute False but with
        # an __init__ that can be called without any arguments is
        # *implicitly serializable*. In this case __init__ will be
        # called during deserialization without arguments. If this is
        # True, we match Python semantics and __init__ won't be called
        # during deserialization.
        #
        # This impacts also all subclasses. Use is_serializable() to
        # also consider base classes.
        self._serializable = False
        # If this a subclass of some built-in python class, the name
        # of the object for that class. We currently only support this
        # in a few ad-hoc cases.
        self.builtin_base: str | None = None
        # Default empty constructor
        self.ctor = FuncDecl(name, None, module_name, FuncSignature([], RInstance(self)))
        # Attributes defined in the class (not inherited)
        self.attributes: dict[str, RType] = {}
        # Deletable attributes
        self.deletable: list[str] = []
        # We populate method_types with the signatures of every method before
        # we generate methods, and we rely on this information being present.
        self.method_decls: dict[str, FuncDecl] = {}
        # Map of methods that are actually present in an extension class
        self.methods: dict[str, FuncIR] = {}
        # Glue methods for boxing/unboxing when a class changes the type
        # while overriding a method. Maps from (parent class overridden, method)
        # to IR of glue method.
        self.glue_methods: dict[tuple[ClassIR, str], FuncIR] = {}

        # Properties are accessed like attributes, but have behavior like method calls.
        # They don't belong in the methods dictionary, since we don't want to expose them to
        # Python's method API. But we want to put them into our own vtable as methods, so that
        # they are properly handled and overridden. The property dictionary values are a tuple
        # containing a property getter and an optional property setter.
        self.properties: dict[str, tuple[FuncIR, FuncIR | None]] = {}
        # We generate these in prepare_class_def so that we have access to them when generating
        # other methods and properties that rely on these types.
        self.property_types: dict[str, RType] = {}

        self.vtable: dict[str, int] | None = None
        self.vtable_entries: VTableEntries = []
        self.trait_vtables: dict[ClassIR, VTableEntries] = {}
        # N.B: base might not actually quite be the direct base.
        # It is the nearest concrete base, but we allow a trait in between.
        self.base: ClassIR | None = None
        self.traits: list[ClassIR] = []
        # Supply a working mro for most generated classes. Real classes will need to
        # fix it up.
        self.mro: list[ClassIR] = [self]
        # base_mro is the chain of concrete (non-trait) ancestors
        self.base_mro: list[ClassIR] = [self]

        # Direct subclasses of this class (use subclasses() to also include non-direct ones)
        # None if separate compilation prevents this from working.
        #
        # Often it's better to use has_no_subclasses() or subclasses() instead.
        self.children: list[ClassIR] | None = []

        # Instance attributes that are initialized in the class body.
        self.attrs_with_defaults: set[str] = set()

        # Attributes that are always initialized in __init__ or class body
        # (inferred in mypyc.analysis.attrdefined using interprocedural analysis)
        self._always_initialized_attrs: set[str] = set()

        # Attributes that are sometimes initialized in __init__
        self._sometimes_initialized_attrs: set[str] = set()

        # If True, __init__ can make 'self' visible to unanalyzed/arbitrary code
        self.init_self_leak = False

        # Definedness of these attributes is backed by a bitmap. Index in the list
        # indicates the bit number. Includes inherited attributes. We need the
        # bitmap for types such as native ints that can't have a dedicated error
        # value that doesn't overlap a valid value. The bitmap is used if the
        # value of an attribute is the same as the error value.
        self.bitmap_attrs: list[str] = []

    def __repr__(self) -> str:
        return (
            "ClassIR("
            "name={self.name}, module_name={self.module_name}, "
            "is_trait={self.is_trait}, is_generated={self.is_generated}, "
            "is_abstract={self.is_abstract}, is_ext_class={self.is_ext_class}, "
            "is_final_class={self.is_final_class}"
            ")".format(self=self)
        )

    @property
    def fullname(self) -> str:
        return f"{self.module_name}.{self.name}"

    def real_base(self) -> ClassIR | None:
        """Return the actual concrete base class, if there is one."""
        if len(self.mro) > 1 and not self.mro[1].is_trait:
            return self.mro[1]
        return None

    def vtable_entry(self, name: str) -> int:
        assert self.vtable is not None, "vtable not computed yet"
        assert name in self.vtable, f"{self.name!r} has no attribute {name!r}"
        return self.vtable[name]

    def attr_details(self, name: str) -> tuple[RType, ClassIR]:
        for ir in self.mro:
            if name in ir.attributes:
                return ir.attributes[name], ir
            if name in ir.property_types:
                return ir.property_types[name], ir
        raise KeyError(f"{self.name!r} has no attribute {name!r}")

    def attr_type(self, name: str) -> RType:
        return self.attr_details(name)[0]

    def method_decl(self, name: str) -> FuncDecl:
        for ir in self.mro:
            if name in ir.method_decls:
                return ir.method_decls[name]
        raise KeyError(f"{self.name!r} has no attribute {name!r}")

    def method_sig(self, name: str) -> FuncSignature:
        return self.method_decl(name).sig

    def has_method(self, name: str) -> bool:
        try:
            self.method_decl(name)
        except KeyError:
            return False
        return True

    def is_method_final(self, name: str) -> bool:
        subs = self.subclasses()
        if subs is None:
            return self.is_final_class

        if self.has_method(name):
            method_decl = self.method_decl(name)
            for subc in subs:
                if subc.method_decl(name) != method_decl:
                    return False
            return True
        else:
            return not any(subc.has_method(name) for subc in subs)

    def has_attr(self, name: str) -> bool:
        try:
            self.attr_type(name)
        except KeyError:
            return False
        return True

    def is_deletable(self, name: str) -> bool:
        return any(name in ir.deletable for ir in self.mro)

    def is_always_defined(self, name: str) -> bool:
        if self.is_deletable(name):
            return False
        return name in self._always_initialized_attrs

    def name_prefix(self, names: NameGenerator) -> str:
        return names.private_name(self.module_name, self.name)

    def struct_name(self, names: NameGenerator) -> str:
        return f"{exported_name(self.fullname)}Object"

    def get_method_and_class(
        self, name: str, *, prefer_method: bool = False
    ) -> tuple[FuncIR, ClassIR] | None:
        for ir in self.mro:
            if name in ir.methods:
                func_ir = ir.methods[name]
                if not prefer_method and func_ir.decl.implicit:
                    # This is an implicit accessor, so there is also an attribute definition
                    # which the caller prefers. This happens if an attribute overrides a
                    # property.
                    return None
                return func_ir, ir

        return None

    def get_method(self, name: str, *, prefer_method: bool = False) -> FuncIR | None:
        res = self.get_method_and_class(name, prefer_method=prefer_method)
        return res[0] if res else None

    def has_method_decl(self, name: str) -> bool:
        return any(name in ir.method_decls for ir in self.mro)

    def has_no_subclasses(self) -> bool:
        return self.children == [] and not self.allow_interpreted_subclasses

    def subclasses(self) -> set[ClassIR] | None:
        """Return all subclasses of this class, both direct and indirect.

        Return None if it is impossible to identify all subclasses, for example
        because we are performing separate compilation.
        """
        if self.children is None or self.allow_interpreted_subclasses:
            return None
        result = set(self.children)
        for child in self.children:
            if child.children:
                child_subs = child.subclasses()
                if child_subs is None:
                    return None
                result.update(child_subs)
        return result

    def concrete_subclasses(self) -> list[ClassIR] | None:
        """Return all concrete (i.e. non-trait and non-abstract) subclasses.

        Include both direct and indirect subclasses. Place classes with no children first.
        """
        subs = self.subclasses()
        if subs is None:
            return None
        concrete = {c for c in subs if not (c.is_trait or c.is_abstract)}
        # We place classes with no children first because they are more likely
        # to appear in various isinstance() checks. We then sort leaves by name
        # to get stable order.
        return sorted(concrete, key=lambda c: (len(c.children or []), c.name))

    def is_serializable(self) -> bool:
        return any(ci._serializable for ci in self.mro)

    def serialize(self) -> JsonDict:
        return {
            "name": self.name,
            "module_name": self.module_name,
            "is_trait": self.is_trait,
            "is_ext_class": self.is_ext_class,
            "is_abstract": self.is_abstract,
            "is_generated": self.is_generated,
            "is_augmented": self.is_augmented,
            "is_final_class": self.is_final_class,
            "inherits_python": self.inherits_python,
            "has_dict": self.has_dict,
            "allow_interpreted_subclasses": self.allow_interpreted_subclasses,
            "needs_getseters": self.needs_getseters,
            "_serializable": self._serializable,
            "builtin_base": self.builtin_base,
            "ctor": self.ctor.serialize(),
            # We serialize dicts as lists to ensure order is preserved
            "attributes": [(k, t.serialize()) for k, t in self.attributes.items()],
            # We try to serialize a name reference, but if the decl isn't in methods
            # then we can't be sure that will work so we serialize the whole decl.
            "method_decls": [
                (k, d.id if k in self.methods else d.serialize())
                for k, d in self.method_decls.items()
            ],
            # We serialize method fullnames out and put methods in a separate dict
            "methods": [(k, m.id) for k, m in self.methods.items()],
            "glue_methods": [
                ((cir.fullname, k), m.id) for (cir, k), m in self.glue_methods.items()
            ],
            # We serialize properties and property_types separately out of an
            # abundance of caution about preserving dict ordering...
            "property_types": [(k, t.serialize()) for k, t in self.property_types.items()],
            "properties": list(self.properties),
            "vtable": self.vtable,
            "vtable_entries": serialize_vtable(self.vtable_entries),
            "trait_vtables": [
                (cir.fullname, serialize_vtable(v)) for cir, v in self.trait_vtables.items()
            ],
            # References to class IRs are all just names
            "base": self.base.fullname if self.base else None,
            "traits": [cir.fullname for cir in self.traits],
            "mro": [cir.fullname for cir in self.mro],
            "base_mro": [cir.fullname for cir in self.base_mro],
            "children": (
                [cir.fullname for cir in self.children] if self.children is not None else None
            ),
            "deletable": self.deletable,
            "attrs_with_defaults": sorted(self.attrs_with_defaults),
            "_always_initialized_attrs": sorted(self._always_initialized_attrs),
            "_sometimes_initialized_attrs": sorted(self._sometimes_initialized_attrs),
            "init_self_leak": self.init_self_leak,
        }

    @classmethod
    def deserialize(cls, data: JsonDict, ctx: DeserMaps) -> ClassIR:
        fullname = data["module_name"] + "." + data["name"]
        assert fullname in ctx.classes, "Class %s not in deser class map" % fullname
        ir = ctx.classes[fullname]

        ir.is_trait = data["is_trait"]
        ir.is_generated = data["is_generated"]
        ir.is_abstract = data["is_abstract"]
        ir.is_ext_class = data["is_ext_class"]
        ir.is_augmented = data["is_augmented"]
        ir.inherits_python = data["inherits_python"]
        ir.has_dict = data["has_dict"]
        ir.allow_interpreted_subclasses = data["allow_interpreted_subclasses"]
        ir.needs_getseters = data["needs_getseters"]
        ir._serializable = data["_serializable"]
        ir.builtin_base = data["builtin_base"]
        ir.ctor = FuncDecl.deserialize(data["ctor"], ctx)
        ir.attributes = {k: deserialize_type(t, ctx) for k, t in data["attributes"]}
        ir.method_decls = {
            k: ctx.functions[v].decl if isinstance(v, str) else FuncDecl.deserialize(v, ctx)
            for k, v in data["method_decls"]
        }
        ir.methods = {k: ctx.functions[v] for k, v in data["methods"]}
        ir.glue_methods = {
            (ctx.classes[c], k): ctx.functions[v] for (c, k), v in data["glue_methods"]
        }
        ir.property_types = {k: deserialize_type(t, ctx) for k, t in data["property_types"]}
        ir.properties = {
            k: (ir.methods[k], ir.methods.get(PROPSET_PREFIX + k)) for k in data["properties"]
        }

        ir.vtable = data["vtable"]
        ir.vtable_entries = deserialize_vtable(data["vtable_entries"], ctx)
        ir.trait_vtables = {
            ctx.classes[k]: deserialize_vtable(v, ctx) for k, v in data["trait_vtables"]
        }

        base = data["base"]
        ir.base = ctx.classes[base] if base else None
        ir.traits = [ctx.classes[s] for s in data["traits"]]
        ir.mro = [ctx.classes[s] for s in data["mro"]]
        ir.base_mro = [ctx.classes[s] for s in data["base_mro"]]
        ir.children = data["children"] and [ctx.classes[s] for s in data["children"]]
        ir.deletable = data["deletable"]
        ir.attrs_with_defaults = set(data["attrs_with_defaults"])
        ir._always_initialized_attrs = set(data["_always_initialized_attrs"])
        ir._sometimes_initialized_attrs = set(data["_sometimes_initialized_attrs"])
        ir.init_self_leak = data["init_self_leak"]

        return ir


class NonExtClassInfo:
    """Information needed to construct a non-extension class (Python class).

    Includes the class dictionary, a tuple of base classes,
    the class annotations dictionary, and the metaclass.
    """

    def __init__(self, dict: Value, bases: Value, anns: Value, metaclass: Value) -> None:
        self.dict = dict
        self.bases = bases
        self.anns = anns
        self.metaclass = metaclass


def serialize_vtable_entry(entry: VTableMethod) -> JsonDict:
    return {
        ".class": "VTableMethod",
        "cls": entry.cls.fullname,
        "name": entry.name,
        "method": entry.method.decl.id,
        "shadow_method": entry.shadow_method.decl.id if entry.shadow_method else None,
    }


def serialize_vtable(vtable: VTableEntries) -> list[JsonDict]:
    return [serialize_vtable_entry(v) for v in vtable]


def deserialize_vtable_entry(data: JsonDict, ctx: DeserMaps) -> VTableMethod:
    if data[".class"] == "VTableMethod":
        return VTableMethod(
            ctx.classes[data["cls"]],
            data["name"],
            ctx.functions[data["method"]],
            ctx.functions[data["shadow_method"]] if data["shadow_method"] else None,
        )
    assert False, "Bogus vtable .class: %s" % data[".class"]


def deserialize_vtable(data: list[JsonDict], ctx: DeserMaps) -> VTableEntries:
    return [deserialize_vtable_entry(x, ctx) for x in data]


def all_concrete_classes(class_ir: ClassIR) -> list[ClassIR] | None:
    """Return all concrete classes among the class itself and its subclasses."""
    concrete = class_ir.concrete_subclasses()
    if concrete is None:
        return None
    if not (class_ir.is_abstract or class_ir.is_trait):
        concrete.append(class_ir)
    return concrete
