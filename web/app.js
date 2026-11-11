/* Argumentation live demo -- front-end.
 * Draws and animates; every semantic result comes from the Python API (web_demo.py). */
"use strict";

const SVGNS = "http://www.w3.org/2000/svg";
const $ = (s, r = document) => r.querySelector(s);
const el = (tag, attrs = {}, parent) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
};
const h = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k === "style") e.style.cssText = v;
    else e.setAttribute(k, v);
  }
  for (const k of kids.flat()) if (k != null) e.append(k instanceof Node ? k : document.createTextNode(k));
  return e;
};
const sleep = ms => new Promise(r => setTimeout(r, ms));
const natKey = s => { const m = String(s).match(/^(.*?)(\d*)$/); return [m[1], m[2] ? +m[2] : -1]; };
const natSort = arr => [...arr].sort((a, b) => { const x = natKey(a), y = natKey(b); return x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : x[1] - y[1]; });
const fmt = s => "{" + natSort(s).join(", ") + "}";

function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 3500);
}

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json();
  if (!r.ok) { toast(j.error || "request failed"); throw new Error(j.error); }
  return j;
}

/* Book-like positions (viewBox 800 x 600) so the figures resemble the book. */
const PRESET = {
  "Figure 5.1": { a3: [170, 170], a2: [400, 170], a1: [640, 300], a5: [170, 430], a4: [400, 430] },
  "Figure 5.2": { a2: [250, 220], a1: [550, 220], a3: [550, 430] },
  "Figure 5.3": { a: [400, 70], b: [400, 210], c: [270, 360], d: [530, 360], e: [530, 520] },
  "Example 5.10 (Fig 5.4)": { a1: [110, 320], a2: [290, 320], a3: [470, 320], a4: [670, 190], a5: [670, 450] },
  "Example 5.11 (Fig 5.5)": { a1: [110, 320], a2: [290, 320], a3: [470, 320], a4: [670, 190], a5: [670, 450], a6: [290, 140] },
};

/* ===================================================================== */
/* GraphView -- SVG argument graph with animated state classes            */
/* ===================================================================== */
class GraphView {
  constructor(svg, opts = {}) {
    this.svg = svg; this.opts = opts; this.R = 26; this.pad = opts.pad ?? 2;
    this.W = 800; this.H = 600;
    svg.setAttribute("viewBox", `0 0 ${this.W} ${this.H}`);
    const id = svg.id;
    const defs = el("defs", {}, svg);
    for (const [suffix, cls] of [["", ""], ["-hl", "hl"]]) {
      const m = el("marker", { id: id + "-arrow" + suffix, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 9, markerHeight: 9, orient: "auto-start-reverse", markerUnits: "userSpaceOnUse", class: cls }, defs);
      el("path", { d: "M0,0 L10,5 L0,10 z" }, m);
    }
    this.bg = el("rect", { x: 0, y: 0, width: this.W, height: this.H, fill: "transparent" }, svg);
    this.gEdges = el("g", {}, svg);
    this.gNodes = el("g", {}, svg);
    this.pos = {}; this.nodes = {}; this.edges = [];
    this.args = []; this.attacks = [];
    this.bg.addEventListener("pointerdown", e => this.opts.onBackground && this.opts.onBackground(this.pt(e)));
  }

  pt(e) {
    const p = this.svg.createSVGPoint(); p.x = e.clientX; p.y = e.clientY;
    const q = p.matrixTransform(this.svg.getScreenCTM().inverse());
    return [Math.max(this.R + 4, Math.min(this.W - this.R - 4, q.x)), Math.max(this.R + 4, Math.min(this.H - this.R - 4, q.y))];
  }

  layout(args, preset) {
    const n = args.length, cx = this.W / 2, cy = this.H / 2 + 10;
    const rad = n <= 2 ? 140 : Math.min(240, 90 + 22 * n);
    const missing = args.filter(a => !this.pos[a]);
    for (const a of args) if (preset && preset[a]) this.pos[a] = [...preset[a]];
    args.forEach((a, i) => {
      if (this.pos[a]) return;
      const t = -Math.PI / 2 + (2 * Math.PI * i) / n;
      this.pos[a] = [cx + rad * Math.cos(t), cy + rad * Math.sin(t)];
    });
    return missing;
  }

  setGraph(args, attacks, { preset = null, reset = false, agentOf = null } = {}) {
    if (reset) this.pos = {};
    this.args = natSort(args); this.attacks = attacks.map(e => [...e]);
    this.layout(this.args, preset);
    for (const a of Object.keys(this.pos)) if (!this.args.includes(a)) delete this.pos[a];
    // nodes
    this.gNodes.innerHTML = ""; this.nodes = {};
    for (const a of this.args) {
      const g = el("g", { class: "node", "data-arg": a }, this.gNodes);
      el("circle", { class: "agent", r: this.R + 7 }, g);
      el("circle", { class: "fs", r: this.R + 11 }, g);
      el("circle", { class: "ring", r: this.R + 3 }, g);
      el("circle", { class: "body", r: this.R }, g);
      const t = el("text", {}, g); t.textContent = a;
      this.nodes[a] = g;
      this.bindNode(a, g);
    }
    if (agentOf) this.setAgents(agentOf);
    this.drawEdges();
    this.placeNodes();
  }

