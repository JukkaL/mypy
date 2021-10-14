"""Classes for producing HTML reports about imprecision."""

from abc import ABCMeta, abstractmethod
import collections
import json
import os
import shutil
import tokenize
import time
import sys
import itertools
from operator import attrgetter
from urllib.request import pathname2url

import typing
from typing import Any, Callable, Dict, List, Optional, Tuple, cast, Iterator
from typing_extensions import Final

from mypy.nodes import MypyFile, Expression, FuncDef
from mypy import stats
from mypy.options import Options
from mypy.traverser import TraverserVisitor
from mypy.types import Type, TypeOfAny
from mypy.version import __version__
from mypy.defaults import REPORTER_NAMES

try:
    # mypyc doesn't properly handle import from of submodules that we
    # don't have stubs for, hence the hacky double import
    import lxml.etree  # type: ignore  # noqa: F401
    from lxml import etree
    LXML_INSTALLED = True
except ImportError:
    LXML_INSTALLED = False

type_of_any_name_map: Final["collections.OrderedDict[int, str]"] = collections.OrderedDict(
    [
        (TypeOfAny.unannotated, "Unannotated"),
        (TypeOfAny.explicit, "Explicit"),
        (TypeOfAny.from_unimported_type, "Unimported"),
        (TypeOfAny.from_omitted_generics, "Omitted Generics"),
        (TypeOfAny.from_error, "Error"),
        (TypeOfAny.special_form, "Special Form"),
        (TypeOfAny.implementation_artifact, "Implementation Artifact"),
    ]
)

ReporterClasses = Dict[str, Tuple[Callable[['Reports', str], 'AbstractReporter'], bool]]

reporter_classes: Final[ReporterClasses] = {}


class Reports:
    def __init__(self, data_dir: str, report_dirs: Dict[str, str]) -> None:
        self.data_dir = data_dir
        self.reporters: List[AbstractReporter] = []
        self.named_reporters: Dict[str, AbstractReporter] = {}

        for report_type, report_dir in sorted(report_dirs.items()):
            self.add_report(report_type, report_dir)

    def add_report(self, report_type: str, report_dir: str) -> 'AbstractReporter':
        try:
            return self.named_reporters[report_type]
        except KeyError:
            pass
        reporter_cls, needs_lxml = reporter_classes[report_type]
        if needs_lxml and not LXML_INSTALLED:
            print(('You must install the lxml package before you can run mypy'
                   ' with `--{}-report`.\n'
                   'You can do this with `python3 -m pip install lxml`.').format(report_type),
                  file=sys.stderr)
            raise ImportError
        reporter = reporter_cls(self, report_dir)
        self.reporters.append(reporter)
        self.named_reporters[report_type] = reporter
        return reporter

    def file(self,
             tree: MypyFile,
             modules: Dict[str, MypyFile],
             type_map: Dict[Expression, Type],
             options: Options) -> None:
        for reporter in self.reporters:
            reporter.on_file(tree, modules, type_map, options)

    def finish(self) -> None:
        for reporter in self.reporters:
            reporter.on_finish()


class AbstractReporter(metaclass=ABCMeta):
    def __init__(self, reports: Reports, output_dir: str) -> None:
        self.output_dir = output_dir
        if output_dir != '<memory>':
            stats.ensure_dir_exists(output_dir)

    @abstractmethod
    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        pass

    @abstractmethod
    def on_finish(self) -> None:
        pass


def register_reporter(report_name: str,
                      reporter: Callable[[Reports, str], AbstractReporter],
                      needs_lxml: bool = False) -> None:
    reporter_classes[report_name] = (reporter, needs_lxml)


def alias_reporter(source_reporter: str, target_reporter: str) -> None:
    reporter_classes[target_reporter] = reporter_classes[source_reporter]


def should_skip_path(path: str) -> bool:
    if stats.is_special_module(path):
        return True
    if path.startswith('..'):
        return True
    if 'stubs' in path.split('/') or 'stubs' in path.split(os.sep):
        return True
    return False


def iterate_python_lines(path: str) -> Iterator[Tuple[int, str]]:
    """Return an iterator over (line number, line text) from a Python file."""
    with tokenize.open(path) as input_file:
        for line_info in enumerate(input_file, 1):
            yield line_info


