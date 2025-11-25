import { ref } from 'vue'
import { useAppStore } from '../stores/app'

export function useApi() {
  const appStore = useAppStore()
  const loading = ref(false)
  const error = ref(null)

  function getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders
    }

    if (appStore.apiKey) {
      headers['Authorization'] = `Bearer ${appStore.apiKey}`
    }

    return headers
  }

  async function request(endpoint, options = {}) {
    loading.value = true
    error.value = null

    const url = `${appStore.apiUrl}${endpoint}`
    const config = {
      headers: getHeaders(options.headers),
      ...options
    }

    if (options.body && typeof options.body === 'object') {
      config.body = JSON.stringify(options.body)
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`
        try {
          const errorData = await response.json()
          errorMessage = errorData.error || errorData.message || errorMessage
        } catch {
          // Response might not be JSON
        }
        throw new Error(errorMessage)
      }

      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      }

      return await response.text()
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString()
    const url = queryString ? `${endpoint}?${queryString}` : endpoint
    return request(url, { method: 'GET' })
  }

  async function post(endpoint, body = {}) {
    return request(endpoint, { method: 'POST', body })
  }

  async function put(endpoint, body = {}) {
    return request(endpoint, { method: 'PUT', body })
  }

  async function del(endpoint) {
    return request(endpoint, { method: 'DELETE' })
  }

  function clearError() {
    error.value = null
  }

  return {
    loading,
    error,
    request,
    get,
    post,
    put,
    del,
    clearError
  }
}
