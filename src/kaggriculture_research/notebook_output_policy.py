"""Conservative policy for notebook stderr streams.

NotebookClient already fails on cell error outputs.  Some dependencies emit known
non-fatal warnings on stderr, so verifiers must distinguish those from errors
without accepting arbitrary stderr.
"""

from __future__ import annotations

from typing import Any

BENIGN_STDERR_LINES = frozenset(
    {
        (
            "Warning! The implementation of 'quoridor' has known issues. "
            "Please see the games list on github or the code for details."
        ),
    }
)


def _field(output: Any, name: str, default: Any = None) -> Any:
    if hasattr(output, name):
        return getattr(output, name)
    if isinstance(output, dict):
        return output.get(name, default)
    return default


def stderr_is_execution_error(text: Any) -> bool:
    """Return True unless every non-empty stderr line is explicitly allow-listed."""
    if isinstance(text, list):
        text = "".join(str(part) for part in text)
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return any(line not in BENIGN_STDERR_LINES for line in lines)


def output_is_execution_error(output: Any) -> bool:
    """Treat cell errors and non-allow-listed stderr as execution failures."""
    kind = _field(output, "output_type")
    if kind == "error":
        return True
    if kind != "stream" or _field(output, "name") != "stderr":
        return False
    return stderr_is_execution_error(_field(output, "text", ""))
