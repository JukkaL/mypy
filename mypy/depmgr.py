"""Dependency manager.

This will replace the dependency management in build.py.

Design
======

Ideally
-------

A. Collapse cycles (each SCC -- strongly connected component --
   becomes one "supernode").

B. Topologically sort nodes based on dependencies.

C. Process from leaves towards roots.

Wrinkles
--------

a. Need to parse source modules to determine dependencies.

b. Processing order for modules within an SCC.

c. Must order mtimes of files to decide whether to re-process; depends
   on clock never resetting.

d. from P import M; checks filesystem whether module P.M exists in
   filesystem.

e. Race conditions, where somebody modifies a file while we're
   processing.  I propose not to modify the algorithm to handle this,
   but to detect when this could lead to inconsistencies.  (For
   example, when we decide on the dependencies based on cache
   metadata, and then we decide to re-parse a file because of a stale
   dependency, if the re-parsing leads to a different list of
   dependencies we should warn the user or start over.)

Steps
-----

1. For each explicitly given module find the source file location.

2. For each such module load and check the cache metadata, and decide
   whether it's valid.

3. Now recursively (or iteratively) find dependencies and add those to
   the graph:

   - for cached nodes use the list of dependencies from the cache
     metadata (this will be valid even if we later end up re-parsing
     the same source);

   - for uncached nodes parse the file and process all imports found,
     taking care of (a) above.

Step 3 should also address (d) above.

Once step 3 terminates we have the entire dependency graph, and for
each module we've either loaded the cache metadata or parsed the
source code.  (However, we may still need to parse those modules for
which we have cache metadata but that depend, directly or indirectly,
on at least one module for which the cache metadata is stale.)

Now we can execute steps A-C from the first section.  Finding SCCs for
step A shouldn't be hard; there's a recipe here:
http://code.activestate.com/recipes/578507/.  There's also a plethora
of topsort recipes, e.g. http://code.activestate.com/recipes/577413/.

For single nodes, processing is simple.  If the node was cached, we
deserialize the cache data and fix up cross-references.  Otherwise, we
do semantic analysis followed by type checking.  We also handle (c)
above; if a module has valid cache data *but* any of its
dependendencies was processed from source, then the module should be
processed from source.

A relatively simple optimization (outside SCCs) we might do in the
future is as follows: if a node's cache data is valid, but one or more
of its dependencies are out of date so we have to re-parse the node
from source, once we have fully type-checked the node, we can decide
whether its symbol table actually changed compared to the cache data
(by reading the cache data and comparing it to the data we would be
writing).  If there is no change we can declare the node up to date,
and any node that depends (and for which we have cached data, and
whose other dependencies are up to date) on it won't need to be
re-parsed from source.

Import cycles
-------------

Finally we have to decide how to handle (c), import cycles.  Here
we'll need a modified version of the original state machine
(build.py), but we only need to do this per SCC, and we won't have to
deal with changes to the list of nodes while we're processing it.

If all nodes in the SCC have valid cache metadata and all dependencies
outside the SCC are still valid, we can proceed as follows:

  1. Load cache data for all nodes in the SCC.

  2. Fix up cross-references for all nodes in the SCC.

Otherwise, the simplest (but potentially slow) way to proceed is to
invalidate all cache data in the SCC and re-parse all nodes in the SCC
from source.  We can do this as follows:

  1. Parse source for all nodes in the SCC.

  2. Semantic analysis for all nodes in the SCC.

  3. Type check all nodes in the SCC.

(If there are more passes the process is the same -- each pass should
be done for all nodes before starting the next pass for any nodes in
the SCC.)

We could process the nodes in the SCC in any order.  For sentimental
reasons, I've decided to process them in the reverse order in which we
encountered them when originally constructing the graph.  That's how
the old build.py deals with cycles, and at least this reproduces the
previous implementation more accurately.

Can we do better than re-parsing all nodes in the SCC when any of its
dependencies are out of date?  It's doubtful.  The optimization
mentioned at the end of the previous section would require re-parsing
and type-checking a node and then comparing its symbol table to the
cached data; but because the node is part of a cycle we can't
technically type-check it until the semantic analysis of all other
nodes in the cycle has completed.  (This is an important issue because
we have a cycle of over 500 modules in the server repo.  But I'd like
to deal with it later.)

Additional wrinkles
-------------------

During implementation more wrinkles were found.

- When a submodule of a package (e.g. x.y) is encountered, the parent
  package (e.g. x) must also be loaded, but it is not strictly a
  dependency.  See State.add_roots() below.
"""

