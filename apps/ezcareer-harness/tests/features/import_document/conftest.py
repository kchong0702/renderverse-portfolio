from pathlib import Path

import pytest

from src.features.import_document import ImportConfig

HARNESS = Path(__file__).parents[3] / "src/features/import_document/harness"


@pytest.fixture
def config(tmp_path: Path) -> ImportConfig:
    """The bundled harness, with a classic template spec in a temporary folder"""
    (tmp_path / "classic.yaml").write_text("id: classic\nkinds: [resume, cv]\n")
    return ImportConfig.load(HARNESS).model_copy(update={"templates": tmp_path})
