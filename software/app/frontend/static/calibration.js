// Interactive calibration wizard.
//
// Two flows, both faithful to the CLI scripts in control/calibration/:
//   * Home Offset  — per selected module: home with offset 0, nudge to the home
//                    flap, then SET_HOME_OFFSET to the found step.
//   * Flap Positions — for each flap position, nudge each selected module onto the
//                    flap and SET_POSITION (stores the current step in EEPROM),
//                    then advance all modules forward ~one flap and repeat.
//
// The motor is forward-only, so a backward nudge re-homes then moves forward.
// The backend stays stateless; this file orchestrates the primitive endpoints.

const API = "/api/v1";
const MOTOR_RESOLUTION = 4096;
const NUM_POSITIONS = 64;
const MOVE_OFFSET = 64; // steps advanced per flap position
const NUDGES = [-100, -64, -20, -10, -4, -1, 1, 4, 10, 20, 64, 100];

// ── Wizard state ──
const cal = {
  type: null, // 'home' | 'flap'
  modules: [], // working list: [{row, column}]
  steps: {}, // "r,c" -> current absolute step
  idx: 0, // home flow: index into modules
  position: 0, // flap flow: current flap value
  done: {}, // flap flow: "r,c" -> bool for current position
  settleMs: 7000,
  locked: new Set(), // "r,c" -> true while a module is rehoming
};

let available = []; // discovered modules [{row, column}]
const selected = new Set(); // selected "r,c" keys
let flapByPosition = new Map(); // position -> {position, glyph, color_hex}

const k = (m) => `${m.row},${m.column}`;
const clampStep = (s) => Math.max(0, Math.min(s, MOTOR_RESOLUTION - 1));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const flapName = (value) => {
  const flap = flapByPosition.get(Number(value));
  if (!flap) return `#${value}`;
  const glyph = String(flap.glyph ?? flap.key ?? flap.character ?? " ");
  if (glyph === " ") return "BLANK";
  return glyph;
};

// ── API helpers ──
async function api(path, opts = {}) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}
const post = (path, body) =>
  api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
const loc = (m) => ({ row: m.row, column: m.column });

const setCalMode = (m, on) => post("/modules/calibration_mode", { location: loc(m), enabled: on });
const homeModule = (m) => post(`/modules/home?row=${m.row}&column=${m.column}`);
const moveToStep = (m, s) => post(`/modules/steps/${s}`, loc(m));
const setHomeOff = (m, v) => post("/modules/home_offset", { location: loc(m), value: v });
const getHomeOff = (m) => api(`/modules/home_offset?row=${m.row}&column=${m.column}`);
const savePos = (m, p) => post(`/modules/save_position/${p}`, { location: loc(m) });

// ── Busy overlay ──
async function runBusy(message, fn) {
  const overlay = document.getElementById("cal-busy");
  document.getElementById("cal-busy-msg").textContent = message;
  document.getElementById("cal-busy-count").textContent = "";
  overlay.classList.add("show");
  try {
    return await fn();
  } finally {
    overlay.classList.remove("show");
  }
}

async function settle(message) {
  const overlay = document.getElementById("cal-busy");
  const countEl = document.getElementById("cal-busy-count");
  const msgEl = document.getElementById("cal-busy-msg");
  if (message) msgEl.textContent = message;
  if (overlay && overlay.classList.contains("show")) {
    const secs = Math.ceil(cal.settleMs / 1000);
    for (let i = secs; i > 0; i--) {
      countEl.textContent = `Waiting ${i}s for motors to settle…`;
      await sleep(1000);
    }
    countEl.textContent = "";
  } else {
    await sleep(cal.settleMs);
  }
}

// ── Setup: module selection ──
async function loadModules() {
  const grid = document.getElementById("cal-modules");
  grid.innerHTML = `<span class="settings-desc">Loading modules…</span>`;
  try {
    const data = await api("/display/modules");
    available = (data.locations || [])
      .map((item) => item.location || item)
      .sort((a, b) => a.row - b.row || a.column - b.column);
  } catch (err) {
    grid.innerHTML = `<span class="discover-error">Could not load modules: ${err.message}</span>`;
    return;
  }
  if (!available.length) {
    grid.innerHTML =
      `<span class="settings-desc">No modules discovered yet. Run a scan on the ` +
      `<a href="/settings" style="color:var(--accent)">Settings</a> page first.</span>`;
    return;
  }
  // Drop selections that no longer exist
  for (const key of [...selected]) if (!available.some((m) => k(m) === key)) selected.delete(key);
  renderModuleGrid();
}

