/* ParcelTrack Lite: small interface helpers (no data, no network calls). */
(function () {
  "use strict";
  var root = document.documentElement;

  // Light / dark mode switch, remembered in this browser only.
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("pt-theme", next); } catch (e) {}
    });
  });

  // Sidebar drawer on phones.
  var app = document.querySelector("[data-app]");
  if (app) {
    var openBtn = document.querySelector("[data-nav-open]");
    var close = function () { app.classList.remove("nav-open"); if (openBtn) openBtn.setAttribute("aria-expanded", "false"); };
    if (openBtn) openBtn.addEventListener("click", function () { app.classList.add("nav-open"); openBtn.setAttribute("aria-expanded", "true"); });
    document.querySelectorAll("[data-nav-close]").forEach(function (el) { el.addEventListener("click", close); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  }

  // Greeting and date in the top bar, using the viewer's own clock.
  var g = document.querySelector("[data-greeting]");
  if (g) {
    var h = new Date().getHours();
    var part = h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
    g.textContent = part + ", " + (g.getAttribute("data-name") || "");
  }
  var d = document.querySelector("[data-today]");
  if (d) d.textContent = new Date().toLocaleDateString("en-MY", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
})();
