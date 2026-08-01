/* Shared light/dark theme control for the course pages. */
(() => {
  const STORAGE_KEY = "course-theme";
  const root = document.documentElement;
  const systemPrefersDark = () =>
    window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

  let savedTheme = null;
  try {
    savedTheme = window.localStorage.getItem(STORAGE_KEY);
  } catch (_) {
    // Private browsing or a restrictive storage policy should not break reading.
  }
  if (savedTheme === "light" || savedTheme === "dark") {
    root.dataset.theme = savedTheme;
  }

  const currentThemeIsDark = () =>
    root.dataset.theme === "dark" ||
    (!root.dataset.theme && systemPrefersDark());

  const addControl = () => {
    const button = document.createElement("button");
    button.className = "theme-toggle";
    button.type = "button";

    const updateLabel = () => {
      const dark = currentThemeIsDark();
      button.textContent = dark ? "☼ Light" : "☾ Dark";
      button.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
      button.title = dark ? "Switch to light theme" : "Switch to dark theme";
    };

    button.addEventListener("click", () => {
      const nextTheme = currentThemeIsDark() ? "light" : "dark";
      root.dataset.theme = nextTheme;
      try {
        window.localStorage.setItem(STORAGE_KEY, nextTheme);
      } catch (_) {
        // The choice still applies for this page when storage is unavailable.
      }
      updateLabel();
    });

    updateLabel();
    document.body.appendChild(button);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", addControl, { once: true });
  } else {
    addControl();
  }
})();