class FuncCounterVisitor(TraverserVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.counts = [0, 0]

    def visit_func_def(self, defn: FuncDef) -> None:
        self.counts[defn.type is not None] += 1


class LineCountReporter(AbstractReporter):
    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)
        self.counts: Dict[str, Tuple[int, int, int, int]] = {}

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        # Count physical lines.  This assumes the file's encoding is a
        # superset of ASCII (or at least uses \n in its line endings).
        with open(tree.path, 'rb') as f:
            physical_lines = len(f.readlines())

        func_counter = FuncCounterVisitor()
        tree.accept(func_counter)
        unannotated_funcs, annotated_funcs = func_counter.counts
        total_funcs = annotated_funcs + unannotated_funcs

        # Don't count lines or functions as annotated if they have their errors ignored.
        if options.ignore_errors:
            annotated_funcs = 0

        imputed_annotated_lines = (physical_lines * annotated_funcs // total_funcs
                                   if total_funcs else physical_lines)

        self.counts[tree._fullname] = (imputed_annotated_lines, physical_lines,
                                       annotated_funcs, total_funcs)

    def on_finish(self) -> None:
        counts: List[Tuple[Tuple[int, int, int, int], str]] = sorted(
            ((c, p) for p, c in self.counts.items()), reverse=True
        )
        total_counts = tuple(sum(c[i] for c, p in counts) for i in range(4))
        with open(os.path.join(self.output_dir, "linecount.txt"), "w") as f:
            f.write("{:7} {:7} {:6} {:6} total\n".format(*total_counts))
            for c, p in counts:
                f.write('{:7} {:7} {:6} {:6} {}\n'.format(
                    c[0], c[1], c[2], c[3], p))


register_reporter('linecount', LineCountReporter)


class AnyExpressionsReporter(AbstractReporter):
    """Report frequencies of different kinds of Any types."""

    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)
        self.counts: Dict[str, Tuple[int, int]] = {}
        self.any_types_counter: Dict[str, typing.Counter[int]] = {}

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        visitor = stats.StatisticsVisitor(inferred=True,
                                          filename=tree.fullname,
                                          modules=modules,
                                          typemap=type_map,
                                          all_nodes=True,
                                          visit_untyped_defs=False)
        tree.accept(visitor)
        self.any_types_counter[tree.fullname] = visitor.type_of_any_counter
        num_unanalyzed_lines = list(visitor.line_map.values()).count(stats.TYPE_UNANALYZED)
        # count each line of dead code as one expression of type "Any"
        num_any = visitor.num_any_exprs + num_unanalyzed_lines
        num_total = visitor.num_imprecise_exprs + visitor.num_precise_exprs + num_any
        if num_total > 0:
            self.counts[tree.fullname] = (num_any, num_total)

    def on_finish(self) -> None:
        self._report_any_exprs()
        self._report_types_of_anys()

    def _write_out_report(self,
                          filename: str,
                          header: List[str],
                          rows: List[List[str]],
                          footer: List[str],
                          ) -> None:
        row_len = len(header)
        assert all(len(row) == row_len for row in rows + [header, footer])
        min_column_distance = 3  # minimum distance between numbers in two columns
        widths = [-1] * row_len
        for row in rows + [header, footer]:
            for i, value in enumerate(row):
                widths[i] = max(widths[i], len(value))
        for i, w in enumerate(widths):
            # Do not add min_column_distance to the first column.
            if i > 0:
                widths[i] = w + min_column_distance
        with open(os.path.join(self.output_dir, filename), 'w') as f:
            header_str = ("{:>{}}" * len(widths)).format(*itertools.chain(*zip(header, widths)))
            separator = '-' * len(header_str)
            f.write(header_str + '\n')
            f.write(separator + '\n')
            for row_values in rows:
                r = ("{:>{}}" * len(widths)).format(*itertools.chain(*zip(row_values, widths)))
                f.writelines(r + '\n')
            f.write(separator + '\n')
            footer_str = ("{:>{}}" * len(widths)).format(*itertools.chain(*zip(footer, widths)))
            f.writelines(footer_str + '\n')

    def _report_any_exprs(self) -> None:
        total_any = sum(num_any for num_any, _ in self.counts.values())
        total_expr = sum(total for _, total in self.counts.values())
        total_coverage = 100.0
        if total_expr > 0:
            total_coverage = (float(total_expr - total_any) / float(total_expr)) * 100

        column_names = ["Name", "Anys", "Exprs", "Coverage"]
        rows: List[List[str]] = []
        for filename in sorted(self.counts):
            (num_any, num_total) = self.counts[filename]
            coverage = (float(num_total - num_any) / float(num_total)) * 100
            coverage_str = '{:.2f}%'.format(coverage)
            rows.append([filename, str(num_any), str(num_total), coverage_str])
        rows.sort(key=lambda x: x[0])
        total_row = ["Total", str(total_any), str(total_expr), '{:.2f}%'.format(total_coverage)]
        self._write_out_report('any-exprs.txt', column_names, rows, total_row)

    def _report_types_of_anys(self) -> None:
        total_counter: typing.Counter[int] = collections.Counter()
        for counter in self.any_types_counter.values():
            for any_type, value in counter.items():
                total_counter[any_type] += value
        file_column_name = "Name"
        total_row_name = "Total"
        column_names = [file_column_name] + list(type_of_any_name_map.values())
        rows: List[List[str]] = []
        for filename, counter in self.any_types_counter.items():
            rows.append([filename] + [str(counter[typ]) for typ in type_of_any_name_map])
        rows.sort(key=lambda x: x[0])
        total_row = [total_row_name] + [str(total_counter[typ])
                                        for typ in type_of_any_name_map]
        self._write_out_report('types-of-anys.txt', column_names, rows, total_row)