import collections
import contextlib
import json
import os

from typing import Any, Dict, List, Set, AbstractSet, Tuple, Iterable, Iterator, Optional, TypeVar

from mypy.build import (BuildManager, BuildSource, CacheMeta,
                        TYPE_CHECK,
                        INCREMENTAL, FAST_PARSER, SILENT_IMPORTS,
                        DUMP_TYPE_STATS, DUMP_INFER_STATS,
                        find_module, read_with_python_encoding,
                        find_cache_meta, write_cache)
from mypy.errors import CompileError
from mypy.fixup import fixup_module_pass_one, fixup_module_pass_two
from mypy.nodes import MypyFile, SymbolTableNode, MODULE_REF
from mypy.parse import parse
from mypy.semanal import FirstPass
from mypy.stats import dump_type_stats


class ModuleNotFound(Exception):
    """Control flow exception to signal that a module was not found."""


class State:
    """The state for a module.

    It's a package if path ends in __init__.py[i].

    The source is only used for the -c command line option; in that
    case path is None.  Otherwise source is None and path isn't.
    """

    manager = None  # type: BuildManager
    order_counter = 0  # Class variable
    order = None  # type: int  # Order in which modules were encountered
    id = None  # type: str  # Fully qualified module name
    path = None  # type: Optional[str]  # Path to module source
    xpath = None  # type: str  # Path or '<string>'
    source = None  # type: Optional[str]  # Module source code
    meta = None  # type: Optional[CacheMeta]
    data = None  # type: Optional[str]
    tree = None  # type: Optional[MypyFile]
    dependencies = None  # type: List[str]
    dep_line_map = None  # tyoe: Dict[str, int]  # Line number where imported
    roots = None  # type: Optional[List[str]]
    import_context = None  # type: List[Tuple[str, int]]
    caller_state = None  # type: Optional[State]
    caller_line = 0

    def __init__(self,
                 id: Optional[str],
                 path: Optional[str],
                 source: Optional[str],
                 manager: BuildManager,
                 caller_state: 'State' = None,
                 caller_line: int = 0,
                 ) -> None:
        assert id or path or source is not None, "Neither id, path nor source given"
        self.manager = manager
        State.order_counter += 1
        self.order = State.order_counter
        self.caller_state = caller_state
        self.caller_line = caller_line
        if caller_state:
            self.import_context = caller_state.import_context[:]
            self.import_context.append((caller_state.xpath, caller_line))
        else:
            self.import_context = []
        self.id = id or '__main__'
        if not path and source is None:
            file_id = id
            if id == 'builtins' and manager.pyversion[0] == 2:
                # The __builtin__ module is called internally by mypy
                # 'builtins' in Python 2 mode (similar to Python 3),
                # but the stub file is __builtin__.pyi.  The reason is
                # that a lot of code hard-codes 'builtins.x' and it's
                # easier to work it around like this.  It also means
                # that the implementation can mostly ignore the
                # difference and just assume 'builtins' everywhere,
                # which simplifies code.
                file_id = '__builtin__'
            path = find_module(file_id, manager.lib_path)
            if not path:
                # Could not find a module.  Typically the reason is a
                # misspelled module name, missing stub, module not in
                # search path or the module has not been installed.
                # TODO: Copy the check for id == '' from build.py?
                if self.caller_state:
                    if not (SILENT_IMPORTS in manager.flags or
                            (caller_state.tree is not None and
                             (caller_line in caller_state.tree.ignored_lines or
                              'import' in caller_state.tree.weak_opts))):
                        save_import_context = manager.errors.import_context()
                        manager.errors.set_import_context(caller_state.import_context)
                        manager.module_not_found(caller_state.xpath, caller_line, id)
                        manager.errors.set_import_context(save_import_context)
                    manager.missing_modules.add(id)
                    raise ModuleNotFound
                else:
                    # If this is a root it's always fatal.
                    # TODO: This might hide non-fatal errors from
                    # roots processed earlier.
                    raise CompileError(["mypy: can't find module '%s'" % id])
        self.path = path
        self.xpath = path or '<string>'
        self.source = source
        if path and source is None and INCREMENTAL in manager.flags:
            self.meta = find_cache_meta(self.id, self.path, manager)
            # TODO: Get mtime if not cached.
        self.add_roots()
        if self.meta:
            self.dependencies = self.meta.dependencies
            self.dep_line_map = {}
        else:
            # Parse the file (and then some) to get the dependencies.
            self.parse_file()

    def add_roots(self) -> None:
        # All parent packages are new roots.
        # TODO: Use build.super_packages()?
        roots = []
        parent = self.id
        while '.' in parent:
            parent, _ = parent.rsplit('.', 1)
            roots.append(parent)
        self.roots = roots

    def is_fresh(self) -> bool:
        """Return whether the cache data for this file is fresh."""
        return self.meta is not None

    def clear_fresh(self) -> None:
        """Throw away the cache data for this file, marking it as stale."""
        self.meta = None

    def check_blockers(self) -> None:
        """Raise CompileError if a blocking error is detected."""
        if self.manager.errors.is_blockers():
            self.manager.log("Bailing due to blocking errors")
            self.manager.errors.raise_error()

    @contextlib.contextmanager
    def wrap_context(self) -> Iterator[None]:
        save_import_context = self.manager.errors.import_context()
        self.manager.errors.set_import_context(self.import_context)
        yield
        self.manager.errors.set_import_context(save_import_context)
        self.check_blockers()

    # Methods for processing cached modules.

    def load_tree(self) -> None:
        with open(self.meta.data_json) as f:
            data = json.load(f)
        # TODO: Assert data file wasn't changed.
        self.tree = MypyFile.deserialize(data)
        self.manager.modules[self.id] = self.tree

    def fix_cross_refs(self) -> None:
        fixup_module_pass_one(self.tree, self.manager.modules)

    def calculate_mros(self) -> None:
        fixup_module_pass_two(self.tree, self.manager.modules)

    # Methods for processing modules from source code.

    def parse_file(self) -> None:
        if self.tree is not None:
            # The file was already parsed (in __init__()).
            return

        manager = self.manager
        modules = manager.modules
        manager.log("Parsing %s" % self.xpath)

        with self.wrap_context():
            source = self.source
            self.source = None  # We won't need it again.
            if self.path and source is None:
                try:
                    source = read_with_python_encoding(self.path, manager.pyversion)
                except IOError as ioerr:
                    raise CompileError([
                        "mypy: can't read file '{}': {}".format(self.path, ioerr.strerror)])
                except UnicodeDecodeError as decodeerr:
                    raise CompileError([
                        "mypy: can't decode file '{}': {}".format(self.path, str(decodeerr))])
            self.tree = parse_file(self.id, self.xpath, source, manager)

        modules[self.id] = self.tree

        # Do the first pass of semantic analysis: add top-level
        # definitions in the file to the symbol table.  We must do
        # this before processing imports, since this may mark some
        # import statements as unreachable.
        first = FirstPass(manager.semantic_analyzer)
        first.analyze(self.tree, self.xpath, self.id)

        # Initialize module symbol table, which was populated by the
        # semantic analyzer.
        # TODO: Why can't FirstPass .analyze() do this?
        self.tree.names = manager.semantic_analyzer.globals

        # Compute (direct) dependencies.
        # Add all direct imports (this is why we needed the first pass).
        # Also keep track of each dependency's source line.
        dependencies = []
        dep_line_map = {}
        for id, line in manager.all_imported_modules_in_file(self.tree):
            # Omit missing modules, as otherwise we could not type-check
            # programs with missing modules.
            if id == self.id or id in manager.missing_modules:
                continue
            if id == '':
                # Must be from a relative import.
                manager.errors.set_file(self.xpath)
                manager.errors.report(line, "No parent module -- cannot perform relative import",
                                      blocker=True)
            if id not in dep_line_map:
                dependencies.append(id)
                dep_line_map[id] = line
        # Every module implicitly depends on builtins.
        if self.id != 'builtins' and 'builtins' not in dependencies:
            dependencies.append('builtins')

        # If self.dependencies is already set, it was read from the
        # cache, but for some reason we're re-parsing the file.
        # Double-check that the dependencies still match (otherwise
        # the graph is out of date).
        if self.dependencies is not None and dependencies != self.dependencies:
            # TODO: Make this into a reasonable error message.
            print("HELP!! Dependencies changed!")  # Probably the file was edited.
            print("  Cached:", self.dependencies)
            print("  Source:", dependencies)
        self.dependencies = dependencies
        self.dep_line_map = dep_line_map
        self.check_blockers()

    def patch_parent(self) -> None:
        # Include module in the symbol table of the enclosing package.
        assert '.' in self.id
        manager = self.manager
        modules = manager.modules
        parent, child = self.id.rsplit('.', 1)
        if parent in modules:
            manager.trace("Added %s.%s" % (parent, child))
            modules[parent].names[child] = SymbolTableNode(MODULE_REF, self.tree, parent)
        else:
            manager.log("Hm... couldn't add %s.%s" % (parent, child))

    def semantic_analysis(self) -> None:
        with self.wrap_context():
            self.manager.semantic_analyzer.visit_file(self.tree, self.xpath)

    def semantic_analysis_pass_three(self) -> None:
        with self.wrap_context():
            self.manager.semantic_analyzer_pass3.visit_file(self.tree, self.xpath)
            if DUMP_TYPE_STATS in self.manager.flags:
                dump_type_stats(self.tree, self.xpath)

    def type_check(self) -> None:
        manager = self.manager
        if manager.target < TYPE_CHECK:
            return
        with self.wrap_context():
            manager.type_checker.visit_file(self.tree, self.xpath)
            type_map = manager.type_checker.type_map
            if DUMP_INFER_STATS in manager.flags:
                dump_type_stats(self.tree, self.xpath, inferred=True, typemap=type_map)
            manager.reports.file(self.tree, type_map=type_map)

    def write_cache(self) -> None:
        if self.path and INCREMENTAL in self.manager.flags and not self.manager.errors.is_errors():
            write_cache(self.id, self.path, self.tree, list(self.dependencies), self.manager)