function renderModuleGrid() {
  const grid = document.getElementById("cal-modules");
  grid.innerHTML = "";

  const rows = [...new Set(available.map((m) => m.row))].sort((a, b) => a - b);
  const columns = [...new Set(available.map((m) => m.column))].sort((a, b) => a - b);
  const maxColumns = Math.max(1, columns.length || 15);
  const moduleByKey = new Map(available.map((m) => [k(m), m]));

  grid.style.gridTemplateColumns = `72px repeat(${maxColumns}, minmax(34px, 1fr))`;

  const rowHeader = document.createElement("div");
  rowHeader.className = "cal-module-empty";
  grid.appendChild(rowHeader);

  for (let col = 1; col <= maxColumns; col++) {
    const colHeader = document.createElement("div");
    colHeader.className = "cal-module-col-label";
    colHeader.textContent = `${col}`;
    grid.appendChild(colHeader);
  }

  rows.forEach((row) => {
    const rowLabel = document.createElement("div");
    rowLabel.className = "cal-module-row-label";
    rowLabel.textContent = `R${row}`;
    grid.appendChild(rowLabel);

    for (let column = 1; column <= maxColumns; column++) {
      const module = moduleByKey.get(`${row},${column}`);
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cal-module-cell" + (module && selected.has(k(module)) ? " selected" : "");
      cell.textContent = module ? `${column}` : "";
      cell.title = module ? `(${row}, ${column})` : "";
      cell.disabled = !module;
      if (module) {
        cell.onclick = () => {
          selected.has(k(module)) ? selected.delete(k(module)) : selected.add(k(module));
          renderModuleGrid();
        };
      }
      grid.appendChild(cell);
    }
  });

  document.getElementById("cal-selected-count").textContent = `${selected.size} selected`;
}

function selectAllModules() {
  available.forEach((m) => selected.add(k(m)));
  renderModuleGrid();
}
function clearModuleSelection() {
  selected.clear();
  renderModuleGrid();
}

// ── Setup: type + params ──
function chooseType(type) {
  cal.type = type;
  document.getElementById("cal-type-home").classList.toggle("selected", type === "home");
  document.getElementById("cal-type-flap").classList.toggle("selected", type === "flap");
  document.getElementById("cal-params").style.display = "flex";
  document.querySelectorAll(".cal-param-home").forEach((e) => (e.style.display = type === "home" ? "flex" : "none"));
  document.querySelectorAll(".cal-param-flap").forEach((e) => (e.style.display = type === "flap" ? "flex" : "none"));
}

function selectedModules() {
  return available.filter((m) => selected.has(k(m)));
}

async function getStartFlapGuess(module, flapPosition) {
  const guessField = document.getElementById("cal-flap-guess");
  const fallback = clampStep(parseInt(guessField ? guessField.value : "0", 10) || 0);

  try {
    const data = await api(`/modules/position?row=${module.row}&column=${module.column}&position=${flapPosition}`);
    const value = Number(data && data.data_value != null ? data.data_value : NaN);
    if (Number.isFinite(value)) return clampStep(value);
  } catch (err) {
    console.warn(`Could not load saved position ${flapPosition} for (${module.row},${module.column}):`, err);
  }

  return fallback;
}

function showSection(id) {
  ["cal-setup", "cal-home", "cal-flap", "cal-done"].forEach((s) => {
    document.getElementById(s).style.display = s === id ? "block" : "none";
  });
}

async function startCalibration() {
  cal.modules = selectedModules();
  if (!cal.modules.length) {
    showToast("Select at least one module", "error");
    return;
  }
  if (!cal.type) {
    showToast("Choose a calibration type", "error");
    return;
  }
  cal.settleMs = Math.max(1, parseInt(document.getElementById("cal-settle").value, 10) || 7) * 1000;
  cal.steps = {};
  try {
    if (cal.type === "home") await startHome();
    else await startFlap();
  } catch (err) {
    showToast(err.message || "Failed to start", "error");
    await safeExitCalMode();
    showSection("cal-setup");
  }
}

function isModuleLocked(m) {
  return cal.locked.has(k(m));
}

function renderCurrentView() {
  if (cal.type === "home") renderHome();
  else if (cal.type === "flap") renderFlap();
}

// ── Shared nudge ──
async function onNudge(row, column, delta) {
  const m = { row, column };
  const key = k(m);
  if (isModuleLocked(m)) return;

  cal.locked.add(key);
  renderCurrentView();

  try {
    const target = clampStep((cal.steps[key] ?? 0) + delta);
    if (delta < 0) {
      await homeModule(m);
      await settle(`Re-homing (${row},${column})…`);
    }
    const r = await moveToStep(m, target);
    cal.steps[key] = r && r.data_value != null ? r.data_value : target;
  } catch (err) {
    showToast(err.message || "Move failed", "error");
  } finally {
    cal.locked.delete(key);
    renderCurrentView();
  }
}

