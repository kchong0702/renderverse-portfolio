import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

# Features never import each other; find_jobs runs analyse_job through its barrel
BARRELS = {"find_jobs": {"src.features.analyse_job"}}
LAYERS_WITHOUT_FEATURES = ("agents", "shared")


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
        "shared/tools/render.py": "import src.features.write_document\n",
        "agents/job_finder.py": "from src.features import find_jobs\n",
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
        "src.shared.tools.render",
        "src.agents.job_finder",
    }
