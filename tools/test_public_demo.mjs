import { replay } from "./replay_public_demo.mjs";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  RULES,
  POLICIES,
  CROPS,
  createSeason,
  observe,
  decide,
  legalActions,
  step,
  ready,
  validateState,
  exportSeason,
  runSeason,
  comparePolicies,
} from "../public-demo/engine.js";
import { mount } from "../public-demo/app.js";
let passed = 0;
const test = (name, run) => {
  run();
  passed++;
  console.log(`PASS ${name}`);
};
const serialized = (x) => JSON.stringify(x),
  clone = (x) => JSON.parse(serialized(x));
test("Seeded seasons replay every action, weather and price exactly", () => {
  assert.deepEqual(
    exportSeason(runSeason(2026, "quick")),
    exportSeason(runSeason(2026, "quick")),
  );
  assert.notDeepEqual(
    exportSeason(runSeason(2026, "quick")).history.map((x) => x.weather),
    exportSeason(runSeason(2027, "quick")).history.map((x) => x.weather),
  );
});
test("The policy observation is an immutable, explicit current-and-past allowlist", () => {
  const s = createSeason(),
    o = observe(s);
  assert.deepEqual(Object.keys(o).sort(), [
    "actions",
    "coins",
    "day",
    "daysRemaining",
    "inventory",
    "past",
    "plots",
    "water",
    "weather",
  ]);
  for (const forbidden of ["seed", "tape", "future", "reward", "ledger"])
    assert.equal(forbidden in o, false);
  assert.equal(o.past.length, 0);
  assert.equal(o.weather.rain, s.current.rain);
  assert.throws(() => {
    o.plots[0].growth = 99;
  }, TypeError);
  assert.equal(s.plots[0].growth, 0);
  const d = decide("quick", o);
  assert(o.actions.some((a) => a.id === d.action));
});
test("All public policies stay legal and conserve coins, water and inventory each turn", () => {
  for (const seed of [1, 7, 42, 2026, 999999999])
    for (const p of POLICIES) {
      const s = createSeason(seed);
      while (!s.done) {
        const o = observe(s),
          d = decide(p.id, o);
        assert(legalActions(s).some((a) => a.id === d.action));
        step(s, d.action);
        assert(validateState(s));
        assert.equal(s.history.length, s.day);
      }
      assert.equal(s.day, 24);
      assert.equal(legalActions(s).length, 0);
    }
});
test("Illegal and stale actions are rejected before any mutation", () => {
  const s = createSeason(42);
  for (const action of ["harvest:0", "sell:radish", "bogus", "water:0"]) {
    const before = serialized(s);
    assert.throws(() => step(s, action), /not legal/);
    assert.equal(serialized(s), before);
  }
  step(s, "plant:0:radish");
  const before = serialized(s);
  assert.throws(() => step(s, "plant:0:beans"), /not legal/);
  assert.equal(serialized(s), before);
});
test("Growth, harvest and sale change computed inventory and cash with a conserved ledger", () => {
  const s = createSeason(42);
  step(s, "plant:0:radish");
  while (!ready(s.plots[0])) {
    const a = legalActions(s).find(
      (x) => x.id === "water:0" && s.plots[0].moisture === 0,
    );
    step(s, a?.id ?? "wait");
  }
  step(s, "harvest:0");
  assert(s.inventory.radish > 0);
  const units = s.inventory.radish,
    coins = s.coins,
    price = s.current.prices.radish;
  step(s, "sell:radish");
  assert.equal(s.coins, coins + units * price);
  assert.equal(s.inventory.radish, 0);
  assert.equal(s.ledger.harvested.radish, s.ledger.sold.radish);
});
test("Terminal state rejects extra days and closing assets exclude standing crops", () => {
  const s = runSeason(6, "mixed"),
    before = serialized(s),
    out = exportSeason(s);
  assert.throws(() => step(s, "work"), /complete/);
  assert.equal(serialized(s), before);
  assert.equal(out.status, "COMPLETE");
  assert.equal(
    out.assets,
    s.coins +
      Object.entries(s.inventory).reduce(
        (v, [k, n]) => v + n * s.current.prices[k],
        0,
      ),
  );
  assert.equal(out.evidence_type, "SYNTHETIC_ONLY");
});
test("Paired comparisons share complete environmental tapes and compute their summaries", () => {
  const r = comparePolicies(200, 8);
  assert.deepEqual(r, comparePolicies(200, 8));
  assert.equal(r.seasons.length, 8);
  for (const s of r.seasons)
    assert.equal(
      new Set(Object.values(s.policies).map((p) => p.weatherChecksum)).size,
      1,
    );
  for (const row of r.summary) {
    const xs = r.seasons.map((s) => s.policies[row.id].assets),
      deltas = r.seasons.map(
        (s) => s.policies[row.id].assets - s.policies.quick.assets,
      );
    assert.equal(row.meanAssets, xs.reduce((a, b) => a + b) / 8);
    assert.equal(row.meanDeltaVsQuick, deltas.reduce((a, b) => a + b) / 8);
  }
  assert(new Set(r.summary.map((x) => x.meanAssets)).size > 1);
  assert.throws(() => comparePolicies(999999999, 8), /range/);
  assert.throws(() => createSeason(NaN), /integer/);
});

