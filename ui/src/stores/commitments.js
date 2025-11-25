import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAppStore } from './app'

export const useCommitmentsStore = defineStore('commitments', () => {
  const appStore = useAppStore()

  // Commitments
  const commitments = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Registration state
  const registering = ref(false)
  const lastRegistration = ref(null)

  // Lookup cache
  const lookupCache = ref(new Map())

  // Computed
  const activeCommitments = computed(() =>
    commitments.value.filter(c => {
      const now = Date.now() / 1000
      return c.expires_at > now
    })
  )

  const expiredCommitments = computed(() =>
    commitments.value.filter(c => {
      const now = Date.now() / 1000
      return c.expires_at <= now
    })
  )

  // Actions
  async function registerCommitment(sessionId, publicKey = null) {
    registering.value = true
    error.value = null

    try {
      const body = { session_id: sessionId }
      if (publicKey) body.public_key = publicKey

      const response = await fetch(`${appStore.apiUrl}/commitments/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || `HTTP ${response.status}`)
      }

      const commitment = await response.json()
      lastRegistration.value = {
        ...commitment,
        timestamp: new Date()
      }

      // Add to local list
      commitments.value.unshift({
        ...commitment,
        session_id: sessionId
      })

      return commitment
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      registering.value = false
    }
  }

  async function lookupCommitment(commitmentId) {
    // Check cache first
    if (lookupCache.value.has(commitmentId)) {
      const cached = lookupCache.value.get(commitmentId)
      if (Date.now() - cached.fetchedAt < 30000) { // 30s cache
        return cached.data
      }
    }

    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${appStore.apiUrl}/commitments/lookup/${commitmentId}`)

      if (!response.ok) {
        if (response.status === 404) {
          return null
        }
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      // Cache the result
      lookupCache.value.set(commitmentId, {
        data,
        fetchedAt: Date.now()
      })

      return data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function addCommitment(commitment) {
    const exists = commitments.value.find(c => c.commitment_id === commitment.commitment_id)
    if (!exists) {
      commitments.value.unshift(commitment)
    }
  }

  function removeExpired() {
    const now = Date.now() / 1000
    commitments.value = commitments.value.filter(c => c.expires_at > now)
  }

  function clearCache() {
    lookupCache.value.clear()
  }

  function clearError() {
    error.value = null
  }

  return {
    commitments,
    loading,
    error,
    registering,
    lastRegistration,
    activeCommitments,
    expiredCommitments,
    registerCommitment,
    lookupCommitment,
    addCommitment,
    removeExpired,
    clearCache,
    clearError
  }
})