  setAgents(agentOf) {
    for (const [a, g] of Object.entries(this.nodes)) {
      const k = agentOf[a];
      g.classList.toggle("has-agent", k !== undefined);
      if (k !== undefined) g.querySelector("circle.agent").style.stroke = `var(--agent${k % 4})`;
    }
  }

  bindNode(a, g) {
    let start = null, moved = false;
    g.addEventListener("pointerdown", e => {
      e.stopPropagation(); start = this.pt(e); moved = false; g.setPointerCapture(e.pointerId);
    });
    g.addEventListener("pointermove", e => {
      if (!start) return;
      const p = this.pt(e);
      if (!moved && Math.hypot(p[0] - start[0], p[1] - start[1]) < 5) return;
      moved = true; this.pos[a] = p; this.placeNodes(); this.drawEdges(true);
    });
    g.addEventListener("pointerup", e => {
      if (start && !moved && this.opts.onNode) this.opts.onNode(a, e);
      start = null;
    });
  }

  placeNodes() {
    for (const [a, g] of Object.entries(this.nodes)) {
      const [x, y] = this.pos[a]; g.setAttribute("transform", `translate(${x},${y})`);
    }
  }

  edgePath(x, y) {
    const R = this.R, P = this.pad, [x1, y1] = this.pos[x], [x2, y2] = this.pos[y];
    if (x === y) {
      const a1 = -2.2, a2 = -0.95;
      const sx = x1 + R * Math.cos(a1), sy = y1 + R * Math.sin(a1);
      const ex = x1 + (R + P) * Math.cos(a2), ey = y1 + (R + P) * Math.sin(a2);
      return `M${sx},${sy} C${x1 - 55},${y1 - 95} ${x1 + 60},${y1 - 90} ${ex},${ey}`;
    }
    const mutual = this.attacks.some(([u, v]) => u === y && v === x);
    const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1;
    if (!mutual) {
      const ux = dx / L, uy = dy / L;
      return `M${x1 + ux * R},${y1 + uy * R} L${x2 - ux * (R + P)},${y2 - uy * (R + P)}`;
    }
    const nx = -dy / L, ny = dx / L, off = 28;
    const cx = (x1 + x2) / 2 + nx * off, cy = (y1 + y2) / 2 + ny * off;
    const trim = (px, py, qx, qy, d) => { const l = Math.hypot(qx - px, qy - py) || 1; return [px + (qx - px) / l * d, py + (qy - py) / l * d]; };
    const [sx, sy] = trim(x1, y1, cx, cy, R), [ex, ey] = trim(x2, y2, cx, cy, R + P);
    return `M${sx},${sy} Q${cx},${cy} ${ex},${ey}`;
  }

  drawEdges(keep = false) {
    if (keep && this.edges.length === this.attacks.length) {
      for (const e of this.edges) { const d = this.edgePath(e.x, e.y); e.path.setAttribute("d", d); e.hit.setAttribute("d", d); }
      return;
    }
    this.gEdges.innerHTML = ""; this.edges = [];
    for (const [x, y] of this.attacks) {
      const d = this.edgePath(x, y);
      const path = el("path", { class: "edge", d, "marker-end": `url(#${this.svg.id}-arrow)` }, this.gEdges);
      const hit = el("path", { class: "edgehit", d }, this.gEdges);
      hit.addEventListener("pointerdown", ev => { ev.stopPropagation(); this.opts.onEdge && this.opts.onEdge(x, y); });
      this.edges.push({ x, y, path, hit });
    }
  }

  /* ---- state ---- */
  setLabels(lab) {           // lab: {arg: "in"|"out"|"undec"} ; missing = neutral
    for (const [a, g] of Object.entries(this.nodes)) {
      g.classList.remove("in", "out", "undec");
      if (lab && lab[a]) g.classList.add(lab[a]);
    }
  }
  setClass(cls, set) {
    for (const [a, g] of Object.entries(this.nodes)) g.classList.toggle(cls, set.has(a));
  }
  setEdgeClass(cls, pred) {
    for (const e of this.edges) {
      const on = !!pred(e.x, e.y);
      e.path.classList.toggle(cls, on);
      if (cls === "hl") e.path.setAttribute("marker-end", `url(#${this.svg.id}-arrow${on ? "-hl" : ""})`);
    }
  }
  pulse(args) {
    for (const a of args) {
      const g = this.nodes[a]; if (!g) continue;
      g.classList.remove("pulse"); void g.getBBox(); g.classList.add("pulse");
      setTimeout(() => g.classList.remove("pulse"), 950);
    }
  }
  async glowWalk(walk, step = 380) {
    this.setEdgeClass("hl", () => false);
    this.setClass("hl", new Set());
    const lit = new Set([walk[0]]);
    this.setClass("hl", lit);
    const pairs = [];
    for (let i = 0; i + 1 < walk.length; i++) {
      await sleep(step);
      pairs.push(walk[i] + ">" + walk[i + 1]);
      lit.add(walk[i + 1]);
      this.setEdgeClass("hl", (x, y) => pairs.includes(x + ">" + y));
      this.setClass("hl", lit);
    }
  }
  clearGlow() { this.setEdgeClass("hl", () => false); this.setClass("hl", new Set()); }
}

