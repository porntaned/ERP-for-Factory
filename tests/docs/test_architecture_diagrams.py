"""docs/ARCHITECTURE.md matches the code (M7.3, Issue #123).

No database: the truth comes from `apps.get_models()`, `_meta`, `admin.site._registry` and `ast`
over the app sources. The rules are in docs/assignments/m73-architecture-diagrams.md.

Each checked Mermaid block in the document is preceded on its own line by
`<!-- architecture-check: NAME -->`. The helpers below turn the document text into what it
claims and the code into what is true; the tests compare them with exact set equality and
report what is missing from the document and what is extra. The mutation tests at the end run
the same comparisons on edited copies of the real document; the real file is never changed.
"""

import ast
import re
from functools import cache
from importlib import import_module
from pathlib import Path
from types import ModuleType

import pytest
from django.apps import apps
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import models

from config.readonly_admin import ReadOnlyAdmin
from manufacturing.models import OrderStatus
from quality.models import LotDisposition

ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = ROOT / "docs" / "ARCHITECTURE.md"

MARKERS = {
    "modules",
    "app-dependencies",
    "domain-er",
    "production-order-states",
    "lot-disposition-states",
    "stock-flow",
}
STATE_DIAGRAMS = {
    "production-order-states": OrderStatus,
    "lot-disposition-states": LotDisposition,
}
ADMIN_SECTION = "## Read-only admin coverage"


class DiagramSyntaxError(ValueError):
    """The document breaks a rule of the checked format (marker, fence or line syntax)."""


# ---------------------------------------------------------------- what the code says


@cache
def project_apps() -> dict[str, str]:
    """Top-level module name -> app label, for the INSTALLED_APPS that live in this repository."""
    return {
        config.name.partition(".")[0]: config.label
        for config in apps.get_app_configs()
        if Path(config.path).parent == ROOT
    }


def project_models() -> list[type[models.Model]]:
    labels = set(project_apps().values())
    return [model for model in apps.get_models() if model._meta.app_label in labels]


def user_model_name() -> str:
    return get_user_model()._meta.object_name


@cache
def code_entities() -> dict[str, str]:
    """Model name -> app label for every project model except AUTH_USER_MODEL."""
    user = get_user_model()
    entities: dict[str, str] = {}
    for model in project_models():
        if model is user:
            continue
        name = model._meta.object_name
        assert name not in entities, f"two project models are named {name}; the ER cannot tell"
        entities[name] = model._meta.app_label
    return entities


def cardinality(field: models.ForeignKey) -> str:
    """Mermaid notation, source side first: FK `}o--||`, O2O `|o--||`; `o|` when null=True."""
    source = "|o" if field.one_to_one else "}o"
    target = "o|" if field.null else "||"
    return f"{source}--{target}"


@cache
def code_er_edges() -> dict[tuple[str, str, str], str]:
    """(source model, target model, field name) -> cardinality, User edges excluded."""
    user = get_user_model()
    edges: dict[tuple[str, str, str], str] = {}
    for model in project_models():
        for field in model._meta.get_fields():
            if isinstance(field, models.ManyToManyField):
                raise AssertionError(
                    f"{model._meta.label}.{field.name} is a ManyToManyField; "
                    "the ER notation for it is not defined (M7.3 spec)"
                )
            if not (field.concrete and isinstance(field, models.ForeignKey)):
                continue
            if field.related_model is user:
                continue
            key = (model._meta.object_name, field.related_model._meta.object_name, field.name)
            edges[key] = cardinality(field)
    return edges