register_reporter('any-exprs', AnyExpressionsReporter)


class LineCoverageVisitor(TraverserVisitor):
    def __init__(self, source: List[str]) -> None:
        self.source = source

        # For each line of source, we maintain a pair of
        #  * the indentation level of the surrounding function
        #    (-1 if not inside a function), and
        #  * whether the surrounding function is typed.
        # Initially, everything is covered at indentation level -1.
        self.lines_covered = [(-1, True) for l in source]

    # The Python AST has position information for the starts of
    # elements, but not for their ends. Fortunately the
    # indentation-based syntax makes it pretty easy to find where a
    # block ends without doing any real parsing.

    # TODO: Handle line continuations (explicit and implicit) and
    # multi-line string literals. (But at least line continuations
    # are normally more indented than their surrounding block anyways,
    # by PEP 8.)

    def indentation_level(self, line_number: int) -> Optional[int]:
        """Return the indentation of a line of the source (specified by
        zero-indexed line number). Returns None for blank lines or comments."""
        line = self.source[line_number]
        indent = 0
        for char in list(line):
            if char == ' ':
                indent += 1
            elif char == '\t':
                indent = 8 * ((indent + 8) // 8)
            elif char == '#':
                # Line is a comment; ignore it
                return None
            elif char == '\n':
                # Line is entirely whitespace; ignore it
                return None
            # TODO line continuation (\)
            else:
                # Found a non-whitespace character
                return indent
        # Line is entirely whitespace, and at end of file
        # with no trailing newline; ignore it
        return None

    def visit_func_def(self, defn: FuncDef) -> None:
        start_line = defn.get_line() - 1
        start_indent = None
        # When a function is decorated, sometimes the start line will point to
        # whitespace or comments between the decorator and the function, so
        # we have to look for the start.
        while start_line < len(self.source):
            start_indent = self.indentation_level(start_line)
            if start_indent is not None:
                break
            start_line += 1
        # If we can't find the function give up and don't annotate anything.
        # Our line numbers are not reliable enough to be asserting on.
        if start_indent is None:
            return

        cur_line = start_line + 1
        end_line = cur_line
        # After this loop, function body will be lines [start_line, end_line)
        while cur_line < len(self.source):
            cur_indent = self.indentation_level(cur_line)
            if cur_indent is None:
                # Consume the line, but don't mark it as belonging to the function yet.
                cur_line += 1
            elif start_indent is not None and cur_indent > start_indent:
                # A non-blank line that belongs to the function.
                cur_line += 1
                end_line = cur_line
            else:
                # We reached a line outside the function definition.
                break

        is_typed = defn.type is not None
        for line in range(start_line, end_line):
            old_indent, _ = self.lines_covered[line]
            # If there was an old indent level for this line, and the new
            # level isn't increasing the indentation, ignore it.
            # This is to be defensive against funniness in our line numbers,
            # which are not always reliable.
            if old_indent <= start_indent:
                self.lines_covered[line] = (start_indent, is_typed)

        # Visit the body, in case there are nested functions
        super().visit_func_def(defn)


class LineCoverageReporter(AbstractReporter):
    """Exact line coverage reporter.

    This reporter writes a JSON dictionary with one field 'lines' to
    the file 'coverage.json' in the specified report directory. The
    value of that field is a dictionary which associates to each
    source file's absolute pathname the list of line numbers that
    belong to typed functions in that file.
    """

    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)
        self.lines_covered: Dict[str, List[int]] = {}

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        with open(tree.path) as f:
            tree_source = f.readlines()

        coverage_visitor = LineCoverageVisitor(tree_source)
        tree.accept(coverage_visitor)

        covered_lines = []
        for line_number, (_, typed) in enumerate(coverage_visitor.lines_covered):
            if typed:
                covered_lines.append(line_number + 1)

        self.lines_covered[os.path.abspath(tree.path)] = covered_lines

    def on_finish(self) -> None:
        with open(os.path.join(self.output_dir, 'coverage.json'), 'w') as f:
            json.dump({'lines': self.lines_covered}, f)