const plusOf = (S, attacks) => new Set(attacks.filter(([x]) => S.has(x)).map(([, y]) => y));

/* ===================================================================== */
/* TAB 1 -- Engine                                                         */
/* ===================================================================== */
const E = {
  examples: [], graph: null, res: null, S: new Set(), mode: "select", pending: null,
  view: { type: "none" }, gStep: 0, gTimer: null, lab: 0, labTimer: null,
};
let engView;

function engInit(examples) {
  E.examples = examples;
  const sel = $("#eng-example");
  examples.forEach((ex, i) => sel.append(h("option", { value: i }, ex.name)));
  sel.append(h("option", { value: "blank" }, "Blank (build your own)"));
  sel.addEventListener("change", () => engLoad(sel.value === "blank" ? { name: "Blank", args: [], attacks: [] } : E.examples[+sel.value]));

  engView = new GraphView($("#eng-svg"), {
    onNode: (a, ev) => engNodeClick(a, ev),
    onBackground: p => engBackground(p),
    onEdge: (x, y) => { if (E.mode === "edit") engToggleAttack(x, y); },
  });

  document.querySelectorAll("#eng-mode button").forEach(b => b.addEventListener("click", () => {
    E.mode = b.dataset.mode; E.pending = null; engView.setClass("pending", new Set());
    document.querySelectorAll("#eng-mode button").forEach(x => x.classList.toggle("on", x === b));
    $("#eng-hint").textContent = E.mode === "edit"
      ? "Click empty space: add argument · click A then B: toggle attack A→B (A then A: self-attack) · click an arrow: delete it · Shift+click: delete argument"
      : "Click arguments to build S.";
  }));
  $("#eng-clearS").addEventListener("click", () => { E.S.clear(); engAnalyze(); });

  $("#g-reset").addEventListener("click", () => { engStopTimers(); E.gStep = 0; engSetView({ type: "grounded" }); });
  $("#g-step").addEventListener("click", () => { engStopTimers(); engGroundedStep(); });
  $("#g-play").addEventListener("click", () => engGroundedPlay());
  $("#l-prev").addEventListener("click", () => { engStopTimers(); engShowLab(E.lab - 1); });
  $("#l-next").addEventListener("click", () => { engStopTimers(); engShowLab(E.lab + 1); });
  $("#l-cycle").addEventListener("click", () => {
    if (E.labTimer) return engStopTimers();
    $("#l-cycle").textContent = "Stop";
    engShowLab(E.lab);
    E.labTimer = setInterval(() => engShowLab(E.lab + 1), 1600);
  });
  engLoad(examples[0]);
}

function engStopTimers() {
  clearInterval(E.gTimer); E.gTimer = null; $("#g-play").textContent = "▶ Play";
  clearInterval(E.labTimer); E.labTimer = null; $("#l-cycle").textContent = "Auto-cycle";
}

function engLoad(ex) {
  engStopTimers();
  E.graph = { name: ex.name, args: [...ex.args], attacks: ex.attacks.map(e => [...e]) };
  E.S.clear(); E.pending = null; E.gStep = 0; E.lab = 0; E.view = { type: "none" };
  engView.setGraph(E.graph.args, E.graph.attacks, { preset: PRESET[ex.name], reset: true });
  engAnalyze();
}

async function engAnalyze() {
  E.res = await api("/api/analyze", { args: E.graph.args, attacks: E.graph.attacks, S: [...E.S] });
  engRenderPanels();
  engApplyView(false);
}

function engGraphChanged() {
  engStopTimers();
  for (const a of [...E.S]) if (!E.graph.args.includes(a)) E.S.delete(a);
  E.gStep = 0; E.lab = 0; E.view = { type: "none" };
  engView.setGraph(E.graph.args, E.graph.attacks);
  engAnalyze();
}

function engNodeClick(a, ev) {
  if (E.mode === "select") {
    E.S.has(a) ? E.S.delete(a) : E.S.add(a);
    engAnalyze();
    return;
  }
  if (ev.shiftKey) {                               // delete argument
    E.graph.args = E.graph.args.filter(x => x !== a);
    E.graph.attacks = E.graph.attacks.filter(([x, y]) => x !== a && y !== a);
    E.pending = null; engGraphChanged(); return;
  }
  if (E.pending === null) { E.pending = a; engView.setClass("pending", new Set([a])); return; }
  const from = E.pending; E.pending = null; engView.setClass("pending", new Set());
  engToggleAttack(from, a);
}

function engToggleAttack(x, y) {
  const i = E.graph.attacks.findIndex(([u, v]) => u === x && v === y);
  if (i >= 0) E.graph.attacks.splice(i, 1); else E.graph.attacks.push([x, y]);
  engGraphChanged();
}

