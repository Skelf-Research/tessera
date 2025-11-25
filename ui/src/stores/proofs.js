import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAppStore } from './app'

export const useProofsStore = defineStore('proofs', () => {
  const appStore = useAppStore()

  // Paginated proofs list
  const recentProofs = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Pagination state
  const page = ref(1)
  const pageSize = ref(50)
  const total = ref(0)
  const searchQuery = ref('')
  const statusFilter = ref('all') // all, verified, unverified

  // Verification state
  const verifying = ref(false)
  const lastVerification = ref(null)

  // Broadcasting state
  const broadcasting = ref(false)
  const lastBroadcast = ref(null)

  // Live stats (updated via polling)
  const liveStats = ref({
    totalProofs: 0,
    verifiedToday: 0,
    pendingVerifications: 0,
    proofsPerMinute: 0
  })

  // Computed
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)
  const proofCount = computed(() => total.value)
  const verifiedCount = computed(() => liveStats.value.verifiedToday)

  // Actions
  async function fetchRecentProofs(options = {}) {
    loading.value = true
    error.value = null

    const params = new URLSearchParams({
      page: options.page || page.value,
      limit: options.pageSize || pageSize.value,
      ...(searchQuery.value && { search: searchQuery.value }),
      ...(statusFilter.value !== 'all' && { status: statusFilter.value })
    })

    try {
      const response = await fetch(`${appStore.apiUrl}/proofs/recent?${params}`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      recentProofs.value = data.proofs || data.items || []
      total.value = data.total || data.count || recentProofs.value.length
      page.value = data.page || options.page || page.value

      // Update live stats if provided
      if (data.stats) {
        liveStats.value = { ...liveStats.value, ...data.stats }
      }
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  async function fetchLiveStats() {
    try {
      const response = await fetch(`${appStore.apiUrl}/stats`)
      if (!response.ok) return

      const data = await response.json()
      liveStats.value = {
        totalProofs: data.total_proofs || data.verified_proofs || 0,
        verifiedToday: data.verified_today || data.verified_proofs || 0,
        pendingVerifications: data.pending_verifications || 0,
        proofsPerMinute: data.proofs_per_minute || data.rate || 0
      }
    } catch {
      // Silent fail for stats
    }
  }

  async function searchProofs(query) {
    searchQuery.value = query
    page.value = 1
    await fetchRecentProofs({ page: 1 })
  }

  async function filterByStatus(status) {
    statusFilter.value = status
    page.value = 1
    await fetchRecentProofs({ page: 1 })
  }

  async function setPage(newPage) {
    page.value = newPage
    await fetchRecentProofs({ page: newPage })
  }

  async function setPageSize(newSize) {
    pageSize.value = newSize
    page.value = 1
    await fetchRecentProofs({ page: 1, pageSize: newSize })
  }

  async function verifyProof(proof) {
    verifying.value = true
    error.value = null

    try {
      const response = await fetch(`${appStore.apiUrl}/proofs/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proof })
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const result = await response.json()
      lastVerification.value = {
        ...result,
        timestamp: new Date()
      }
      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      verifying.value = false
    }
  }

  async function broadcastProof(proof, options = {}) {
    broadcasting.value = true
    error.value = null

    try {
      const response = await fetch(`${appStore.apiUrl}/proofs/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          proof,
          recipients: options.recipients,
          commitments: options.commitments,
          metadata: options.metadata
        })
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const result = await response.json()
      lastBroadcast.value = {
        ...result,
        timestamp: new Date()
      }
      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      broadcasting.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    recentProofs,
    loading,
    error,
    page,
    pageSize,
    total,
    searchQuery,
    statusFilter,
    verifying,
    lastVerification,
    broadcasting,
    lastBroadcast,
    liveStats,
    totalPages,
    proofCount,
    verifiedCount,
    fetchRecentProofs,
    fetchLiveStats,
    searchProofs,
    filterByStatus,
    setPage,
    setPageSize,
    verifyProof,
    broadcastProof,
    clearError
  }
})
