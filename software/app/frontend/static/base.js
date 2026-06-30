// Shared chrome behaviour for every page: connection status + mobile sidebar.
(function () {
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
  // Pages that load their own logic (e.g. the compose page via app.js) set
  // data-status-managed="true" so they own the status text; we only drive the dot.
  const managed = document.body.dataset.statusManaged === "true";

  async function ping() {
    try {
      const res = await fetch("/api/v1/health");
      if (!res.ok) throw new Error("offline");
      if (dot) dot.classList.add("connected");
      if (!managed && text) text.textContent = "Online";
    } catch (err) {
      if (dot) dot.classList.remove("connected");
      if (!managed && text) text.textContent = "Offline";
    }
  }
  ping();
  setInterval(ping, 5000);

  // ── Mobile sidebar toggle ──
  const toggle = document.getElementById("sidebar-toggle");
  const backdrop = document.getElementById("sidebar-backdrop");
  const open = () => document.body.classList.toggle("sidebar-open");
  const close = () => document.body.classList.remove("sidebar-open");
  if (toggle) toggle.addEventListener("click", open);
  if (backdrop) backdrop.addEventListener("click", close);
})();

// Shared toast helper, available on every page (compose page's app.js has its own
// identical copy that harmlessly overrides this where it is loaded).
function showToast(msg, type = "success") {
  const container = document.getElementById("toast-container");
  if (!container) return;
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
