"""Execute the bounded development reference; reuse checksum-verified episodes."""

import argparse
from pathlib import Path

from kaggriculture_research.audit import audit_episodes
from kaggriculture_research.environment import read_protocol
from kaggriculture_research.progress import Progress
from kaggriculture_research.rollouts import run_references


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    protocol = read_protocol(args.root)
    progress = Progress(protocol["heartbeat_seconds"])
    episodes, reused = run_references(args.root, protocol, progress)
    with progress.stage("observation_feature_audit"):
        summary = audit_episodes(args.root, episodes, protocol)
    progress.log(
        "verified",
        "foundation",
        progress.started,
        episodes=summary["episodes"],
        reused_episodes=reused,
        candidates=summary["candidate_features"],
        feature_research_complete=False,
    )


if __name__ == "__main__":
    main()
