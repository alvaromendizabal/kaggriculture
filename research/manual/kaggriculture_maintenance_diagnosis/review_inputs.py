"""Validate notebook-12 evidence and bind its action stream to accepted checkpoints."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import gzip
from artifact_io import read, digest, sha
START, END = 480, 718
ROLES = ('candidate', 'same_state_control', 'same_state_null_fork', 'opponent')

def checkpoint(path: Path) -> dict:
    import json
    doc = json.loads(gzip.decompress(path.read_bytes()))
    checksum = doc.pop('checksum')
    if checksum != digest(doc):
        raise ValueError('Notebook12 checkpoint checksum mismatch')
    return doc['payload']

def action_stream(root: Path, expected_hashes: dict | None = None) -> dict:
    """The reviewed run contains one control block then one defer block, not retries.

    Timing, step, command counts and cash traces must agree with the independently
    serialized branch checkpoints before any recorded action is used for replay.
    """
    import json
    root = Path(root)
    if expected_hashes:
        for name, value in expected_hashes.items():
            p = (root / name).resolve()
            if not p.is_relative_to(root.resolve()) or sha(p) != value:
                raise ValueError('Notebook12 evidence changed: ' + name)
    report = read(root / 'outputs/pilot/report.json')
    if report['decision'] != 'STOP_NEGATIVE_ENDPOINT' or report['completed_pairs'] != 1:
        raise ValueError('This diagnosis requires the reviewed one-pair negative result')
    if len(report['paired_results']) != 1:
        raise ValueError('Ambiguous source pair')
    pair = report['paired_results'][0]
    key = {k: pair[k] for k in ('seed','seat','opponent','arm')}
    if key != {'seed':1601,'seat':0,'opponent':'livestock_fertilizer','arm':'coordinated'}:
        raise ValueError('Unexpected research source')
    rows = [json.loads(line) for line in (root/'outputs/callback_trace.jsonl').read_text().splitlines() if line.strip()]
    pilot = [r for r in rows if r['role'] in ROLES]
    if len(pilot) != 2 * 239 * 4:
        raise ValueError('Incomplete or repeated pilot action blocks; do not guess')
    result = {}
    for block, mode in enumerate(('control','defer')):
        matches = sorted((root/'outputs/pilot/checkpoints').glob('*-'+mode+'.json.gz'))
        if len(matches) != 1:
            raise ValueError('Ambiguous checkpoint for ' + mode)
        saved = checkpoint(matches[0])
        if saved['key'] != key or saved['mode'] != mode or len(saved['trace']) != 239:
            raise ValueError('Checkpoint identity/length differs')
        stream = []
        for index, step in enumerate(range(START, END+1)):
            group = pilot[(block*239+index)*4:(block*239+index+1)*4]
            if tuple(r['role'] for r in group) != ROLES or any(r['step'] != step for r in group):
                raise ValueError('Action stream is out of order')
            by_role = {r['role']:r for r in group}
            t = saved['trace'][index]
            for role, field in zip(ROLES, ('candidate_callback_ms','reference_callback_ms','null_callback_ms','opponent_callback_ms')):
                if by_role[role]['milliseconds'] != t[field]:
                    raise ValueError('Log timing does not bind to checkpoint trace')
            actual = by_role['candidate']['action']
            ref = by_role['same_state_control']['action']
            if ref != by_role['same_state_null_fork']['action']:
                raise ValueError('Recorded null-fork parity failed')
            if (actual != ref) != t['same_state_action_changed']:
                raise ValueError('Action change counter differs')
            commands = [actual['farmer'], *actual['hands']]
            for op, field in [('WATER','water_commands'),('HARVEST','harvest_commands'),('PLANT','plant_commands')]:
                if sum(a[0] == op for a in commands) != t[field]:
                    raise ValueError('Command count differs')
            if mode == 'control' and actual != ref:
                raise ValueError('Recorded control is not the reference')
            actions = [None,None]
            actions[key['seat']] = actual
            actions[1-key['seat']] = by_role['opponent']['action']
            stream.append({'step':step,'actions':actions,'expected':t})
        result[mode] = {'key':key,'actions':stream,'checkpoint':saved}
    if result['control']['checkpoint']['initial_sha256'] != result['defer']['checkpoint']['initial_sha256']:
        raise ValueError('Different initial states')
    return result
