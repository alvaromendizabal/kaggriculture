#!/usr/bin/env python3
"""Data-preserving, manually invoked Kaggriculture workspace recovery.

No training, simulation, submissions, AWS resource changes, or GitHub writes.
The original checkout and runtime are never modified. A read-only shared runtime
is allowed; its kernel is explicitly bound to the new checkout's source tree.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import signal
import subprocess
import sys
import time
import uuid
import zipfile

HERE = Path(__file__).resolve().parent
STATE = HERE / "state"
EXPECTED = "7194116dfc92a8663139611233b5a221dad431a4"
ORIGIN = "https://github.com/alvaromendizabal/kaggriculture.git"
ENGINE_SHA = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
KERNEL = "kaggriculture-manual"
SESSION = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
DEADLINE = float("inf")


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def paths(home=None):
    home = Path(home or Path.home()).absolute()
    return {
        "old": home / "projects/kaggriculture",
        "repo": home / "projects/kaggriculture-manual",
        "private": home / "kaggriculture-private/manual-resume/staffing",
        "raw": home / "kaggriculture-private/raw/kaggle-downloads",
    }


def emit(event, **values):
    STATE.mkdir(parents=True, exist_ok=True)
    row = {"utc": utc(), "event": event, **values}
    with (STATE / f"events-{SESSION}.jsonl").open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True), flush=True)


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temp.open("x") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            if time.monotonic() > DEADLINE:
                raise TimeoutError("Stage deadline reached while hashing; originals unchanged")
            h.update(chunk)
    return h.hexdigest()


def remaining(limit):
    value = min(float(limit), DEADLINE - time.monotonic())
    if value <= 0:
        raise TimeoutError("Stage deadline reached")
    return value


def stop_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def run(args, *, cwd=None, seconds=60, label="command", echo=False, env=None):
    """Bound a whole process group, save complete output, and emit UTC heartbeats."""
    timeout = remaining(seconds)
    STATE.mkdir(parents=True, exist_ok=True)
    logfile = STATE / f"{SESSION}-{label}-{uuid.uuid4().hex[:6]}.log"
    merged = os.environ.copy()
    merged.update({"GIT_TERMINAL_PROMPT": "0", "PYTHONDONTWRITEBYTECODE": "1",
                   "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                   "LITELLM_LOCAL_MODEL_COST_MAP": "True", "OPENBLAS_NUM_THREADS": "1",
                   "OMP_NUM_THREADS": "1", "MPLBACKEND": "Agg"})
    merged.update(env or {})
    started = time.monotonic()
    next_heartbeat = started + 15
    emit("start", stage=label, limit_seconds=round(timeout, 1))
    with logfile.open("w") as output:
        proc = subprocess.Popen([str(a) for a in args], cwd=cwd, env=merged,
                                stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while proc.poll() is None:
                now = time.monotonic()
                if now - started > timeout:
                    stop_group(proc)
                    raise TimeoutError(f"{label} exceeded {timeout:.0f}s. Log: {logfile}")
                if now >= next_heartbeat:
                    emit("heartbeat", stage=label, elapsed_seconds=round(now-started, 1))
                    next_heartbeat = now + 15
                time.sleep(0.1)
        except BaseException:
            if proc.poll() is None:
                stop_group(proc)
            raise
    text = logfile.read_text(errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed (exit {proc.returncode}). Log: {logfile}\n{text[-5000:]}")
    if echo and text:
        print(text, end="", flush=True)
    emit("passed", stage=label, elapsed_seconds=round(time.monotonic()-started, 3))
    return text.strip()


def git(repo, *args, seconds=30):
    return run(["git", "-C", str(repo), *args], seconds=seconds, label="git-" + args[0])


def safe_target(root, relative):
    """Reject absolute paths, traversal, and symlink parents or final files."""
    root = Path(root).absolute()
    rel = PurePosixPath(relative)
    if not rel.parts or rel.is_absolute() or any(p in ("..", ".", "") for p in rel.parts):
        raise ValueError(f"Unsafe artifact path: {relative}")
    if "\\" in relative:
        raise ValueError("Backslashes are not accepted in artifact paths")
    target = root.joinpath(*rel.parts)
    for part in [root, *root.parents, target, *target.parents]:
        if part.is_symlink():
            raise ValueError(f"Refusing symlink in destination: {part}")
    target.resolve().relative_to(root.resolve())
    return target


def validate_record(relative, record):
    if not relative.startswith(("artifacts/staffing_episodes/", "reports/")):
        raise ValueError("Unexpected manifest family")
    if not isinstance(record.get("bytes"), int) or not 0 < record["bytes"] < 10_000_000:
        raise ValueError("Invalid/oversized manifest byte count")
    digest = record.get("sha256", "")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid SHA256")
    if not record.get("version_id") or not record.get("readback_verified"):
        raise ValueError("Manifest is missing exact version/readback evidence")


def verified_file(path, record):
    return path.is_file() and path.stat().st_size == record["bytes"] and sha256(path) == record["sha256"]


def restore_one(client, manifest, root, relative, record):
    validate_record(relative, record)
    target = safe_target(root, relative)
    if target.exists():
        if not verified_file(target, record):
            raise RuntimeError(f"Existing artifact differs; preserved for inspection: {target}")
        return {"path": relative, "status": "REUSED_HASH_VERIFIED", **record}
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + "." + uuid.uuid4().hex + ".partial")
    response = client.get_object(Bucket=manifest["bucket"], Key=manifest["prefix"] + relative,
                                 VersionId=record["version_id"])
    body = response["Body"]
    try:
        if response.get("VersionId") != record["version_id"]:
            raise RuntimeError("S3 returned a different version")
        if response.get("ContentLength") != record["bytes"]:
            raise RuntimeError("S3 byte-count mismatch")
        total = 0
        with tmp.open("xb") as f:
            while True:
                remaining(1)
                chunk = body.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > record["bytes"]:
                    raise RuntimeError("Download exceeded expected byte count")
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        if not verified_file(tmp, record):
            raise RuntimeError(f"Downloaded hash mismatch; partial preserved: {tmp}")
        if target.exists():
            raise RuntimeError("Destination appeared during download; refusing replacement")
        # Hard-link publication is atomic and fails rather than overwriting an existing file.
        os.link(tmp, target)
        tmp.unlink()
    finally:
        body.close()
    return {"path": relative, "status": "DOWNLOADED_VERSION_AND_HASH_VERIFIED", **record}


def inventory():
    p = paths()
    rows = []
    # Bounded metadata inventory, not a claimed whole-volume backup or exhaustive raw-data audit.
    excluded = {".git", ".venv", "node_modules", "__pycache__", ".ipynb_checkpoints"}
    for root in (p["old"], p["raw"]):
        if not root.exists():
            continue
        for directory, dirs, filenames in os.walk(root, followlinks=False):
            remaining(1)
            dirs[:] = [d for d in dirs if d not in excluded and not d.startswith(".")
                       and not (Path(directory) / d).is_symlink()]
            for filename in filenames:
                item = Path(directory) / filename
                if not filename.startswith(".") and filename.endswith(
                    (".zip", ".json.gz", ".parquet", ".csv", ".npy", ".npz")):
                    try:
                        st = item.stat()
                        rows.append({"path": str(item), "bytes": st.st_size,
                                     "symlink": item.is_symlink(), "mtime_ns": st.st_mtime_ns})
                    except OSError:
                        rows.append({"path": str(item), "status": "STAT_FAILED"})
                if len(rows) >= 10000:
                    break
            if len(rows) >= 10000:
                break
    data = {"observed_utc": utc(), "paths": {k:str(v) for k,v in p.items()},
            "original_exists": p["old"].exists(), "candidate_data_files": rows,
            "inventory_scope": "Selected data/archive extensions only; no credential contents read",
            "listing_limit_reached": len(rows) >= 10000,
            "full_raw_inventory_verified": False, "original_modified_by_this_tool": False}
    if (p["old"] / ".git").exists():
        data["original_git_head"] = git(p["old"], "rev-parse", "HEAD")
        data["original_git_status"] = git(p["old"], "status", "--porcelain", "--untracked-files=all")
        data["original_worktrees"] = git(p["old"], "worktree", "list", "--porcelain")
    import shutil
    data["free_disk_bytes"] = shutil.disk_usage(Path.home()).free
    atomic_json(STATE / "inventory.json", data)
    emit("inventory_saved", candidates=len(rows), original_exists=data["original_exists"])
    return data


def assert_checkout(repo, *, expected=EXPECTED, remote=ORIGIN):
    if repo.is_symlink() or not (repo / ".git").is_dir():
        raise RuntimeError("Destination must be a separate real clone, not a symlink/worktree")
    if git(repo, "remote", "get-url", "origin") != remote:
        raise RuntimeError("Unexpected origin; nothing was overwritten")
    if git(repo, "rev-parse", "HEAD") != expected:
        raise RuntimeError("Checkout is not the reviewed commit; do not reset or delete it")
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("New checkout contains changes; preserve and review before continuing")


def sync_checkout(p, *, expected=EXPECTED, remote=ORIGIN):
    old, repo = p["old"], p["repo"]
    if old.resolve() == repo.resolve() or old.resolve() in repo.resolve().parents:
        raise RuntimeError("New clone must not replace or live inside the original checkout")
    tip = run(["git", "ls-remote", "--exit-code", "--heads", remote, "refs/heads/main"],
              seconds=30, label="remote-main").split()[0]
    if tip != expected:
        raise RuntimeError(f"GitHub main moved to {tip}. Reviewed kit expects {expected}. "
                           "STOP: preserve everything and obtain a refreshed review; no reset occurred.")
    if repo.exists():
        assert_checkout(repo, expected=expected, remote=remote)
        emit("reused_checkout", commit=expected)
    else:
        repo.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", "--single-branch", "--branch", "main", remote, repo],
            seconds=120, label="clone-main")
        assert_checkout(repo, expected=expected, remote=remote)
    return {"status":"PASSED", "head":expected, "origin":remote, "repo":str(repo),
            "original_untouched":True, "observed_utc":utc()}


def runtime_probe(repo):
    return r'''import hashlib, importlib.metadata as md, importlib.util, json, pathlib, sys, tomllib
root=pathlib.Path(REPO)
assert sys.version_info[:2] == (3,12), 'Requires Python 3.12; do not upgrade the old environment'
project=tomllib.loads((root/'pyproject.toml').read_text())
expected=dict(dep.split('==',1) for dep in project['project']['dependencies'])
expected['jupyter-client']='8.10.0'
actual={name:md.version(name) for name in expected}
assert actual==expected, f'Pinned package mismatch: {actual}; expected {expected}'
spec=importlib.util.find_spec('kaggle_environments')
assert spec is not None and spec.origin, 'Missing official engine'
engine=pathlib.Path(spec.origin).parent/'envs/kaggriculture/kaggriculture.py'
engine_hash=hashlib.sha256(engine.read_bytes()).hexdigest()
assert engine_hash==ENGINE_SHA, f'Engine bytes differ: {engine_hash}'
sys.dont_write_bytecode=True
sys.path[:0]=[str(root/'src'), str(root/'scripts')]
from kaggriculture_research.environment import engine_manifest
import kaggriculture_research.environment as module
pathlib.Path(module.__file__).resolve().relative_to((root/'src').resolve())
assert engine_manifest()['version']=='1.32.7'
import plotly.graph_objects as go
assert '<html>' in go.Figure(go.Scatter(x=[0,1],y=[0,1])).to_html().lower()
print('RUNTIME_RESULT '+json.dumps({'status':'PASSED','python':sys.version.split()[0],
'executable':sys.executable,'packages':actual,'engine_sha256':engine_hash,
'source_module':module.__file__,'repo':str(root),'games_run':0}))
'''.replace("REPO", repr(str(repo))).replace("ENGINE_SHA", repr(ENGINE_SHA))


def kernel_document(repo, interpreter, kit=HERE):
    source_paths = [str(repo / "src"), str(repo / "scripts"), str(kit)]
    boot = ("import sys\nsys.dont_write_bytecode=True\n"
            f"paths={source_paths!r}\n"
            "sys.path[:]=paths+[p for p in sys.path if p not in paths]\n"
            "from ipykernel.kernelapp import IPKernelApp\n"
            "app=IPKernelApp.instance()\napp.initialize()\n"
            "sys.path[:]=paths+[p for p in sys.path if p not in paths]\napp.start()\n")
    return {"argv":[str(interpreter),"-I","-B","-c",boot,"-f","{connection_file}"],
            "display_name":"Kaggriculture Manual (verified source)","language":"python",
            "env":{"PYTHONDONTWRITEBYTECODE":"1","HF_HUB_OFFLINE":"1",
                   "TRANSFORMERS_OFFLINE":"1","LITELLM_LOCAL_MODEL_COST_MAP":"True",
                   "OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MPLBACKEND":"Agg"},
            "metadata":{"source_checkout":str(repo),"base_commit":EXPECTED,
                        "runtime_reuse_is_read_only":True}}


def prepare():
    p = paths()
    inv = inventory()
    if inv["free_disk_bytes"] < 2 * 1024**3:
        raise RuntimeError("Less than 2 GiB free. Stop; do not delete the original workspace")
    source = sync_checkout(p)
    atomic_json(STATE / "source.json", source)
    candidates = [p["repo"] / ".venv/bin/python", p["old"] / ".venv/bin/python"]
    interpreter = next((x for x in candidates if x.is_file() and os.access(x,os.X_OK)), None)
    if interpreter is None:
        raise RuntimeError("No existing project Python found. Source is safe. See START_HERE.md, "
                           "Missing or incompatible runtime; no installation was attempted.")
    text = run([interpreter,"-I","-B","-c",runtime_probe(p["repo"])],
               seconds=60,label="runtime-probe")
    result = [json.loads(line.split(" ",1)[1]) for line in text.splitlines()
              if line.startswith("RUNTIME_RESULT ")]
    if len(result)!=1:
        raise RuntimeError("No unique successful runtime receipt")
    runtime = {**result[0],"checked_utc":utc(), "shared_read_only_runtime":interpreter==candidates[1]}
    kernel_path = Path.home()/".local/share/jupyter/kernels"/KERNEL/"kernel.json"
    if any(x.is_symlink() for x in [kernel_path,*kernel_path.parents]):
        raise RuntimeError("Refusing symlinked kernelspec location")
    doc = kernel_document(p["repo"],interpreter)
    if kernel_path.exists() and json.loads(kernel_path.read_text())!=doc:
        backup=STATE/f"previous-manual-kernel-{SESSION}.json"
        atomic_json(backup,json.loads(kernel_path.read_text()))
    atomic_json(kernel_path,doc)
    smoke = r'''import json
from jupyter_client import KernelManager
manager=KernelManager(kernel_name='kaggriculture-manual')
client=None
try:
 manager.start_kernel(cwd=REPO)
 client=manager.client(); client.start_channels(); client.wait_for_ready(timeout=15)
 reply=client.execute_interactive(PROBE,timeout=30,allow_stdin=False,store_history=False)
 assert reply['content'].get('status')=='ok', reply
 print('KERNEL_SMOKE_PASSED')
finally:
 if client is not None: client.stop_channels()
 if manager.has_kernel: manager.shutdown_kernel(now=True)
'''.replace("REPO",repr(str(p["repo"]))).replace("PROBE",repr(runtime_probe(p["repo"])))
    run([interpreter,"-I","-B","-c",smoke],seconds=60,label="real-kernel-smoke")
    runtime["real_kernel_smoke"]="PASSED"
    atomic_json(STATE/"runtime.json",runtime)
    for name in ("private","raw"):
        p[name].mkdir(parents=True,exist_ok=True)
    env = {"KAG_PYTHON":str(interpreter),"KAG_REPO":str(p["repo"]),
           "KAG_PRIVATE":str(p["private"]),"KAG_RAW":str(p["raw"])}
    (STATE/"runtime.env").write_text("\n".join(f"export {k}={shlex.quote(v)}" for k,v in env.items())+"\n")
    assert_checkout(p["repo"])
    emit("PREPARE_PASSED",head=EXPECTED,kernel=KERNEL,original_untouched=True,games_run=0)


def load_manifest():
    manifest=json.loads((HERE/"staffing_manifest.json").read_text())
    if manifest["bucket"]!="sagemaker-kaggriculture-560403859723-us-west-2" or manifest["prefix"]!="runs/staffing-controlled-routing-20260911/":
        raise ValueError("Unexpected checkpoint bucket/prefix")
    if len(manifest["artifacts"])!=10:
        raise ValueError("Expected seven episodes and three research receipts")
    for relative,record in manifest["artifacts"].items():
        validate_record(relative,record)
    return manifest


def restore():
    from botocore.config import Config
    import boto3
    if not (STATE/"runtime.json").exists():
        raise RuntimeError("Run prepare successfully first")
    runtime=json.loads((STATE/"runtime.json").read_text())
    if Path(sys.executable).absolute()!=Path(runtime["executable"]).absolute():
        raise RuntimeError('Use: source state/runtime.env; "$KAG_PYTHON" resume.py restore')
    p=paths()
    assert_checkout(p["repo"])
    client=boto3.client("s3",region_name="us-west-2",config=Config(connect_timeout=5,
                       read_timeout=10,retries={"total_max_attempts":2,"mode":"standard"}))
    manifest=load_manifest()
    completed=[]
    for index,(relative,record) in enumerate(sorted(manifest["artifacts"].items()),1):
        remaining(1)
        completed.append(restore_one(client,manifest,p["private"],relative,record))
        atomic_json(STATE/"restore_progress.json",{"utc":utc(),"completed":completed,"total":10})
        emit("checkpoint_verified",completed=index,total=10,path=relative)
    # Make private episode files available at the new checkout's ignored canonical location.
    link=p["repo"]/"artifacts/staffing_episodes"
    run(["git","-C",p["repo"],"check-ignore","--quiet","artifacts/staffing_episodes/probe.json.gz"],
        seconds=10,label="verify-private-ignore")
    link.parent.mkdir(exist_ok=True)
    expected_link=p["private"]/"artifacts/staffing_episodes"
    if link.is_symlink():
        if link.resolve()!=expected_link.resolve():
            raise RuntimeError("Existing episode symlink points elsewhere; preserved")
    elif link.exists():
        for relative,record in manifest["artifacts"].items():
            if relative.startswith("artifacts/") and not verified_file(p["repo"]/relative,record):
                raise RuntimeError("Existing checkout episode directory differs; preserved")
    else:
        link.symlink_to(expected_link,target_is_directory=True)
    receipt={"status":"PASSED","verified_utc":utc(),"episode_count":7,"artifact_count":10,
             "downloaded_or_reused":completed,"private_root":str(p["private"]),
             "original_untouched":True,"all_historical_studies_restored":False,
             "official_kaggle_raw_assets_verified":False,"games_run":0}
    atomic_json(STATE/"restore.json",receipt)
    assert_checkout(p["repo"])
    emit("RESTORE_PASSED",episodes=7,verified_objects=10,games_run=0)


def register_raw():
    root=paths()["raw"]
    root.mkdir(parents=True,exist_ok=True)
    rows=[]
    for item in sorted(root.rglob("*")):
        remaining(1)
        if item.is_symlink():
            raise RuntimeError("Use real uploaded files in the raw registration folder")
        if not item.is_file() or any(x.startswith(".") for x in item.relative_to(root).parts):
            continue
        if item.name.lower() in {"kaggle.json","credentials","credentials.json"}:
            raise RuntimeError("Credential file found in raw data folder. Move it to its secure location")
        row={"path":str(item),"bytes":item.stat().st_size,"sha256":sha256(item)}
        if zipfile.is_zipfile(item):
            with zipfile.ZipFile(item) as archive:
                members=archive.infolist()
                for member in members:
                    if member.filename.startswith("/") or ".." in PurePosixPath(member.filename).parts:
                        raise RuntimeError("Archive includes an unsafe member path; not extracted")
                row["archive_member_count"]=len(members)
                row["archive_uncompressed_bytes"]=sum(x.file_size for x in members)
                row["archive_member_names"]=[x.filename for x in members[:5000]]
                row["member_listing_truncated"]=len(members)>5000
                row["archive_extracted"]=False
                row["all_crc_checked"]=False
        rows.append(row)
        emit("raw_file_registered",files=len(rows),filename=item.name,bytes=row["bytes"])
    data={"status":"LOCAL_FILES_REGISTERED" if rows else "NO_RAW_DOWNLOADS_FOUND",
          "observed_utc":utc(),"files":rows,"official_completeness_verified":False,
          "note":"Local hashes do not prove provenance/completeness versus the Kaggle file listing. "
                 "Original archives are preserved; nothing extracted, submitted, or redistributed."}
    atomic_json(STATE/"raw_inventory.json",data)
    if not rows:
        raise RuntimeError(f"No files in {root}. Upload the original Kaggle download, not an API token")
    emit("RAW_REGISTERED",files=len(rows),official_completeness_verified=False)


def audit():
    p=paths()
    assert_checkout(p["repo"])
    runtime=json.loads((STATE/"runtime.json").read_text())
    assert runtime["status"]=="PASSED" and runtime["real_kernel_smoke"]=="PASSED"
    required=["reports/workforce_scope_audit.json","reports/bottleneck_research.json",
              "docs/feature_next_milestone.md","pyproject.toml","uv.lock"]
    file_hashes={name:sha256(p["repo"]/name) for name in required}
    restored=0
    for relative,record in load_manifest()["artifacts"].items():
        if not verified_file(safe_target(p["private"],relative),record):
            raise RuntimeError(f"Private recovery incomplete or corrupt: {relative}")
        restored+=1
    report={"status":"READY_FOR_ZERO_GAME_FEATURE_EVIDENCE_REVIEW","utc":utc(),
            "source_commit":EXPECTED,"source_files":file_hashes,"verified_private_objects":restored,
            "runtime_receipt_sha256":sha256(STATE/"runtime.json"),
            "games_run":0,"models_fit":0,"aws_resources_created":0,"github_updated":False,
            "original_workspace_modified":False,"feature_completion_gate":"OPEN",
            "official_metric_measured":False,"leaderboard_target_user_reported":3140.0,
            "raw_inventory":json.loads((STATE/"raw_inventory.json").read_text()) if (STATE/"raw_inventory.json").exists() else {"status":"NOT_REGISTERED"},
            "not_ready_for":"Full historical notebook reexecution, completed staffing pilot, "
                            "new policy promotion, or a leaderboard-strength claim"}
    atomic_json(STATE/"readiness.json",report)
    emit("READINESS_PASSED",source=EXPECTED,verified_private_objects=restored,games_run=0)


def bundle():
    files=list(STATE.glob("*.json"))+list(STATE.glob("*.jsonl"))
    if not files:
        raise RuntimeError("No local receipts exist yet")
    target=HERE/"kaggriculture_readiness_receipts.zip"
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.write(item,arcname="state/"+item.name)
    emit("receipts_bundled",path=str(target),files=len(files))


def main():
    global DEADLINE
    # Never place this recovery kit inside either source checkout.
    for protected in (paths()["old"], paths()["repo"]):
        if HERE == protected or protected in HERE.parents:
            print("STOP: extract the kit into your home directory, outside both checkouts.")
            return 1
    def terminate(signum, frame):
        raise TimeoutError("Stage interrupted by SIGTERM; child processes will be stopped")
    signal.signal(signal.SIGTERM, terminate)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["inventory","prepare","restore","audit","register-raw","bundle"])
    parser.add_argument("--seconds",type=int,default=None)
    args=parser.parse_args()
    limits={"inventory":60,"prepare":300,"restore":120,"audit":60,"register-raw":120,"bundle":30}
    seconds=args.seconds or limits[args.command]
    if seconds<1 or seconds>600:
        parser.error("Stage limit must be 1..600 seconds")
    DEADLINE=time.monotonic()+seconds
    functions={"inventory":inventory,"prepare":prepare,"restore":restore,"audit":audit,
               "register-raw":register_raw,"bundle":bundle}
    try:
        functions[args.command]()
    except Exception as exc:
        failure={"status":"FAILED","utc":utc(),"command":args.command,"error":str(exc),
                 "original_files_preserved":True,"automatic_retry":False}
        atomic_json(STATE/f"failure-{SESSION}.json",failure)
        emit("STOP",**failure)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
