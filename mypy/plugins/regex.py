"""
A plugin for analyzing regexes to determine how many groups a
regex can contain and whether those groups are always matched or not.
For example:

    pattern: Final = re.compile("(foo)(bar)?")
    match: Final = pattern.match(input_text)
    if match:
        reveal_type(match.groups())

Without the plugin, the best we can really do is determine revealed
type is either Sequence[str] or Tuple[str, ...]. But with this plugin,
we can obtain a more precise type of Tuple[str, Optionl[str]]. We were
able to deduce th first group is mandatory and the second optional.

Broadly, this plugin works by using the underlying builtin regex
parsing engine to obtain the regex AST. We can then crawl this AST
to obtain the mandatory groups, total number of groups, and any
named groups.

We then inject this obtained data into the Pattern or Match objects
into a "metadata" field on a per-instance basis.

Note that while we parse the regex, we at no point will ever actually
try matching anything against it.
"""

from typing import Union, Iterator, Tuple, List, Any, Optional, Dict
from typing_extensions import Final

import sys

from mypy.types import (
    Type, ProperType, Instance, NoneType, LiteralType,
    TupleType, remove_optional,
)
from mypy.typeops import make_simplified_union, coerce_to_literal, get_proper_type
import mypy.plugin  # To avoid circular imports.

from sre_parse import parse, SubPattern
from sre_constants import (
    SUBPATTERN, MIN_REPEAT, MAX_REPEAT, GROUPREF_EXISTS, BRANCH,
    error as SreError, _NamedIntConstant as NIC,
)

STR_LIKE_TYPES = {
    'builtins.unicode',
    'builtins.str',
    'builtins.bytes',
}  # type: Final

FUNCTIONS_PRODUCING_MATCH_OBJECT = {
    're.search',
    're.match',
    're.fullmatch',
}

METHODS_PRODUCING_MATCH_OBJECT = {
    'typing.Pattern.search',
    'typing.Pattern.match',
    'typing.Pattern.fullmatch',
}  # type: Final

METHODS_PRODUCING_GROUP = {
    'typing.Match.group',
    'typing.Match.__getitem__',
}

OBJECTS_SUPPORTING_REGEX_METADATA = {
    'typing.Pattern',
    'typing.Match',
}


