/* Authored educational surrogate. Not Kaggriculture's official interpreter or a private agent. */
export const RULES = Object.freeze({
  version: "public-farm-surrogate-v1",
  days: 24,
  plots: 4,
  startingCoins: 16,
  startingWater: 6,
  waterCapacity: 12,
  waterCost: 3,
  waterPurchase: 4,
  irrigationCost: 2,
  workIncome: 1,
});
export const CROPS = Object.freeze({
  radish: Object.freeze({
    name: "Radish",
    seedCost: 3,
    days: 3,
    yield: 4,
    basePrice: 3,
    color: "#bf695a",
  }),
  beans: Object.freeze({
    name: "Beans",
    seedCost: 5,
    days: 5,
    yield: 6,
    basePrice: 4,
    color: "#47774a",
  }),
  squash: Object.freeze({
    name: "Squash",
    seedCost: 7,
    days: 7,
    yield: 8,
    basePrice: 5,
    color: "#b57b25",
  }),
});
export const POLICIES = Object.freeze([
  {
    id: "quick",
    name: "Quick harvest",
    description: "Short crops, prompt harvests and steady sales.",
  },
  {
    id: "mixed",
    name: "Mixed planting",
    description: "A varied field, timely irrigation and current-price sales.",
  },
  {
    id: "reserve",
    name: "Cash reserve",
    description: "Keep a cash buffer and cultivate two plots at a time.",
  },
]);
const worlds = new WeakMap();
const clone = (x) => JSON.parse(JSON.stringify(x));
const require = (ok, message) => {
  if (!ok) throw new Error(message);
};
const zeroInventory = () =>
  Object.fromEntries(Object.keys(CROPS).map((k) => [k, 0]));
