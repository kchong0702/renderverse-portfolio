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
    """Every name the module imports, qualified by its module, and every name and
    attribute its code uses"""
    names = _imports(path)
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def test_the_jobs_feature_knows_no_job_source_by_name():
    offenders = {
        f"{path.relative_to(SRC.parent)}: {name}"
        for path in (SRC / "features" / "jobs").rglob("*.py")
        for name in _names(path)
        if "jsearch" in name.casefold()
    }

    assert offenders == set(), f"jobs modules naming JSearch: {sorted(offenders)}"


def test_only_the_agent_runner_talks_to_the_harness():
    offenders = [
        str(path.relative_to(SRC.parent))
        for path in SRC.rglob("*.py")
        if not str(path.relative_to(SRC.parent)).startswith(tuple(_HARNESS_CALLERS))
        and any(name.endswith(".EzcareerClient") for name in _imports(path))
    ]

    assert offenders == [], f"modules importing EzcareerClient: {offenders}"
