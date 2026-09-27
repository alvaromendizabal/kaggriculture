"""Regression tests for the notebook stderr acceptance boundary."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from verify_terminal_notebook import (  # noqa: E402
    KNOWN_KAGGLE_ENGINE_STDERR,
    _allowed_stderr,
)


def test_known_kaggle_engine_warning_is_allowed() -> None:
    output = {"text": KNOWN_KAGGLE_ENGINE_STDERR + "\n"}
    assert _allowed_stderr(output)


def test_repeated_known_kaggle_engine_warning_is_allowed() -> None:
    output = {
        "text": [
            KNOWN_KAGGLE_ENGINE_STDERR + "\n",
            KNOWN_KAGGLE_ENGINE_STDERR + "\n",
        ]
    }
    assert _allowed_stderr(output)


def test_unknown_stderr_is_rejected() -> None:
    assert not _allowed_stderr({"text": "Traceback: unexpected failure\n"})


def test_empty_stderr_is_rejected() -> None:
    assert not _allowed_stderr({"text": ""})