register_reporter('linecoverage', LineCoverageReporter)


class FileInfo:
    def __init__(self, name: str, module: str) -> None:
        self.name = name
        self.module = module
        self.counts = [0] * len(stats.precision_names)

    def total(self) -> int:
        return sum(self.counts)

    def attrib(self) -> Dict[str, str]:
        return {name: str(val) for name, val in sorted(zip(stats.precision_names, self.counts))}


class MemoryXmlReporter(AbstractReporter):
    """Internal reporter that generates XML in memory.

    This is used by all other XML-based reporters to avoid duplication.
    """

    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)

        self.xslt_html_path = os.path.join(reports.data_dir, 'xml', 'mypy-html.xslt')
        self.xslt_txt_path = os.path.join(reports.data_dir, 'xml', 'mypy-txt.xslt')
        self.css_html_path = os.path.join(reports.data_dir, 'xml', 'mypy-html.css')
        xsd_path = os.path.join(reports.data_dir, 'xml', 'mypy.xsd')
        self.schema = etree.XMLSchema(etree.parse(xsd_path))
        self.last_xml: Optional[Any] = None
        self.files: List[FileInfo] = []

    # XML doesn't like control characters, but they are sometimes
    # legal in source code (e.g. comments, string literals).
    # Tabs (#x09) are allowed in XML content.
    control_fixer: Final = str.maketrans("".join(chr(i) for i in range(32) if i != 9), "?" * 31)

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        self.last_xml = None

        try:
            path = os.path.relpath(tree.path)
        except ValueError:
            return

        if should_skip_path(path) or os.path.isdir(path):
            return  # `path` can sometimes be a directory, see #11334

        visitor = stats.StatisticsVisitor(inferred=True,
                                          filename=tree.fullname,
                                          modules=modules,
                                          typemap=type_map,
                                          all_nodes=True)
        tree.accept(visitor)

        root = etree.Element('mypy-report-file', name=path, module=tree._fullname)
        doc = etree.ElementTree(root)
        file_info = FileInfo(path, tree._fullname)

        for lineno, line_text in iterate_python_lines(path):
            status = visitor.line_map.get(lineno, stats.TYPE_EMPTY)
            file_info.counts[status] += 1
            etree.SubElement(root, 'line',
                             any_info=self._get_any_info_for_line(visitor, lineno),
                             content=line_text.rstrip('\n').translate(self.control_fixer),
                             number=str(lineno),
                             precision=stats.precision_names[status])
        # Assumes a layout similar to what XmlReporter uses.
        xslt_path = os.path.relpath('mypy-html.xslt', path)
        transform_pi = etree.ProcessingInstruction('xml-stylesheet',
                'type="text/xsl" href="%s"' % pathname2url(xslt_path))
        root.addprevious(transform_pi)
        self.schema.assertValid(doc)

        self.last_xml = doc
        self.files.append(file_info)

    @staticmethod
    def _get_any_info_for_line(visitor: stats.StatisticsVisitor, lineno: int) -> str:
        if lineno in visitor.any_line_map:
            result = "Any Types on this line: "
            counter: typing.Counter[int] = collections.Counter()
            for typ in visitor.any_line_map[lineno]:
                counter[typ.type_of_any] += 1
            for any_type, occurrences in counter.items():
                result += "\n{} (x{})".format(type_of_any_name_map[any_type], occurrences)
            return result
        else:
            return "No Anys on this line!"

    def on_finish(self) -> None:
        self.last_xml = None
        # index_path = os.path.join(self.output_dir, 'index.xml')
        output_files = sorted(self.files, key=lambda x: x.module)

        root = etree.Element('mypy-report-index', name='index')
        doc = etree.ElementTree(root)

        for file_info in output_files:
            etree.SubElement(root, 'file',
                             file_info.attrib(),
                             module=file_info.module,
                             name=pathname2url(file_info.name),
                             total=str(file_info.total()))
        xslt_path = os.path.relpath('mypy-html.xslt', '.')
        transform_pi = etree.ProcessingInstruction('xml-stylesheet',
                'type="text/xsl" href="%s"' % pathname2url(xslt_path))
        root.addprevious(transform_pi)
        self.schema.assertValid(doc)

        self.last_xml = doc


