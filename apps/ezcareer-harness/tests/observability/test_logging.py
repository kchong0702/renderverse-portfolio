import io
import json
import logging

import pytest
import structlog

from src.infrastructure.observability import logging as obs_logging


@pytest.fixture
def json_logs(make_settings):
    """Configure JSON logging into a private buffer, restoring global logging after"""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    buffer = io.StringIO()

    obs_logging.configure_logging(make_settings(log_format="json"), force=True)
    root.handlers[-1].setStream(buffer)

    yield buffer

    root.handlers[:] = handlers
    root.setLevel(level)
    obs_logging._configured = False
    structlog.reset_defaults()


def test_long_fields_truncated_but_tracebacks_kept(json_logs):
    logger = obs_logging.get_logger("test")
    try:
        raise ValueError("boom " + "y" * 1000)
    except ValueError:
        logger.exception("failed", payload="x" * 1001, short="ok")

    line = json.loads(json_logs.getvalue().strip().splitlines()[-1])

    assert line["payload"] == "<TRUNCATED_LARGE_STRING | len: 1001>"
    assert line["short"] == "ok"
    assert "ValueError: boom yyy" in line["exception"]
    assert len(line["exception"]) > 1000