function engBackground(p) {
  if (E.mode !== "edit") return;
  if (E.pending !== null) { E.pending = null; engView.setClass("pending", new Set()); return; }
  const names = E.graph.args;
  let name;
  if (names.length && names.every(n => /^[a-z]$/.test(n))) {
    name = "abcdefghijklmnopqrstuvwxyz".split("").find(c => !names.includes(c));
  }
  if (!name) { let k = 1; while (names.includes("a" + k)) k++; name = "a" + k; }
  if (names.length >= 14) return toast("at most 14 arguments in the demo");
  E.graph.args.push(name);
  engView.pos[name] = p;
  engGraphChanged();
}

/* ---- views ---- */
function engSetView(v) { E.view = v; engApplyView(true); }

function engApplyView(animate) {
  const r = E.res; if (!r) return;
  engView.setClass("sel", E.S);
  engView.setClass("fs", new Set(E.S.size && r.S ? r.S.F : []));
  let lab = {}, info = "";
  const v = E.view;
  if (v.type === "grounded") {
    const k = E.gStep, tr = r.grounded_trace;
    if (k === 0) info = "F⁰(∅) = ∅";
    else {
      const Sk = new Set(tr[k - 1]), out = plusOf(Sk, E.graph.attacks);
      for (const a of E.graph.args) if (Sk.has(a)) lab[a] = "in"; else if (out.has(a)) lab[a] = "out";
      const prev = k >= 2 ? new Set(tr[k - 2]) : new Set();
      if (animate) engView.pulse([...Sk].filter(a => !prev.has(a)));
      const fixed = k === tr.length;
      info = `F${sup(k)}(∅) = ${fmt(tr[k - 1])}` + (fixed ? `  ✓ fixed point → grounded = ${fmt(r.grounded)}` : "");
    }
    // undecided after fixpoint
    if (k === r.grounded_trace.length) for (const a of E.graph.args) if (!lab[a]) lab[a] = "undec";
  } else if (v.type === "ext") {
    const Es = new Set(v.ext), out = plusOf(Es, E.graph.attacks);
    for (const a of E.graph.args) lab[a] = Es.has(a) ? "in" : out.has(a) ? "out" : "undec";
    if (animate) engView.pulse(v.ext);
  } else if (v.type === "lab") {
    lab = r.labellings[E.lab] || {};
  }
  engView.setLabels(lab);
  $("#g-info").textContent = v.type === "grounded" ? info : `${r.grounded_trace.length} step(s) to the fixed point`;
  document.querySelectorAll("#eng-ext .chip").forEach(c => c.classList.toggle("on", v.type === "ext" && c.dataset.key === v.key));
  $("#l-info").textContent = r.labellings.length ? `L${E.lab + 1} / ${r.labellings.length}` : "none";
  $("#l-text").textContent = v.type === "lab" && r.labellings[E.lab] ? labStr(r.labellings[E.lab]) : "";
}

const sup = k => String(k).split("").map(d => "⁰¹²³⁴⁵⁶⁷⁸⁹"[+d]).join("");
const labStr = L => ["in", "out", "undec"].map(t => `${t}=${fmt(Object.keys(L).filter(a => L[a] === t))}`).join("   ");

function engGroundedStep() {
  const n = E.res.grounded_trace.length;
  if (E.view.type !== "grounded") E.gStep = 0;
  E.gStep = Math.min(E.gStep + 1, n);
  engSetView({ type: "grounded" });
  return E.gStep < n;
}
function engGroundedPlay() {
  if (E.gTimer) return engStopTimers();
  engStopTimers();
  E.gStep = 0; engSetView({ type: "grounded" });
  $("#g-play").textContent = "⏸ Pause";
  E.gTimer = setInterval(() => { if (!engGroundedStep()) engStopTimers(); }, 1100);
}
function engShowLab(i) {
  const n = E.res.labellings.length; if (!n) return;
  E.lab = ((i % n) + n) % n;
  engSetView({ type: "lab" });
}

