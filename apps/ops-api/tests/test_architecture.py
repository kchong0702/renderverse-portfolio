import ast
from pathlib import Path

SRC = Path(__file__).parent.parent / "src"

_HARNESS_CALLERS = {
    "src/core/agent_runner.py",
    "src/clients/ezcareer",
    "src/app/container.py",
}
"""Where EzcareerClient may be named: the runner, its own package and the container
that builds it"""


def _imports(path: Path) -> set[str]:
    """Every name the module imports, qualified by its module"""
    names = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            names |= {f"{node.module}.{alias.name}" for alias in node.names}
    return names


def _names(path: Path) -> set[str]:
    """Every name the module imports, qualified by its module, every name and
    attribute its code uses and every string literal"""
    names = _imports(path)
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.add(node.value)
    return names


def _classes(root: Path) -> list[ast.ClassDef]:
    """Every class defined under the directory"""
    return [
        node
        for path in root.rglob("*.py")
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.ClassDef)
    ]


def _methods(cls: ast.ClassDef) -> set[str]:
    """The class's public method names"""
    return {
        node.name
        for node in cls.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    }


def test_the_jobs_feature_knows_no_job_source_by_name():
    offenders = {
        f"{path.relative_to(SRC.parent)}: {name}"
        for path in (SRC / "features" / "jobs").rglob("*.py")
        for name in _names(path)
        if "jsearch" in name.casefold()
    }

    assert offenders == set(), f"jobs modules naming JSearch: {sorted(offenders)}"


def test_adapters_import_no_feature():
    offenders = {
        f"{path.relative_to(SRC.parent)}: {name}"
        for path in (SRC / "adapters").rglob("*.py")
        for name in _imports(path)
        if name.startswith("src.features.")
    }

    assert offenders == set(), f"adapters importing features: {sorted(offenders)}"


def test_clients_implement_no_adapter_interface():
    interfaces = {
        cls.name: _methods(cls)
        for cls in _classes(SRC / "adapters")
        if any(getattr(base, "id", None) in {"ABC", "Protocol"} for base in cls.bases)
    }
    offenders = {
        f"{cls.name} implements {name}"
        for cls in _classes(SRC / "clients")
        for name, methods in interfaces.items()
        if methods <= _methods(cls)
        or name in {getattr(base, "id", None) for base in cls.bases}
    }

    assert offenders == set(), f"adapters in src/clients: {sorted(offenders)}"


def test_only_the_agent_runner_talks_to_the_harness():
    offenders = [
        str(path.relative_to(SRC.parent))
        for path in SRC.rglob("*.py")
        if not str(path.relative_to(SRC.parent)).startswith(tuple(_HARNESS_CALLERS))
        and any(name.endswith(".EzcareerClient") for name in _imports(path))
    ]

    assert offenders == [], f"modules importing EzcareerClient: {offenders}"
