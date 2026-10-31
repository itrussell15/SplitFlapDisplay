// Shared chrome behaviour for every page: connection status + mobile sidebar.
(function () {
  const displayStatus = document.getElementById("display-status");
  if (displayStatus) {
    const dot = displayStatus.querySelector(".status-dot");
    // const text = displayStatus.querySelector("#status-text");
    // Pages that load their own logic (e.g. the compose page via app.js) set
    // data-status-managed="true" so they own the status text; we only drive the dot.
    // const managed = document.body.dataset.statusManaged === "true";

    async function ping() {
      try {
        const res = await fetch("/api/v1/health");
        if (!res.ok) throw new Error("offline");
        if (dot) dot.classList.add("connected");
      } catch (err) {
        if (dot) dot.classList.remove("connected");
      }
    }
    ping();
    setInterval(ping, 5000);
  }

  // ── Mobile sidebar toggle ──
  const toggle = document.getElementById("sidebar-toggle");
  const backdrop = document.getElementById("sidebar-backdrop");
  const open = () => document.body.classList.toggle("sidebar-open");
  const close = () => document.body.classList.remove("sidebar-open");
  if (toggle) toggle.addEventListener("click", open);
  if (backdrop) backdrop.addEventListener("click", close);

  // ── Generic popup modal trigger ──
  const popupTriggers = document.querySelectorAll(".popup-trigger");
  const popupOverlays = document.querySelectorAll(".modal-overlay");

  window.openPopup = function openPopup(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("modal-open");

    const firstField = modal.querySelector("input, textarea, select, button");
    if (firstField && !firstField.disabled) {
      setTimeout(() => firstField.focus(), 0);
    }
  }

  window.closePopup = function closePopup(modal) {
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");

    if (!document.querySelector(".modal-overlay.open")) {
      document.body.classList.remove("modal-open");
    }
  }

  popupTriggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const targetId = trigger.dataset.target;
      window.openPopup(targetId);
    });
  });

  popupOverlays.forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) window.closePopup(modal);
    });
  });

  document.querySelectorAll(".modal-close, .modal-close-btn").forEach((control) => {
    control.addEventListener("click", () => {
      const modal = control.closest(".modal-overlay");
      window.closePopup(modal);
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      popupOverlays.forEach((modal) => {
        if (modal.classList.contains("open")) closePopup(modal);
      });
    }
  });
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


