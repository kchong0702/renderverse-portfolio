import pytest

from src.core.config import get_settings
from src.features.import_document.configurations import ImportResumeConfigurations


@pytest.fixture
def configurations() -> ImportResumeConfigurations:
    """The import-resume graph profile's configurations"""
    return (
        get_settings().graph_profile("import-resume").load(ImportResumeConfigurations)
    )
