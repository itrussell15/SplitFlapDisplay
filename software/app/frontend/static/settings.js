// Settings page: module discovery.

async function runDiscover() {
  const rowsEl = document.getElementById("discover-rows");
  const colsEl = document.getElementById("discover-cols");
  const btn = document.getElementById("discover-btn");
  const result = document.getElementById("discover-result");

  const maxRow = parseInt(rowsEl.value, 10);
  const maxColumn = parseInt(colsEl.value, 10);
  if (!Number.isInteger(maxRow) || !Number.isInteger(maxColumn) || maxRow < 1 || maxColumn < 1) {
    showToast("Enter valid row and column counts", "error");
    return;
  }

  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "SCANNING…";
  result.innerHTML = `<div class="discover-summary">Scanning ${maxRow}×${maxColumn} for modules…</div>`;

  try {
    const res = await fetch("/api/v1/display/discover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ max_row: maxRow, max_column: maxColumn }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    renderDiscover(await res.json());
  } catch (err) {
    result.innerHTML = `<span class="discover-error">Discovery failed: ${err.message}</span>`;
    showToast("Discovery failed", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

function renderDiscover(data) {
  const result = document.getElementById("discover-result");
  const locations = (data.locations || []).slice().sort(
    (a, b) => a.row - b.row || a.column - b.column
  );

  const count = data.num_modules ?? locations.length;
  showToast(`Found ${count} module${count === 1 ? "" : "s"}`);

  if (!locations.length) {
    result.innerHTML = `<div class="discover-summary">No modules responded.</div>`;
    return;
  }

  const chips = locations
    .map(l => `<span class="loc-chip">${l.row},${l.column}</span>`)
    .join("");
  result.innerHTML =
    `<div class="discover-summary">Found <strong>${count}</strong> module(s) ` +
    `on ${data.num_buses} bus(es):</div>` +
    `<div class="loc-grid">${chips}</div>`;
}
