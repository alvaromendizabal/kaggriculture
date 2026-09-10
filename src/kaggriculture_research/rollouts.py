"""Paired full-season references and exact callback-observation capture."""

import copy
import time
from pathlib import Path
from typing import Any

from kaggriculture_research.artifacts import digest, file_digest, load_checkpoint, save_checkpoint
from kaggriculture_research.environment import engine_manifest, game, make_environment
from kaggriculture_research.features import PUBLIC_FIELDS
from kaggriculture_research.progress import Progress


def semantic_episode_hash(payload: dict[str, Any]) -> str:
    # Timing measurements are intentionally outside the determinism claim.
    records = [
        {k: v for k, v in row.items() if k != "latency_ms"} for row in payload["observations"]
    ]
    return digest(
        {
            "observations": records,
            "rewards": payload["rewards"],
            "statuses": payload["statuses"],
            "states": payload["states"],
        }
    )


def run_episode(seed: int, seat: int, configuration: dict[str, Any]) -> dict[str, Any]:
    env = make_environment(seed, configuration)
    records: list[dict[str, Any]] = []
    names = ["starter", "pass"] if seat == 0 else ["pass", "starter"]

    def instrument(name: str):
        policy = game.agents[name]

        def agent(obs, config):
            if config.get("seed") is not None:
                raise ValueError("Seed leaked into the agent configuration")
            legal = {k: copy.deepcopy(obs[k]) for k in PUBLIC_FIELDS}
            before = copy.deepcopy(legal)
            start = time.perf_counter()
            action = policy(legal)
            latency_ms = (time.perf_counter() - start) * 1000
            records.append(
                {
                    "player": obs["player"],
                    "policy": name,
                    "observation": before,
                    "action": copy.deepcopy(action),
                    "latency_ms": latency_ms,
                }
            )
            return action

        return agent

    env.run([instrument(n) for n in names])
    statuses = [s.status for s in env.state]
    if statuses != ["DONE", "DONE"]:
        raise RuntimeError(f"Unsuccessful simulator episode: {statuses}")
    if len(env.steps) != configuration["episodeSteps"]:
        raise RuntimeError("Episode ended before the official full horizon")
    rewards = [s.reward for s in env.state]
    payload = {
        "seed": seed,
        "starter_seat": seat,
        "policies": names,
        "configuration": dict(env.configuration),
        "states": len(env.steps),
        "decision_steps": len(records) // 2,
        "rewards": rewards,
        "statuses": statuses,
        "observations": records,
        "starter_win": float(rewards[seat] > rewards[1 - seat]),
        "starter_tie": float(rewards[seat] == rewards[1 - seat]),
        "coin_margin": rewards[seat] - rewards[1 - seat],
    }
    payload["semantic_sha256"] = semantic_episode_hash(payload)
    return payload


def run_references(root: Path, protocol: dict[str, Any], progress: Progress) -> tuple[list, int]:
    episodes, reused = [], 0
    code_path = Path(__file__)
    common = {
        "engine": engine_manifest(),
        "rollout_code": file_digest(code_path),
        "environment_code": file_digest(code_path.with_name("environment.py")),
        "configuration": protocol["configuration"],
        "reference": "official_starter",
        "opponent": "official_pass",
    }
    for seed in protocol["development_seeds"]:
        for seat in protocol["seats"]:
            lineage = {**common, "seed": seed, "starter_seat": seat}
            path = root / "artifacts/episodes" / (digest(lineage) + ".json.gz")
            with progress.stage(f"development_seed_{seed}_seat_{seat}"):
                result = load_checkpoint(path, lineage)
                if result is None:
                    result = run_episode(seed, seat, protocol["configuration"])
                    save_checkpoint(path, lineage, result)
                else:
                    reused += 1
                if result["semantic_sha256"] != semantic_episode_hash(result):
                    raise ValueError("Episode semantic digest differs from checkpoint")
                episodes.append(result)
    return episodes, reused
