"""Time the full online feature pipeline on one fixed saved development trace."""

import json
import time
from pathlib import Path

import numpy as np

from kaggriculture_livestock.experiment import feature_bank, job_plan, validate_episode
from kaggriculture_livestock.features import _plant_path
from kaggriculture_research.artifacts import file_digest, load_checkpoint, write_json
from kaggriculture_research.market_history import MarketHistory
from kaggriculture_research.relationship_features import CausalHistory


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads((root / "configs/livestock_research.json").read_text())
    _, jobs = job_plan(root, protocol)
    job = next(
        j
        for j in jobs
        if j["key"] == {"seed": 1401, "seat": 0, "opponent": "market10", "arm": "fertilizer"}
    )
    payload = load_checkpoint(root / job["path"], job["lineage"])
    if payload is None:
        raise ValueError("The fixed profiling trace is unavailable")
    validate_episode(payload, job["key"])
    history, market_history = CausalHistory(), MarketHistory()
    _plant_path.cache_clear()
    samples = {s["step"]: s["values"] for s in payload["feature_samples"]}
    state_times, full_times = [], []
    for record in payload["records"]:
        if record["player"] != 0:
            continue
        obs = record["observation"]
        start = time.perf_counter()
        past, market_past = history.observe(obs), market_history.observe(obs)
        history_end = time.perf_counter()
        if obs["step"] in samples:
            values, _ = feature_bank(obs, past, market_past)
        assembly_end = time.perf_counter()
        market_history.record_action(record["action"])
        end = time.perf_counter()
        state_times.append(1000 * (history_end - start + end - assembly_end))
        if obs["step"] in samples:
            full_times.append(1000 * (end - start))
            np.testing.assert_allclose(
                [values[k] for k in payload["feature_columns"]],
                samples[obs["step"]],
                rtol=0,
                atol=1e-12,
            )

    def stats(values):
        return {
            "samples": len(values),
            "median_ms": float(np.median(values)),
            "p95_ms": float(np.quantile(values, 0.95)),
            "max_ms": float(max(values)),
        }

    result = {
        "job": job["key"],
        "episode_path": job["path"],
        "episode_sha256": file_digest(root / job["path"]),
        "analysis_code_sha256": file_digest(Path(__file__)),
        "history_state_update": stats(state_times),
        "full_sampled_feature_pipeline": stats(full_times),
        "features_per_sample": 1500,
        "feature_vectors_matched": len(full_times),
        "scope": "One saved trace, local CPU, cache initially empty then naturally warmed; "
        "excludes policy inference, I/O and checkpoint serialization",
        "registered_timing_scope": "Policy inference is separate; "
        "registered sampled assembly excludes history-state updates",
        "games_executed": 0,
    }
    write_json(root / "reports/livestock_runtime.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
