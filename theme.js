// Light and dark themes. Loaded without defer, so the theme is set before first paint.
// Shares its storage key with the blog, so one choice holds across the site.
(() => {
  const KEY = 'clm-theme';
  const root = document.documentElement;
  const system = matchMedia('(prefers-color-scheme: dark)');
  let saved = null;
  try { saved = localStorage.getItem(KEY); } catch { /* storage unavailable */ }

  function apply(theme) {
    root.dataset.theme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = theme === 'dark' ? '#0f0e22' : '#ffffff';
  }
  apply(saved || (system.matches ? 'dark' : 'light'));
  // Follow the system setting until the reader picks a theme.
  system.addEventListener('change', event => { if (!saved) apply(event.matches ? 'dark' : 'light'); });

  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;
    toggle.addEventListener('click', () => {
      saved = root.dataset.theme === 'dark' ? 'light' : 'dark';
      apply(saved);
      try { localStorage.setItem(KEY, saved); } catch { /* storage unavailable */ }
    });
  });
})();
