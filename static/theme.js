// Motyw jasny/ciemny. Ładowany w <head> (bez defer), żeby strona nie mignęła złym kolorem.
(function () {
  var saved = null;
  try { saved = localStorage.getItem("leetrepeat-theme"); } catch (e) {}
  var theme = saved;
  if (theme !== "ciemny" && theme !== "jasny") {
    // brak zapisanego wyboru → ustawienie systemu, a gdy go nie ma → ciemny
    var prefersLight = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
    theme = prefersLight ? "jasny" : "ciemny";
  }
  document.documentElement.className = theme === "jasny" ? "lr-light" : "lr-dark";

  window.lrIsDark = function () {
    return document.documentElement.className !== "lr-light";
  };

  var SUN = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path></svg>';
  var MOON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path></svg>';

  document.addEventListener("DOMContentLoaded", function () {
    var button = document.getElementById("theme-toggle");
    if (!button) return;
    button.innerHTML = window.lrIsDark() ? SUN : MOON;
    button.addEventListener("click", function () {
      var next = window.lrIsDark() ? "jasny" : "ciemny";
      document.documentElement.className = next === "jasny" ? "lr-light" : "lr-dark";
      try { localStorage.setItem("leetrepeat-theme", next); } catch (e) {}
      button.innerHTML = next === "ciemny" ? SUN : MOON;
      window.dispatchEvent(new CustomEvent("themechange", { detail: next }));
    });
  });
})();
