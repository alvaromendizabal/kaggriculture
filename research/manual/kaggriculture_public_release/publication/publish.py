"""User-run public release for ONE existing repository. No visibility changes.

Commands are deliberately separate: inspect -> prepare -> check -> seal -> stage.
Only prepare/sync contact the Git remote. This module never commits, pushes,
opens/merges a PR, changes permissions, removes a file, or launches research.
Existing source trees, data, environments, and checkpoint files are not overwritten.
A content scan is a limited safeguard, not a guarantee of secret-free history.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'release_state'
BASELINE = '7194116dfc92a8663139611233b5a221dad431a4'
REPOSITORY = 'alvaromendizabal/kaggriculture'
BRANCH = 'publication/manual-research-21-22'
PACKAGES = (
    'kaggriculture_manual_resume', 'kaggriculture_workforce_milestone',
    'kaggriculture_action_features', 'kaggriculture_cash_realization',
    'kaggriculture_terminal_ablation', 'kaggriculture_sale_timing',
    'kaggriculture_route_opportunity', 'kaggriculture_water_maintenance',
    'kaggriculture_maintenance_diagnosis', 'kaggriculture_harvest_value',
    'kaggriculture_crop_lifecycle', 'kaggriculture_renewal_factorial',
    'kaggriculture_two_rounds', 'kaggriculture_service_value',
    'kaggriculture_public_release',
)
PROTECTED = ('src', 'configs', 'pyproject.toml', 'uv.lock',
    'docs/feature_next_milestone.md', 'reports/bottleneck_research.json',
    'reports/workforce_scope_audit.json')
SKIP_DIRS = {'.git', '.venv', 'venv', 'env', '__pycache__', '.ipynb_checkpoints',
    'node_modules', 'raw', 'artifacts', 'checkpoints', 'state', 'release_state'}
EXTENSIONS = {'.py', '.ipynb', '.md', '.csv', '.json', '.toml', '.lock',
    '.yaml', '.yml', '.sh', '.txt', '.html'}
REPORTS = {'report.json', 'summary.json', 'tests.json', 'mechanics.json',
    'comparison.csv', 'comparisons.csv', 'endpoint_review.json', 'feature_analysis.json',
    'feature_registry.csv', 'dashboard.html', 'feature_readiness_dashboard.html'}
SKIP_NAMES = {'USER_RULES.md', 'kaggle.json', '.env', '.credentials',
    'credentials', 'config', 'BUNDLE_MANIFEST.json', 'PUBLIC_MANIFEST.json'}
MAX_FILE = 25 * 1024**2
MAX_TOTAL = 500 * 1024**2
SECRET_RULES = (
    ('key_material', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('aws_key', re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b')),
    ('github_token', re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b')),
    ('signed_url', re.compile(r'(?i)X-Amz-(?:Signature|Credential)=[A-Za-z0-9%/]{20,}')),
    ('assigned_secret', re.compile(r'''(?i)(?:aws_secret_access_key|api_key|access_token)\s*[=:]\s*["'][A-Za-z0-9/+_=.-]{24,}["']''')),
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.receipt-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(value, handle, indent=2, allow_nan=False)
            handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def inside(root: Path, relative: str) -> Path:
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('Unsafe relative path')
    candidate = root / p
    if not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escapes expected root')
    current = candidate
    while current != root:
        if current.is_symlink():
            raise ValueError('Symlink excluded')
        current = current.parent
    return candidate


def git(repo: Path, *args: str, cap: int = 30) -> str:
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True,
        text=True, timeout=cap, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'})
    if result.returncode:
        # Do not reflect an embedded credential from a remote URL into a receipt.
        raise RuntimeError('Git command failed: ' + args[0] + '. Inspect locally; do not reset or force-push.')
    return result.stdout.strip()


def remote_ok(value: str) -> bool:
    return value.rstrip('/') in (
        f'https://github.com/{REPOSITORY}', f'https://github.com/{REPOSITORY}.git',
        f'git@github.com:{REPOSITORY}', f'git@github.com:{REPOSITORY}.git',
    )


def scan(path: Path) -> list[str]:
    if path.stat().st_size > MAX_FILE:
        return ['file_exceeds_25_MiB_review_limit']
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return ['non_text_file_requires_separate_review']
    return [name for name, pattern in SECRET_RULES if pattern.search(text)]


def allowed(relative: Path) -> bool:
    if set(relative.parts) & SKIP_DIRS or relative.name in SKIP_NAMES:
        return False
    if relative.name.startswith('.env') or relative.suffix in ('.pem', '.key', '.pkl', '.pt', '.parquet'):
        return False
    if 'outputs' in relative.parts and relative.name not in REPORTS:
        return False
    return relative.suffix.lower() in EXTENSIONS or relative.name in ('LICENSE', 'NOTICE', '.gitignore', '.gitattributes')


def notebook_info(path: Path) -> dict:
    nb = read(path)
    cells = [c for c in nb.get('cells', []) if c.get('cell_type') == 'code']
    active = [c for c in cells if ''.join(c.get('source', [])).strip()]
    errors = sum(o.get('output_type') == 'error' for c in cells for o in c.get('outputs', []))
    executed = sum(c.get('execution_count') is not None for c in active)
    return {'code_cells': len(active), 'saved_execution_counts': executed, 'error_outputs': errors,
        'status': 'saved_counts_present_not_independent_execution_proof' if active and executed == len(active) and not errors else 'partial_or_unexecuted_or_error_evidence'}


def original_repos(home: Path) -> list[dict]:
    result = []
    for name in ('kaggriculture', 'kaggriculture-manual'):
        p = home / 'projects' / name
        if not (p / '.git').exists():
            result.append({'name': name, 'present': False}); continue
        origin = git(p, 'remote', 'get-url', 'origin')
        if not remote_ok(origin):
            raise ValueError('Unexpected or credential-bearing origin in ' + name)
        status = git(p, 'status', '--porcelain=v1', '--untracked-files=normal')
        core = git(p, 'diff', '--name-only', 'HEAD', '--', 'src', 'scripts', 'tests', 'configs', 'pyproject.toml', 'uv.lock', '.github')
        result.append({'name': name, 'present': True, 'head': git(p, 'rev-parse', 'HEAD'),
            'branch': git(p, 'branch', '--show-current'), 'status': status, 'uncommitted_core_paths': core.splitlines(),
            'origin_expected': True})
    return result


def inspect(home: Path) -> None:
    start = time.monotonic(); entries = []; flags = []; missing = []; omissions = []
    repos = original_repos(home)
    for name in PACKAGES:
        root = home / name
        if not root.is_dir() or root.is_symlink():
            missing.append(name); continue
        for directory, dirs, filenames in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (Path(directory) / d).is_symlink())
            for filename in sorted(filenames):
                p = Path(directory) / filename; rel = p.relative_to(root)
                if p.is_symlink() or not allowed(rel):
                    omissions.append(name + '/' + rel.as_posix()); continue
                if time.monotonic() - start > 120:
                    raise TimeoutError('120-second inventory limit; preserve partial diagnostics')
                finding = scan(p)
                if finding:
                    flags.append({'path': name + '/' + rel.as_posix(), 'categories': finding})
                row = {'package': name, 'relative': rel.as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)}
                if p.suffix == '.ipynb':
                    row['notebook'] = notebook_info(p)
                entries.append(row)
                if len(entries) % 100 == 0:
                    print(utc(), 'INVENTORY_PROGRESS', len(entries), 'files', flush=True)
    total = sum(x['bytes'] for x in entries)
    if total > MAX_TOTAL:
        flags.append({'path': '(total)', 'categories': ['more_than_500_MiB_requires_review']})
    if any(r.get('uncommitted_core_paths') for r in repos):
        flags.append({'path': '(workspace)', 'categories': ['uncommitted_core_code_requires_explicit_reconciliation']})
    required = {'kaggriculture_service_value', 'kaggriculture_public_release'}
    if required & set(missing):
        flags.append({'path': '(required packages)', 'categories': ['required_package_missing']})
    report = {'status': 'REVIEW_REQUIRED' if flags else 'LOCAL_INVENTORY_READY', 'utc': utc(),
        'repos': repos, 'files': entries, 'candidate_bytes': total, 'flags': flags,
        'missing_older_packages': missing, 'excluded_paths': omissions,
        'scope': 'Known home-directory packages and the two named local repositories; not a disk or history-wide inventory',
        'remote_checked': False, 'raw_data_changed': False}
    save(STATE / 'inventory.json', report)
    print(report['status'], len(entries), 'files;', len(flags), 'blocking findings;', len(missing), 'absent packages', flush=True)
    if flags:
        raise ValueError('Review release_state/inventory.json before staging. Nothing has been pushed.')


def copy_checked(source: Path, destination: Path, expected: str) -> None:
    if source.is_symlink() or digest(source) != expected:
        raise ValueError('Source changed after inventory: ' + source.name)
    if destination.exists():
        if destination.is_symlink() or digest(destination) != expected:
            raise ValueError('Destination differs; preserve it: ' + destination.name)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open('rb') as inp, destination.open('xb') as out:
        shutil.copyfileobj(inp, out)
        out.flush(); os.fsync(out.fileno())
    if digest(destination) != expected:
        raise ValueError('Copy readback mismatch')


def prepare(home: Path) -> None:
    inventory = read(STATE / 'inventory.json')
    if inventory['status'] != 'LOCAL_INVENTORY_READY' or inventory['flags']:
        raise ValueError('Clean reviewed inventory required')
    repo = home / 'projects/kaggriculture-manual'
    work = home / 'projects/kaggriculture-publish'
    if not remote_ok(git(repo, 'remote', 'get-url', 'origin')):
        raise ValueError('Unexpected repository')
    if work.exists() or (STATE / 'prepared.json').exists():
        raise ValueError('Publication workspace already exists. Resume check/seal/stage; do not recreate or remove it.')
    # Recheck inputs before network or copying.
    for row in inventory['files']:
        p = inside(home / row['package'], row['relative'])
        if digest(p) != row['sha256']:
            raise ValueError('Inventory is stale. Run inspect again before prepare.')
    if original_repos(home) != inventory['repos']:
        raise ValueError('Local Git state changed after inspect; inspect again')
    git(repo, 'fetch', '--no-tags', 'origin', 'refs/heads/main:refs/remotes/origin/main', cap=90)
    base = git(repo, 'rev-parse', 'origin/main')
    git(repo, 'merge-base', '--is-ancestor', BASELINE, base)
    if git(repo, 'diff', '--name-only', BASELINE, base, '--', *PROTECTED):
        raise ValueError('Remote core/data-contract changed. Review compatibility rather than reset.')
    backup = home / 'kaggriculture-publication-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True)
    for info in inventory['repos']:
        if not info.get('present'):
            continue
        original = home / 'projects' / info['name']
        bundle = backup / (info['name'] + '.bundle')
        git(original, 'bundle', 'create', str(bundle), '--all', cap=90)
        git(original, 'bundle', 'verify', str(bundle), cap=30)
        # Patch files remain local and are NOT included in the Git publication.
        for label, args in [('worktree', ['diff', '--binary']), ('index', ['diff', '--cached', '--binary'])]:
            data = subprocess.check_output(['git', '-C', str(original), *args], timeout=30)
            (backup / (info['name'] + '-' + label + '.patch')).write_bytes(data)
    git(repo, 'worktree', 'add', '-b', BRANCH, str(work), base, cap=60)
    save(STATE / 'prepared.json', {'status': 'COPYING', 'worktree': str(work), 'base': base,
        'branch': BRANCH, 'backup': str(backup), 'utc': utc()})
    changed = []
    for i, row in enumerate(inventory['files']):
        source = inside(home / row['package'], row['relative'])
        relative = 'research/manual/' + row['package'] + '/' + row['relative']
        destination = inside(work, relative)
        copy_checked(source, destination, row['sha256']); changed.append(relative)
        if i % 100 == 0:
            print(utc(), 'PUBLIC_SOURCE_COPY', i + 1, '/', len(inventory['files']), flush=True)
    old_readme = work / 'README.md'
    archive = work / ('docs/archive/README-before-public-research-' + base[:12] + '.md')
    if old_readme.exists():
        copy_checked(old_readme, archive, digest(old_readme)); changed.append(archive.relative_to(work).as_posix())
    # New site files are deliberately enumerated in the delivery, not selected by glob from HOME.
    site = ROOT / 'site'
    for p in sorted(site.rglob('*')):
        if not p.is_file():
            continue
        relative = p.relative_to(site).as_posix(); destination = inside(work, relative)
        if relative == 'README.md':
            destination.write_bytes(p.read_bytes())
        else:
            copy_checked(p, destination, digest(p))
        changed.append(relative)
    manifest = {'status': 'PUBLIC_SOURCE_AND_EVIDENCE_SNAPSHOT', 'utc': utc(),
        'source_baseline': BASELINE, 'remote_base_observed': base, 'files': inventory['files'],
        'missing_older_packages': inventory['missing_older_packages'],
        'excluded_count': len(inventory['excluded_paths']), 'notebook_statuses_are_saved_output_observations': True,
        'exclusions': ['credentials', 'runtime environments', 'raw episodes/data archives', 'large checkpoints', 'logs'],
        'not_a_complete_disk_backup': True, 'core_source_unchanged': True, 'visibility_changed': False}
    manifest_path = 'research/PUBLICATION_MANIFEST.json'
    save(work / manifest_path, manifest); changed.append(manifest_path)
    hashes = {p: digest(inside(work, p)) for p in sorted(set(changed))}
    save(STATE / 'prepared.json', {'status': 'PUBLIC_WORKTREE_READY', 'utc': utc(), 'worktree': str(work),
        'base': base, 'branch': BRANCH, 'backup': str(backup), 'paths': hashes,
        'overview_source': notebook_source(work / 'notebooks/00_research_overview.ipynb')})
    print('PUBLIC_WORKTREE_READY', work, flush=True)


def notebook_source(path: Path) -> str:
    nb = read(path)
    body = [{'cell_type': c['cell_type'], 'source': ''.join(c.get('source', []))} for c in nb['cells']]
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def candidate_paths(home: Path) -> tuple[Path, dict]:
    prepared = read(STATE / 'prepared.json')
    if prepared['status'] != 'PUBLIC_WORKTREE_READY':
        raise ValueError('Incomplete publication copy; return diagnostics')
    work = Path(prepared['worktree'])
    if work != home / 'projects/kaggriculture-publish':
        raise ValueError('Unexpected publication worktree')
    if git(work, 'branch', '--show-current') != BRANCH:
        raise ValueError('Unexpected publication branch')
    paths = dict(prepared['paths'])
    overview = 'notebooks/00_research_overview.ipynb'
    for name, expected in paths.items():
        p = inside(work, name)
        if name == overview:
            if notebook_source(p) != prepared['overview_source']:
                raise ValueError('Overview source changed after preparation')
        elif digest(p) != expected:
            raise ValueError('Publication file changed after preparation: ' + name)
    for name in ('docs/research/index.html', 'docs/research/overview_execution.json'):
        p = inside(work, name)
        if p.is_file():
            paths[name] = digest(p)
    paths[overview] = digest(work / overview)
    return work, paths


def static_checks(work: Path, paths: dict) -> list[dict]:
    issues = []
    for name in paths:
        p = inside(work, name)
        findings = scan(p)
        if findings:
            issues.append({'path': name, 'categories': findings})
        try:
            if p.suffix == '.py':
                ast.parse(p.read_text(), filename=name)
            elif p.suffix == '.ipynb':
                nb = read(p)
                if nb.get('nbformat') != 4:
                    raise ValueError('Expected notebook format 4')
                # Historical notebooks can contain legitimate IPython magics.
                for c in nb['cells']:
                    if c['cell_type'] == 'code':
                        source = ''.join(c.get('source', []))
                        if any(line.lstrip().startswith(('%', '!')) for line in source.splitlines()):
                            continue
                        ast.parse(source)
        except (SyntaxError, ValueError, KeyError) as error:
            issues.append({'path': name, 'categories': [type(error).__name__]})
    return issues


def check(home: Path) -> None:
    work, paths = candidate_paths(home)
    logpath = STATE / 'publication_tests.log'
    proc = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(ROOT / 'publication/tests'), '-v'],
        cwd=ROOT / 'publication', capture_output=True, text=True, timeout=45)
    logpath.write_text(proc.stdout + proc.stderr)
    print(proc.stdout + proc.stderr, end='')
    if proc.returncode:
        raise RuntimeError('Publication safety tests failed; do not publish')
    issues = static_checks(work, paths)
    # Inspect all CURRENT tracked paths, not only the newly exported files.
    current_flags = []
    for name in git(work, 'ls-files').splitlines():
        if not name:
            continue
        p = inside(work, name)
        if p.is_file() and p.suffix in EXTENSIONS:
            if scan(p):
                current_flags.append({'path': name, 'categories': scan(p)})
    report = {'status': 'PUBLICATION_CHECKS_PASSED' if not issues and not current_flags else 'REVIEW_REQUIRED',
        'utc': utc(), 'scanned_candidate_files': len(paths), 'issues': issues,
        'existing_tracked_content_flags': current_flags,
        'test_log_sha256': digest(logpath), 'test_source_sha256': {p.name: digest(p) for p in sorted((ROOT / 'publication/tests').glob('*.py'))},
        'publisher_sha256': digest(Path(__file__)), 'paths': paths,
        'historical_secret_scan': False, 'research_tests_executed_by_this_command': False}
    save(STATE / 'checks.json', report)
    print(report['status'])
    if issues or current_flags:
        raise ValueError('Review findings; no Git changes have been staged')


def seal(home: Path, acknowledge: str) -> None:
    if acknowledge != 'PUBLISH_RESEARCH_SOURCE':
        raise ValueError('Explicit source-publication acknowledgement required')
    work, paths = candidate_paths(home)
    checked = read(STATE / 'checks.json')
    if checked['status'] != 'PUBLICATION_CHECKS_PASSED' or checked['paths'] != paths or checked['publisher_sha256'] != digest(Path(__file__)):
        raise ValueError('Current files need a fresh check')
    info = notebook_info(work / 'notebooks/00_research_overview.ipynb')
    if info['error_outputs'] or info['saved_execution_counts'] != info['code_cells'] or not info['code_cells']:
        raise ValueError('Run, save and inspect the reporting notebook first')
    if 'docs/research/index.html' not in paths:
        raise ValueError('Expected rendered dashboard')
    save(STATE / 'sealed.json', {'status': 'PUBLIC_SOURCE_APPROVED', 'utc': utc(), 'paths': paths,
        'repository': REPOSITORY, 'branch': BRANCH, 'publisher_sha256': digest(Path(__file__)),
        'acknowledgement': acknowledge})
    print('PUBLIC_SOURCE_APPROVED')


def stage(home: Path) -> None:
    work, paths = candidate_paths(home)
    approved = read(STATE / 'sealed.json')
    if approved['paths'] != paths or approved['publisher_sha256'] != digest(Path(__file__)):
        raise ValueError('Approved bytes changed')
    existing = git(work, 'diff', '--cached', '--name-only').splitlines()
    if any(p not in paths for p in existing):
        raise ValueError('Unexpected files already staged')
    # -f is ONLY for exact approved report paths ignored by historical .gitignore files.
    # It is never git add -A or a force-push.
    names = sorted(paths)
    for offset in range(0, len(names), 60):
        git(work, 'add', '-f', '--', *names[offset:offset + 60])
    staged = git(work, 'diff', '--cached', '--name-only').splitlines()
    if any(name not in paths for name in staged):
        raise ValueError('Staged path outside approved manifest')
    for name in staged:
        data = subprocess.check_output(['git', '-C', str(work), 'show', ':' + name], timeout=20)
        if hashlib.sha256(data).hexdigest() != paths[name]:
            raise ValueError('Git filter changed approved bytes: ' + name)
    save(STATE / 'staged.json', {'status': 'READY_TO_COMMIT', 'utc': utc(), 'files': len(staged), 'approved_paths': paths})
    print('READY_TO_COMMIT', len(staged), 'paths; inspect the staged diff before committing')


def sync(home: Path) -> None:
    """After user merges the PR: verify remote files and fast-forward active code.

    The old original checkout is NOT changed. No reset, clean, rebase, or force.
    """
    active = home / 'projects/kaggriculture-manual'
    approved = read(STATE / 'sealed.json')
    if git(active, 'status', '--porcelain=v1', '--untracked-files=normal'):
        raise ValueError('Active checkout is not clean; preserve it and review before sync')
    git(active, 'fetch', '--no-tags', 'origin', 'refs/heads/main:refs/remotes/origin/main', cap=90)
    target = git(active, 'rev-parse', 'origin/main')
    git(active, 'merge-base', '--is-ancestor', git(active, 'rev-parse', 'HEAD'), target)
    if git(active, 'diff', '--name-only', BASELINE, target, '--', *PROTECTED):
        raise ValueError('Merged core/receipt-contract differs; inspect before advancing')
    for name, expected in approved['paths'].items():
        data = subprocess.check_output(['git', '-C', str(active), 'show', target + ':' + name], timeout=20)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Merged main does not contain exact reviewed publication: ' + name)
    git(active, 'merge', '--ff-only', 'origin/main', cap=60)
    advertised = git(active, 'ls-remote', 'origin', 'refs/heads/main', cap=30).split()[0]
    actual = git(active, 'rev-parse', 'HEAD')
    if actual != advertised:
        raise ValueError('Remote main moved during verification; no reset; rerun sync after review')
    save(STATE / 'sync.json', {'status': 'AWS_CODE_MATCHES_REMOTE_MAIN', 'utc': utc(), 'head': actual,
        'repo': str(active), 'reviewed_publication_verified': True, 'raw_data_changed': False,
        'old_original_checkout_untouched': True, 'visibility_not_changed': True})
    print('AWS_CODE_MATCHES_REMOTE_MAIN', actual)


def bundle(home: Path) -> None:
    destination = home / 'kaggriculture_public_release_results.zip'
    records = []
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for folder in (STATE, ROOT / 'research/outputs'):
            if not folder.exists():
                continue
            for p in sorted(folder.rglob('*')):
                if not p.is_file() or p.is_symlink() or p.stat().st_size > 30 * 1024**2:
                    continue
                if p.name != 'relative_task_features.csv.gz' and scan(p):
                    continue
                name = p.relative_to(ROOT).as_posix()
                archive.write(p, name); records.append({'path': name, 'sha256': digest(p)})
        for p in sorted((ROOT / 'research').glob('*.ipynb')):
            archive.write(p, 'research/' + p.name); records.append({'path': 'research/' + p.name, 'sha256': digest(p)})
        for family in ('19', '20'):
            base = home / 'kaggriculture_service_value/outputs' / ('round' + family) / 'pair1'
            if base.exists():
                for p in sorted(base.rglob('*')):
                    if p.is_file() and not p.is_symlink() and p.name in ('report.json', 'status.json', 'comparison.csv', 'trajectories.csv') and not scan(p):
                        name = 'outcome_evidence/round' + family + '/' + p.name
                        archive.write(p, name); records.append({'path': name, 'sha256': digest(p)})
        archive.writestr('BUNDLE_MANIFEST.json', json.dumps({'utc': utc(), 'files': records,
            'raw_data_archives_included': False, 'backups_included': False}, indent=2))
    print('RETURN_PACKAGE', destination)


def verify_delivery() -> None:
    manifest = read(ROOT / 'PACKAGE_MANIFEST.json')
    for name, expected in manifest['files'].items():
        if digest(inside(ROOT, name)) != expected:
            raise ValueError('Delivery file changed: ' + name)
    for name, expected in manifest['notebook_sources'].items():
        if notebook_source(inside(ROOT, name)) != expected:
            raise ValueError('Delivery notebook source changed: ' + name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect', 'prepare', 'check', 'seal', 'stage', 'sync', 'bundle'))
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--acknowledge', default='')
    args = parser.parse_args(); STATE.mkdir(parents=True, exist_ok=True)
    try:
        if args.command != 'bundle':
            verify_delivery()
        if args.command == 'seal':
            seal(args.home, args.acknowledge)
        else:
            globals()[args.command](args.home)
    except Exception as error:
        save(STATE / ('failure_' + args.command + '.json'), {'utc': utc(), 'type': type(error).__name__,
            'message': str(error), 'action': 'preserve files; review diagnostics; no destructive retry'})
        raise


if __name__ == '__main__':
    main()