def app_imports(source: str, own_module: str, project_modules: set[str]) -> set[str]:
    """Project apps that `source` imports absolutely, anywhere in its AST (functions included).

    Not counted: relative imports, the own app, and anything outside `project_modules`
    (Django, the standard library, other packages, `config`).
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        for name in names:
            top = name.partition(".")[0]
            if top in project_modules and top != own_module:
                found.add(top)
    return found


@cache
def code_app_dependencies() -> set[tuple[str, str]]:
    """(importing app, imported app) over every app .py file outside migrations/ and tests/."""
    modules = project_apps()
    edges: set[tuple[str, str]] = set()
    for module, label in modules.items():
        app_dir = ROOT / module
        for path in sorted(app_dir.rglob("*.py")):
            parts = path.relative_to(app_dir).parts
            if "migrations" in parts or "tests" in parts:
                continue
            source = path.read_text(encoding="utf-8")
            for target in app_imports(source, module, set(modules)):
                edges.add((label, modules[target]))
    return edges


def code_admin_apps() -> set[str]:
    labels = set(project_apps().values())
    return {
        model._meta.app_label for model in admin.site._registry if model._meta.app_label in labels
    }


def code_admin_coverage() -> dict[str, tuple[int, int, frozenset[str]]]:
    """App label -> (registered, total, names not registered), for apps that have models."""
    coverage: dict[str, tuple[int, int, frozenset[str]]] = {}
    for label in sorted(set(project_apps().values())):
        names = {m._meta.object_name for m in apps.get_app_config(label).get_models()}
        if not names:
            continue
        registered = {
            m._meta.object_name for m in admin.site._registry if m._meta.app_label == label
        }
        coverage[label] = (len(registered), len(names), frozenset(names - registered))
    return coverage


_MISSING = object()


def resolve(reference: str) -> object:
    """Import the longest module prefix of a dotted name, then follow attributes."""
    parts = reference.split(".")
    for cut in range(len(parts), 0, -1):
        name = ".".join(parts[:cut])
        try:
            target: object = import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name == name or (exc.name and name.startswith(exc.name + ".")):
                continue
            raise
        for attribute in parts[cut:]:
            target = getattr(target, attribute, _MISSING)
            if target is _MISSING:
                return _MISSING
        return target
    return _MISSING


# ---------------------------------------------------------------- what the document says

BLOCK = re.compile(r"^<!-- architecture-check: ([\w-]+) -->\n```mermaid\n(.*?)\n```$", re.M | re.S)
MARKER = re.compile(r"^<!-- architecture-check: ([\w-]+) -->$", re.M)


def diagram_blocks(text: str) -> dict[str, list[str]]:
    """Marker name -> the lines of the ```mermaid block that follows the marker."""
    blocks: dict[str, list[str]] = {}
    for match in BLOCK.finditer(text):
        if match[1] in blocks:
            raise DiagramSyntaxError(f"marker {match[1]!r} appears twice")
        blocks[match[1]] = match[2].splitlines()
    unfenced = sorted(set(MARKER.findall(text)) - set(blocks))
    if unfenced:
        raise DiagramSyntaxError(f"markers not followed by a ```mermaid block: {unfenced}")
    return blocks


def block(text: str, name: str) -> list[str]:
    blocks = diagram_blocks(text)
    if name not in blocks:
        raise DiagramSyntaxError(f"no checked block {name!r}")
    return blocks[name]


def statements(lines: list[str]) -> list[tuple[int, str]]:
    """(line number in the block, stripped text), without blank lines and %% comments."""
    return [
        (number, line.strip())
        for number, line in enumerate(lines, 1)
        if line.strip() and not line.strip().startswith("%%")
    ]


ER_APP = re.compile(r"^%%\s*app:\s*(\w+)\s*$")
ER_EDGE = re.compile(r'^(\w+)\s+([|}][o|](?:--|\.\.)[o|][|{])\s+(\w+)\s*:\s*"?([^"]+?)"?$')
ER_ENTITY = re.compile(r"^(\w+)$")


def parse_er(lines: list[str]) -> tuple[dict[str, str], dict[tuple[str, str, str], str]]:
    """(entity -> app label from the `%% app:` line above it, edge -> cardinality)."""
    entities: dict[str, str] = {}
    edges: dict[tuple[str, str, str], str] = {}
    app: str | None = None
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if match := ER_APP.match(line):
            app = match[1]
            continue
        if not line or line.startswith("%%") or (number == 1 and line == "erDiagram"):
            continue
        if match := ER_EDGE.match(line):
            key = (match[1], match[3], match[4])
            if key in edges:
                raise DiagramSyntaxError(f"domain-er line {number}: edge {key} twice")
            edges[key] = match[2]
        elif match := ER_ENTITY.match(line):
            if app is None:
                raise DiagramSyntaxError(f"domain-er line {number}: {line} is under no %% app:")
            if line in entities:
                raise DiagramSyntaxError(f"domain-er line {number}: entity {line} twice")
            entities[line] = app
        else:
            raise DiagramSyntaxError(f"domain-er line {number} not understood: {raw!r}")
    return entities, edges


