import { ref, onUnmounted } from 'vue'
import { useAppStore } from '../stores/app'

export function useWebSocket(subscriberId) {
  const appStore = useAppStore()

  const connected = ref(false)
  const error = ref(null)
  const lastMessage = ref(null)
  const messageQueue = ref([])

  let ws = null
  let reconnectTimeout = null
  let reconnectAttempts = 0
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  const listeners = new Map()

  function getWsUrl() {
    const baseUrl = appStore.apiUrl.replace(/^http/, 'ws')
    return `${baseUrl}/ws/${subscriberId}`
  }

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      return
    }

    try {
      ws = new WebSocket(getWsUrl())

      ws.onopen = () => {
        connected.value = true
        error.value = null
        reconnectAttempts = 0
        emit('connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastMessage.value = data
          messageQueue.value.push(data)

          // Keep only last 100 messages
          if (messageQueue.value.length > 100) {
            messageQueue.value.shift()
          }

          emit('message', data)

          // Handle specific message types
          if (data.type) {
            emit(data.type, data)
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (event) => {
        error.value = 'WebSocket error'
        emit('error', event)
      }

      ws.onclose = (event) => {
        connected.value = false
        emit('disconnected', event)

        // Attempt to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++
          reconnectTimeout = setTimeout(() => {
            connect()
          }, reconnectDelay * reconnectAttempts)
        }
      }
    } catch (err) {
      error.value = err.message
    }
  }

  function disconnect() {
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }

    if (ws) {
      ws.close()
      ws = null
    }

    connected.value = false
  }

  function send(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(typeof data === 'string' ? data : JSON.stringify(data))
      return true
    }
    return false
  }

  function subscribe(bucket, bloomFilter, options = {}) {
    return send({
      type: 'subscribe',
      bucket,
      bloom_filter: bloomFilter,
      org_hints: options.orgHints,
      time_window: options.timeWindow
    })
  }

  function ping() {
    return send({ type: 'ping' })
  }

  function on(event, callback) {
    if (!listeners.has(event)) {
      listeners.set(event, new Set())
    }
    listeners.get(event).add(callback)
  }

  function off(event, callback) {
    if (listeners.has(event)) {
      if (callback) {
        listeners.get(event).delete(callback)
      } else {
        listeners.delete(event)
      }
    }
  }

  function emit(event, data) {
    if (listeners.has(event)) {
      listeners.get(event).forEach(callback => {
        try {
          callback(data)
        } catch (err) {
          console.error(`WebSocket listener error for ${event}:`, err)
        }
      })
    }
  }

  function clearMessages() {
    messageQueue.value = []
    lastMessage.value = null
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
    listeners.clear()
  })

  return {
    connected,
    error,
    lastMessage,
    messageQueue,
    connect,
    disconnect,
    send,
    subscribe,
    ping,
    on,
    off,
    clearMessages
  }
}
