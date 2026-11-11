const FLIP_SPEED_MS = 50;

let flapMap = {};
let flapChars = [];
let charToNameMap = {};
let flapByPosition = new Map();
let flapByCharacter = new Map();
let gridRows = 0;
let gridCols = 0;
let activeCell = -1;
let boardState = [];
let flapElements = [];
let selectedColor = null;

// ── Init ──

function normalizeColor(color) {
  if (!color) return "#ffffff";
  return color.startsWith("#") ? color : `#${color}`;
}

function normalizeFlapEntry(flap) {
  if (!flap || typeof flap !== "object") return null;

  const position = Number(flap.position);
  if (!Number.isFinite(position)) return null;

  const key = String(flap.key ?? flap.character ?? flap.glyph ?? " ");
  const glyph = String(flap.glyph ?? flap.character ?? flap.key ?? " ");

  return {
    position,
    key,
    glyph,
    color: normalizeColor(flap.color_hex ?? flap.color ?? "#ffffff"),
  };
}

function cacheFlapsFromApi(apiFlaps) {
  flapMap = apiFlaps || {};
  flapChars = Object.keys(flapMap);
  flapByPosition.clear();
  flapByCharacter.clear();

  Object.values(flapMap).forEach((flap) => {
    const entry = normalizeFlapEntry(flap);
    if (!entry) return;

    flapByPosition.set(entry.position, entry);

    const aliases = new Set([
      entry.key,
      entry.glyph,
      entry.key.toUpperCase(),
      entry.glyph.toUpperCase(),
      entry.key.toLowerCase(),
      entry.glyph.toLowerCase(),
    ]);

    aliases.forEach((value) => {
      if (value) flapByCharacter.set(value, entry);
    });
  });

  charToNameMap = buildCharToNameMap(flapMap);
  console.log(`Loaded ${flapChars.length} flaps, ${Object.keys(charToNameMap).length} typeable chars`);
}

async function init() {
  const dot = document.getElementById("display-status-dot");
  const text = document.getElementById("status-text");

  try {
    const flapRes = await fetch("/api/v1/flaps/");
    if (!flapRes.ok) throw new Error(`Flap fetch failed: HTTP ${flapRes.status}`);

    const flapData = await flapRes.json();
    const allFlaps = flapData.flaps || flapData;
    cacheFlapsFromApi(allFlaps);

    const infoRes = await fetch("/api/v1/display/info");
    if (!infoRes.ok) throw new Error(`Info fetch failed: HTTP ${infoRes.status}`);
    const config = await infoRes.json();

    gridRows = config.rows;
    gridCols = config.columns;
    boardState = new Array(gridRows * gridCols).fill(" ");

    dot.classList.add("connected");
    text.textContent = `Connected (${gridRows}×${gridCols} · ${flapChars.length} flaps)`;

    buildGrid();
    buildColorPalette();
    buildLoadPopup();
    document.addEventListener("keydown", handleKeyDown);
  } catch (err) {
    console.error("Init failed:", err);
    text.textContent = "Connection failed. Retrying...";
    setTimeout(init, 3000);
  }
}

// ── Grid ──

function buildGrid() {
  const grid = document.getElementById("preview-grid");
  grid.innerHTML = "";
  grid.style.gridTemplateColumns = `repeat(${gridCols}, 1fr)`;
  flapElements = [];

  for (let i = 0; i < gridRows * gridCols; i++) {
    const mod = document.createElement("div");
    mod.className = "flap-module";
    mod.dataset.index = i;
    mod.innerHTML = `
      <div class="flap-half flap-top"><span class="flap-char"></span></div>
      <div class="flap-half flap-bottom"><span class="flap-char"></span></div>
      <div class="flap-divider"></div>
    `;
    mod.addEventListener("click", () => setActiveCell(i));
    grid.appendChild(mod);
    flapElements.push(mod);
  }
}

function setActiveCell(index) {
  flapElements.forEach(el => el.classList.remove("active"));
  activeCell = index;
  if (index >= 0 && index < flapElements.length) {
    flapElements[index].classList.add("active");
  }
}

// ── Flap Display ──

function getCharDisplay(ch) {
  const key = String(ch ?? "");
  const lookup = flapByCharacter.get(key)
    || flapByCharacter.get(key.toUpperCase())
    || flapByCharacter.get(key.toLowerCase());

  if (lookup) {
    const glyph = String(lookup.glyph ?? lookup.key ?? lookup.character ?? " ");
    const text = glyph === " " ? "" : glyph;
    return { text, color: lookup.color || "#fff" };
  }

  const fallback = key === " " ? "" : key.toUpperCase();
  return { text: fallback, color: "#fff" };
}

function renderChar(index, ch) {
  const el = flapElements[index];
  if (!el) return;
  const { text, color } = getCharDisplay(ch);
  el.querySelectorAll(".flap-char").forEach(span => {
    span.textContent = text;
    span.style.color = color;
  });
}