function engRenderPanels() {
  const r = E.res;
  // S panel
  const sp = $("#eng-S"); sp.innerHTML = "";
  const yes = b => h("span", { class: "badge " + (b ? "yes" : "no") }, b ? "yes" : "no");
  if (r.S) {
    const defended = Object.keys(r.S.defends).filter(a => r.S.defends[a]);
    sp.append(
      h("span", { class: "k" }, "S"), h("span", { class: "mono" }, fmt(r.S.S)),
      h("span", { class: "k" }, "conflict-free"), yes(r.S.conflict_free),
      h("span", { class: "k" }, "S⁺"), h("span", { class: "mono" }, fmt(r.S.S_plus)),
      h("span", { class: "k" }, "F(S) = defended"), h("span", { class: "mono" }, fmt(r.S.F)),
      h("span", { class: "k" }, "admissible"), yes(r.S.admissible),
      h("span", { class: "k" }, "complete"), yes(r.S.complete),
      h("span", { class: "k" }, "stable"), yes(r.S.stable),
    );
    if (!defended.length) sp.append(h("span", { class: "k" }, ""), h("span", { class: "muted" }, "S defends nothing"));
  }
  // extensions
  const ext = $("#eng-ext"); ext.innerHTML = "";
  for (const [sem, list] of Object.entries(r.extensions)) {
    const g = h("div", { class: "extgroup" }, h("span", { class: "name" }, sem));
    if (!list.length) g.append(h("span", { class: "muted" }, "(none)"));
    list.forEach((e, i) => {
      const key = sem + i;
      g.append(h("button", { class: "chip", "data-key": key, onclick: () => { engStopTimers(); engSetView({ type: "ext", ext: e, key }); } }, fmt(e)));
    });
    ext.append(g);
  }
  // status table
  const sems = Object.keys(r.extensions);
  const cls = { "skeptically accepted": "sk", "credulously accepted": "cr", rejected: "rj" };
  const short = { "skeptically accepted": "skeptical", "credulously accepted": "credulous", rejected: "rejected" };
  const tb = h("table", {}, h("tr", {}, h("th", {}, "arg"), sems.map(s => h("th", {}, s))));
  for (const [a, row] of Object.entries(r.status)) {
    const tr = h("tr", {}, h("td", { class: "mono" }, a), sems.map(s => h("td", { class: cls[row[s]] }, short[row[s]])));
    tr.addEventListener("mouseenter", () => engView.setClass("hl", new Set([a])));
    tr.addEventListener("mouseleave", () => engView.setClass("hl", new Set()));
    tb.append(tr);
  }
  const st = $("#eng-status"); st.innerHTML = ""; st.append(tb);
}

/* ===================================================================== */
/* TAB 2 -- Strategic                                                      */
/* ===================================================================== */
const T = { examples: [], inst: null, reports: {}, util: {}, check: null, busy: false };
let stView;

function stInit(examples) {
  T.examples = examples;
  const sel = $("#st-example");
  examples.forEach((ex, i) => sel.append(h("option", { value: i }, ex.name)));
  sel.addEventListener("change", () => { if (sel.value !== "random") stLoad(T.examples[+sel.value]); });
  stView = new GraphView($("#st-svg"), { onNode: a => stToggle(a), pad: 10 });
  $("#st-random").addEventListener("click", async () => {
    const inst = await api("/api/random", { p: +$("#st-p").value, self_attacks: $("#st-self").checked });
    let o = sel.querySelector('option[value="random"]');
    if (!o) { o = h("option", { value: "random" }, "Random instance"); sel.append(o); }
    o.textContent = inst.name; sel.value = "random";
    stLoad(inst);
  });
  $("#st-truth").addEventListener("click", () => { stTruthful(); stUpdate(); });
  $("#st-check").addEventListener("click", stCheck);
  $("#st-manip").addEventListener("click", stManipulate);
  stLoad(examples[0]);
}

const agentNames = () => Object.keys(T.inst.types);
const ownerOf = a => agentNames().find(k => T.inst.types[k].includes(a));

function stTruthful() { for (const k of agentNames()) T.reports[k] = new Set(T.inst.types[k]); }

function stLoad(inst) {
  T.inst = { name: inst.name, args: [...inst.args], attacks: inst.attacks.map(e => [...e]), types: JSON.parse(JSON.stringify(inst.types)) };
  T.check = null; T.util = {};
  const old = $("#st-step"); if (old) old.remove();
  stTruthful();
  stRedraw(true);
  stRenderVerdict();
  $("#st-br").innerHTML = '<p class="muted">Click “Best response” on an agent.</p>';
  const notes = {
    "Example 5.10 (Fig 5.4)": "Book misprint: Example 5.10 writes u_y(o,{α3})=1, u_z(o,{α2})=0 — the sets are swapped. Correct values are shown in the agent cards (u_y=0, u_z=1). Try unticking a1 of x.",
    "Example 5.11 (Fig 5.5)": "Book misprint: the argument that cancels x's indirect self-defeat is α6, not α5. Check, then press ✕ on a6 (manipulation returns) or on a5 (still strategyproof).",
  };
  if (notes[inst.name]) $("#st-verdict").append(h("p", { class: "note" }, notes[inst.name]));
}

function stRedraw(reset) {
  const agentOf = {};
  agentNames().forEach((k, i) => T.inst.types[k].forEach(a => (agentOf[a] = i)));
  stView.setGraph(T.inst.args, T.inst.attacks, { preset: PRESET[T.inst.name], reset, agentOf });
  $("#st-agentlegend").innerHTML = "";
  agentNames().forEach((k, i) => $("#st-agentlegend").append(h("span", {}, h("i", { class: "dot", style: `border-color:var(--agent${i % 4});border-width:3px` }), "agent " + k)));
  stRenderAgents();
  stUpdate();
}

function stToggle(a) {
  const k = ownerOf(a); if (k === undefined || T.busy) return;
  T.reports[k].has(a) ? T.reports[k].delete(a) : T.reports[k].add(a);
  stUpdate();
}

function stDrop(k, a) {
  T.inst.types[k] = T.inst.types[k].filter(x => x !== a);
  T.reports[k].delete(a);
  T.inst.args = T.inst.args.filter(x => x !== a);
  T.inst.attacks = T.inst.attacks.filter(([x, y]) => x !== a && y !== a);
  T.check = null; stRenderVerdict();
  $("#st-verdict").append(h("p", { class: "note" }, `Dropped ${a} from agent ${k}. Press “Check” again.`));
  stRedraw(false);
}

