// Streamlit 1.66.1 exposes theme selection through these native menu controls.
// Select that theme in this browser session; never rewrite server config or
// reload the app, so registration drafts and other users remain unaffected.
(() => {
  const desired = "__PARKING_THEME__";
  if (window.parkingNativeTheme === desired) return;
  const menu = document.querySelector('[data-testid="stMainMenuButton"]');
  if (!menu) return;
  const wasOpen = menu.getAttribute("aria-expanded") === "true";
  const previousFocus = document.activeElement;
  const root = document.documentElement;
  let finished = false;
  let selected = false;
  let timeout;
  const finish = success => {
    if (finished) return;
    finished = true;
    observer.disconnect();
    clearTimeout(timeout);
    if (!wasOpen && menu.getAttribute("aria-expanded") === "true") menu.click();
    root.classList.remove("parking-theme-sync");
    if (previousFocus instanceof HTMLElement && previousFocus.isConnected) {
      previousFocus.focus({ preventScroll: true });
    }
    if (success) {
      window.parkingNativeTheme = desired;
      root.dataset.parkingNativeTheme = desired;
    } else {
      console.warn("Parking theme: native theme selector was unavailable.");
    }
  };
  const select = () => {
    if (finished) return;
    const name = desired === "dark" ? "Dark" : "Light";
    const option = document.querySelector(`[data-testid="stMainMenuItem-theme-${name}"]`);
    if (!option) return;
    if (option.getAttribute("aria-checked") === "true") {
      finish(true);
    } else if (!selected) {
      selected = true;
      option.click();
    }
  };
  const observer = new MutationObserver(select);
  observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["aria-checked"] });
  root.classList.add("parking-theme-sync");
  timeout = setTimeout(() => finish(false), 2000);
  if (!wasOpen) menu.click();
  select();
})();
