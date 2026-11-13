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


def test_only_the_agent_runner_talks_to_the_harness():
    offenders = [
        str(path.relative_to(SRC.parent))
        for path in SRC.rglob("*.py")
        if not str(path.relative_to(SRC.parent)).startswith(tuple(_HARNESS_CALLERS))
        and any(name.endswith(".EzcareerClient") for name in _imports(path))
    ]

    assert offenders == [], f"modules importing EzcareerClient: {offenders}"
