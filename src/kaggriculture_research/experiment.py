"""Bounded development-only paired ablations, private traces and honest summaries."""

import copy
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from kaggriculture_research.artifacts import (
    digest,
    file_digest,
    load_checkpoint,
    save_checkpoint,
    write_json,
)
from kaggriculture_research.crop_policy import FEATURES, VARIANTS, CropPolicy
from kaggriculture_research.environment import (
    engine_manifest,
    game,
    make_environment,
    validate_protocol,
)
from kaggriculture_research.features import PUBLIC_FIELDS
from kaggriculture_research.progress import Progress


def semantic_hash(payload: dict) -> str:
    return digest({k: v for k, v in payload.items() if k not in ("latency_ms", "semantic_sha256")})


def run_game(
    seed: int, seat: int, variant: str, opponent: str, configuration: dict, max_hands: int
) -> dict:
    policy = CropPolicy(variant, max_hands)
    if opponent == "starter":
        rival = game.agents["starter"]
    elif opponent == "carrot_scheduler":
        rival = CropPolicy("full", 0, "CARROT")
    else:
        raise ValueError(f"Unsupported opponent: {opponent}")
    records, latencies = [], []
    action_counts = Counter()
    ineffective = 0
    latest = {}

    def instrument(which, actor):
        def call(obs, config):
            nonlocal ineffective
            if config.get("seed") is not None:
                raise ValueError("Seed entered the policy configuration")
            legal = {k: copy.deepcopy(obs[k]) for k in PUBLIC_FIELDS}
            before = copy.deepcopy(legal)
            start = time.perf_counter()
            action = actor(legal)
            elapsed = (time.perf_counter() - start) * 1000
            if legal != before:
                raise ValueError("Policy mutated the callback observation")
            row = {"player": obs["player"], "observation": before, "action": action}
            if which == "candidate":
                row["diagnostics"] = copy.deepcopy(policy.last_diagnostics)
                ineffective += policy.last_diagnostics["ineffective_farm_actions"]
                latencies.append(elapsed)
                action_counts.update(a[0] for a in [action["farmer"], *action["hands"]])
                action_counts.update(
                    "plant_" + a[1] for a in [action["farmer"], *action["hands"]] if a[0] == "PLANT"
                )
                latest.update(before)
            records.append(row)
            return action

        return call

    env = make_environment(seed, configuration)
    actors = [instrument("candidate", policy), instrument("opponent", rival)]
    env.run(actors if seat == 0 else list(reversed(actors)))
    statuses = [s.status for s in env.state]
    if statuses != ["DONE", "DONE"] or len(env.steps) != 720 or len(latencies) != 719:
        raise RuntimeError(f"Incomplete official episode: {statuses}, states={len(env.steps)}")
    rewards = [s.reward for s in env.state]
    # Final private inventory is available to the evaluator, never fed to either policy.
    private = env.state[seat].observation["private"]
    unsold = sum(
        n
        for inv in [private["shed"], *private["inventories"]]
        for c, n in inv.items()
        if c in game.PRODUCTS
    )
    summary = {
        "seed": seed,
        "seat": seat,
        "variant": variant,
        "opponent": opponent,
        "match_score": float(rewards[seat] > rewards[1 - seat])
        + 0.5 * (rewards[seat] == rewards[1 - seat]),
        "coins": rewards[seat],
        "coin_margin": rewards[seat] - rewards[1 - seat],
        "unsold_product_units": unsold,
        "ineffective_farm_actions": ineffective,
        "plants": action_counts["PLANT"],
        "harvests": action_counts["HARVEST"],
        "waters": action_counts["WATER"],
        "passes": action_counts["PASS"],
        **{"plant_" + crop: action_counts["plant_" + crop] for crop in sorted(game.CROPS)},
    }
    payload = {
        "summary": summary,
        "records": records,
        "statuses": statuses,
        "states": len(env.steps),
        "latency_ms": latencies,
    }
    payload["semantic_sha256"] = semantic_hash(payload)
    return payload


def paired_summary(frame: pd.DataFrame, resamples: int, seed: int) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(seed)  # Statistical resampling only, outside policy.
    for variant in VARIANTS[1:]:
        joined = frame[frame.variant == "full"].merge(
            frame[frame.variant == variant],
            on=["seed", "seat", "opponent"],
            suffixes=("_full", "_ablated"),
            validate="one_to_one",
        )
        if len(joined) != len(frame[frame.variant == "full"]):
            raise ValueError("Missing paired episode")
        for metric in ("match_score", "coin_margin", "coins", "unsold_product_units"):
            diff = joined[f"{metric}_full"] - joined[f"{metric}_ablated"]
            clusters = diff.groupby(joined.seed).mean()
            draws = rng.choice(
                clusters.to_numpy(), size=(resamples, len(clusters)), replace=True
            ).mean(axis=1)
            rows.append(
                {
                    "ablation": variant,
                    "metric": metric,
                    "full_minus_ablated": float(clusters.mean()),
                    "bootstrap_low": float(np.quantile(draws, 0.025)),
                    "bootstrap_high": float(np.quantile(draws, 0.975)),
                    "seed_clusters": len(clusters),
                    "seed_differences": clusters.to_json(),
                }
            )
    return pd.DataFrame(rows)


