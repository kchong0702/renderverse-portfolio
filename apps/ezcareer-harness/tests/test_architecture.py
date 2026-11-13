import ast
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

# Features never import each other; find_jobs runs analyse_job through its barrel
BARRELS = {"find_jobs": {"src.features.analyse_job"}}
LAYERS_WITHOUT_FEATURES = ("agents", "clients", "shared", "tools")


def _module_name(path: Path, root: Path) -> str:
    parts = path.relative_to(root.parent).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imports(path: Path, root: Path) -> set[str]:
    module = _module_name(path, root)
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = (
                    package.rsplit(".", node.level - 1)[0]
                    if node.level > 1
                    else package
                )
                base = f"{anchor}.{base}" if base else anchor
            found.add(base)
            # `from pkg import x` reaches a submodule only when x is one on disk;
            # otherwise it is a name the package itself exports
            found.update(
                f"{base}.{alias.name}"
                for alias in node.names
                if _is_module(f"{base}.{alias.name}", root)
            )
    return found


def _is_module(name: str, root: Path) -> bool:
    path = root.parent.joinpath(*name.split("."))
    return path.is_dir() or path.with_suffix(".py").is_file()


def _feature_of(name: str) -> str | None:
    parts = name.split(".")
    return parts[2] if len(parts) > 2 and parts[:2] == ["src", "features"] else None


def boundary_violations(root: Path) -> list[str]:
    violations = []
    for path in sorted(root.rglob("*.py")):
        module = _module_name(path, root)
        owner = _feature_of(module)
        layer = module.split(".")[1] if "." in module else ""
        for name in _imports(path, root):
            target = _feature_of(name)
            if target is None:
                continue
            crosses_feature = (
                owner and target != owner and name not in BARRELS.get(owner, set())
            )
            if layer in LAYERS_WITHOUT_FEATURES or crosses_feature:
                violations.append(f"{module} imports {name}")
    return violations


def test_source_respects_feature_boundaries():
    assert boundary_violations(SRC) == []


def test_boundary_check_catches_cross_feature_imports(tmp_path: Path):
    root = tmp_path / "src"
    files = {
        "features/write_document/nodes/emit.py": "from src.features.generate_template.checks import verbatim\n",
        "features/find_jobs/graph.py": "from src.features.analyse_job import build_graph\n",
        "features/find_jobs/nodes/rate.py": "from src.features.analyse_job.nodes import rate\n",
        "features/find_jobs/nodes/fetch.py": "from src.features.analyse_job import nodes\n",
        "features/analyse_job/nodes/rate.py": "",
        "features/analyse_job/graph.py": "from ..find_jobs import graph\n",
        "tools/render.py": "import src.features.write_document\n",
        "shared/jobs/types.py": "from src.features.find_jobs.schemas import JobPosting\n",
        "agents/job_analyst.py": "from src.features import find_jobs\n",
        "app/container.py": "from src.features.find_jobs import graph\n",
    }
    for rel, code in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(code)

    flagged = {v.split(" imports ")[0] for v in boundary_violations(root)}

    assert flagged == {
        "src.features.write_document.nodes.emit",
        "src.features.find_jobs.nodes.rate",
        "src.features.find_jobs.nodes.fetch",
        "src.features.analyse_job.graph",
        "src.tools.render",
        "src.shared.jobs.types",
        "src.agents.job_analyst",
    }


def init_logic(root: Path) -> list[str]:
    found = []
    for path in sorted(root.rglob("__init__.py")):
        for node in ast.parse(path.read_text()).body:
            reexport = isinstance(node, (ast.Import, ast.ImportFrom)) or (
                isinstance(node, ast.Assign)
                and [getattr(t, "id", None) for t in node.targets] == ["__all__"]
            )
            if not reexport:
                found.append(f"{path.relative_to(root.parent)}:{node.lineno}")
    return found


def test_package_inits_only_reexport():
    assert init_logic(SRC) == []


def test_init_check_catches_logic(tmp_path: Path):
    root = tmp_path / "src"
    files = {
        "shared/browser/__init__.py": "from .browser import Browser\n\n__all__ = ['Browser']\n",
        "shared/pool/__init__.py": "import asyncio\n\n\nclass Pool:\n    pass\n",
        "core/__init__.py": "SIZE = 4\n",
    }
    for rel, code in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(code)

    assert init_logic(root) == [
        "src/core/__init__.py:1",
        "src/shared/pool/__init__.py:4",
    ]


def feature_tools(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root.parent))
        for path in root.glob("features/*/tools")
        if any(path.glob("*.py"))
    )


def test_workflows_own_no_tools():
    assert feature_tools(SRC) == []


def test_tools_check_catches_a_features_tools(tmp_path: Path):
    root = tmp_path / "src"
    for folder in (
        "find_jobs/tools",
        "find_jobs/nodes",
        "analyse_job/tools/__pycache__",
    ):
        (root / "features" / folder).mkdir(parents=True)
    (root / "features/find_jobs/tools/__init__.py").write_text("")

    assert feature_tools(root) == ["src/features/find_jobs/tools"]


def misnamed_agents(root: Path) -> list[str]:
    return sorted(
        str(prompt.relative_to(root.parent))
        for prompt in root.glob("agents/*/system.md")
        if not re.match(
            rf"You are {prompt.parent.name.replace('_', '-')}[.,]", prompt.read_text()
        )
    )


def test_each_agent_prompt_names_its_own_agent():
    assert misnamed_agents(SRC) == []


def test_name_check_catches_a_prompt_naming_another_agent(tmp_path: Path):
    root = tmp_path / "src"
    for name, opening in (
        ("job_analyst", "You are job-analyst. You read jobs."),
        ("document_analyst", "You are a career consultant. You read files."),
    ):
        (root / "agents" / name).mkdir(parents=True)
        (root / "agents" / name / "system.md").write_text(opening)

    assert misnamed_agents(root) == ["src/agents/document_analyst/system.md"]
