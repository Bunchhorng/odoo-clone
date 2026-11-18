import { computed, ref } from 'vue'

export type ThemePreference = 'system' | 'light' | 'dark'
const preference = ref<ThemePreference>('system')
const systemDark = ref(false)
const resolved = computed(() => preference.value === 'system' ? (systemDark.value ? 'dark' : 'light') : preference.value)

function applyTheme() {
  document.documentElement.dataset.theme = resolved.value
  document.documentElement.style.colorScheme = resolved.value
}

export function initializeTheme() {
  try {
    const saved = localStorage.getItem('kerp.theme')
    if (saved === 'light' || saved === 'dark') preference.value = saved
  } catch { /* Storage may be unavailable in private or restricted contexts. */ }
  const media = window.matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = media.matches
  const changed = () => { systemDark.value = media.matches; applyTheme() }
  media.addEventListener('change', changed)
  applyTheme()
  return () => media.removeEventListener('change', changed)
}

export function useTheme() {
  function setTheme(value: ThemePreference) {
    preference.value = value
    try { localStorage.setItem('kerp.theme', value) } catch { /* Preference still applies for this visit. */ }
    applyTheme()
  }
  return { preference, resolved, setTheme }
}
