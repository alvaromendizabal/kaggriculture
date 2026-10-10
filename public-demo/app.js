import {
  RULES,
  CROPS,
  POLICIES,
  createSeason,
  observe,
  decide,
  legalActions,
  step,
  ready,
  harvestYield,
  assets,
  exportSeason,
  comparePolicies,
  checksum,
} from "./engine.js";

export function mount(doc, win) {
  const $ = (id) => doc.getElementById(id),
    copy = (x) => JSON.parse(JSON.stringify(x));
  let season = createSeason(2026),
    selected = 0,
    timer = null,
    decisions = [],
    comparison = null;
  const element = (tag, text, attrs = {}) => {
    const e = doc.createElement(tag);
    if (text !== undefined) e.textContent = text;
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
    return e;
  };
  const svg = (tag, attrs = {}, text) => {
    const e = doc.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, String(v));
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const number = (x) => Number(x).toFixed(1),
    signed = (x) => `${x > 0 ? "+" : ""}${number(x)}`;
  function notice(message = "") {
    $("notice").textContent = message;
  }
  function stop() {
    if (timer !== null) win.clearInterval(timer);
    timer = null;
  }
  function renderField() {
    const field = $("field"),
      width = field.clientWidth || 660,
      narrow = width < 450,
      viewWidth = narrow ? 340 : 660,
      font = Math.max(15, (12 * viewWidth) / Math.max(220, width));
    field.setAttribute("viewBox", narrow ? "0 0 340 670" : "0 0 660 340");
    field.replaceChildren();
    for (const p of season.plots) {
      const x = narrow ? 20 : p.id % 2 ? 344 : 16,
        y = narrow ? 13 + p.id * 165 : p.id < 2 ? 13 : 178,
        c = p.crop ? CROPS[p.crop] : null,
        ripe = ready(p);
      const state = c
        ? ripe
          ? `Ready · ${harvestYield(p)} units`
          : `Growth ${p.growth}/${c.days} · soil ${p.moisture}/4`
        : `Open soil · moisture ${p.moisture}/4`;
      const g = svg("g", {
        id: `field-plot-${p.id}`,
        role: "button",
        tabindex: 0,
        "aria-pressed": p.id === selected,
        "aria-label": `Plot ${p.id + 1}. ${c ? c.name : "Empty"}. ${state}. Select to inspect.`,
      });
      g.append(
        svg("rect", {
          x,
          y,
          width: 300,
          height: 145,
          rx: 9,
          fill: ripe ? "#ede1b3" : c ? "#dce6cb" : "#e8d9ba",
          stroke: p.id === selected ? "#2f6043" : "#bec9aa",
          "stroke-width": p.id === selected ? 3 : 1,
          class: "plot-border",
        }),
      );
      for (let k = 0; k < 4; k++)
        g.append(
          svg("path", {
            d: `M${x + 18} ${y + 55 + k * 15}H${x + 282}`,
            stroke: c ? "#b6c4a0" : "#cfbb92",
            "stroke-width": 2,
            "aria-hidden": true,
          }),
        );
      g.append(
        svg(
          "text",
          {
            x: x + 16,
            y: y + 29,
            fill: "#203e32",
            "font-size": font,
            "font-weight": 650,
          },
          `${String(p.id + 1).padStart(2, "0")} / ${c ? c.name : "Open plot"}`,
        ),
      );
      if (c) {
        const size = ripe ? 18 : 8 + Math.min(p.growth / c.days, 1) * 10;
        for (let k = 0; k < 4; k++) {
          const cx = x + 50 + k * 66,
            cy = y + 86;
          g.append(
            svg("path", {
              d: `M${cx} ${cy + 12}v-${size + 8}`,
              stroke: "#376445",
              "stroke-width": 4,
              "stroke-linecap": "round",
              "aria-hidden": true,
            }),
          );
          g.append(
            svg("ellipse", {
              cx: cx - size / 2,
              cy: cy - 5,
              rx: size * 0.65,
              ry: size * 0.32,
              transform: `rotate(30 ${cx - size / 2} ${cy - 5})`,
              fill: "#47774a",
              "aria-hidden": true,
            }),
          );
          g.append(
            svg("ellipse", {
              cx: cx + size / 2,
              cy: cy - 12,
              rx: size * 0.65,
              ry: size * 0.32,
              transform: `rotate(-30 ${cx + size / 2} ${cy - 12})`,
              fill: "#47774a",
              "aria-hidden": true,
            }),
          );
          if (ripe)
            g.append(
              svg("circle", {
                cx,
                cy: cy + 12,
                r: 7,
                fill: c.color,
                stroke: "#6e562f",
                "stroke-width": 1,
                "aria-hidden": true,
              }),
            );
        }
      }
      g.append(
        svg(
          "text",
          { x: x + 16, y: y + 127, fill: "#344f3d", "font-size": font },
          state,
        ),
      );
      function select() {
        selected = p.id;
        renderField();
        renderManual();
        $(`field-plot-${p.id}`).focus();
      }
      g.addEventListener("click", select);
      g.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          select();
        }
      });
      field.append(g);
    }
  }
  function commit(action, source, reason) {
    const observation = observe(season),
      legal = observation.actions.find((a) => a.id === action);
    if (!legal)
      throw new Error(
        "That action is no longer legal. Choose an enabled current action.",
      );
    step(season, action);
    decisions.push({
      day: observation.day,
      source,
      policy: source === "policy" ? $("policy").value : null,
      action,
      reason,
      observationChecksum: checksum(observation),
    });
    if (source === "manual" || season.done) stop();
    notice();
    render();
  }
  function manual(action) {
    try {
      commit(
        action,
        "manual",
        "Manual choice from the current legal action mask.",
      );
    } catch (error) {
      notice(error.message);
    }
  }
  function actionButton(id, label, container) {
    const button = element("button", label, {
      type: "button",
      "data-action": id,
    });
    button.disabled = !legalActions(season).some((a) => a.id === id);
    button.addEventListener("click", () => manual(id));
    container.append(button);
  }
  function renderManual() {
    const p = season.plots[selected],
      c = p.crop ? CROPS[p.crop] : null;
    $("plot-title").textContent =
      `Plot ${String(selected + 1).padStart(2, "0")}`;
    $("plot-detail").textContent = c
      ? `${c.name} · ${ready(p) ? `ready, ${harvestYield(p)} units` : `${p.growth} of ${c.days} growth days`} · soil moisture ${p.moisture}/4 · ${p.stress} dry growth days`
      : "Available soil. Choose a seed cost and growth horizon.";
    const pa = $("plot-actions");
    pa.replaceChildren();
    if (!c)
      for (const [id, crop] of Object.entries(CROPS))
        actionButton(
          `plant:${selected}:${id}`,
          `${crop.name} · ${crop.seedCost} coins · ${crop.days} days`,
          pa,
        );
    else {
      actionButton(`water:${selected}`, "Water · 2 reservoir units", pa);
      actionButton(
        `harvest:${selected}`,
        `Harvest · ${harvestYield(p)} units`,
        pa,
      );
    }
    const prices = $("market-prices"),
      actions = $("market-actions");
    prices.replaceChildren();
    actions.replaceChildren();
    for (const [crop, c] of Object.entries(CROPS)) {
      prices.append(
        element(
          "span",
          `${c.name}: ${season.current.prices[crop]} coins/unit · ${season.inventory[crop]} stored`,
        ),
      );
      actionButton(`sell:${crop}`, `Sell ${c.name.toLowerCase()}`, actions);
    }
    actionButton("refill", `Buy water · 3 coins`, actions);
    actionButton("work", "Farm work · +1 coin", actions);
    actionButton("wait", "Wait one day", actions);
    $("plot-actions-note").textContent = season.done
      ? "The season is complete. Reset to make another decision."
      : "Enabled actions spend one day. Disabled actions are outside the current legal mask.";
  }
  function renderWeather() {
    const box = $("weather-history");
    box.replaceChildren();
    for (let i = 0; i < RULES.days; i++) {
      const weather =
        season.history[i]?.weather ??
        (!season.done && i === season.day ? season.current : null);
      const label = weather
        ? `Day ${i + 1}: ${weather.condition}${i === season.day ? " (current)" : ""}`
        : `Day ${i + 1}: not yet observed`;
      box.append(
        element("span", weather ? (weather.rain ? "•" : "–") : "·", {
          class: `weather-day${weather?.rain ? " rain" : ""}${i === season.day ? " current" : ""}`,
          title: label,
          "aria-label": label,
        }),
      );
    }
  }
  function render() {
    $("status").textContent = season.done
      ? "COMPLETE"
      : timer !== null
        ? "PLAYING"
        : season.day
          ? "PAUSED"
          : "READY";
    $("play").textContent = timer !== null ? "Pause season" : "Play season";
    $("play").disabled = season.done;
    $("step").disabled = season.done || timer !== null;
    $("seed").disabled = season.day > 0 || timer !== null;
    $("day").textContent = String(
      Math.min(season.day + 1, RULES.days),
    ).padStart(2, "0");
    $("day").append(element("small", ` / ${RULES.days}`));
    $("coins").textContent = season.coins;
    $("water").textContent = season.water;
    $("water").append(element("small", ` / ${RULES.waterCapacity}`));
    $("assets").textContent = assets(season);
    $("weather").textContent = season.current.condition;
    $("rain-detail").textContent =
      `${season.current.rain} rain units ${season.done ? "at close" : "today"}`;
    $("policy-description").textContent = POLICIES.find(
      (p) => p.id === $("policy").value,
    ).description;
    const o = observe(season);
    $("legal-count").textContent = o.actions.length;
    $("observation").textContent = JSON.stringify(o, null, 2);
    if (season.done) {
      $("decision").textContent = "Season complete";
      $("reason").textContent =
        "All 24 actions are recorded. Reset for another season or export the evidence.";
    } else {
      const d = decide($("policy").value, o);
      $("decision").textContent =
        `Next policy choice: ${o.actions.find((a) => a.id === d.action).label}`;
      $("reason").textContent = d.reason;
    }
    const last = season.history.at(-1),
      lastDecision = decisions.at(-1);
    $("season-note").textContent = season.done
      ? `Season closed at ${assets(season)} assets: ${season.coins} coins plus ${assets(season) - season.coins} stored crop value. Standing plants count zero.`
      : last
        ? `Day ${last.day} · ${lastDecision.source === "manual" ? "Manual choice" : POLICIES.find((p) => p.id === lastDecision.policy).name}: ${last.label}. ${last.events.join(" ")}`
        : "You begin with 16 coins and 6 water. A season lasts 24 days.";
    renderField();
    renderManual();
    renderWeather();
  }
  function oneDay() {
    try {
      if (!season.done) {
        const d = decide($("policy").value, observe(season));
        commit(d.action, "policy", d.reason);
      }
    } catch (error) {
      stop();
      render();
      notice(error.message);
    }
  }
  function play() {
    if (timer !== null) {
      stop();
      render();
      return;
    }
    if (season.done) return;
    timer = win.setInterval(oneDay, Number($("speed").value));
    notice();
    render();
  }
  function reset() {
    try {
      const replacement = createSeason(Number($("seed").value));
      stop();
      season = replacement;
      selected = 0;
      decisions = [];
      comparison = null;
      notice();
      renderComparison();
      render();
    } catch (error) {
      notice(error.message);
    }
  }
  function renderComparison() {
    const body = $("comparison-body");
    body.replaceChildren();
    if (!comparison) {
      const row = element("tr"),
        cell = element("td", "Run the comparison to compute these outcomes.", {
          colspan: 4,
          class: "empty-table",
        });
      row.append(cell);
      body.append(row);
      $("comparison-scope").textContent =
        "Eight paired 24-day seasons · no fitting or policy search";
      $("comparison-note").textContent =
        "These are descriptive outcomes in a simplified generated environment, not estimates of official game performance.";
      return;
    }
    for (const row of comparison.summary) {
      const tr = element("tr"),
        name = element("td", row.name),
        detail = element("span", row.description, { class: "policy-copy" });
      name.append(detail);
      tr.append(
        name,
        element("td", number(row.meanAssets)),
        element("td", signed(row.meanDeltaVsQuick), {
          class: row.meanDeltaVsQuick >= 0 ? "positive" : "negative",
        }),
        element("td", `${row.minAssets}–${row.maxAssets}`),
      );
      body.append(tr);
    }
    $("comparison-scope").textContent =
      `Seeds ${comparison.seed}–${comparison.seed + comparison.count - 1} · ${comparison.count} paired seasons × 3 fixed policies`;
    $("comparison-note").textContent =
      "Computed from fresh, complete seasons with identical weather and prices per seed. Your interactive season is separate and may include manual choices or policy switches. Export includes each paired outcome and its action sequence.";
  }
  function compare() {
    try {
      const result = comparePolicies(Number($("seed").value), 8);
      comparison = result;
      notice();
      renderComparison();
    } catch (error) {
      notice(error.message);
    }
  }
  function exported() {
    return {
      evidence_type: "SYNTHETIC_ONLY",
      schema: "field-notes-evidence-v1",
      interactiveSeason: {
        ...exportSeason(season),
        control:
          "Interactive session: may mix manual actions and public policy choices. Not a fixed-policy comparison.",
        decisions: copy(decisions),
      },
      pairedComparison: comparison ? copy(comparison) : null,
    };
  }
  function download() {
    const data = JSON.stringify(exported(), null, 2),
      url = win.URL.createObjectURL(
        new win.Blob([data], { type: "application/json" }),
      ),
      a = element("a", undefined, {
        href: url,
        download: "field-notes-evidence.json",
      });
    doc.body.append(a);
    a.click();
    a.remove();
    win.setTimeout(() => win.URL.revokeObjectURL(url), 0);
    notice(
      "Evidence exported: actual interactive actions and any separately computed paired comparison.",
    );
  }
  for (const policy of POLICIES)
    $("policy").append(element("option", policy.name, { value: policy.id }));
  $("policy").value = "quick";
  $("play").addEventListener("click", play);
  $("step").addEventListener("click", oneDay);
  $("reset").addEventListener("click", reset);
  $("compare").addEventListener("click", compare);
  $("export").addEventListener("click", download);
  $("policy").addEventListener("change", () => {
    notice();
    render();
  });
  $("seed").addEventListener("change", () => {
    if (season.day === 0 && timer === null) reset();
  });
  $("speed").addEventListener("change", () => {
    if (timer !== null) {
      stop();
      play();
    }
  });
  $("asset-help").addEventListener("click", () =>
    notice(
      "Assets equal coins plus stored crop units valued at current prices. Unharvested plants have zero closing value.",
    ),
  );
  const resize = () => renderField();
  win.addEventListener("resize", resize);
  render();
  return {
    snapshot: exported,
    destroy() {
      stop();
      win.removeEventListener("resize", resize);
    },
  };
}
if (typeof document !== "undefined") mount(document, window);
