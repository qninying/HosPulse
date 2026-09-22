// HosPulse Command Center: shared runtime.
// Fetches .hospulse/*.json at runtime (never hard-coded into a page), renders
// the shared nav and "Data as of" header, and manages the sample/real toggle.
// Every page includes this file and calls CommandCenter.init(tabId, render).

const TABS = [
  { id: "overview", label: "Overview", href: "index.html" },
  { id: "outcomes", label: "Outcomes", href: "outcomes.html" },
  { id: "users", label: "Users & Use Case", href: "users.html" },
  { id: "guardrails", label: "Guardrails", href: "guardrails.html" },
  { id: "systems", label: "Systems", href: "systems.html" },
  { id: "project-management", label: "Project Management", href: "project-management.html" },
  { id: "agents", label: "AI Agents", href: "agents.html" },
  { id: "knowledge-base", label: "Knowledge Base", href: "knowledge-base.html" },
  { id: "data-model", label: "Data Model", href: "data-model.html" },
];

const DATA_DIR = "../.colaberry";
const MODE_KEY = "hospulse-cc-mode"; // "sample" | "real"
const THEME_KEY = "hospulse-theme";
const STALE_AFTER_DAYS = 7;

function storageGet(key) {
  try { return localStorage.getItem(key); } catch (e) { return null; }
}

function storageSet(key, value) {
  try { localStorage.setItem(key, value); } catch (e) { /* private window: preference just won't persist */ }
}

function getMode() {
  return storageGet(MODE_KEY) || "sample";
}

function setMode(mode) {
  storageSet(MODE_KEY, mode);
  location.reload();
}

function getTheme() {
  const explicit = document.documentElement.getAttribute("data-theme");
  if (explicit === "light" || explicit === "dark") return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  storageSet(THEME_KEY, theme);
  renderThemeToggleIcon();
}

const SUN_ICON = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>';
const MOON_ICON = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/></svg>';

function renderThemeToggleIcon() {
  const btn = document.getElementById("cc-theme-toggle");
  if (btn) btn.innerHTML = getTheme() === "dark" ? MOON_ICON : SUN_ICON;
}

async function fetchJson(path) {
  // no-store: these files change whenever scripts/build_plan.py runs, and a
  // cached copy would make the "Data as of" stamp itself go stale.
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

async function loadData() {
  const load = (name) => fetchJson(`${DATA_DIR}/${name}`).catch((err) => {
    console.error(`[command-center] could not load ${name}:`, err.message);
    return null;
  });
  const [plan, progress, manifest] = await Promise.all([load("plan.json"), load("progress.json"), load("manifest.json")]);
  return { plan, progress, manifest };
}

function formatDataAsOf(manifest) {
  if (!manifest || !manifest.generated_at) {
    return { text: "Data as of: unknown. .hospulse/manifest.json is missing or unreadable.", stale: true };
  }
  const generated = new Date(manifest.generated_at);
  const diffDays = (Date.now() - generated.getTime()) / (1000 * 60 * 60 * 24);
  const absolute = generated.toLocaleDateString("en-US", { day: "numeric", month: "long", year: "numeric" });
  let relative;
  if (diffDays < 1) relative = "today";
  else if (diffDays < 2) relative = "1 day ago";
  else relative = `${Math.floor(diffDays)} days ago`;
  const stale = diffDays > STALE_AFTER_DAYS;
  let text = `Data as of ${absolute} (${relative})`;
  if (stale) text += ". Over a week old: run python3 scripts/build_plan.py to refresh.";
  return { text, stale };
}

function sampleBadge() {
  return getMode() === "sample" ? '<span class="cc-sample-badge">Sample data</span>' : "";
}

// Drill-down param, e.g. outcomes.html?id=REQ-016. Every tab handles a list
// view (no id) and a detail view (id present) in the same file.
function getParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

// Exported as `esc`, named escapeHtml here so pages can destructure `esc`
// without colliding with a top-level function of the same name.
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}

function storyState(progress, id) {
  const s = ((progress && progress.stories) || []).find((x) => x.id === id);
  return s && s.verification ? s.verification.state : "not_started";
}

