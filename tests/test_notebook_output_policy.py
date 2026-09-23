from __future__ import annotations

import nbformat

from notebook_output_policy import output_is_execution_error, stderr_is_execution_error

QUORIDOR_WARNING = (
    "Warning! The implementation of 'quoridor' has known issues. "
    "Please see the games list on github or the code for details."
)


def test_known_quoridor_stderr_warning_is_benign() -> None:
    assert not stderr_is_execution_error(QUORIDOR_WARNING)
    assert not stderr_is_execution_error("\n" + QUORIDOR_WARNING + "\n")


def test_unknown_stderr_remains_fail_closed() -> None:
    assert stderr_is_execution_error("unexpected warning")
    assert stderr_is_execution_error("Traceback: boom")


def test_notebook_error_output_is_always_failure() -> None:
    output = nbformat.v4.new_output(
        "error",
        ename="RuntimeError",
        evalue="boom",
        traceback=["RuntimeError: boom"],
    )
    assert output_is_execution_error(output)


def test_stdout_stream_is_not_failure() -> None:
    output = nbformat.v4.new_output("stream", name="stdout", text="ok\n")
    assert not output_is_execution_error(output)