function stRenderAgents() {
  const box = $("#st-agents"); box.innerHTML = "";
  agentNames().forEach((k, i) => {
    const args = natSort(T.inst.types[k]);
    const card = h("div", { class: "agent", style: `--c:var(--agent${i % 4})`, id: "agent-" + k },
      h("div", { class: "top" },
        h("span", { class: "name" }, `agent ${k}`),
        h("span", { class: "muted mono" }, "A = " + fmt(args)),
        h("button", { class: "ghost", onclick: () => stBest(k), disabled: args.length ? null : "" }, "Best response")),
      h("div", { class: "args" }, args.length ? args.map(a => {
        const cb = h("input", { type: "checkbox", "data-arg": a });
        cb.checked = T.reports[k].has(a);
        cb.addEventListener("change", () => stToggle(a));
        return h("label", { class: "arg" + (cb.checked ? "" : " hidden") }, cb, a,
          h("button", { title: `drop ${a} from the instance`, onclick: ev => { ev.preventDefault(); stDrop(k, a); } }, "✕"));
      }) : h("span", { class: "muted" }, "no arguments")),
      h("div", { class: "util" }, h("span", { class: "u" }, ""), h("div", { class: "bar" }, h("div")), h("span", { class: "delta" }, "")));
    box.append(card);
  });
}

async function stUpdate() {
  const reports = {}; for (const k of agentNames()) reports[k] = [...T.reports[k]];
  const res = await api("/api/mechanism", { attacks: T.inst.attacks, types: T.inst.types, reports });
  const revealed = new Set(Object.values(reports).flat());
  stView.setLabels(res.labelling);
  stView.setClass("ghost", new Set(T.inst.args.filter(a => !revealed.has(a))));
  stView.setEdgeClass("ghost", (x, y) => !revealed.has(x) || !revealed.has(y));
  $("#st-outcome").textContent = `outcome = grounded(⋃ reports) = ${fmt(res.outcome)}`;
  agentNames().forEach(k => {
    const card = $("#agent-" + k); if (!card) return;
    const n = T.inst.types[k].length, u = res.utilities[k];
    card.querySelectorAll("input[data-arg]").forEach(cb => {
      cb.checked = T.reports[k].has(cb.dataset.arg);
      cb.parentElement.classList.toggle("hidden", !cb.checked);
    });
    card.querySelector(".u").textContent = `u_${k} = ${u} / ${n}`;
    card.querySelector(".bar > div").style.width = n ? (100 * u / n) + "%" : "0";
    const d = card.querySelector(".delta"), prev = T.util[k];
    if (prev !== undefined && u !== prev) {
      d.textContent = (u > prev ? "+" : "") + (u - prev); d.style.color = u > prev ? "var(--in)" : "var(--out)";
      d.classList.add("show"); setTimeout(() => d.classList.remove("show"), 1600);
    }
    T.util[k] = u;
  });
}

async function stBest(k) {
  const reports = {}; for (const j of agentNames()) reports[j] = [...T.reports[j]];
  const r = await api("/api/best_response", { attacks: T.inst.attacks, types: T.inst.types, agent: k, reports });
  const others = agentNames().filter(j => j !== k).map(j => `${j}:${fmt(reports[j])}`).join("  ");
  const tb = h("table", {}, h("tr", {}, h("th", {}, `agent ${k} reveals`), h("th", {}, "outcome"), h("th", { class: "num" }, "u")));
  for (const row of r.table) {
    const truthful = row.report.length === T.inst.types[k].length;
    const best = row.utility === r.best_utility;
    const tr = h("tr", { style: "cursor:pointer", title: "click to play this report" },
      h("td", { class: "mono" }, fmt(row.report), truthful ? "  (truth)" : ""),
      h("td", { class: "mono" }, fmt(row.outcome)),
      h("td", { class: "num " + (best ? "sk" : "") }, String(row.utility) + (best ? " ★" : "")));
    tr.addEventListener("click", () => { T.reports[k] = new Set(row.report); stUpdate(); });
    tb.append(tr);
  }
  const box = $("#st-br"); box.innerHTML = "";
  box.append(h("p", { class: "muted small" }, `others fixed at ${others}`), h("div", { class: "tablewrap" }, tb),
    h("p", {}, r.truthful_is_best ? h("span", { class: "badge yes" }, "truth-telling is a best response")
                                  : h("span", { class: "badge no" }, `lying pays: best u=${r.best_utility} > truthful u=${r.truthful_utility}`)),
    h("p", { class: "muted small" }, "Click a row to play that report on the graph."));
}

async function stCheck() {
  T.check = await api("/api/strategic", { args: T.inst.args, attacks: T.inst.attacks, types: T.inst.types });
  stRenderVerdict();
}