function flipTo(index, ch) {
  const el = flapElements[index];
  if (!el) return;

  const oldChar = boardState[index];
  if (oldChar === ch) return;

  boardState[index] = ch;

  const { text: newDisplay, color: newColor } = getCharDisplay(ch);
  const { text: oldDisplay, color: oldColor } = getCharDisplay(oldChar);

  el.querySelectorAll(".flip-panel").forEach(p => p.remove());

  const down = document.createElement("div");
  down.className = "flip-panel flip-down";
  down.style.setProperty("--flip-speed", FLIP_SPEED_MS + "ms");
  down.innerHTML = `<span class="flap-char" style="color:${oldColor}">${oldDisplay}</span>`;

  const up = document.createElement("div");
  up.className = "flip-panel flip-up";
  up.style.setProperty("--flip-speed", FLIP_SPEED_MS + "ms");
  up.innerHTML = `<span class="flap-char" style="color:${newColor}">${newDisplay}</span>`;

  el.querySelector(".flap-bottom .flap-char").textContent = newDisplay;
  el.querySelector(".flap-bottom .flap-char").style.color = newColor;

  el.appendChild(down);
  el.appendChild(up);

  setTimeout(() => {
    down.remove();
    up.remove();
    el.querySelector(".flap-top .flap-char").textContent = newDisplay;
    el.querySelector(".flap-top .flap-char").style.color = newColor;
  }, FLIP_SPEED_MS * 2 + 20);
}

// ── Keyboard Input ──

function handleKeyDown(e) {
  if (document.body.classList.contains("modal-open")) {
    return;
  }

  if (activeCell < 0) return;

  if (e.key === "Backspace") {
    e.preventDefault();
    flipTo(activeCell, " ");
    if (activeCell > 0) setActiveCell(activeCell - 1);
    return;
  }

  if (e.key === "Delete") {
    e.preventDefault();
    flipTo(activeCell, " ");
    return;
  }

  if (e.key === "ArrowLeft") {
    e.preventDefault();
    if (activeCell > 0) setActiveCell(activeCell - 1);
    return;
  }

  if (e.key === "ArrowRight") {
    e.preventDefault();
    if (activeCell < boardState.length - 1) setActiveCell(activeCell + 1);
    return;
  }

  if (e.key === "ArrowUp") {
    e.preventDefault();
    if (activeCell - gridCols >= 0) setActiveCell(activeCell - gridCols);
    return;
  }

  if (e.key === "ArrowDown") {
    e.preventDefault();
    if (activeCell + gridCols < boardState.length) setActiveCell(activeCell + gridCols);
    return;
  }

  if (e.key === "Escape") {
    e.preventDefault();
    setActiveCell(-1);
    return;
  }

  if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    const ch = e.key;
    const resolved = flapByCharacter.get(ch)
      || flapByCharacter.get(ch.toUpperCase())
      || flapByCharacter.get(ch.toLowerCase());

    if (resolved) {
      const glyph = String(resolved.glyph ?? resolved.key ?? resolved.character ?? " ");
      flipTo(activeCell, glyph);
      if (activeCell < boardState.length - 1) setActiveCell(activeCell + 1);
    }
  }
}

// ── Color Palette ──

function buildColorPalette() {
  const palette = document.getElementById("color-palette");
  palette.innerHTML = "";

  const paletteEntries = [...new Map([...flapByCharacter.values()].map(flap => [flap.glyph ?? flap.key ?? flap.character ?? " ", flap])).values()]
    .filter(flap => {
      const glyph = String(flap.glyph ?? flap.key ?? flap.character ?? "").trim();
      return glyph && !/[A-Za-z0-9]/.test(glyph);
    });

  paletteEntries.forEach((flap) => {
    const glyph = String(flap.glyph ?? flap.key ?? flap.character ?? " ");
    const swatch = document.createElement("div");
    swatch.className = "color-swatch";
    swatch.title = glyph;
    swatch.style.background = "#222";
    swatch.style.display = "flex";
    swatch.style.alignItems = "center";
    swatch.style.justifyContent = "center";
    swatch.style.fontSize = "18px";
    swatch.style.color = flap.color || "#fff";
    swatch.textContent = glyph;
    swatch.addEventListener("click", () => {
      if (activeCell < 0) return;
      flipTo(activeCell, glyph);
      if (activeCell < boardState.length - 1) setActiveCell(activeCell + 1);
    });
    palette.appendChild(swatch);
  });

  const eraseSwatch = document.createElement("div");
  eraseSwatch.className = "color-swatch";
  eraseSwatch.style.background = "#333";
  eraseSwatch.style.display = "flex";
  eraseSwatch.style.alignItems = "center";
  eraseSwatch.style.justifyContent = "center";
  eraseSwatch.style.fontSize = "14px";
  eraseSwatch.style.color = "#999";
  eraseSwatch.textContent = "⌫";
  eraseSwatch.title = "Clear cell";
  eraseSwatch.addEventListener("click", () => {
    if (activeCell < 0) return;
    flipTo(activeCell, " ");
  });
  palette.appendChild(eraseSwatch);
}