class FakeElement {
  constructor(tag, doc) {
    this.tagName = tag;
    this.doc = doc;
    this.children = [];
    this.listeners = {};
    this.attributes = {};
    this._text = "";
    this.value = "";
    this.disabled = false;
    this.clientWidth = 660;
  }
  set textContent(v) {
    this._text = String(v);
    this.children = [];
  }
  get textContent() {
    return this._text + this.children.map((c) => c.textContent).join("");
  }
  setAttribute(k, v) {
    this.attributes[k] = String(v);
    if (k === "id") this.doc.ids.set(String(v), this);
    if (k === "value") this.value = String(v);
  }
  getAttribute(k) {
    return this.attributes[k] ?? null;
  }
  append(...items) {
    for (const item of items) {
      this.children.push(item);
      item.parent = this;
    }
  }
  replaceChildren(...items) {
    this.children = [];
    this._text = "";
    this.append(...items);
  }
  addEventListener(k, fn) {
    (this.listeners[k] ??= []).push(fn);
  }
  removeEventListener(k, fn) {
    this.listeners[k] = (this.listeners[k] ?? []).filter((x) => x !== fn);
  }
  dispatch(type, extra = {}) {
    for (const fn of this.listeners[type] ?? [])
      fn({ key: undefined, preventDefault() {}, ...extra });
  }
  click() {
    if (!this.disabled) this.dispatch("click");
  }
  focus() {
    this.doc.activeElement = this;
  }
  remove() {
    if (this.parent)
      this.parent.children = this.parent.children.filter((x) => x !== this);
  }
}
function harness() {
  const html = readFileSync(
      fileURLToPath(new URL("../public-demo/index.html", import.meta.url)),
      "utf8",
    ),
    doc = {
      ids: new Map(),
      activeElement: null,
      getElementById(id) {
        return this.ids.get(id);
      },
      createElement(tag) {
        return new FakeElement(tag, this);
      },
      createElementNS(_, tag) {
        return this.createElement(tag);
      },
    };
  doc.body = doc.createElement("body");
  for (const match of html.matchAll(/id="([^"]+)"/g)) {
    const e = doc.createElement("div");
    e.setAttribute("id", match[1]);
    doc.body.append(e);
  }
  doc.getElementById("seed").value = "2026";
  doc.getElementById("speed").value = "800";
  let counter = 0;
  const timers = new Map(),
    blobs = [],
    listeners = {},
    win = {
      setInterval(fn) {
        timers.set(++counter, fn);
        return counter;
      },
      clearInterval(id) {
        timers.delete(id);
      },
      setTimeout(fn) {
        fn();
      },
      URL: {
        createObjectURL(blob) {
          blobs.push(blob);
          return "blob:local-evidence";
        },
        revokeObjectURL() {},
      },
      Blob: class {
        constructor(parts) {
          this.text = parts.join("");
        }
      },
      addEventListener(type, fn) {
        listeners[type] = fn;
      },
      removeEventListener(type) {
        delete listeners[type];
      },
    };
  const app = mount(doc, win),
    $ = (id) => doc.getElementById(id),
    tick = () => {
      for (const fn of [...timers.values()]) fn();
    },
    buttons = () =>
      [$("plot-actions"), $("market-actions")].flatMap((x) => x.children),
    button = (id) =>
      buttons().find((b) => b.getAttribute("data-action") === id);
  return { app, doc, win, $, timers, tick, blobs, button, listeners };
}
test("Actual one-day handler advances once and exports legal observation-based policy provenance", () => {
  const h = harness();
  h.$("step").click();
  const s = h.app.snapshot().interactiveSeason;
  assert.equal(s.daysCompleted, 1);
  assert.equal(s.decisions.length, 1);
  assert.equal(s.decisions[0].source, "policy");
  assert.equal(s.history[0].action, s.decisions[0].action);
  assert.equal(h.$("status").textContent, "PAUSED");
  assert(!Object.hasOwn(JSON.parse(h.$("observation").textContent), "seed"));
  h.app.destroy();
});
test("Actual manual plot action and keyboard selection work without advancing on inspection", () => {
  const h = harness();
  h.$("field-plot-1").dispatch("keydown", { key: "Enter" });
  assert.equal(h.app.snapshot().interactiveSeason.daysCompleted, 0);
  assert.equal(h.doc.activeElement, h.$("field-plot-1"));
  h.button("plant:1:beans").click();
  const s = h.app.snapshot().interactiveSeason;
  assert.equal(s.daysCompleted, 1);
  assert.equal(s.plots[1].crop, "beans");
  assert.equal(s.decisions[0].source, "manual");
  assert.equal(s.decisions[0].policy, null);
  assert.match(s.control, /may mix/);
  h.app.destroy();
});
test("A stale illegal manual handler preserves state and log, including an active play timer", () => {
  const h = harness(),
    stale = h.button("plant:0:beans");
  h.button("plant:0:radish").click();
  h.$("play").click();
  const before = serialized(h.app.snapshot()),
    timerCount = h.timers.size;
  stale.listeners.click[0]();
  assert.equal(serialized(h.app.snapshot()), before);
  assert.equal(h.timers.size, timerCount);
  assert.match(h.$("notice").textContent, /no longer legal/);
  h.app.destroy();
});
test("Actual play, pause and terminal handlers stop timers and disable actions", () => {
  const h = harness();
  h.$("play").click();
  assert.equal(h.timers.size, 1);
  h.tick();
  h.$("play").click();
  assert.equal(h.timers.size, 0);
  assert.equal(h.app.snapshot().interactiveSeason.daysCompleted, 1);
  h.$("play").click();
  for (let i = 0; i < 30; i++) h.tick();
  assert.equal(h.app.snapshot().interactiveSeason.daysCompleted, 24);
  assert.equal(h.timers.size, 0);
  assert.equal(h.$("play").disabled, true);
  assert.equal(h.$("step").disabled, true);
  assert(h.$("market-actions").children.every((x) => x.disabled));
  const before = serialized(h.app.snapshot());
  h.$("step").click();
  assert.equal(serialized(h.app.snapshot()), before);
  h.app.destroy();
});
test("Actual paired comparison does not mutate the interactive season and exports computed evidence", () => {
  const h = harness();
  h.$("step").click();
  const before = serialized(h.app.snapshot().interactiveSeason);
  h.$("compare").click();
  assert.equal(serialized(h.app.snapshot().interactiveSeason), before);
  assert.deepEqual(h.app.snapshot().pairedComparison, comparePolicies(2026, 8));
  assert.equal(h.$("comparison-body").children.length, 3);
  h.$("export").click();
  const output = JSON.parse(h.blobs[0].text);
  assert.deepEqual(output, h.app.snapshot());
  assert.equal(output.pairedComparison.seasons.length, 8);
  assert.equal(replay(output).interactive_days, 1);
  assert.equal(replay(output).comparison_policy_seasons, 24);
  h.app.destroy();
});
test("Actual reset clears derived evidence and invalid seed leaves the current session intact", () => {
  const h = harness();
  h.$("step").click();
  h.$("compare").click();
  h.$("seed").value = "bad";
  const before = serialized(h.app.snapshot());
  h.$("reset").click();
  assert.equal(serialized(h.app.snapshot()), before);
  assert.match(h.$("notice").textContent, /integer/);
  h.$("seed").value = "9";
  h.$("reset").click();
  assert.equal(h.app.snapshot().interactiveSeason.seed, 9);
  assert.equal(h.app.snapshot().interactiveSeason.daysCompleted, 0);
  assert.equal(h.app.snapshot().interactiveSeason.decisions.length, 0);
  assert.equal(h.app.snapshot().pairedComparison, null);
  assert.equal(h.$("seed").disabled, false);
  h.app.destroy();
});
test("Responsive field retains readable text, plot semantics and keyboard targets", () => {
  const h = harness();
  h.$("field").clientWidth = 280;
  h.listeners.resize();
  assert.equal(h.$("field").getAttribute("viewBox"), "0 0 340 670");
  assert.equal(h.$("day").children[0].tagName, "small");
  assert.equal(h.$("water").children[0].tagName, "small");
  for (const plot of h.$("field").children) {
    assert.equal(plot.getAttribute("role"), "button");
    assert.equal(plot.getAttribute("tabindex"), "0");
    for (const text of plot.children.filter((e) => e.tagName === "text"))
      assert((Number(text.getAttribute("font-size")) * 280) / 340 >= 12);
  }
  h.app.destroy();
});
test("Public assets have synthetic scope and no runtime external libraries or network APIs", () => {
  const root = new URL("../public-demo/", import.meta.url),
    html = readFileSync(new URL("index.html", root), "utf8"),
    app = readFileSync(new URL("app.js", root), "utf8"),
    engine = readFileSync(new URL("engine.js", root), "utf8"),
    css = readFileSync(new URL("styles.css", root), "utf8");
  assert.match(html, /SYNTHETIC_ONLY/);
  assert.match(html, /separate from Kaggriculture/);
  assert.match(html, /tree\/main\/public-demo/);
  assert(
    !/\bfetch\s*\(|XMLHttpRequest|WebSocket|import\s*\(/.test(app + engine),
  );
  assert(!/<script[^>]+src="https?:/.test(html));
  assert(
    !/<link[^>]+rel="(?:stylesheet|preload|modulepreload)"[^>]+href="https?:/.test(
      html,
    ),
  );
  assert(!/font-size:\s*(?:[0-9]|10|11)px/.test(css));
});
console.log(
  `\n${passed} public demo checks passed (engine + actual UI handlers; no rendered browser QA).`,
);
