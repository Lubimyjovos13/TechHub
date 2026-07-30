export function getTheme() {
  return localStorage.getItem("th_theme") || "light";
}

export function applyTheme(theme) {
  const root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
  localStorage.setItem("th_theme", theme);
}

// Apply on load
applyTheme(getTheme());