# TODO: This would make a nice method on BuildManager.
def parse_file(id: str, path: str, source: str, manager: BuildManager) -> MypyFile:
    """Parse the source of a file with the given name.

    Raise CompileError if there is a parse error.
    """
    errors = manager.errors
    num_errs = errors.num_messages()
    tree = parse(source, path, errors,
                 pyversion=manager.pyversion,
                 custom_typing_module=manager.custom_typing_module,
                 implicit_any=manager.implicit_any,
                 fast_parser=FAST_PARSER in manager.flags)
    tree._fullname = id
    if errors.num_messages() != num_errs:
        manager.log("Bailing due to parse errors")
        errors.raise_error()
    return tree


Graph = Dict[str, State]


def dispatch(sources: List[BuildSource], manager: BuildManager) -> None:
    manager.log("Using new dependency manager")
    graph = load_graph(sources, manager)
    manager.log("Loaded graph with %d nodes" % len(graph))
    process_graph(graph, manager)
    if manager.errors.is_errors():
        manager.log("Found %d errors (before de-duping)" % manager.errors.num_messages())
        manager.errors.raise_error()


def load_graph(sources: List[BuildSource], manager: BuildManager) -> Graph:
    """Given some source files, load the full dependency graph."""
    graph = {}  # type: Graph
    # The deque is used to implement breadth first traversal.
    new = collections.deque()  # type: collections.deque[State]
    # Seed graph with roots.
    for bs in sources:
        try:
            st = State(bs.module, bs.path, bs.text, manager)
        except ModuleNotFound:
            continue
        if st.id in graph:
            manager.errors.set_file(st.xpath)
            manager.errors.report(1, "Duplicate module named '%s'" % st.id)
            manager.errors.raise_error()
        graph[st.id] = st
        new.append(st)
    # Collect dependencies.  We go breadth-first.
    while new:
        st = new.popleft()
        for dep in st.roots + st.dependencies:
            if dep not in graph:
                try:
                    if dep in st.roots:
                        # Roots don't have import context.
                        newst = State(dep, None, None, manager)
                    else:
                        newst = State(dep, None, None, manager, st, st.dep_line_map.get(dep, 1))
                except ModuleNotFound:
                    if dep in st.dependencies:
                        st.dependencies.remove(dep)
                else:
                    assert newst.id not in graph, newst.id
                    graph[newst.id] = newst
                    new.append(newst)
    return graph


