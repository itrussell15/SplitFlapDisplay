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

async function setRate() {
  const minutesEl = document.getElementById("rate-minutes");
  const secondsEl = document.getElementById("rate-seconds");
  const btn = document.getElementById("rate-limit-btn");
  const result = document.getElementById("rate-limit-result");

  const minutesValue = parseInt(minutesEl.value, 10);
  const secondsValue = parseInt(secondsEl.value, 10);
  if (!Number.isInteger(minutesValue) || !Number.isInteger(secondsValue) || minutesValue < 0 || secondsValue < 0) {
    showToast("Enter valid minutes and seconds", "error");
    return;
  }

  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = "SETTING...";

  try {
    const res = await fetch("/api/v1/rate_limiting/rate?" + new URLSearchParams({minutes: minutesValue, seconds: secondsValue}), 
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }
    );
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

  } catch (err) {
    result.innerHTML = `<span class="rate-limit-error">Set Rate Limit failed: ${err.message}</span>`;
    showToast("Set Rate Limit Fail", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

// Initialize or refresh the rate-limit fields. Call this when the
// settings page/tab is shown.
async function initSettingsRate() {
  try {
    const res = await fetch("/api/v1/rate_limiting/rate", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    console.log("Data received:", data);

    const minutesEl = document.getElementById("rate-minutes");
    const secondsEl = document.getElementById("rate-seconds");
    if (minutesEl) minutesEl.value = data.rate.minutes ?? 0;
    if (secondsEl) secondsEl.value = data.rate.seconds ?? 0;
  } catch (error) {
    console.error("Failed to fetch rate:", error);
  }
}

// Call on initial page load and when common tab events fire.
document.addEventListener("DOMContentLoaded", () => {

  // Loads rate value
  initSettingsRate();

  // If the settings tab is activated by a button with id `settings-tab-btn`.
  const settingsTabBtn = document.getElementById("settings-tab-btn");
  if (settingsTabBtn) settingsTabBtn.addEventListener("click", initSettingsRate);

  // Bootstrap-style tabs: listen for the shown.bs.tab event on the settings tab link.
  const bsTabLink = document.querySelector('a[data-bs-toggle="tab"][href="#settings"]');
  if (bsTabLink) bsTabLink.addEventListener('shown.bs.tab', initSettingsRate);
});

