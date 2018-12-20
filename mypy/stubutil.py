import enum
import io
import re
import sys
import os
import tokenize

from typing import Optional, Tuple, Sequence, MutableSequence, List, MutableMapping, IO, NamedTuple
from types import ModuleType


# Type Alias for Signatures
Sig = Tuple[str, str]

TypedArgSig = NamedTuple('TypedArgSig', [
    ('name', str),
    ('type', Optional[str]),
    ('default', Optional[str])
])

ArgList = List[TypedArgSig]

TypedFunctionSig = NamedTuple('TypedFunctionSig', [
    ('name', str),
    ('args', ArgList),
    ('ret_type', str)
])


def parse_signature(sig: str) -> Optional[Tuple[str,
                                                List[str],
                                                List[str]]]:
    m = re.match(r'([.a-zA-Z0-9_]+)\(([^)]*)\)', sig)
    if not m:
        return None
    name = m.group(1)
    name = name.split('.')[-1]
    arg_string = m.group(2)
    if not arg_string.strip():
        return (name, [], [])
    args = [arg.strip() for arg in arg_string.split(',')]
    fixed = []
    optional = []
    i = 0
    while i < len(args):
        if args[i].startswith('[') or '=' in args[i]:
            break
        fixed.append(args[i].rstrip('['))
        i += 1
        if args[i - 1].endswith('['):
            break
    while i < len(args):
        arg = args[i]
        arg = arg.strip('[]')
        arg = arg.split('=')[0]
        optional.append(arg)
        i += 1
    return (name, fixed, optional)


def build_signature(fixed: Sequence[str],
                    optional: Sequence[str]) -> str:
    args = []  # type: MutableSequence[str]
    args.extend(fixed)
    for arg in optional:
        if arg.startswith('*'):
            args.append(arg)
        else:
            args.append('%s=...' % arg)
    sig = '(%s)' % ', '.join(args)
    # Ad-hoc fixes.
    sig = sig.replace('(self)', '')
    return sig


def parse_all_signatures(lines: Sequence[str]) -> Tuple[List[Sig],
                                                        List[Sig]]:
    sigs = []
    class_sigs = []
    for line in lines:
        line = line.strip()
        m = re.match(r'\.\. *(function|method|class) *:: *[a-zA-Z_]', line)
        if m:
            sig = line.split('::')[1].strip()
            parsed = parse_signature(sig)
            if parsed:
                name, fixed, optional = parsed
                if m.group(1) != 'class':
                    sigs.append((name, build_signature(fixed, optional)))
                else:
                    class_sigs.append((name, build_signature(fixed, optional)))

    return sorted(sigs), sorted(class_sigs)


def find_unique_signatures(sigs: Sequence[Sig]) -> List[Sig]:
    sig_map = {}  # type: MutableMapping[str, List[str]]
    for name, sig in sigs:
        sig_map.setdefault(name, []).append(sig)
    result = []
    for name, name_sigs in sig_map.items():
        if len(set(name_sigs)) == 1:
            result.append((name, name_sigs[0]))
    return sorted(result)


def is_c_module(module: ModuleType) -> bool:
    return ('__file__' not in module.__dict__ or
            os.path.splitext(module.__dict__['__file__'])[-1] in ['.so', '.pyd'])


def write_header(file: IO[str], module_name: Optional[str] = None,
                 pyversion: Tuple[int, int] = (3, 5)) -> None:
    if module_name:
        if pyversion[0] >= 3:
            version = '%d.%d' % (sys.version_info.major,
                                 sys.version_info.minor)
        else:
            version = '2'
        file.write('# Stubs for %s (Python %s)\n' % (module_name, version))
    file.write(
        '#\n'
        '# NOTE: This dynamically typed stub was automatically generated by stubgen.\n\n')


class State(enum.Enum):
    INIT = 1
    FUNCTION_NAME = 2
    ARGUMENT_LIST = 3
    ARGUMENT_TYPE = 4
    ARGUMENT_DEFAULT = 5
    RETURN_VALUE = 6
    OPEN_BRACKET = 7