def process_graph(graph: Graph, manager: BuildManager) -> None:
    """Process everything in dependency order."""
    sccs = sorted_components(graph)
    manager.log("Found %d SCCs; largest has %d nodes" %
                (len(sccs), max(len(scc) for scc in sccs)))
    for ascc in sccs:
        # Sort the SCC's nodes in *reverse* order or encounter.
        # This is a heuristic for handling import cycles.
        # Note that ascc is a set, and scc is a list.
        scc = sorted(ascc, key=lambda id: -graph[id].order)
        # If builtins is in the list, move it last.
        if 'builtins' in ascc:
            scc.remove('builtins')
            scc.append('builtins')
        # TODO: Do something about mtime ordering.
        stale_scc = {id for id in scc if not graph[id].is_fresh()}
        fresh = not stale_scc
        deps = set()
        for id in scc:
            deps.update(graph[id].dependencies)
        deps -= ascc
        stale_deps = {id for id in deps if not graph[id].is_fresh()}
        fresh = fresh and not stale_deps
        if fresh:
            fresh_msg = "fresh"
        elif stale_scc:
            fresh_msg = "inherently stale (%s)" % " ".join(sorted(stale_scc))
            if stale_deps:
                fresh_msg += " with stale deps (%s)" % " ".join(sorted(stale_deps))
        else:
            fresh_msg = "stale due to deps (%s)" % " ".join(sorted(stale_deps))
        manager.log("Processing SCC of size %d (%s) as %s" %
                    (len(scc), " ".join(scc), fresh_msg))
        if fresh:
            process_fresh_scc(graph, scc)
        else:
            process_stale_scc(graph, scc)