class RegexPluginException(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg


def find_mandatory_groups(ast: Union[SubPattern, Tuple[NIC, Any]]) -> Iterator[int]:
    """Yields the all group numbers that are guaranteed to match something
    in the Match object corresponding to the given regex.

    For example, if the provided AST corresponds to the regex
    "(a)(?:(b)|(c))(d)?(e)+(f)", this function would yield 1, 5, and 6.

    We do not yield 0 even though that group will always have a match. This
    function only group numbers that can actually be found in the AST.
    """
    if isinstance(ast, tuple):
        data = [ast]      # type: List[Tuple[NIC, Any]]
    elif isinstance(ast, SubPattern):
        data = ast.data
    else:
        raise RegexPluginException("Internal error: unexpected regex AST item '{}'".format(ast))

    for op, av in data:
        if op is SUBPATTERN:
            # Use relative indexing for maximum compatibility:
            # av contains just these two elements in Python 3.5
            # but four elements for newer Pythons.
            group, children = av[0], av[-1]

            # This can be 'None' for "extension notation groups"
            if group is not None:
                yield group
            for child in children:
                yield from find_mandatory_groups(child)
        elif op in (MIN_REPEAT, MAX_REPEAT):
            min_repeats, _, children = av
            if min_repeats == 0:
                continue
            for child in children:
                yield from find_mandatory_groups(child)
        elif op in (BRANCH, GROUPREF_EXISTS):
            # Note: We deliberately ignore branches (e.g. "(a)|(b)") or
            # conditional matches (e.g. "(?(named-group)yes-branch|no-branch)".
            # The whole point of a branch is that it'll be matched only
            # some of the time, therefore no subgroups in either branch can
            # ever be mandatory.
            continue
        elif isinstance(av, list):
            for child in av:
                yield from find_mandatory_groups(child)


def extract_regex_group_info(pattern: str) -> Tuple[List[int], int, Dict[str, int]]:
    """Analyzes the given regex pattern and returns a tuple of:

    1. A list of all mandatory group indexes in sorted order (including 0).
    2. The total number of groups, including optional groups and the zero-th group.
    3. A mapping of named groups to group indices.

    If the given str is not a valid regex, raises RegexPluginException.
    """
    try:
        ast = parse(pattern)
    except SreError as ex:
        raise RegexPluginException("Invalid regex: {}".format(ex.msg))

    mandatory_groups = [0] + list(sorted(find_mandatory_groups(ast)))

    if sys.version_info >= (3, 8, 0):
        state = ast.state
    else:
        state = ast.pattern
    total_groups = state.groups
    named_groups = state.groupdict

    return mandatory_groups, total_groups, named_groups


def analyze_regex_pattern_call(
        pattern_type: Type,
        default_return_type: Type,
) -> Type:
    """The re module contains several methods or functions
    that accept some string containing a regex pattern and returns
    either a typing.Pattern or typing.Match object.

    This function handles the core logic for extracting and
    attaching this regex metadata to the return object in all
    these cases.
    """

    pattern_type = coerce_to_literal(pattern_type)
    if not isinstance(pattern_type, LiteralType):
        return default_return_type
    if pattern_type.fallback.type.fullname() not in STR_LIKE_TYPES:
        return default_return_type

    return_type = get_proper_type(default_return_type)
    if not isinstance(return_type, Instance):
        return default_return_type
    if return_type.type.fullname() not in OBJECTS_SUPPORTING_REGEX_METADATA:
        return default_return_type

    pattern = pattern_type.value
    assert isinstance(pattern, str)
    mandatory_groups, total_groups, named_groups = extract_regex_group_info(pattern)

    metadata = {
        "default_re_plugin": {
            "mandatory_groups": mandatory_groups,
            "total_groups": total_groups,
            "named_groups": named_groups,
        }
    }

    return return_type.copy_modified(
        metadata={**return_type.metadata, **metadata},
    )


def extract_metadata(typ: ProperType) -> Optional[Tuple[Dict[str, Any], Instance]]:
    """Returns the regex metadata from the given type, if it exists.
    Otherwise returns None.

    This function is the dual of 'analyze_regex_pattern_call'. That function
    tries finding and attaching the metadata to Pattern or Match objects;
    this function tries extracting the attached metadata.
    """
    if not isinstance(typ, Instance):
        return None

    metadata = typ.metadata.get('default_re_plugin', None)
    if metadata is None:
        return None

    arg_type = get_proper_type(typ.args[0])
    if not isinstance(arg_type, Instance):
        return None

    return metadata, arg_type


def re_direct_match_callback(ctx: mypy.plugin.FunctionContext) -> Type:
    """Analyzes functions such as 're.match(PATTERN, INPUT)'"""
    try:
        return analyze_regex_pattern_call(
            ctx.arg_types[0][0],
            remove_optional(ctx.default_return_type),
        )
    except RegexPluginException as ex:
        ctx.api.fail(ex.msg, ctx.context)
        return ctx.default_return_type


def re_compile_callback(ctx: mypy.plugin.FunctionContext) -> Type:
    """Analyzes the 're.compile(PATTERN)' function."""
    try:
        return analyze_regex_pattern_call(
            ctx.arg_types[0][0],
            ctx.default_return_type,
        )
    except RegexPluginException as ex:
        ctx.api.fail(ex.msg, ctx.context)
        return ctx.default_return_type


def re_get_match_callback(ctx: mypy.plugin.MethodContext) -> Type:
    """Analyzes the 'typing.Pattern.match(...)' method."""
    self_type = ctx.type
    return_type = ctx.default_return_type

    if not isinstance(self_type, Instance) or 'default_re_plugin' not in self_type.metadata:
        return return_type

    match_object = remove_optional(return_type)
    assert isinstance(match_object, Instance)

    pattern_metadata = self_type.metadata['default_re_plugin']
    new_match_object = match_object.copy_modified(metadata={'default_re_plugin': pattern_metadata})
    return make_simplified_union([new_match_object, NoneType()])


def re_match_groups_callback(ctx: mypy.plugin.MethodContext) -> Type:
    """Analyzes the 'typing.Match.group(...)' method, which returns
    a tuple of all matched groups."""
    info = extract_metadata(ctx.type)
    if info is None:
        return ctx.default_return_type

    metadata, mandatory_match_type = info
    mandatory = set(metadata['mandatory_groups'])
    total = metadata['total_groups']

    if len(ctx.arg_types) > 0 and len(ctx.arg_types[0]) > 0:
        default_type = ctx.arg_types[0][0]
    else:
        default_type = NoneType()

    optional_match_type = make_simplified_union([mandatory_match_type, default_type])

    items = []  # type: List[Type]
    for i in range(1, total):
        if i in mandatory:
            items.append(mandatory_match_type)
        else:
            items.append(optional_match_type)

    fallback = ctx.api.named_generic_type("builtins.tuple", [mandatory_match_type])
    return TupleType(items, fallback)


def re_match_group_callback(ctx: mypy.plugin.MethodContext) -> Type:
    """Analyzes the 'typing.Match.group()' and '__getitem__(...)' methods."""
    info = extract_metadata(ctx.type)
    if info is None:
        return ctx.default_return_type

    metadata, mandatory_match_type = info
    mandatory = set(metadata['mandatory_groups'])
    total = metadata['total_groups']
    named_groups = metadata['named_groups']

    if len(mandatory) != total:
        optional_match_type = make_simplified_union([mandatory_match_type, NoneType()])
    else:
        optional_match_type = mandatory_match_type

    possible_indices = []
    for arg_type in ctx.arg_types:
        if len(arg_type) >= 1:
            possible_indices.append(coerce_to_literal(arg_type[0]))

    outputs = []  # type: List[Type]
    for possible_index in possible_indices:
        if not isinstance(possible_index, LiteralType):
            outputs.append(optional_match_type)
            continue

        value = possible_index.value
        fallback_name = possible_index.fallback.type.fullname()

        if isinstance(value, str) and fallback_name in STR_LIKE_TYPES:
            if value not in named_groups:
                ctx.api.fail("Regex does not contain group named '{}'".format(value), ctx.context)
                outputs.append(optional_match_type)
                continue

            index = named_groups[value]
        elif isinstance(value, int):
            if value < 0:
                ctx.api.fail("Regex group number should not be negative", ctx.context)
                outputs.append(optional_match_type)
                continue
            elif value >= total:
                msg = "Regex has {} total groups, given group number {} is too big"
                ctx.api.fail(msg.format(total, value), ctx.context)
                outputs.append(optional_match_type)
                continue
            index = value
        else:
            outputs.append(optional_match_type)
            continue

        if index in mandatory:
            outputs.append(mandatory_match_type)
        else:
            outputs.append(optional_match_type)

    if len(outputs) == 1:
        return outputs[0]
    else:
        fallback = ctx.api.named_generic_type("builtins.tuple", [mandatory_match_type])
        return TupleType(outputs, fallback)