def infer_sig_from_docstring(docstr: str, name: str) -> Optional[List[TypedFunctionSig]]:
    if not docstr:
        return None

    state = [State.INIT, ]
    accumulator = ""
    arg_type = None
    arg_name = ""
    arg_default = None
    ret_type = "Any"
    found = False
    args = []  # type: List[TypedArgSig]
    signatures = []  # type: List[TypedFunctionSig]
    try:
        for token in tokenize.tokenize(io.BytesIO(docstr.encode('utf-8')).readline):
            if token.type == tokenize.NAME and token.string == name and state[-1] == State.INIT:
                state.append(State.FUNCTION_NAME)

            elif token.type == tokenize.OP and token.string == '(' and state[-1] == \
                    State.FUNCTION_NAME:
                state.pop()
                accumulator = ""
                found = True
                state.append(State.ARGUMENT_LIST)

            elif state[-1] == State.FUNCTION_NAME:
                # reset state, function name not followed by '('
                state.pop()

            elif token.type == tokenize.OP and token.string in ('[', '(', '{') and \
                    state[-1] != State.INIT:
                accumulator += token.string
                state.append(State.OPEN_BRACKET)

            elif token.type == tokenize.OP and token.string in (']', ')', '}') and \
                    state[-1] == State.OPEN_BRACKET:
                accumulator += token.string
                state.pop()

            elif token.type == tokenize.OP and token.string == ':' and \
                    state[-1] == State.ARGUMENT_LIST:
                arg_name = accumulator
                accumulator = ""
                state.append(State.ARGUMENT_TYPE)

            elif token.type == tokenize.OP and token.string == '=' and state[-1] in (
                    State.ARGUMENT_LIST, State.ARGUMENT_TYPE):
                if state[-1] == State.ARGUMENT_TYPE:
                    arg_type = accumulator
                    state.pop()
                else:
                    arg_name = accumulator
                accumulator = ""
                state.append(State.ARGUMENT_DEFAULT)

            elif token.type == tokenize.OP and token.string in (',', ')') and state[-1] in (
                    State.ARGUMENT_LIST, State.ARGUMENT_DEFAULT, State.ARGUMENT_TYPE):
                if state[-1] == State.ARGUMENT_DEFAULT:
                    arg_default = accumulator
                    state.pop()
                elif state[-1] == State.ARGUMENT_TYPE:
                    arg_type = accumulator
                    state.pop()
                elif state[-1] == State.ARGUMENT_LIST:
                    arg_name = accumulator

                if token.string == ')':
                    state.pop()
                args.append(TypedArgSig(name=arg_name, type=arg_type, default=arg_default))
                arg_name = ""
                arg_type = None
                arg_default = None
                accumulator = ""

            elif token.type == tokenize.OP and token.string == '->' and state[-1] == State.INIT:
                accumulator = ""
                state.append(State.RETURN_VALUE)

            # ENDMAKER is necessary for python 3.4 and 3.5
            elif token.type in (tokenize.NEWLINE, tokenize.ENDMARKER) and state[-1] in (
                    State.INIT, State.RETURN_VALUE):
                if state[-1] == State.RETURN_VALUE:
                    ret_type = accumulator
                    accumulator = ""
                    state.pop()

                if found:
                    signatures.append(TypedFunctionSig(name=name, args=args, ret_type=ret_type))
                    found = False
                args = []
                ret_type = 'Any'
                # leave state as INIT
            else:
                accumulator += token.string

        return signatures
    except tokenize.TokenError:
        # return as much as collected
        return signatures


def infer_arg_sig_from_docstring(docstr: str) -> ArgList:
    """
    convert signature in form of "(self: TestClass, arg0: str='ada')" to ArgList

    :param docstr:
    :return: ArgList with infered argument names and its types
    """
    ret = []  # type: ArgList
    arguments = []
    right = docstr[1:-1]
    accumulator = ""
    while right:
        left, sep, right = right.partition(',')
        if right.count('[') == right.count(']'):
            arguments.append(accumulator + left)
            accumulator = ""
        else:
            accumulator += left + sep

    for arg in arguments:
        arg_name_type, _, default_value = arg.partition('=')
        arg_name, _, arg_type = arg_name_type.partition(':')

        ret.append(TypedArgSig(
            name=arg_name.strip(),
            type=None if arg_type == '' else arg_type.strip(),
            default=None if default_value == '' else default_value.strip()
        ))
    return ret


def infer_prop_type_from_docstring(docstr: str) -> Optional[str]:
    if not docstr:
        return None

    # check for Google/Numpy style docstring type annotation
    # the docstring has the format "<type>: <descriptions>"
    # in the type string, we allow the following characters
    # dot: because something classes are annotated using full path,
    # brackets: to allow type hints like List[int]
    # comma/space: things like Tuple[int, int]
    test_str = r'^([a-zA-Z0-9_, \.\[\]]*): '
    m = re.match(test_str, docstr)
    return m.group(1) if m else None
