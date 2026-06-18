import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export const useAppStore = defineStore('app', () => {
  // Node mode: 'regular' or 'organization'
  const mode = ref(localStorage.getItem('tessera-mode') || 'regular')

  // Theme: 'light', 'dark', or 'system'
  const theme = ref(localStorage.getItem('tessera-theme') || 'system')

  // API configuration
  const apiUrl = ref(localStorage.getItem('tessera-api-url') || '/api')
  const orgId = ref(localStorage.getItem('tessera-org-id') || '')
  const apiKey = ref(localStorage.getItem('tessera-api-key') || '')

  // Sidebar collapsed state
  const sidebarCollapsed = ref(false)

  // Computed
  const isOrgMode = computed(() => mode.value === 'organization')
  const isDarkMode = computed(() => {
    if (theme.value === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return theme.value === 'dark'
  })

  // Actions
  function setMode(newMode) {
    mode.value = newMode
    localStorage.setItem('tessera-mode', newMode)
  }

  function setTheme(newTheme) {
    theme.value = newTheme
    localStorage.setItem('tessera-theme', newTheme)
    applyTheme()
  }

  function applyTheme() {
    if (isDarkMode.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function setApiConfig({ url, organizationId, key }) {
    if (url !== undefined) {
      apiUrl.value = url
      localStorage.setItem('tessera-api-url', url)
    }
    if (organizationId !== undefined) {
      orgId.value = organizationId
      localStorage.setItem('tessera-org-id', organizationId)
    }
    if (key !== undefined) {
      apiKey.value = key
      localStorage.setItem('tessera-api-key', key)
    }
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // Watch for system theme changes
  if (typeof window !== 'undefined') {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (theme.value === 'system') {
        applyTheme()
      }
    })
    // Apply theme on init
    applyTheme()
  }

  return {
    mode,
    theme,
    apiUrl,
    orgId,
    apiKey,
    sidebarCollapsed,
    isOrgMode,
    isDarkMode,
    setMode,
    setTheme,
    setApiConfig,
    toggleSidebar,
    applyTheme
  }
})