FLOW_OTHER = re.compile(
    r"^(?:(?:flowchart|graph)\s+\w+|subgraph\b.*|end|direction\s+\w+"
    r"|(?:classDef|class|style|linkStyle)\s.*)$"
)
FLOW_EDGE = re.compile(r"^(\w+)\s*(?:-->|-\.->|==>)\s*(?:\|[^|]*\|\s*)?(\w+)$")
FLOW_NODE = re.compile(r"^\w+\s*(?:\[.*\]|\(.*\)|\{.*\})?$")


def parse_flowchart(name: str, lines: list[str]) -> tuple[set[str], set[tuple[str, str]]]:
    """(node ids, edges) of a flowchart; one statement per line, edges between bare ids."""
    nodes: set[str] = set()
    edges: set[tuple[str, str]] = set()
    for number, line in statements(lines):
        if FLOW_OTHER.match(line):
            continue
        if match := FLOW_EDGE.match(line):
            edges.add((match[1], match[2]))
            nodes.update((match[1], match[2]))
        elif FLOW_NODE.match(line):
            nodes.add(re.match(r"\w+", line)[0])
        else:
            raise DiagramSyntaxError(f"{name} line {number} not understood: {line!r}")
    return nodes, edges


STATE_EDGE = re.compile(r"^(\[\*\]|\w+)\s*-->\s*(\[\*\]|\w+)\s*(?::\s*(.*))?$")


def parse_states(name: str, lines: list[str]) -> list[tuple[str, str, str]]:
    """Transitions (source, target, label) of a stateDiagram-v2."""
    transitions: list[tuple[str, str, str]] = []
    for number, line in statements(lines):
        if line == "stateDiagram-v2" or line.startswith("direction "):
            continue
        match = STATE_EDGE.match(line)
        if match is None:
            raise DiagramSyntaxError(f"{name} line {number} not understood: {line!r}")
        transitions.append((match[1], match[2], match[3] or ""))
    return transitions


def doc_states(text: str, name: str) -> set[str]:
    return {
        state
        for source, target, _ in parse_states(name, block(text, name))
        for state in (source, target)
        if state != "[*]"
    }


FUNCTIONS = re.compile(r"^%%\s*functions:\s*(.+)$")
SNAKE_CASE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


def admin_table(text: str) -> dict[str, tuple[int, int, frozenset[str]]]:
    """Rows of the table in the read-only admin coverage section."""
    start = text.find(f"\n{ADMIN_SECTION}\n")
    if start < 0:
        raise DiagramSyntaxError(f"no section {ADMIN_SECTION!r}")
    section = text[start + 1 :]
    end = section.find("\n## ", 1)
    section = section if end < 0 else section[:end]
    row = re.compile(r"^\|\s*`(\w+)`\s*\|\s*(\d+)\s*/\s*(\d+)\s*\|(.*)\|\s*$", re.M)
    table: dict[str, tuple[int, int, frozenset[str]]] = {}
    for match in row.finditer(section):
        if match[1] in table:
            raise DiagramSyntaxError(f"admin coverage: app {match[1]} twice")
        missing = frozenset(re.findall(r"`(\w+)`", match[4]))
        table[match[1]] = (int(match[2]), int(match[3]), missing)
    return table


BACKTICKED = re.compile(r"`([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)`")


# ---------------------------------------------------------------- comparisons


def set_problems(what: str, claimed: set, actual: set) -> list[str]:
    problems = []
    if missing := sorted(actual - claimed):
        problems.append(f"{what} missing from the doc: {', '.join(map(str, missing))}")
    if extra := sorted(claimed - actual):
        problems.append(f"{what} in the doc but not in the code: {', '.join(map(str, extra))}")
    return problems


def er_entity_problems(text: str) -> list[str]:
    entities, _ = parse_er(block(text, "domain-er"))
    claimed = set(entities) - {user_model_name()}
    return set_problems("domain-er: entities", claimed, set(code_entities()))


def er_grouping_problems(text: str) -> list[str]:
    entities, _ = parse_er(block(text, "domain-er"))
    truth = code_entities()
    return [
        f"domain-er: {name} is under %% app: {app}, the code has it in {truth[name]}"
        for name, app in sorted(entities.items())
        if name in truth and truth[name] != app
    ]