def process_fresh_scc(graph: Graph, scc: List[str]) -> None:
    """Process the modules in one SCC from their cached data."""
    for id in scc:
        graph[id].load_tree()
    for id in scc:
        graph[id].fix_cross_refs()
    for id in scc:
        graph[id].calculate_mros()


def process_stale_scc(graph: Graph, scc: List[str]) -> None:
    """Process the modules in one SCC from source code."""
    for id in scc:
        graph[id].clear_fresh()
    for id in scc:
        # We may already have parsed the module, or not.
        # If the former, parse_file() is a no-op.
        graph[id].parse_file()
        # But we still need to patch a submodule into its parent package.
        if '.' in id:
            graph[id].patch_parent()
    for id in scc:
        graph[id].semantic_analysis()
    for id in scc:
        graph[id].semantic_analysis_pass_three()
    for id in scc:
        graph[id].type_check()
        graph[id].write_cache()


def sorted_components(graph: Graph) -> List[AbstractSet[str]]:
    """Return the graph's SCCs, topologically sorted by dependencies."""
    # Compute SCCs.
    vertices = set(graph)
    edges = {id: st.dependencies for id, st in graph.items()}
    sccs = list(strongly_connected_components_path(vertices, edges))
    # Topsort.
    sccsmap = {id: frozenset(scc) for scc in sccs for id in scc}
    data = {}  # type: Dict[AbstractSet[str], Set[AbstractSet[str]]]
    for scc in sccs:
        deps = set()  # type: Set[AbstractSet[str]]
        for id in scc:
            deps.update(sccsmap[x] for x in graph[id].dependencies)
        data[frozenset(scc)] = deps
    return list(topsort(data))


def strongly_connected_components_path(vertices: Set[str],
                                       edges: Dict[str, List[str]]) -> Iterator[Set[str]]:
    """Compute Strongly Connected Components of a graph.

    From http://code.activestate.com/recipes/578507/.
    """
    identified = set()  # type: Set[str]
    stack = []  # type: List[str]
    index = {}  # type: Dict[str, int]
    boundaries = []  # type: List[int]

    def dfs(v: str) -> Iterator[Set[str]]:
        index[v] = len(stack)
        stack.append(v)
        boundaries.append(index[v])

        for w in edges[v]:
            if w not in index:
                # For Python >= 3.3, replace with "yield from dfs(w)"
                for scc in dfs(w):
                    yield scc
            elif w not in identified:
                while index[w] < boundaries[-1]:
                    boundaries.pop()

        if boundaries[-1] == index[v]:
            boundaries.pop()
            scc = set(stack[index[v]:])
            del stack[index[v]:]
            identified.update(scc)
            yield scc

    for v in vertices:
        if v not in index:
            # For Python >= 3.3, replace with "yield from dfs(v)"
            for scc in dfs(v):
                yield scc


def topsort(data: Dict[AbstractSet[str], Set[AbstractSet[str]]]) -> Iterable[AbstractSet[str]]:
    """Topological sort.  Consumes its argument.

    From http://code.activestate.com/recipes/577413/.
    """
    # TODO: Use a faster algorithm?
    for k, v in data.items():
        v.discard(k)  # Ignore self dependencies.
    for item in set.union(*data.values()) - set(data.keys()):
        data[item] = set()
    while True:
        ready = {item for item, dep in data.items() if not dep}
        if not ready:
            break
        # TODO: Return the items in a reproducible order, or return
        # the entire set of items.
        for item in ready:
            yield item
        data = {item: (dep - ready)
                for item, dep in data.items()
                if item not in ready}
    assert not data, "A cyclic dependency exists amongst %r" % data