register_reporter('memory-xml', MemoryXmlReporter, needs_lxml=True)


def get_line_rate(covered_lines: int, total_lines: int) -> str:
    if total_lines == 0:
        return str(1.0)
    else:
        return '{:.4f}'.format(covered_lines / total_lines)


class CoberturaPackage(object):
    """Container for XML and statistics mapping python modules to Cobertura package."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.classes: Dict[str, Any] = {}
        self.packages: Dict[str, CoberturaPackage] = {}
        self.total_lines = 0
        self.covered_lines = 0

    def as_xml(self) -> Any:
        package_element = etree.Element('package',
                                        complexity='1.0',
                                        name=self.name)
        package_element.attrib['branch-rate'] = '0'
        package_element.attrib['line-rate'] = get_line_rate(self.covered_lines, self.total_lines)
        classes_element = etree.SubElement(package_element, 'classes')
        for class_name in sorted(self.classes):
            classes_element.append(self.classes[class_name])
        self.add_packages(package_element)
        return package_element

    def add_packages(self, parent_element: Any) -> None:
        if self.packages:
            packages_element = etree.SubElement(parent_element, 'packages')
            for package in sorted(self.packages.values(), key=attrgetter('name')):
                packages_element.append(package.as_xml())


class CoberturaXmlReporter(AbstractReporter):
    """Reporter for generating Cobertura compliant XML."""

    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)

        self.root = etree.Element('coverage',
                                  timestamp=str(int(time.time())),
                                  version=__version__)
        self.doc = etree.ElementTree(self.root)
        self.root_package = CoberturaPackage('.')

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        path = os.path.relpath(tree.path)
        visitor = stats.StatisticsVisitor(inferred=True,
                                          filename=tree.fullname,
                                          modules=modules,
                                          typemap=type_map,
                                          all_nodes=True)
        tree.accept(visitor)

        class_name = os.path.basename(path)
        file_info = FileInfo(path, tree._fullname)
        class_element = etree.Element('class',
                                      complexity='1.0',
                                      filename=path,
                                      name=class_name)
        etree.SubElement(class_element, 'methods')
        lines_element = etree.SubElement(class_element, 'lines')

        with tokenize.open(path) as input_file:
            class_lines_covered = 0
            class_total_lines = 0
            for lineno, _ in enumerate(input_file, 1):
                status = visitor.line_map.get(lineno, stats.TYPE_EMPTY)
                hits = 0
                branch = False
                if status == stats.TYPE_EMPTY:
                    continue
                class_total_lines += 1
                if status != stats.TYPE_ANY:
                    class_lines_covered += 1
                    hits = 1
                if status == stats.TYPE_IMPRECISE:
                    branch = True
                file_info.counts[status] += 1
                line_element = etree.SubElement(lines_element, 'line',
                                                branch=str(branch).lower(),
                                                hits=str(hits),
                                                number=str(lineno),
                                                precision=stats.precision_names[status])
                if branch:
                    line_element.attrib['condition-coverage'] = '50% (1/2)'
            class_element.attrib['branch-rate'] = '0'
            class_element.attrib['line-rate'] = get_line_rate(class_lines_covered,
                                                              class_total_lines)
            # parent_module is set to whichever module contains this file.  For most files, we want
            # to simply strip the last element off of the module.  But for __init__.py files,
            # the module == the parent module.
            parent_module = file_info.module.rsplit('.', 1)[0]
            if file_info.name.endswith('__init__.py'):
                parent_module = file_info.module

            if parent_module not in self.root_package.packages:
                self.root_package.packages[parent_module] = CoberturaPackage(parent_module)
            current_package = self.root_package.packages[parent_module]
            packages_to_update = [self.root_package, current_package]
            for package in packages_to_update:
                package.total_lines += class_total_lines
                package.covered_lines += class_lines_covered
            current_package.classes[class_name] = class_element

    def on_finish(self) -> None:
        self.root.attrib['line-rate'] = get_line_rate(self.root_package.covered_lines,
                                                      self.root_package.total_lines)
        self.root.attrib['branch-rate'] = '0'
        sources = etree.SubElement(self.root, 'sources')
        source_element = etree.SubElement(sources, 'source')
        source_element.text = os.getcwd()
        self.root_package.add_packages(self.root)
        out_path = os.path.join(self.output_dir, 'cobertura.xml')
        self.doc.write(out_path, encoding='utf-8', pretty_print=True)
        print('Generated Cobertura report:', os.path.abspath(out_path))


register_reporter('cobertura-xml', CoberturaXmlReporter, needs_lxml=True)


class AbstractXmlReporter(AbstractReporter):
    """Internal abstract class for reporters that work via XML."""

    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)

        memory_reporter = reports.add_report('memory-xml', '<memory>')
        # The dependency will be called first.
        self.memory_xml = cast(MemoryXmlReporter, memory_reporter)


class XmlReporter(AbstractXmlReporter):
    """Public reporter that exports XML.

    The produced XML files contain a reference to the absolute path
    of the html transform, so they will be locally viewable in a browser.

    However, there is a bug in Chrome and all other WebKit-based browsers
    that makes it fail from file:// URLs but work on http:// URLs.
    """

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        last_xml = self.memory_xml.last_xml
        if last_xml is None:
            return
        path = os.path.relpath(tree.path)
        if path.startswith('..'):
            return
        out_path = os.path.join(self.output_dir, 'xml', path + '.xml')
        stats.ensure_dir_exists(os.path.dirname(out_path))
        last_xml.write(out_path, encoding='utf-8')

    def on_finish(self) -> None:
        last_xml = self.memory_xml.last_xml
        assert last_xml is not None
        out_path = os.path.join(self.output_dir, 'index.xml')
        out_xslt = os.path.join(self.output_dir, 'mypy-html.xslt')
        out_css = os.path.join(self.output_dir, 'mypy-html.css')
        last_xml.write(out_path, encoding='utf-8')
        shutil.copyfile(self.memory_xml.xslt_html_path, out_xslt)
        shutil.copyfile(self.memory_xml.css_html_path, out_css)
        print('Generated XML report:', os.path.abspath(out_path))


register_reporter('xml', XmlReporter, needs_lxml=True)


class XsltHtmlReporter(AbstractXmlReporter):
    """Public reporter that exports HTML via XSLT.

    This is slightly different than running `xsltproc` on the .xml files,
    because it passes a parameter to rewrite the links.
    """

    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)

        self.xslt_html = etree.XSLT(etree.parse(self.memory_xml.xslt_html_path))
        self.param_html = etree.XSLT.strparam('html')

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        last_xml = self.memory_xml.last_xml
        if last_xml is None:
            return
        path = os.path.relpath(tree.path)
        if path.startswith('..'):
            return
        out_path = os.path.join(self.output_dir, 'html', path + '.html')
        stats.ensure_dir_exists(os.path.dirname(out_path))
        transformed_html = bytes(self.xslt_html(last_xml, ext=self.param_html))
        with open(out_path, 'wb') as out_file:
            out_file.write(transformed_html)

    def on_finish(self) -> None:
        last_xml = self.memory_xml.last_xml
        assert last_xml is not None
        out_path = os.path.join(self.output_dir, 'index.html')
        out_css = os.path.join(self.output_dir, 'mypy-html.css')
        transformed_html = bytes(self.xslt_html(last_xml, ext=self.param_html))
        with open(out_path, 'wb') as out_file:
            out_file.write(transformed_html)
        shutil.copyfile(self.memory_xml.css_html_path, out_css)
        print('Generated HTML report (via XSLT):', os.path.abspath(out_path))


register_reporter('xslt-html', XsltHtmlReporter, needs_lxml=True)


class XsltTxtReporter(AbstractXmlReporter):
    """Public reporter that exports TXT via XSLT.

    Currently this only does the summary, not the individual reports.
    """

    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)

        self.xslt_txt = etree.XSLT(etree.parse(self.memory_xml.xslt_txt_path))

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:
        pass

    def on_finish(self) -> None:
        last_xml = self.memory_xml.last_xml
        assert last_xml is not None
        out_path = os.path.join(self.output_dir, 'index.txt')
        transformed_txt = bytes(self.xslt_txt(last_xml))
        with open(out_path, 'wb') as out_file:
            out_file.write(transformed_txt)
        print('Generated TXT report (via XSLT):', os.path.abspath(out_path))


register_reporter('xslt-txt', XsltTxtReporter, needs_lxml=True)

alias_reporter('xslt-html', 'html')
alias_reporter('xslt-txt', 'txt')


class LinePrecisionReporter(AbstractReporter):
    """Report per-module line counts for typing precision.

    Each line is classified into one of these categories:

    * precise (fully type checked)
    * imprecise (Any types in a type component, such as List[Any])
    * any (something with an Any type, implicit or explicit)
    * empty (empty line, comment or docstring)
    * unanalyzed (mypy considers line unreachable)

    The meaning of these categories varies slightly depending on
    context.
    """

    def __init__(self, reports: Reports, output_dir: str) -> None:
        super().__init__(reports, output_dir)
        self.files: List[FileInfo] = []

    def on_file(self,
                tree: MypyFile,
                modules: Dict[str, MypyFile],
                type_map: Dict[Expression, Type],
                options: Options) -> None:

        try:
            path = os.path.relpath(tree.path)
        except ValueError:
            return

        if should_skip_path(path):
            return

        visitor = stats.StatisticsVisitor(inferred=True,
                                          filename=tree.fullname,
                                          modules=modules,
                                          typemap=type_map,
                                          all_nodes=True)
        tree.accept(visitor)

        file_info = FileInfo(path, tree._fullname)
        for lineno, _ in iterate_python_lines(path):
            status = visitor.line_map.get(lineno, stats.TYPE_EMPTY)
            file_info.counts[status] += 1

        self.files.append(file_info)

    def on_finish(self) -> None:
        if not self.files:
            # Nothing to do.
            return
        output_files = sorted(self.files, key=lambda x: x.module)
        report_file = os.path.join(self.output_dir, 'lineprecision.txt')
        width = max(4, max(len(info.module) for info in output_files))
        titles = ('Lines', 'Precise', 'Imprecise', 'Any', 'Empty', 'Unanalyzed')
        widths = (width,) + tuple(len(t) for t in titles)
        fmt = '{:%d}  {:%d}  {:%d}  {:%d}  {:%d}  {:%d}  {:%d}\n' % widths
        with open(report_file, 'w') as f:
            f.write(
                fmt.format('Name', *titles))
            f.write('-' * (width + 51) + '\n')
            for file_info in output_files:
                counts = file_info.counts
                f.write(fmt.format(file_info.module.ljust(width),
                                   file_info.total(),
                                   counts[stats.TYPE_PRECISE],
                                   counts[stats.TYPE_IMPRECISE],
                                   counts[stats.TYPE_ANY],
                                   counts[stats.TYPE_EMPTY],
                                   counts[stats.TYPE_UNANALYZED]))


register_reporter('lineprecision', LinePrecisionReporter)


# Reporter class names are defined twice to speed up mypy startup, as this
# module is slow to import. Ensure that the two definitions match.
assert set(reporter_classes) == set(REPORTER_NAMES)