def er_edge_problems(text: str) -> list[str]:
    entities, edges = parse_er(block(text, "domain-er"))
    user = user_model_name()
    problems: list[str] = []
    if undeclared := sorted({n for key in edges for n in key[:2]} - set(entities)):
        problems.append(f"domain-er: entities used in edges but not declared: {undeclared}")
    claimed = {key: notation for key, notation in edges.items() if user not in key[:2]}
    truth = code_er_edges()
    problems += set_problems("domain-er: edges", set(claimed), set(truth))
    problems += [
        f"domain-er: cardinality of {key}: doc {claimed[key]}, code {truth[key]}"
        for key in sorted(set(claimed) & set(truth))
        if claimed[key] != truth[key]
    ]
    return problems


def app_dependency_problems(text: str) -> list[str]:
    nodes, edges = parse_flowchart("app-dependencies", block(text, "app-dependencies"))
    return set_problems(
        "app-dependencies: nodes", nodes, set(project_apps().values())
    ) + set_problems("app-dependencies: edges", edges, code_app_dependencies())


def admin_node_problems(text: str) -> list[str]:
    _, edges = parse_flowchart("modules", block(text, "modules"))
    claimed = {target for source, target in edges if source == "admin"}
    return set_problems("modules: apps the admin node points to", claimed, code_admin_apps())


def admin_table_problems(text: str) -> list[str]:
    claimed, truth = admin_table(text), code_admin_coverage()
    problems = set_problems("admin coverage: apps", set(claimed), set(truth))
    for label in sorted(set(claimed) & set(truth)):
        if claimed[label] != truth[label]:
            registered, total, missing = truth[label]
            problems.append(
                f"admin coverage: {label} row says {claimed[label][0]}/{claimed[label][1]} "
                f"not registered {sorted(claimed[label][2])}; the code has {registered}/{total} "
                f"not registered {sorted(missing)}"
            )
    return problems


def state_problems(text: str, name: str) -> list[str]:
    choices = STATE_DIAGRAMS[name]
    return set_problems(f"{name}: states", doc_states(text, name), set(choices.values))


def function_problems(text: str, name: str) -> list[str]:
    """Every snake_case name in the block is a callable of a module on its `%% functions:` line.

    In a state diagram every transition label must name at least one such function.
    """
    lines = block(text, name)
    module_names = [
        module
        for line in lines
        if (match := FUNCTIONS.match(line.strip()))
        for module in match[1].replace(",", " ").split()
    ]
    if not module_names:
        return [f"{name}: no '%% functions:' line"]
    modules: list[ModuleType] = [import_module(module) for module in module_names]
    problems: list[str] = []
    named: set[str] = set()
    for number, line in statements(lines):
        for function in SNAKE_CASE.findall(line):
            named.add(function)
            if not any(callable(getattr(module, function, None)) for module in modules):
                problems.append(f"{name} line {number}: {function} is not in {module_names}")
    if not named:
        problems.append(f"{name}: names no function")
    if name in STATE_DIAGRAMS:
        for source, target, label in parse_states(name, lines):
            if not SNAKE_CASE.search(label):
                problems.append(f"{name}: {source} --> {target} names no function")
    return problems


def reference_problems(text: str) -> list[str]:
    roots = set(project_apps()) | {"config"}
    return [
        f"`{reference}` does not resolve"
        for reference in sorted(set(BACKTICKED.findall(text)))
        if reference.partition(".")[0] in roots and resolve(reference) is _MISSING
    ]


def report(problems: list[str]) -> str:
    return "docs/ARCHITECTURE.md differs from the code:\n" + "\n".join(problems)


# ---------------------------------------------------------------- the real document


@cache
def _read_doc() -> str | None:
    return DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else None


def real_doc() -> str:
    text = _read_doc()
    if text is None:
        pytest.fail(f"{DOC_PATH.relative_to(ROOT)} does not exist", pytrace=False)
    return text


def test_every_checked_diagram_has_its_marker_and_mermaid_block():
    doc = real_doc()
    assert set(diagram_blocks(doc)) == MARKERS


def test_er_entities_equal_the_domain_models():
    doc = real_doc()
    assert not (problems := er_entity_problems(doc)), report(problems)