const CAT = {
  "walk-only": "the odd connection exists only as a walk through an odd cycle, not as a simple path",
  "self-defeat-only": "the only violations are self-defeating arguments, which can never be accepted anyway",
  "victim-never-in": "the target argument is never accepted in any profile — nothing to gain",
  "hiding-never-helps": "hiding the source never reinstates the target (another attacker keeps it out/undec)",
  "compensated": "hiding the source frees the target, but the agent loses at least as much elsewhere",
};

function stRenderVerdict() {
  const v = $("#st-verdict"); v.innerHTML = ""; v.className = "verdict";
  $("#st-manip").disabled = !(T.check && T.check.witness);
  stView.clearGlow();
  const c = T.check; if (!c) return;
  v.append(h("div", {}, "Theorem 5.3 (exhaustive): ",
    h("span", { class: "badge " + (c.strategyproof ? "yes" : "no") }, c.strategyproof ? "strategyproof" : "NOT strategyproof")));
  if (c.witness) {
    const w = c.witness;
    v.append(h("p", { class: "note" }, `Witness: agent ${w.agent}, when the others reveal ${fmt(w.others_reveal)}, `
      + `hiding ${fmt(w.hidden)} raises u from ${w.truthful_utility} to ${w.better_utility} `
      + `(outcome ${fmt(w.truthful_outcome)} → ${fmt(w.better_outcome)}).`));
  }
  v.append(h("div", {}, "Theorem 5.4 condition: ",
    h("span", { class: "badge " + (c.cond_walk ? "yes" : "no") }, c.cond_walk ? "holds" : "fails"),
    c.cond_walk !== c.cond_simple ? h("span", { class: "muted small" }, `  (simple-path reading: ${c.cond_simple ? "holds" : "fails"})`) : null));
  if (c.violations.length) {
    v.append(h("div", { class: "muted small" }, "Odd paths between an agent's own arguments (click to trace):"));
    for (const x of c.violations) {
      const len = x.walk ? x.walk.length - 1 : "?";
      const row = h("div", { class: "viol" }, `${x.agent}: ${x.from} ⇝ ${x.to}   via ${x.walk ? x.walk.join(" → ") : "?"}  (length ${len}${x.simple_path_too ? "" : ", walk only"})`);
      row.addEventListener("click", () => {
        v.querySelectorAll(".viol").forEach(r => r.classList.toggle("on", r === row));
        if (x.walk) stView.glowWalk(x.walk);
      });
      v.append(row);
    }
  }
  if (c.cond_walk && c.strategyproof) v.append(h("p", { class: "note" }, "Condition holds ⇒ Theorem 5.4 guarantees strategyproofness, confirmed by the exhaustive check."));
  if (!c.cond_walk && c.strategyproof && c.diagnosis) {
    v.append(h("p", { class: "note" }, h("b", {}, "Strategyproof although the condition fails — why? "),
      CAT[c.diagnosis.category] || c.diagnosis.category, ". ", c.diagnosis.detail || ""));
  }
}

async function stManipulate() {
  const w = T.check && T.check.witness; if (!w || T.busy) return;
  T.busy = true; $("#st-manip").disabled = true;
  try {
    const others = new Set(w.others_reveal);
    for (const k of agentNames()) T.reports[k] = k === w.agent ? new Set(T.inst.types[k]) : new Set(T.inst.types[k].filter(a => others.has(a)));
    T.util = {};
    await stUpdate();
    toast_info(`Step 1: agent ${w.agent} tells the truth → u = ${w.truthful_utility}`);
    await sleep(1600);
    stView.setClass("hl", new Set(w.hidden)); stView.pulse(w.hidden);
    toast_info(`Step 2: agent ${w.agent} hides ${fmt(w.hidden)} …`);
    await sleep(1200);
    stView.setClass("hl", new Set());
    for (const a of w.hidden) T.reports[w.agent].delete(a);
    await stUpdate();
    toast_info(`Step 3: outcome ${fmt(w.better_outcome)} → u = ${w.better_utility}  (lying paid off)`);
  } finally { T.busy = false; $("#st-manip").disabled = false; }
}
function toast_info(msg) { $("#st-outcome").dataset.step = msg; const s = $("#st-step") || h("div", { id: "st-step", class: "note" }); s.textContent = msg; $("#st-outcome").after(s); }

/* ===================================================================== */
/* TAB 3 -- Experiments                                                    */
/* ===================================================================== */
let expLoaded = false;
const Q3NAMES = {
  "compensated/source-itself-lost": "Hiding gains nothing on balance (hidden argument itself lost)",
  "compensated/other-own-argument-lost": "Hiding loses other own arguments (α6 effect)",
  "hiding-never-helps": "Hiding never frees the target",
  "victim-never-in": "Target never accepted",
  "self-defeat-only": "Only self-attacking arguments",
  "walk-only": "Odd walk only (no odd simple path)",
};