function nudgeButtons(m) {
  const locked = isModuleLocked(m);
  return NUDGES.map(
    (d) =>
      `<button class="cal-nudge ${d < 0 ? "neg" : "pos"}" ${locked ? "disabled" : ""} onclick="onNudge(${m.row},${m.column},${d})">${d > 0 ? "+" : ""}${d}</button>`
  ).join("");
}

// ── Home offset flow ──
async function startHome() {
  const guess = clampStep(parseInt(document.getElementById("cal-home-guess").value, 10) || 0);
  cal.idx = 0;
  await runBusy("Preparing modules…", async () => {
    for (const m of cal.modules) {
      await setCalMode(m, true);
      await setHomeOff(m, 0);
    }
    for (const m of cal.modules) await homeModule(m);
    await settle("Homing all selected modules…");
    for (const m of cal.modules) {
      const r = await moveToStep(m, guess);
      cal.steps[k(m)] = r && r.data_value != null ? r.data_value : guess;
    }
  });
  showSection("cal-home");
  renderHome();
}

function renderHome() {
  const m = cal.modules[cal.idx];
  if (!m) return;
  document.getElementById("cal-home-module").textContent = `(${m.row}, ${m.column})`;
  document.getElementById("cal-home-progress").textContent = `${cal.idx + 1} / ${cal.modules.length}`;
  document.getElementById("cal-home-step").textContent = cal.steps[k(m)] ?? 0;
  document.getElementById("cal-home-nudge").innerHTML = nudgeButtons(m);
  document.getElementById("cal-home-nudge").setAttribute("aria-busy", isModuleLocked(m) ? "true" : "false");
}

async function acceptHome() {
  const m = cal.modules[cal.idx];
  const step = cal.steps[k(m)] ?? 0;
  try {
    await runBusy("Saving home offset…", async () => {
      await setHomeOff(m, step);
      const v = await getHomeOff(m);
      if (v && v.data_value !== step) {
        showToast(`Verify mismatch: wrote ${step}, read ${v.data_value}`, "error");
      } else {
        showToast(`Saved offset ${step} for (${m.row},${m.column})`);
      }
    });
  } catch (err) {
    showToast(err.message || "Save failed", "error");
    return;
  }
  nextHomeModule();
}

async function acceptAllHome() {
  const m = cal.modules[cal.idx];
  const step = cal.steps[k(m)] ?? 0;
  try {
    await runBusy(`Saving home offsets for all modules…`, async () => {
      for (const module of cal.modules) {
        await setHomeOff(module, step);
        const v = await getHomeOff(module);
        if (v && v.data_value !== step) {
          showToast(`Verify mismatch: wrote ${step}, read ${v.data_value} for (${module.row},${module.column})`, "error");
        }
      }
      showToast(`Saved offset ${step} for ${cal.modules.length} module(s)`);
    });
  } catch (err) {
    showToast(err.message || "Save all failed", "error");
    return;
  }
  await finishCalibration();
}

function skipHome() {
  nextHomeModule();
}

async function nextHomeModule() {
  cal.idx++;
  if (cal.idx >= cal.modules.length) await finishCalibration();
  else renderHome();
}

// ── Flap position flow ──
async function startFlap() {
  const startValue = Number(document.getElementById("cal-flap-start").value || 0);
  cal.position = Number.isFinite(startValue) ? startValue : 0;

  await runBusy("Preparing modules…", async () => {
    for (const m of cal.modules) await setCalMode(m, true);
    for (const m of cal.modules) await homeModule(m);
    await settle("Homing all selected modules…");

    for (const m of cal.modules) {
      const guess = await getStartFlapGuess(m, cal.position);
      const r = await moveToStep(m, guess);
      cal.steps[k(m)] = r && r.data_value != null ? r.data_value : guess;
    }
  });
  showSection("cal-flap");
  startPosition();
}

function startPosition() {
  cal.done = {};
  cal.modules.forEach((m) => (cal.done[k(m)] = false));
  renderFlap();
}

