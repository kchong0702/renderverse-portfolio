import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

BARRELS: dict[str, set[str]] = {}
LAYERS_WITHOUT_FEATURES = ("shared",)


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
        "features/measure_document/measure.py": "from src.features.render_document.render import render\n",
        "features/compare_original/compare.py": "from ..render_document import render\n",
        "features/render_document/render.py": "from src.shared.browser import pool\n",
        "shared/browser/pool.py": "import src.features.render_document\n",
        "app/routes.py": "from src.features.render_document import router\n",
    }
    for rel, code in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(code)

    flagged = {v.split(" imports ")[0] for v in boundary_violations(root)}

    assert flagged == {
        "src.features.measure_document.measure",
        "src.features.compare_original.compare",
        "src.shared.browser.pool",
    }
