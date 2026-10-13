import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  createSeason,
  observe,
  decide,
  step,
  exportSeason,
  comparePolicies,
  checksum,
  POLICIES,
  RULES,
} from "../public-demo/engine.js";
import { match, requireThat, runBundle } from "./replay_bundle.mjs";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const control =
  "Interactive session: may mix manual actions and public policy choices. Not a fixed-policy comparison.";
const manualReason = "Manual choice from the current legal action mask.";
function packageSeason(season, decisions, comparison) {
  return {
    evidence_type: "SYNTHETIC_ONLY",
    schema: "field-notes-evidence-v1",
    interactiveSeason: { ...exportSeason(season), control, decisions },
    pairedComparison: comparison,
  };
}
export function generate() {
  const season = createSeason(2026),
    decisions = [];
  while (!season.done) {
    const observation = observe(season),
      policy = POLICIES[season.day % POLICIES.length].id;
    const selected =
      season.day === 0
        ? { action: "work", reason: manualReason }
        : decide(policy, observation);
    decisions.push({
      day: observation.day,
      source: season.day === 0 ? "manual" : "policy",
      policy: season.day === 0 ? null : policy,
      ...selected,
      observationChecksum: checksum(observation),
    });
    step(season, selected.action);
  }
  return packageSeason(season, decisions, comparePolicies(2026, 8));
}
export function replay(exported) {
  requireThat(
    exported?.schema === "field-notes-evidence-v1" &&
      exported.evidence_type === "SYNTHETIC_ONLY",
    "Unsupported farming evidence export.",
  );
  const interactive = exported.interactiveSeason;
  requireThat(
    interactive &&
      Array.isArray(interactive.decisions) &&
      interactive.decisions.length <= RULES.days,
    "Invalid decision history.",
  );
  const season = createSeason(interactive.seed),
    decisions = [];
  for (const stored of interactive.decisions) {
    requireThat(
      stored && ["manual", "policy"].includes(stored.source),
      "Invalid decision source.",
    );
    const observation = observe(season);
    const chosen =
      stored.source === "policy"
        ? decide(stored.policy, observation)
        : { action: stored.action, reason: manualReason };
    const decision = {
      day: observation.day,
      source: stored.source,
      policy: stored.source === "policy" ? stored.policy : null,
      ...chosen,
      observationChecksum: checksum(observation),
    };
    match(decision, stored, `decision.${decisions.length}`);
    step(season, chosen.action);
    decisions.push(decision);
  }
  let comparison = null;
  if (exported.pairedComparison !== null) {
    requireThat(
      exported.pairedComparison?.seed === interactive.seed,
      "Comparison must use the interactive season's seed range.",
    );
    comparison = comparePolicies(
      exported.pairedComparison.seed,
      exported.pairedComparison.count,
    );
  }
  match(packageSeason(season, decisions, comparison), exported, "export");
  return {
    scope: "SYNTHETIC_ONLY",
    interactive_days: season.day,
    status: season.done ? "COMPLETE" : "IN_PROGRESS",
    manual_actions: decisions.filter((d) => d.source === "manual").length,
    policy_actions: decisions.filter((d) => d.source === "policy").length,
    paired_seeds: comparison?.count ?? 0,
    comparison_policy_seasons: (comparison?.count ?? 0) * POLICIES.length,
    checks: [
      "current and past legal observations recomputed",
      "policy decisions and observation checksums replayed",
      "all legal actions, resources, and terminal accounting replayed",
      "all paired environment tapes and policy summaries recomputed",
    ],
    tolerance:
      "Exact structural and numerical equality; no approximate acceptance.",
  };
}
export const options = { root, project: "kaggriculture", generate, replay };
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  try {
    runBundle(options);
  } catch (error) {
    console.error(`REPLAY_FAILED: ${error.message}`);
    process.exitCode = 1;
  }
}
