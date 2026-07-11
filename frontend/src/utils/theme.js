export const THEME_STORAGE_KEY = 'factoryVisionThemeV2'

export function getStoredTheme() {
  return localStorage.getItem(THEME_STORAGE_KEY) || 'dark'
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
  localStorage.setItem(THEME_STORAGE_KEY, theme)
  window.dispatchEvent(new CustomEvent('factory-theme-change', { detail: { theme } }))
}
