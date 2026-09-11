from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "ensure_notebook_kernel.py"
    spec = importlib.util.spec_from_file_location("ensure_notebook_kernel", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_kernel_document_binds_source_inside_interpreter(tmp_path):
    module = load_module()
    repo = tmp_path / "repo"
    interpreter = repo / ".venv/bin/python"
    document = module.kernel_document(repo, interpreter)

    assert document["argv"][:4] == [str(interpreter), "-I", "-B", "-c"]
    assert str(repo / "src") in document["argv"][4]
    assert str(repo / "scripts") in document["argv"][4]
    assert "app.initialize()" in document["argv"][4]
    assert "app.start()" in document["argv"][4]
    assert "PYTHONPATH" not in document["env"]
    assert document["display_name"] == "Kaggriculture (Python 3.12)"


def test_managed_kernel_dirs_include_user_and_runtime(tmp_path):
    module = load_module()
    home = tmp_path / "home"
    interpreter = tmp_path / "repo/.venv/bin/python"

    directories = module.managed_kernel_dirs(home, interpreter)

    assert directories == [
        home / ".local/share/jupyter/kernels/kaggriculture",
        tmp_path / "repo/.venv/share/jupyter/kernels/kaggriculture",
    ]


def test_write_kernel_specs_backs_up_existing_managed_spec(tmp_path):
    module = load_module()
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    interpreter = repo / ".venv/bin/python"
    user_dir, runtime_dir = module.managed_kernel_dirs(home, interpreter)
    user_dir.mkdir(parents=True)
    old = {"argv": [str(interpreter), "-m", "ipykernel_launcher"], "language": "python"}
    (user_dir / "kernel.json").write_text(json.dumps(old))

    records = module.write_kernel_specs(repo, interpreter, home, tmp_path / "backup")

    assert len(records) == 2
    assert records[0]["previous_sha256"] is not None
    assert Path(records[0]["backup_path"]).is_file()
    expected = module.kernel_document(repo, interpreter)
    assert json.loads((user_dir / "kernel.json").read_text()) == expected
    assert json.loads((runtime_dir / "kernel.json").read_text()) == expected


def test_smoke_code_requires_engine_interpreter_and_static_figure(tmp_path):
    module = load_module()
    repo = tmp_path / "repo"
    interpreter = repo / ".venv/bin/python"

    code = module.smoke_code(repo, interpreter)

    assert "engine_manifest" in code
    assert "terminal_features" in code
    assert "Unexpected Python interpreter" in code
    assert "Static figure smoke failed" in code
    assert "games_run': 0" in code
