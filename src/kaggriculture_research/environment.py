"""Pinned official engine: no alternate game mechanics or private simulator state."""

import importlib.metadata
import json
from pathlib import Path
from typing import Any

import kaggle_environments
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from kaggriculture_research.artifacts import file_digest

PINNED_VERSION = "1.32.7"
__all__ = ["game", "engine_manifest", "make_environment", "read_protocol", "validate_protocol"]


def engine_manifest() -> dict[str, Any]:
    version = importlib.metadata.version("kaggle-environments")
    if version != PINNED_VERSION:
        raise ValueError(f"Expected official engine {PINNED_VERSION}, found {version}")
    root = Path(kaggle_environments.__file__).parent
    files = [
        "core.py",
        "agent.py",
        "utils.py",
        "schemas.json",
        "envs/kaggriculture/kaggriculture.py",
        "envs/kaggriculture/kaggriculture.json",
    ]
    return {
        "package": "kaggle-environments",
        "version": version,
        "files": {f: file_digest(root / f) for f in files},
    }


def make_environment(seed: int, configuration: dict[str, Any] | None = None):
    engine_manifest()
    config = dict(configuration or {"episodeSteps": 720})
    if "seed" in config:
        raise ValueError("Set the seed through the experiment protocol only")
    env = kaggle_environments.make("kaggriculture", configuration={**config, "seed": seed})
    if env.configuration.get("seed") is not None:
        raise ValueError("Simulator exposed its seed to the agent")
    return env


def validate_protocol(protocol: dict[str, Any]) -> None:
    pools = [protocol[name] for name in ("development_seeds", "validation_seeds", "holdout_seeds")]
    for pool in pools:
        if not pool or len(set(pool)) != len(pool):
            raise ValueError("Each seed pool must be nonempty and unique")
    if len(set(sum(pools, []))) != sum(map(len, pools)):
        raise ValueError("Seed pools overlap; episodes cannot cross validation boundaries")
    if protocol["configuration"] != {"episodeSteps": 720}:
        raise ValueError("Foundation comparisons must use the unmodified official configuration")
    if protocol["environment_version"] != PINNED_VERSION:
        raise ValueError("Protocol engine version differs")
    if protocol["seats"] != [0, 1]:
        raise ValueError("Evaluate both seats for every seed")
    # The upstream random_agent creates random.Random() without a seed on every call.
    for key in ("reference_agent", "opponent_agent"):
        if protocol[key] not in {"pass", "starter"}:
            raise ValueError("Foundation references must be deterministic official agents")


def read_protocol(root: Path) -> dict[str, Any]:
    protocol = json.loads((root / "configs/research.json").read_text())
    validate_protocol(protocol)
    return protocol