async function buildLoadPopup() {
  console.log("Fetching static items");
  const selection = document.querySelector("#load-select");
  if (!selection) return;

  try {
    const nameRequest = await fetch("/api/v1/static/names");
    if (!nameRequest.ok) {
      throw new Error(`Static names request failed: HTTP ${nameRequest.status}`);
    }

    const namesData = await nameRequest.json();
    const names = Object.entries(namesData?.names ?? {});

    selection.innerHTML = "";

    if (names.length === 0) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "No saved layouts";
      option.disabled = true;
      option.selected = true;
      selection.appendChild(option);
      return;
    }

    names.forEach(([name, id]) => {
      const option = document.createElement("option");
      option.value = name;
      option.id = id;
      option.textContent = name;
      selection.appendChild(option);
    });
  } catch (err) {
    console.error("Error loading saved layouts:", err);
    selection.innerHTML = "<option value=''>Unable to load</option>";
  }
}

// ── Actions ──

function getPositionForCharacter(ch) {
  const key = String(ch ?? " ");
  const lookup = flapByCharacter.get(key) || flapByCharacter.get(key.toUpperCase()) || flapByCharacter.get(key.toLowerCase());
  return lookup ? Number(lookup.position) : null;
}

async function collectDisplayInputs() {
  const total = gridRows * gridCols;
  const requests = [];

  for (let i = 0; i < total; i++) {
    const row = Math.floor(i / gridCols) + 1;
    const col = (i % gridCols) + 1;
    const ch = boardState[i] || " ";
    const position = getPositionForCharacter(ch);

    if (position == null || position < 0) continue;

    requests.push({
      location: { row, column: col },
      position,
    });
  }
  return requests;
}

async function submitBoard() {
  const displayInputs = await collectDisplayInputs();

  try {
    const res = await fetch("/api/v1/display/positions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_time: new Date().toISOString(),
        module_requests: displayInputs,
      }),
    });

    if (res.ok) {
      showToast("Display updated");
    } else {
      const err = await res.json();
      showToast(err.detail || "Update failed", "error");
    }
  } catch (err) {
    showToast("Connection error", "error");
  }
}

async function saveBoard() {
  console.log("Saving static board");
  const displayInputs = await collectDisplayInputs();
  const nameInput = document.getElementById("static-item-name");

  const res = await fetch("/api/v1/static/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: nameInput.value.trim(),
      request_time: new Date().toISOString(),
      module_requests: displayInputs,
    }),
  });

  if (res.ok) {
    const modal = document.getElementById("static-item-save-popup");
    console.log(modal);
    window.closePopup(modal);
    showToast("Display locations saved!");
  } else {
    const err = await res.json();
    showToast(err.detail || "Save failed", "error");
  }
  await buildLoadPopup();

}

async function loadBoard() {
  console.log("Loading board from selection");
  // Fetch the selected value
  const selection = document.querySelector("#load-select");
  const selectedId = selection.options[selection.selectedIndex].id;

  // Fill grid with saved values
  await loadBoardFromUuid(selectedId);

  // Close pop up
  const modal = document.getElementById("static-item-load-popup");
  console.log(modal);
  window.closePopup(modal);
}

async function loadBoardFromUuid(uuid)
{
  const res = await fetch(`/api/v1/static/uuid?uuid=${encodeURIComponent(uuid)}`);
  if (res.ok) {
    const itemData = await res.json();
    const modules = itemData?.data ?? [];
    modules.forEach((module) => {
      const index = ((module.location.row - 1) * gridCols) + (module.location.column - 1);
      const rawNumericPosition = Number(module.position ?? module.value ?? -1);
      const flap = flapByPosition.get(rawNumericPosition);
      const charValue = flap ? (flap.glyph ?? flap.key ?? flap.character ?? " ") : " ";
      flipTo(index, charValue);
    });
    showToast("Load successful");
  } else {
    const err = await res.json();
    showToast(err.detail || "Loading item failed");
  }
}

function clearBoard() {
  for (let i = 0; i < boardState.length; i++) {
    flipTo(i, " ");
  }
  showToast("Board cleared");
}

async function homeAll() {
  try {
    const res = await fetch("/api/v1/display/home", { method: "POST" });
    if (res.ok) {
      clearBoard();
      showToast("Homing all modules");
    } else {
      showToast("Home failed", "error");
    }
  } catch (err) {
    showToast("Connection error", "error");
  }
}

// ── Helpers ──

function buildCharToNameMap(serverFlapMap) {
  const map = {};
  const flapValues = Object.values(serverFlapMap || {});

  flapValues.forEach((flap) => {
    if (!flap || typeof flap !== "object") return;
    const keyValue = String(flap.key ?? flap.glyph ?? flap.character ?? "").trim();
    if (!keyValue) return;
    map[keyValue] = keyValue;
    map[keyValue.toUpperCase()] = keyValue;
    map[keyValue.toLowerCase()] = keyValue;
  });

  return map;
}

// ── Toast ──

function showToast(msg, type = "success") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "error" : ""}`;
  toast.textContent = msg;
  container.appendChild(toast);
  requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add("show")));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

// ── Boot ──

document.addEventListener("DOMContentLoaded", init);
