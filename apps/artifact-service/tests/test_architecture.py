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
        "features/validate_template/validate.py": "from src.features.render_document.html import render_html\n",
        "features/compare_original/compare.py": "from ..render_document import render\n",
        "features/render_document/html.py": "from src.shared.browser import pool\n",
        "shared/browser/pool.py": "import src.features.render_document\n",
        "app/app.py": "from src.features.render_document import router\n",
    }
    for rel, code in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(code)

    flagged = {v.split(" imports ")[0] for v in boundary_violations(root)}

    assert flagged == {
        "src.features.validate_template.validate",
        "src.features.compare_original.compare",
        "src.shared.browser.pool",
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


_ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "api_route", "websocket"}


def route_handlers_outside_features(root: Path) -> list[str]:
    found = []
    for path in sorted(root.rglob("*.py")):
        if _feature_of(_module_name(path, root)) is not None:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                call = decorator.func if isinstance(decorator, ast.Call) else None
                if isinstance(call, ast.Attribute) and call.attr in _ROUTE_METHODS:
                    found.append(f"{path.relative_to(root.parent)}:{node.lineno}")
    return found


def test_route_handlers_live_in_features():
    assert route_handlers_outside_features(SRC) == []


def test_handler_check_allows_app_to_only_include_routers(tmp_path: Path):
    root = tmp_path / "src"
    files = {
        "features/render_document/router.py": (
            "router = APIRouter()\n\n\n@router.post('/render')\nasync def render(): ...\n"
        ),
        "app/routes.py": "router = APIRouter(prefix='/v1')\nrouter.include_router(render_router)\n",
        "app/extra.py": "router = APIRouter()\n\n\n@router.get('/x')\ndef x(): ...\n",
        "shared/api.py": "api = APIRouter()\n\n\n@api.post('/y')\nasync def y(): ...\n",
    }
    for rel, code in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(code)

    assert route_handlers_outside_features(root) == [
        "src/app/extra.py:5",
        "src/shared/api.py:5",
    ]