async function expInit() {
  if (expLoaded) return; expLoaded = true;
  const d = await api("/api/experiments");
  const runs = [["self_attacks", "self-attacks allowed (main)"], ["no_self_attacks", "no self-attacks"]].filter(([k]) => d[k]);
  const cfg = d[runs[0][0]].config;
  $("#exp-config").textContent = `${cfg.instances_per_p} instances per p · ${cfg.agents} agents · ${cfg.n_args.join("/")} arguments · seed ${cfg.seed}`;
  const ps = Object.keys(d[runs[0][0]].per_p);
  const series = key => runs.map(([k, label]) => ({ label, values: ps.map(p => d[k].per_p[p][key]) }));
  barChart($("#exp-chart-sp"), ps, series("frac_strategyproof"));
  barChart($("#exp-chart-cond"), ps, series("frac_cond_walk"));

  const q2 = $("#exp-q2");
  for (const [k, label] of runs) {
    const t = d[k].total;
    const holds = Object.values(d[k].per_p).reduce((s, x) => s + x.cond_walk, 0);
    q2.append(h("p", {}, h("span", { class: "badge " + (t.q2_walk_count ? "no" : "yes") }, String(t.q2_walk_count)), `  ${label}  (condition held in ${holds} instances)`));
  }
  q2.append(h("p", { class: "note" }, "Zero in every run, matching Theorem 5.4: the condition is sufficient for strategyproofness."));

  const keys = [...new Set(runs.flatMap(([k]) => Object.keys(d[k].total.q3_categories)))];
  keys.sort((a, b) => (d.self_attacks?.total.q3_categories[b] || 0) - (d.self_attacks?.total.q3_categories[a] || 0));
  const tb = h("table", {}, h("tr", {}, h("th", {}, "reason"), runs.map(([, l]) => h("th", { class: "num" }, l))));
  for (const c of keys) tb.append(h("tr", {}, h("td", {}, Q3NAMES[c] || c), runs.map(([k]) => h("td", { class: "num" }, String(d[k].total.q3_categories[c] || 0)))));
  tb.append(h("tr", {}, h("td", {}, h("b", {}, "total")), runs.map(([k]) => h("td", { class: "num" }, h("b", {}, String(d[k].total.q3_count))))));
  $("#exp-q3").append(h("div", { class: "tablewrap" }, tb), h("p", { class: "note" }, "The condition is far from necessary: most manipulable-looking structures are neutralised."));

  const ct = h("table", {}, h("tr", {}, h("th", {}, "run"), h("th", {}, "p"), h("th", { class: "num" }, "cond ∧ SP"), h("th", { class: "num" }, "cond ∧ ¬SP"), h("th", { class: "num" }, "¬cond ∧ SP"), h("th", { class: "num" }, "¬cond ∧ ¬SP")));
  for (const [k, label] of runs) for (const p of ps) {
    const s = d[k].per_p[p];
    ct.append(h("tr", {}, h("td", {}, label), h("td", {}, p), [s.cond_and_sp, s.cond_not_sp, s.notcond_sp, s.notcond_not_sp].map(x => h("td", { class: "num" }, String(x)))));
  }
  $("#exp-cont").append(ct);
}

function barChart(box, cats, series) {
  const W = 720, H = 260, L = 46, B = 30, T = 16, plotH = H - B - T, plotW = W - L - 10;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" });
  for (const t of [0, 0.25, 0.5, 0.75, 1]) {
    const y = T + plotH * (1 - t);
    el("line", { x1: L, x2: W - 10, y1: y, y2: y, class: "axis" }, svg);
    const tx = el("text", { x: L - 8, y: y + 4, "text-anchor": "end", class: "lbl" }, svg); tx.textContent = Math.round(t * 100) + "%";
  }
  const gw = plotW / cats.length, bw = Math.min(56, (gw - 30) / series.length);
  const bars = [];
  cats.forEach((c, i) => {
    const gx = L + gw * i + (gw - bw * series.length - 6 * (series.length - 1)) / 2;
    series.forEach((s, j) => {
      const v = s.values[i], x = gx + j * (bw + 6);
      const r = el("rect", { x, y: T + plotH * (1 - v), width: bw, height: Math.max(plotH * v, 0.5), rx: 4, class: "b" + j }, svg);
      const t = el("text", { x: x + bw / 2, y: T + plotH * (1 - v) - 5, "text-anchor": "middle" }, svg);
      t.textContent = (v * 100).toFixed(1) + "%";
      bars.push([r, v]);
    });
    const lt = el("text", { x: L + gw * i + gw / 2, y: H - 8, "text-anchor": "middle", class: "lbl" }, svg); lt.textContent = "p = " + c;
  });
  box.innerHTML = ""; box.append(svg);
  box.append(h("div", { class: "key" }, series.map((s, j) => h("span", {}, h("i", { style: `background:var(--${j ? "agent1" : "accent"})` }), s.label))));
  requestAnimationFrame(() => requestAnimationFrame(() => bars.forEach(([r]) => r.classList.add("grown"))));
}

/* ===================================================================== */
/* boot                                                                    */
/* ===================================================================== */
document.querySelectorAll(".tab").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("active", x === b));
  document.querySelectorAll(".tabpane").forEach(p => p.classList.toggle("active", p.id === "tab-" + b.dataset.tab));
  if (b.dataset.tab === "experiments") expInit();
}));

api("/api/examples").then(ex => { engInit(ex.engine); stInit(ex.strategic); });