def test_er_entities_sit_under_their_app():
    doc = real_doc()
    assert not (problems := er_grouping_problems(doc)), report(problems)


def test_er_edges_and_cardinality_equal_the_relation_fields():
    doc = real_doc()
    assert not (problems := er_edge_problems(doc)), report(problems)


def test_app_dependency_edges_equal_the_imports():
    doc = real_doc()
    assert not (problems := app_dependency_problems(doc)), report(problems)


def test_admin_node_points_to_the_apps_in_the_admin_registry():
    doc = real_doc()
    assert not (problems := admin_node_problems(doc)), report(problems)


def test_admin_coverage_table_equals_the_admin_registry():
    doc = real_doc()
    assert not (problems := admin_table_problems(doc)), report(problems)


def test_every_project_model_in_the_admin_uses_read_only_admin():
    labels = set(project_apps().values())
    wrong = sorted(
        f"{model._meta.label}: {type(model_admin).__name__}"
        for model, model_admin in admin.site._registry.items()
        if model._meta.app_label in labels and type(model_admin) is not ReadOnlyAdmin
    )
    assert wrong == []


@pytest.mark.parametrize("name", sorted(STATE_DIAGRAMS))
def test_states_equal_the_choices(name):
    doc = real_doc()
    assert not (problems := state_problems(doc, name)), report(problems)


@pytest.mark.parametrize("name", [*sorted(STATE_DIAGRAMS), "stock-flow"])
def test_every_function_named_in_a_flow_exists(name):
    doc = real_doc()
    assert not (problems := function_problems(doc, name)), report(problems)


def test_every_backticked_project_reference_resolves():
    doc = real_doc()
    assert not (problems := reference_problems(doc)), report(problems)


def test_import_rule_counts_function_level_imports_only_across_project_apps():
    source = (
        "import os\n"
        "from django.db import models\n"
        "from config.readonly_admin import ReadOnlyAdmin\n"
        "from .models import Lot\n"
        "from quality.services import get_lot_disposition\n"
        "import inventory.models\n"
        "def later():\n"
        "    from catalog.models import Item\n"
    )
    project = {"quality", "inventory", "catalog"}
    assert app_imports(source, "inventory", project) == {"quality", "catalog"}


# ---------------------------------------------------------------- mutations of the real document


def edit(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"{old!r} occurs {text.count(old)} times in the document"
    return text.replace(old, new)


MUTATIONS = {
    "missing-er-entity": (
        er_entity_problems,
        "    RequestKey\n",
        "",
        ["domain-er: entities missing from the doc: RequestKey"],
    ),
    "extra-er-entity": (
        er_entity_problems,
        "    %% app: inventory\n",
        "    %% app: inventory\n    Invoice\n",
        ["domain-er: entities in the doc but not in the code: Invoice"],
    ),
    "missing-er-edge": (
        er_edge_problems,
        '    StockReceipt |o--|| StockLedgerEntry : "ledger_entry"\n',
        "",
        [
            "domain-er: edges missing from the doc: "
            "('StockReceipt', 'StockLedgerEntry', 'ledger_entry')"
        ],
    ),
    "extra-app-dependency": (
        app_dependency_problems,
        "    catalog --> facilities\n",
        "    catalog --> facilities\n    catalog --> inventory\n",
        ["app-dependencies: edges in the doc but not in the code: ('catalog', 'inventory')"],
    ),
    "wrong-cardinality": (
        er_edge_problems,
        '    StockReversal |o--o| StockReceipt : "receipt"\n',
        '    StockReversal |o--|| StockReceipt : "receipt"\n',
        [
            "domain-er: cardinality of ('StockReversal', 'StockReceipt', 'receipt'): "
            "doc |o--||, code |o--o|"
        ],
    ),
    "extra-state": (
        lambda text: state_problems(text, "production-order-states"),
        "    OPEN --> CLOSED : close_production_order\n",
        "    OPEN --> CLOSED : close_production_order\n"
        "    CLOSED --> REOPENED : close_production_order\n",
        ["production-order-states: states in the doc but not in the code: REOPENED"],
    ),
}


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_comparison_reports_a_mutated_document(mutation):
    doc = real_doc()
    compare, old, new, expected = MUTATIONS[mutation]
    assert compare(doc) == [], "the real document must pass before it is mutated"
    assert compare(edit(doc, old, new)) == expected
