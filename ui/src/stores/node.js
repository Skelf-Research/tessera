import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAppStore } from './app'

export const useNodeStore = defineStore('node', () => {
  const appStore = useAppStore()

  // Health status
  const health = ref(null)
  const healthLoading = ref(false)
  const healthError = ref(null)

  // Stats
  const stats = ref(null)
  const statsLoading = ref(false)

  // WebSocket connection
  const wsConnected = ref(false)
  const wsClients = ref(0)

  // Last updated timestamps
  const lastHealthCheck = ref(null)
  const lastStatsUpdate = ref(null)

  // Polling interval ID
  let pollInterval = null

  // Computed
  const isHealthy = computed(() => health.value?.status === 'healthy')

  const statusColor = computed(() => {
    if (healthLoading.value) return 'gray'
    if (healthError.value) return 'red'
    if (isHealthy.value) return 'green'
    return 'yellow'
  })

  const activeCommitments = computed(() => stats.value?.active_commitments || 0)
  const verifiedProofs = computed(() => stats.value?.verified_proofs || 0)
  const totalVerifications = computed(() => stats.value?.total_verifications || 0)

  // Actions
  async function fetchHealth() {
    healthLoading.value = true
    healthError.value = null

    try {
      const response = await fetch(`${appStore.apiUrl}/health`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      health.value = await response.json()
      lastHealthCheck.value = new Date()

      // Update WebSocket status from health response
      if (health.value.websocket) {
        wsConnected.value = health.value.websocket.connected !== false
        wsClients.value = health.value.websocket.clients || 0
      }
    } catch (error) {
      healthError.value = error.message
      health.value = null
    } finally {
      healthLoading.value = false
    }
  }

  async function fetchStats() {
    statsLoading.value = true

    try {
      const response = await fetch(`${appStore.apiUrl}/stats`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      stats.value = await response.json()
      lastStatsUpdate.value = new Date()
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    } finally {
      statsLoading.value = false
    }
  }

  function startPolling(interval = 10000) {
    if (pollInterval) return

    // Initial fetch
    fetchHealth()
    fetchStats()

    // Start polling
    pollInterval = setInterval(() => {
      fetchHealth()
      fetchStats()
    }, interval)
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval)
      pollInterval = null
    }
  }

  return {
    health,
    healthLoading,
    healthError,
    stats,
    statsLoading,
    wsConnected,
    wsClients,
    lastHealthCheck,
    lastStatsUpdate,
    isHealthy,
    statusColor,
    activeCommitments,
    verifiedProofs,
    totalVerifications,
    fetchHealth,
    fetchStats,
    startPolling,
    stopPolling
  }
})