function renderFlap() {
  document.getElementById("cal-flap-name").textContent = flapName(cal.position);
  document.getElementById("cal-flap-progress").textContent = `${cal.position} / ${NUM_POSITIONS - 1}`;
  const wrap = document.getElementById("cal-flap-modules");
  wrap.innerHTML = "";
  cal.modules.forEach((m) => {
    const done = cal.done[k(m)];
    const busy = isModuleLocked(m);
    const row = document.createElement("div");
    row.className = "cal-flap-row" + (done ? " done" : "") + (busy ? " busy" : "");
    row.innerHTML = `
      <div class="cal-flap-loc">(${m.row},${m.column})</div>
      <div class="cal-flap-step">step <strong>${cal.steps[k(m)] ?? 0}</strong></div>
      <div class="cal-nudge-row">${done || busy ? "" : nudgeButtons(m)}</div>
      <button class="btn ${done ? "btn-secondary" : busy ? "btn-secondary cal-flap-busy" : "btn-primary"} btn-sm cal-flap-ok"
        ${done || busy ? "disabled" : ""} onclick="okFlap(${m.row},${m.column})">${done ? "✓ OK" : busy ? "Working…" : "OK"}</button>`;
    wrap.appendChild(row);
  });
}

async function okFlap(row, column) {
  const m = { row, column };
  if (isModuleLocked(m)) return;
  try {
    await runBusy(`Saving ${flapName(cal.position)} for (${row},${column})…`, () =>
      savePos(m, cal.position)
    );
  } catch (err) {
    showToast(err.message || "Save failed", "error");
    return;
  }
  cal.done[k(m)] = true;
  if (cal.modules.every((x) => cal.done[k(x)])) await advancePosition();
  else renderFlap();
}

async function acceptAllFlap() {
  try {
    await runBusy(`Saving ${flapName(cal.position)} for all modules…`, async () => {
      for (const m of cal.modules) {
        await savePos(m, cal.position);
        cal.done[k(m)] = true;
      }
      showToast(`Saved ${flapName(cal.position)} for ${cal.modules.length} module(s)`);
    });
  } catch (err) {
    showToast(err.message || "Save all failed", "error");
    return;
  }
  await advancePosition();
}

async function advancePosition() {
  if (cal.position >= NUM_POSITIONS - 1) {
    await finishCalibration();
    return;
  }
  cal.position++;
  try {
    await runBusy(`Advancing to ${flapName(cal.position)}…`, async () => {
      for (const m of cal.modules) {
        const target = clampStep((cal.steps[k(m)] ?? 0) + MOVE_OFFSET);
        const r = await moveToStep(m, target);
        cal.steps[k(m)] = r && r.data_value != null ? r.data_value : target;
      }
    });
  } catch (err) {
    showToast(err.message || "Advance failed", "error");
  }
  startPosition();
}

function skipPosition() {
  advancePosition();
}

// ── Finish / abort ──
async function safeExitCalMode() {
  for (const m of cal.modules) {
    try { await setCalMode(m, false); } catch (e) {}
  }
}

async function finishCalibration() {
  await runBusy("Finishing up…", safeExitCalMode);
  document.getElementById("cal-done-msg").textContent =
    cal.type === "home"
      ? `Home offsets saved for ${cal.modules.length} module(s).`
      : `Flap positions saved for ${cal.modules.length} module(s).`;
  showSection("cal-done");
}

async function abortCalibration() {
  const warn =
    cal.type === "home"
      ? "Abort? Modules you haven't saved keep a home offset of 0 until re-calibrated."
      : "Abort? Flaps you haven't saved keep their previous stored positions.";
  if (!confirm(warn)) return;
  await runBusy("Aborting…", safeExitCalMode);
  resetWizard();
}

function resetWizard() {
  cal.type = null;
  document.getElementById("cal-params").style.display = "none";
  document.getElementById("cal-type-home").classList.remove("selected");
  document.getElementById("cal-type-flap").classList.remove("selected");
  showSection("cal-setup");
  loadModules();
}

// ── Boot ──
async function initCalibration() {
  try {
    const data = await api("/flaps/");
    const flapList = Object.values(data.flaps || {});
    flapByPosition = new Map();

    flapList.forEach((flap) => {
      if (!flap || flap.position == null) return;
      const position = Number(flap.position);
      const glyph = String(flap.glyph ?? flap.key ?? flap.character ?? " ");
      flapByPosition.set(position, {
        position,
        key: String(flap.key ?? flap.character ?? glyph),
        glyph,
        color_hex: flap.color_hex ?? "#ffffff",
      });
    });

    const sel = document.getElementById("cal-flap-start");
    sel.innerHTML = "";
    [...flapByPosition.keys()]
      .sort((a, b) => a - b)
      .forEach((position) => {
        const flap = flapByPosition.get(position);
        const label = `${position} · ${flapName(position)}`;
        const opt = document.createElement("option");
        opt.value = String(position);
        opt.textContent = label;
        sel.appendChild(opt);
      });

    if (sel.options.length > 0) {
      sel.value = String(Math.min(0, sel.options.length - 1));
    }
  } catch (err) {
    showToast("Could not load flap list", "error");
  }
  await loadModules();
}

document.addEventListener("DOMContentLoaded", initCalibration);