// A requirement counts as "enforced" only if EVERY fulfilling story is
// verified. Partial coverage is shown as partial, never rounded up.
function verificationForRequirement(plan, progress, req) {
  const storyIds = (req && req.fulfilled_by) || [];
  if (storyIds.length === 0) return { state: "unfulfilled", stories: [] };
  const stories = storyIds.map((id) => {
    const planStory = (plan.stories || []).find((s) => s.id === id);
    return { id, title: planStory ? planStory.title : id, state: storyState(progress, id) };
  });
  const allVerified = stories.every((s) => s.state === "verified");
  const anyVerified = stories.some((s) => s.state === "verified");
  return { state: allVerified ? "enforced" : anyVerified ? "partial" : "not_enforced", stories };
}

// Some plan sources (the Colaberry platform's own plan.json) don't
// precompute `derived.owners`; others (this project's own .hospulse
// planner) do. Read it when present, otherwise derive the same shape from
// stories[].owner_agent client-side, so the Agents tab works either way.
function ownersFromPlan(plan) {
  const precomputed = plan.derived && plan.derived.owners;
  if (precomputed) return precomputed;
  const owners = [];
  (plan.stories || []).forEach((s) => {
    if (!s.owner_agent) return;
    let entry = owners.find((o) => o.name === s.owner_agent);
    if (!entry) {
      entry = { name: s.owner_agent, owns: [] };
      owners.push(entry);
    }
    entry.owns.push(s.id);
  });
  return owners;
}

function statusDot(state) {
  const cls = state === "verified" || state === "enforced" ? "cc-dot-ok"
    : state === "in_progress" || state === "submitted" || state === "partial" ? "cc-dot-warn"
    : state === "error" ? "cc-dot-error" : "";
  return `<span class="cc-dot ${cls}"></span>`;
}

function missingDataState(el, file) {
  el.innerHTML = `<div class="cc-empty-state">.hospulse/${file} is missing or unreadable, so there is nothing to show yet. Run <code>python3 scripts/build_plan.py</code> and serve the repo root over HTTP.</div>`;
}

function renderChrome(activeTabId, dataAsOf, plan) {
  const nav = document.getElementById("cc-nav");
  const modeToggle = document.getElementById("cc-mode-toggle");
  const stamp = document.getElementById("cc-data-as-of");
  const sub = document.getElementById("cc-project-sub");

  if (sub && plan && plan.project) sub.textContent = plan.project.name;

  if (nav) {
    nav.innerHTML = TABS.map(
      (t) => `<a href="${t.href}" class="cc-tab${t.id === activeTabId ? " active" : ""}">${t.label}</a>`
    ).join("");
  }

  if (modeToggle) {
    const mode = getMode();
    modeToggle.innerHTML = `
      <button class="cc-mode-btn${mode === "sample" ? " active" : ""}" data-mode="sample">Sample</button>
      <button class="cc-mode-btn${mode === "real" ? " active" : ""}" data-mode="real">Real</button>
    `;
    modeToggle.querySelectorAll(".cc-mode-btn").forEach((btn) => {
      btn.addEventListener("click", () => setMode(btn.dataset.mode));
    });
  }

  if (stamp && dataAsOf) {
    stamp.textContent = dataAsOf.text;
    stamp.className = "cc-data-as-of" + (dataAsOf.stale ? " cc-stale" : "");
  }

  const themeToggle = document.getElementById("cc-theme-toggle");
  if (themeToggle) {
    renderThemeToggleIcon();
    themeToggle.addEventListener("click", () => setTheme(getTheme() === "dark" ? "light" : "dark"));
  }
}

// init(tabId, renderFn): fetch data, render shared chrome, then hand the page
// { plan, progress, manifest, mode, dataAsOf }. Pages must handle plan === null.
async function init(tabId, renderFn) {
  const { plan, progress, manifest } = await loadData();
  const dataAsOf = formatDataAsOf(manifest);
  renderChrome(tabId, dataAsOf, plan);
  const el = document.getElementById("cc-content");
  if (!plan) {
    if (el) missingDataState(el, "plan.json");
    return;
  }
  // Some plan sources leave `schedule` null until dates are finalized (seen
  // from the Colaberry platform's own plan.json). Normalize to an empty
  // object so every page's `plan.schedule.field` reads undefined rather
  // than throwing, and renders an honest blank instead of crashing.
  if (!plan.schedule) plan.schedule = {};
  if (renderFn) renderFn({ plan, progress, manifest, mode: getMode(), dataAsOf });
}

window.CommandCenter = {
  TABS, getMode, setMode, loadData, formatDataAsOf, renderChrome, sampleBadge,
  init, getParam, esc: escapeHtml, verificationForRequirement, statusDot, storyState,
  getTheme, setTheme, ownersFromPlan,
};
