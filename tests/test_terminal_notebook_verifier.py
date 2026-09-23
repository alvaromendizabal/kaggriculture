"""Regression tests for notebook stderr classification."""

from scripts.verify_terminal_notebook import stderr_is_failure


def test_benign_library_warning_is_not_an_execution_failure() -> None:
    warning = (
        "Warning! The implementation of 'quoridor' has known issues. "
        "Please see the games list on github or the code for details."
    )
    assert stderr_is_failure(warning) is False


def test_python_traceback_is_an_execution_failure() -> None:
    assert stderr_is_failure(
        "Traceback (most recent call last):\n  File \"x.py\", line 1\nValueError: broken"
    )


def test_explicit_python_error_is_an_execution_failure() -> None:
    assert stderr_is_failure("RuntimeError: model gate failed")