def run_experiment(
    root: Path,
    protocol: dict,
    foundation_protocol: dict,
    progress: Progress,
    checkpoint_ready=None,
) -> dict:
    validate_protocol(foundation_protocol)
    if protocol["development_seeds"] != foundation_protocol["development_seeds"]:
        raise ValueError("Only the registered development seed group may be used")
    if protocol["variants"] != list(VARIANTS) or protocol["configuration"] != {"episodeSteps": 720}:
        raise ValueError("Experiment differs from the registered variants or official horizon")
    count = (
        len(protocol["variants"])
        * len(protocol["opponents"])
        * len(protocol["development_seeds"])
        * len(protocol["seats"])
    )
    if count != 80 or count > protocol["max_games"] or protocol["seats"] != [0, 1]:
        raise ValueError("Experiment does not match the bounded paired design")
    source = Path(__file__).parent
    common = {
        "engine": engine_manifest(),
        "protocol": protocol,
        "code": {
            name: file_digest(source / name)
            for name in (
                "experiment.py",
                "crop_policy.py",
                "features.py",
                "environment.py",
                "artifacts.py",
            )
        },
    }
    rows, timing, manifest = [], {}, []
    reused = 0
    start = time.monotonic()
    for seed in protocol["development_seeds"]:
        for opponent in protocol["opponents"]:
            for seat in protocol["seats"]:
                for variant in protocol["variants"]:
                    if time.monotonic() - start > protocol["max_seconds"]:
                        raise TimeoutError(
                            "Research time budget reached; completed checkpoints are reusable"
                        )
                    lineage = {
                        **common,
                        "seed": seed,
                        "opponent": opponent,
                        "seat": seat,
                        "variant": variant,
                    }
                    path = root / "artifacts/feature_episodes" / (digest(lineage) + ".json.gz")
                    with progress.stage(f"{variant}_{opponent}_{seed}_seat{seat}"):
                        payload = load_checkpoint(path, lineage)
                        if payload is None:
                            payload = run_game(
                                seed,
                                seat,
                                variant,
                                opponent,
                                protocol["configuration"],
                                protocol["max_hands"],
                            )
                            save_checkpoint(path, lineage, payload)
                        else:
                            reused += 1
                        if payload["semantic_sha256"] != semantic_hash(payload):
                            raise ValueError("Episode semantic hash mismatch")
                        if checkpoint_ready is not None:
                            checkpoint_ready(path)
                        rows.append(payload["summary"])
                        timing.setdefault(variant, []).extend(payload["latency_ms"])
                        manifest.append(
                            {
                                "path": path.relative_to(root).as_posix(),
                                "sha256": file_digest(path),
                                "semantic_sha256": payload["semantic_sha256"],
                            }
                        )
    frame = pd.DataFrame(rows)
    frame.to_csv(root / "reports/feature_games.csv", index=False)
    pairs = paired_summary(frame, protocol["bootstrap_resamples"], protocol["bootstrap_seed"])
    pairs.to_csv(root / "reports/feature_ablations.csv", index=False)
    groups = (
        frame.groupby(["variant", "opponent"])
        .agg(
            games=("match_score", "size"),
            match_score=("match_score", "mean"),
            mean_coins=("coins", "mean"),
            mean_coin_margin=("coin_margin", "mean"),
            mean_unsold_units=("unsold_product_units", "mean"),
            ineffective_farm_actions=("ineffective_farm_actions", "sum"),
        )
        .reset_index()
    )
    summary = {
        "experiment": protocol["experiment"],
        "protocol_sha256": digest(protocol),
        "lineage": common,
        "games": len(rows),
        "reused_games": reused,
        "seed_clusters": 4,
        "feature_templates": FEATURES,
        "generated_templates": sum(map(len, FEATURES.values())),
        "screened_templates": sum(map(len, FEATURES.values())),
        "retained_templates": 0,
        "rejected_templates": 0,
        "provisional_templates": sum(map(len, FEATURES.values())),
        "screening": "mechanics, availability and family ablation; no final selection",
        "feature_completion_gate": "closed",
        "validation_or_holdout_used": False,
        "group_results": groups.to_dict("records"),
        "paired_results": pairs.to_dict("records"),
        "latency_ms": {
            v: {"median": float(np.median(t)), "p95": float(np.quantile(t, 0.95)), "max": max(t)}
            for v, t in timing.items()
        },
        "artifact_manifest": manifest,
        "limitations": [
            "Four development seed clusters only",
            "Two limited deterministic opponents",
            "Policy-component effects depend on the fixed scheduler and weights",
            "Current-price irrigated scenarios are not future market forecasts",
            "Shared environmental RNG may diverge when policies change farm state",
            "No final model selection, competitive claim, or leaderboard submission",
        ],
    }
    write_json(root / "reports/feature_research.json", summary)
    return summary