function random(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export function checksum(value) {
  let h = 2166136261;
  for (const c of JSON.stringify(value))
    h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return (h >>> 0).toString(16).padStart(8, "0");
}
function makeWorld(seed) {
  const r = random(seed),
    tape = [];
  for (let day = 0; day < RULES.days; day++) {
    const roll = r(),
      rain = roll < 0.5 ? 0 : roll < 0.84 ? 1 : 2;
    const prices = Object.fromEntries(
      Object.entries(CROPS).map(([k, c], i) => [
        k,
        Math.max(
          1,
          Math.round(
            c.basePrice * (0.77 + 0.46 * r() + 0.16 * Math.sin(day * 0.53 + i)),
          ),
        ),
      ]),
    );
    tape.push({
      rain,
      condition: ["Dry", "Light rain", "Steady rain"][rain],
      prices,
    });
  }
  return { seed, tape };
}
function emptyPlot(id) {
  return { id, crop: null, growth: 0, moisture: 2, stress: 0, ripeDays: 0 };
}
export function createSeason(seed = 2026) {
  require(Number.isInteger(seed) &&
    seed >= 1 &&
    seed <= 999999999, "Use an integer seed from 1 to 999999999.");
  const world = makeWorld(seed),
    state = {
      day: 0,
      done: false,
      coins: RULES.startingCoins,
      water: RULES.startingWater,
      plots: Array.from({ length: RULES.plots }, (_, i) => emptyPlot(i)),
      inventory: zeroInventory(),
      current: clone(world.tape[0]),
      history: [],
      ledger: {
        work: 0,
        sales: 0,
        seeds: 0,
        waterSpending: 0,
        waterCollected: 0,
        waterBought: 0,
        waterUsed: 0,
        harvested: zeroInventory(),
        sold: zeroInventory(),
      },
    };
  worlds.set(state, world);
  return state;
}
export function ready(plot) {
  return plot.crop !== null && plot.growth >= CROPS[plot.crop].days;
}
export function harvestYield(plot) {
  return plot.crop === null
    ? 0
    : Math.max(
        1,
        CROPS[plot.crop].yield -
          Math.floor(plot.stress / 2) -
          Math.max(0, plot.ripeDays - 3),
      );
}
export function assets(state) {
  return (
    state.coins +
    Object.entries(state.inventory).reduce(
      (sum, [crop, n]) => sum + n * state.current.prices[crop],
      0,
    )
  );
}
export function legalActions(state) {
  if (state.done) return [];
  const actions = [];
  for (const p of state.plots) {
    if (p.crop === null)
      for (const [crop, c] of Object.entries(CROPS))
        if (state.coins >= c.seedCost)
          actions.push({
            id: `plant:${p.id}:${crop}`,
            type: "plant",
            plot: p.id,
            crop,
            label: `Plant ${c.name.toLowerCase()} · ${c.seedCost} coins`,
          });
    if (
      p.crop !== null &&
      !ready(p) &&
      p.moisture <= 2 &&
      state.water >= RULES.irrigationCost
    )
      actions.push({
        id: `water:${p.id}`,
        type: "water",
        plot: p.id,
        label: `Water plot ${p.id + 1} · 2 water`,
      });
    if (ready(p))
      actions.push({
        id: `harvest:${p.id}`,
        type: "harvest",
        plot: p.id,
        label: `Harvest ${harvestYield(p)} ${CROPS[p.crop].name.toLowerCase()}`,
      });
  }
  for (const [crop, count] of Object.entries(state.inventory))
    if (count > 0)
      actions.push({
        id: `sell:${crop}`,
        type: "sell",
        crop,
        label: `Sell ${count} ${CROPS[crop].name.toLowerCase()} · ${count * state.current.prices[crop]} coins`,
      });
  if (state.coins >= RULES.waterCost && state.water < RULES.waterCapacity)
    actions.push({
      id: "refill",
      type: "refill",
      label: `Buy ${Math.min(RULES.waterPurchase, RULES.waterCapacity - state.water)} water · 3 coins`,
    });
  actions.push(
    { id: "work", type: "work", label: "Do farm work · earn 1 coin" },
    { id: "wait", type: "wait", label: "Wait · no resource cost" },
  );
  return actions;
}
function deepFreeze(x) {
  if (x && typeof x === "object") {
    Object.freeze(x);
    for (const v of Object.values(x)) deepFreeze(v);
  }
  return x;
}
export function observe(state) {
  // Explicit allowlist: no seed, future weather, tape, hidden objects or final reward.
  return deepFreeze({
    day: Math.min(state.day + 1, RULES.days),
    daysRemaining: RULES.days - state.day,
    coins: state.coins,
    water: state.water,
    plots: clone(state.plots),
    inventory: clone(state.inventory),
    weather: clone(state.current),
    actions: legalActions(state).map((a) => ({ ...a })),
    past: state.history.map((h) => ({
      day: h.day,
      weather: clone(h.weather),
      action: h.action,
      coins: h.coins,
      water: h.water,
    })),
  });
}
export function decide(policyId, observation) {
  require(POLICIES.some((p) => p.id === policyId), "Unknown public policy.");
  const o = observation,
    find = (type, test = () => true) =>
      o.actions.find((a) => a.type === type && test(a));
  let action, reason;
  const choose = (a, r) => (a ? { action: a.id, reason: r } : null);
  const ripe = o.plots
    .filter(ready)
    .sort(
      (a, b) =>
        b.ripeDays - a.ripeDays ||
        harvestYield(b) * o.weather.prices[b.crop] -
          harvestYield(a) * o.weather.prices[a.crop],
    );
  if (ripe.length)
    return choose(
      find("harvest", (a) => a.plot === ripe[0].id),
      "Harvest a ready crop before its stored field yield declines.",
    );
  const sales = o.actions
    .filter((a) => a.type === "sell")
    .sort(
      (a, b) =>
        o.inventory[b.crop] * o.weather.prices[b.crop] -
        o.inventory[a.crop] * o.weather.prices[a.crop],
    );
  if (
    sales.length &&
    (policyId !== "mixed" ||
      o.daysRemaining <= 2 ||
      o.coins < 7 ||
      sales.some((a) => o.weather.prices[a.crop] >= CROPS[a.crop].basePrice))
  )
    return choose(
      sales[0],
      "Sell available produce at the current observed market price.",
    );
  const thirsty = o.plots
    .filter((p) => p.crop && !ready(p) && p.moisture === 0)
    .sort((a, b) => b.growth - a.growth || b.stress - a.stress);
  if (thirsty.length && o.weather.rain === 0) {
    action = find("water", (a) => a.plot === thirsty[0].id);
    if (action)
      return choose(action, "Irrigate a dry growing crop; today has no rain.");
    action = find("refill");
    if (action)
      return choose(
        action,
        "Replenish the reservoir before the next irrigation decision.",
      );
  }
  const growing = o.plots.filter((p) => p.crop).length;
  if (policyId === "reserve" && o.coins < 10)
    return choose(
      find("work"),
      "Maintain a cash buffer rather than committing to another seed purchase.",
    );
  for (const p of o.plots.filter((p) => !p.crop)) {
    if (policyId === "reserve" && growing >= 2) break;
    let preferred =
      policyId === "quick"
        ? "radish"
        : policyId === "reserve"
          ? "beans"
          : ["radish", "beans", "squash", "radish"][p.id];
    if (CROPS[preferred].days + 1 > o.daysRemaining) preferred = "radish";
    if (CROPS[preferred].days + 1 <= o.daysRemaining) {
      action = find("plant", (a) => a.plot === p.id && a.crop === preferred);
      if (action)
        return choose(
          action,
          "Plant a crop with enough remaining days to grow and be harvested.",
        );
    }
  }
  if (sales.length)
    return choose(
      sales[0],
      "Convert stored crops to cash while no higher-priority field action is available.",
    );
  return choose(
    find("work"),
    "Use an otherwise idle day for a small guaranteed cash return.",
  );
}
export function validateState(s) {
  require(Number.isInteger(s.day) &&
    s.day >= 0 &&
    s.day <= RULES.days &&
    s.done === (s.day === RULES.days), "Invalid season progress.");
  require(Number.isInteger(s.coins) &&
    s.coins >= 0 &&
    Number.isInteger(s.water) &&
    s.water >= 0 &&
    s.water <= RULES.waterCapacity, "Invalid resources.");
  require(s.coins ===
    RULES.startingCoins +
      s.ledger.work +
      s.ledger.sales -
      s.ledger.seeds -
      s.ledger.waterSpending, "Coin conservation failed.");
  require(s.water ===
    RULES.startingWater +
      s.ledger.waterCollected +
      s.ledger.waterBought -
      s.ledger.waterUsed, "Water conservation failed.");
  for (const crop of Object.keys(CROPS))
    require(Number.isInteger(s.inventory[crop]) &&
      s.inventory[crop] >= 0 &&
      s.inventory[crop] ===
        s.ledger.harvested[crop] -
          s.ledger.sold[crop], "Inventory conservation failed.");
  for (const p of s.plots)
    require(p.crop === null || Object.hasOwn(CROPS, p.crop), "Unknown crop.");
  return true;
}
export function step(state, actionId) {
  const world = worlds.get(state);
  require(world, "Unknown season instance.");
  validateState(state);
  require(!state.done, "The season is complete. Reset to begin another.");
  const action = legalActions(state).find((a) => a.id === actionId);
  require(action, "That action is not legal in the current observation.");
  // Validate first and commit last: rejected actions cannot partially alter a season.
  const next = clone(state),
    weather = clone(world.tape[state.day]),
    events = [];
  const plot = action.plot === undefined ? null : next.plots[action.plot];
  if (action.type === "plant") {
    next.coins -= CROPS[action.crop].seedCost;
    next.ledger.seeds += CROPS[action.crop].seedCost;
    Object.assign(plot, {
      crop: action.crop,
      growth: 0,
      stress: 0,
      ripeDays: 0,
    });
  }
  if (action.type === "water") {
    next.water -= RULES.irrigationCost;
    next.ledger.waterUsed += RULES.irrigationCost;
    plot.moisture = Math.min(4, plot.moisture + 3);
  }
  if (action.type === "harvest") {
    const crop = plot.crop,
      units = harvestYield(plot);
    next.inventory[crop] += units;
    next.ledger.harvested[crop] += units;
    events.push(`${units} ${CROPS[crop].name.toLowerCase()} moved to storage.`);
    Object.assign(plot, { crop: null, growth: 0, stress: 0, ripeDays: 0 });
  }
  if (action.type === "sell") {
    const crop = action.crop,
      units = next.inventory[crop],
      value = units * weather.prices[crop];
    next.coins += value;
    next.ledger.sales += value;
    next.ledger.sold[crop] += units;
    next.inventory[crop] = 0;
  }
  if (action.type === "refill") {
    const water = Math.min(
      RULES.waterPurchase,
      RULES.waterCapacity - next.water,
    );
    next.coins -= RULES.waterCost;
    next.ledger.waterSpending += RULES.waterCost;
    next.water += water;
    next.ledger.waterBought += water;
  }
  if (action.type === "work") {
    next.coins += RULES.workIncome;
    next.ledger.work += RULES.workIncome;
  }
  const collected = Math.min(
    RULES.waterCapacity - next.water,
    weather.rain * 2,
  );
  next.water += collected;
  next.ledger.waterCollected += collected;
  for (const p of next.plots) {
    p.moisture = Math.min(4, p.moisture + weather.rain);
    if (!p.crop) {
      p.moisture = Math.max(0, p.moisture - 1);
      continue;
    }
    if (ready(p)) {
      p.ripeDays++;
      continue;
    }
    if (p.moisture > 0) {
      p.growth++;
      p.moisture--;
    } else {
      p.stress++;
      events.push(`Plot ${p.id + 1} missed a growth day: dry soil.`);
    }
    if (p.stress >= 6) {
      events.push(`Plot ${p.id + 1} withered after six dry growth days.`);
      Object.assign(p, { crop: null, growth: 0, stress: 0, ripeDays: 0 });
    } else if (ready(p)) events.push(`Plot ${p.id + 1} is ready to harvest.`);
  }
  next.day++;
  next.done = next.day === RULES.days;
  next.history.push({
    day: next.day,
    action: action.id,
    label: action.label,
    weather,
    coins: next.coins,
    water: next.water,
    events,
  });
  if (!next.done) next.current = clone(world.tape[next.day]);
  validateState(next);
  Object.assign(state, next);
  return clone(next.history.at(-1));
}
export function runSeason(seed, policyId) {
  const s = createSeason(seed);
  while (!s.done) {
    const decision = decide(policyId, observe(s));
    step(s, decision.action);
  }
  return s;
}
export function exportSeason(state) {
  const world = worlds.get(state);
  require(world, "Unknown season instance.");
  return {
    schema: RULES.version,
    evidence_type: "SYNTHETIC_ONLY",
    scope:
      "Authored educational farming surrogate. No official-engine, private-policy or competition-performance equivalence.",
    seed: world.seed,
    rules: RULES,
    crops: CROPS,
    status: state.done ? "COMPLETE" : "IN_PROGRESS",
    daysCompleted: state.day,
    coins: state.coins,
    water: state.water,
    inventory: clone(state.inventory),
    plots: clone(state.plots),
    assets: assets(state),
    profit: assets(state) - RULES.startingCoins,
    valuation:
      "Coins plus stored crops at the current observed market prices; unharvested plants have zero closing value.",
    ledger: clone(state.ledger),
    history: clone(state.history),
    observedEnvironmentChecksum: checksum(state.history.map((h) => h.weather)),
  };
}
export function comparePolicies(seed, count = 8) {
  require(Number.isInteger(count) &&
    count >= 2 &&
    count <= 32, "Compare 2–32 paired seasons.");
  require(Number.isInteger(seed) &&
    seed >= 1 &&
    seed + count - 1 <= 999999999, "Comparison seed range is invalid.");
  const seasons = [];
  for (let i = 0; i < count; i++) {
    const row = { seed: seed + i, policies: {} };
    for (const policy of POLICIES) {
      const s = runSeason(seed + i, policy.id),
        r = exportSeason(s);
      row.policies[policy.id] = {
        assets: r.assets,
        profit: r.profit,
        weatherChecksum: r.observedEnvironmentChecksum,
        harvested: r.ledger.harvested,
        actions: r.history.map((h) => h.action),
      };
    }
    require(new Set(Object.values(row.policies).map((p) => p.weatherChecksum))
      .size === 1, "Paired environmental tapes differ.");
    seasons.push(row);
  }
  const summary = POLICIES.map((policy) => {
    const values = seasons.map((s) => s.policies[policy.id].assets),
      deltas = seasons.map(
        (s) => s.policies[policy.id].assets - s.policies.quick.assets,
      );
    return {
      ...policy,
      meanAssets: values.reduce((a, b) => a + b, 0) / count,
      minAssets: Math.min(...values),
      maxAssets: Math.max(...values),
      meanDeltaVsQuick: deltas.reduce((a, b) => a + b, 0) / count,
      pairedWinsVsQuick: deltas.filter((x) => x > 0).length,
      pairedTiesVsQuick: deltas.filter((x) => x === 0).length,
    };
  });
  return {
    evidence_type: "SYNTHETIC_ONLY",
    scope:
      "Descriptive paired comparison of fixed educational policies. Same generated weather and market sequence per seed; no policy tuning or generalization claim.",
    seed,
    count,
    days: RULES.days,
    summary,
    seasons,
  };
}

/** Describe matched outcomes without treating eight visible seeds as a holdout. */
export function pairedDiagnostics(comparison) {
  require(comparison && comparison.evidence_type === "SYNTHETIC_ONLY",
    "Paired diagnostics require a synthetic comparison.");
  require(Number.isInteger(comparison.count) && comparison.count >= 2 &&
    comparison.count <= 32 && Array.isArray(comparison.seasons) &&
    comparison.seasons.length === comparison.count, "Incomplete paired seasons.");
  const ids = POLICIES.map(policy => policy.id);
  const rows = comparison.seasons.map((season, index) => {
    require(season.seed === comparison.seed + index, "Unaligned comparison seeds.");
    require(season.policies && Object.keys(season.policies).sort().join() ===
      [...ids].sort().join(), "Missing or unexpected policy outcomes.");
    require(ids.every(id => Number.isFinite(season.policies[id].assets)) &&
      new Set(ids.map(id => season.policies[id].weatherChecksum)).size === 1 &&
      typeof season.policies.quick.weatherChecksum === "string",
    "Invalid assets or unpaired environmental tapes.");
    return {
      seed: season.seed,
      assets: Object.fromEntries(ids.map(id => [id, season.policies[id].assets])),
      deltas: Object.fromEntries(ids.map(id => [id,
        season.policies[id].assets - season.policies.quick.assets])),
    };
  });
  return {
    baseline: "quick",
    scope: "Descriptive differences on the displayed paired seeds; no significance or generalization claim.",
    rows,
    policies: Object.fromEntries(ids.map(id => {
      const deltas = rows.map(row => row.deltas[id]).sort((a, b) => a - b);
      const middle = Math.floor(deltas.length / 2);
      return [id, {
        wins: deltas.filter(delta => delta > 0).length,
        ties: deltas.filter(delta => delta === 0).length,
        losses: deltas.filter(delta => delta < 0).length,
        worstDelta: deltas[0],
        bestDelta: deltas.at(-1),
        medianDelta: deltas.length % 2 ? deltas[middle] :
          (deltas[middle - 1] + deltas[middle]) / 2,
      }];
    })),
  };
}
