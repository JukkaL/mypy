from typing import Optional, Container, Callable

from mypy.types import (
    Type, TypeVisitor, UnboundType, AnyType, NoneType, TypeVarId, Instance, TypeVarType,
    CallableType, TupleType, TypedDictType, UnionType, Overloaded, ErasedType, PartialType,
    DeletedType, TypeTranslator, UninhabitedType, TypeType, TypeOfAny, LiteralType, ProperType,
    get_proper_type
)
from mypy.nodes import ARG_STAR, ARG_STAR2


def erase_type(typ: Type) -> ProperType:
    """Erase any type variables from a type.

    Also replace tuple types with the corresponding concrete types.

    Examples:
      A -> A
      B[X] -> B[Any]
      Tuple[A, B] -> tuple
      Callable[[A1, A2, ...], R] -> Callable[..., Any]
      Type[X] -> Type[Any]
    """
    typ = get_proper_type(typ)
    return typ.accept(EraseTypeVisitor())


class EraseTypeVisitor(TypeVisitor[ProperType]):

    def visit_unbound_type(self, t: UnboundType) -> ProperType:
        # TODO: replace with an assert after UnboundType can't leak from semantic analysis.
        return AnyType(TypeOfAny.from_error)

    def visit_any(self, t: AnyType) -> ProperType:
        return t

    def visit_none_type(self, t: NoneType) -> ProperType:
        return t

    def visit_uninhabited_type(self, t: UninhabitedType) -> ProperType:
        return t

    def visit_erased_type(self, t: ErasedType) -> ProperType:
        # Should not get here.
        raise RuntimeError()

    def visit_partial_type(self, t: PartialType) -> ProperType:
        # Should not get here.
        raise RuntimeError()

    def visit_deleted_type(self, t: DeletedType) -> ProperType:
        return t

    def visit_instance(self, t: Instance) -> ProperType:
        return Instance(t.type, [AnyType(TypeOfAny.special_form)] * len(t.args), t.line)

    def visit_type_var(self, t: TypeVarType) -> ProperType:
        return AnyType(TypeOfAny.special_form)

    def visit_callable_type(self, t: CallableType) -> ProperType:
        # We must preserve the fallback type for overload resolution to work.
        any_type = AnyType(TypeOfAny.special_form)
        return CallableType(
            arg_types=[any_type, any_type],
            arg_kinds=[ARG_STAR, ARG_STAR2],
            arg_names=[None, None],
            ret_type=any_type,
            fallback=t.fallback,
            is_ellipsis_args=True,
            implicit=True,
        )

    def visit_overloaded(self, t: Overloaded) -> ProperType:
        return t.fallback.accept(self)

    def visit_tuple_type(self, t: TupleType) -> ProperType:
        return t.partial_fallback.accept(self)

    def visit_typeddict_type(self, t: TypedDictType) -> ProperType:
        return t.fallback.accept(self)

    def visit_literal_type(self, t: LiteralType) -> ProperType:
        # The fallback for literal types should always be either
        # something like int or str, or an enum class -- types that
        # don't contain any TypeVars. So there's no need to visit it.
        return t

    def visit_union_type(self, t: UnionType) -> ProperType:
        erased_items = [erase_type(item) for item in t.items]
        from mypy.typeops import make_simplified_union  # asdf
        return make_simplified_union(erased_items)

    def visit_type_type(self, t: TypeType) -> ProperType:
        return TypeType.make_normalized(t.item.accept(self), line=t.line)


def erase_typevars(t: Type, ids_to_erase: Optional[Container[TypeVarId]] = None) -> Type:
    """Replace all type variables in a type with any,
    or just the ones in the provided collection.
    """
    def erase_id(id: TypeVarId) -> bool:
        if ids_to_erase is None:
            return True
        return id in ids_to_erase
    return t.accept(TypeVarEraser(erase_id, AnyType(TypeOfAny.special_form)))


def replace_meta_vars(t: Type, target_type: Type) -> Type:
    """Replace unification variables in a type with the target type."""
    return t.accept(TypeVarEraser(lambda id: id.is_meta_var(), target_type))


class TypeVarEraser(TypeTranslator):
    """Implementation of type erasure"""

    def __init__(self, erase_id: Callable[[TypeVarId], bool], replacement: Type) -> None:
        self.erase_id = erase_id
        self.replacement = replacement

    def visit_type_var(self, t: TypeVarType) -> Type:
        if self.erase_id(t.id):
            return self.replacement
        return t


def remove_instance_transient_info(t: Type) -> Type:
    """Recursively removes any info from Instances that exist
    on a per-instance basis. Currently, this means erasing the
    last-known literal type and any plugin metadata.
    """
    return t.accept(TransientInstanceInfoEraser())


class TransientInstanceInfoEraser(TypeTranslator):
    def visit_instance(self, t: Instance) -> Type:
        if t.last_known_value or t.metadata:
            return t.copy_modified(last_known_value=None, metadata={})
        return t
