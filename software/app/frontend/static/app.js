const FLIP_SPEED_MS = 50;

const SPECIAL_FLAPS = [
  { char: "r", label: "Red",    display: "■", color: "#dc3545" },
  { char: "o", label: "Orange", display: "■", color: "#fd7e14" },
  { char: "y", label: "Yellow", display: "■", color: "#ffc107" },
  { char: "g", label: "Green",  display: "■", color: "#28a745" },
  { char: "b", label: "Blue",   display: "■", color: "#007bff" },
  { char: "w", label: "White",  display: "■", color: "#ffffff" },
  { char: "h", label: "Heart",  display: "♥", color: "#dc3545" },
  { char: "s", label: "Star",   display: "★", color: "#ffc107" },
];

let flapMap = {};
let flapChars = [];
let charToNameMap = {};
let gridRows = 0;
let gridCols = 0;
let activeCell = -1;
let boardState = [];
let flapElements = [];
let selectedColor = null;

// ── Init ──

async function init() {
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");

  try {
    const flapRes = await fetch("/api/v1/display/flap");
    if (!flapRes.ok) throw new Error(`Flap fetch failed: HTTP ${flapRes.status}`);
    flapMap = await flapRes.json();
    flapChars = Object.keys(flapMap);
    charToNameMap = buildCharToNameMap(flapMap);
    console.log(`Loaded ${flapChars.length} flaps, ${Object.keys(charToNameMap).length} typeable chars`);

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
  const special = SPECIAL_FLAPS.find(c => c.char === ch);
  if (special) return { text: special.display, color: special.color };
  return { text: ch === " " ? "" : ch.toUpperCase(), color: "#fff" };
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
    const ch = e.key.toUpperCase();
    if (charToFlapName(ch)) {
      flipTo(activeCell, ch);
      if (activeCell < boardState.length - 1) setActiveCell(activeCell + 1);
    }
  }
}

// ── Color Palette ──

function buildColorPalette() {
  const palette = document.getElementById("color-palette");
  palette.innerHTML = "";

  SPECIAL_FLAPS.forEach(cf => {
    if (!charToFlapName(cf.char)) return;
    const swatch = document.createElement("div");
    swatch.className = "color-swatch";
    swatch.title = cf.label;
    if (cf.display === "■") {
      swatch.style.background = cf.color;
    } else {
      swatch.style.background = "#222";
      swatch.style.display = "flex";
      swatch.style.alignItems = "center";
      swatch.style.justifyContent = "center";
      swatch.style.fontSize = "18px";
      swatch.style.color = cf.color;
      swatch.textContent = cf.display;
    }
    swatch.addEventListener("click", () => {
      if (activeCell < 0) return;
      flipTo(activeCell, cf.char);
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

// ── Actions ──

async function submitBoard() {
  const total = gridRows * gridCols;
  const requests = [];

  for (let i = 0; i < total; i++) {
    const row = Math.floor(i / gridCols) + 1;
    const col = (i % gridCols) + 1;
    const ch = boardState[i] || " ";

    const flapName = charToFlapName(ch);
    if (!flapName) continue;

    console.log(`Moving (${row}, ${col})`);
    requests.push({
      location: { row, column: col },
      flap: flapName,
    });
  }

  try {
    const res = await fetch("/api/v1/display/flap", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_time: new Date().toISOString(),
        module_requests: requests,
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

const SPECIAL_CHAR_MAP = {
  " ": "BLANK", "!": "EXCLAIMATION", "?": "QUESTION_MARK", "@": "AT",
  "#": "POUND", "$": "DOLLAR", "%": "PERCENT", "&": "AMPERSAND",
  "(": "LEFT_PAREN", ")": "RIGHT_PAREN", "-": "HYPHEN", "\"": "QUOTE",
  "=": "EQUALS", "+": "PLUS", "/": "SLASH", "*": "STAR",
  ".": "PERIOD", ",": "COMMA", ":": "COLON", ";": "SEMICOLON",
  "'": "QUOTE",
  "0": "ZERO", "1": "ONE", "2": "TWO", "3": "THREE", "4": "FOUR",
  "5": "FIVE", "6": "SIX", "7": "SEVEN", "8": "EIGHT", "9": "NINE",
  "r": "RED", "o": "ORANGE", "y": "YELLOW", "g": "GREEN",
  "b": "BLUE", "w": "WHITE", "h": "HEART", "s": "STAR",
};

function buildCharToNameMap(serverFlapMap) {
  const map = {};
  for (const name of Object.keys(serverFlapMap)) {
    if (name.length === 1) {
      map[name] = name;
    }
  }
  for (const [ch, name] of Object.entries(SPECIAL_CHAR_MAP)) {
    if (name in serverFlapMap) {
      map[ch] = name;
    }
  }
  return map;
}

function charToFlapName(ch) {
  return charToNameMap[ch] || null;
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
