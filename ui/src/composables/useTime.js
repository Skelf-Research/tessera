import { ref, computed, onUnmounted } from 'vue'

export function useTime() {
  const now = ref(Date.now())

  // Update time every second
  const interval = setInterval(() => {
    now.value = Date.now()
  }, 1000)

  onUnmounted(() => {
    clearInterval(interval)
  })

  function formatTimestamp(timestamp) {
    if (!timestamp) return '-'

    const date = timestamp instanceof Date ? timestamp : new Date(
      typeof timestamp === 'number' && timestamp < 1e12
        ? timestamp * 1000 // Unix seconds
        : timestamp // Unix milliseconds or ISO string
    )

    return date.toLocaleString()
  }

  function formatRelativeTime(timestamp) {
    if (!timestamp) return '-'

    const ts = typeof timestamp === 'number' && timestamp < 1e12
      ? timestamp * 1000
      : timestamp instanceof Date
        ? timestamp.getTime()
        : new Date(timestamp).getTime()

    const diff = now.value - ts
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (seconds < 5) return 'just now'
    if (seconds < 60) return `${seconds}s ago`
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`

    return formatTimestamp(timestamp)
  }

  function formatDuration(seconds) {
    if (!seconds || seconds < 0) return '-'

    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    const s = Math.floor(seconds % 60)

    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m ${s}s`
    return `${s}s`
  }

  function formatTimeRemaining(expiresAt) {
    if (!expiresAt) return '-'

    const ts = typeof expiresAt === 'number' && expiresAt < 1e12
      ? expiresAt * 1000
      : new Date(expiresAt).getTime()

    const remaining = ts - now.value
    if (remaining <= 0) return 'Expired'

    return formatDuration(Math.floor(remaining / 1000))
  }

  return {
    now: computed(() => now.value),
    formatTimestamp,
    formatRelativeTime,
    formatDuration,
    formatTimeRemaining
  }
}
