import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAppStore } from './app'

export const useCustomersStore = defineStore('customers', () => {
  const appStore = useAppStore()

  // Paginated customers list (only current page in memory)
  const customers = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Pagination state
  const page = ref(1)
  const pageSize = ref(50)
  const total = ref(0)
  const searchQuery = ref('')

  // Selected customer details
  const selectedCustomer = ref(null)
  const selectedDevices = ref([])
  const selectedCommitments = ref([])
  const detailsLoading = ref(false)

  // Computed
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)
  const hasCustomers = computed(() => total.value > 0)

  // API helper
  function getHeaders() {
    const headers = { 'Content-Type': 'application/json' }
    if (appStore.apiKey) {
      headers['Authorization'] = `Bearer ${appStore.apiKey}`
    }
    return headers
  }

  // Actions
  async function fetchCustomers(options = {}) {
    loading.value = true
    error.value = null

    const params = new URLSearchParams({
      page: options.page || page.value,
      page_size: options.pageSize || pageSize.value,
      ...(searchQuery.value && { search: searchQuery.value })
    })

    try {
      const response = await fetch(`${appStore.apiUrl}/customers?${params}`, {
        headers: getHeaders()
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      customers.value = data.customers || data.items || []
      total.value = data.total || data.count || customers.value.length
      page.value = data.page || options.page || page.value
    } catch (err) {
      error.value = err.message
      // Keep existing data on error
    } finally {
      loading.value = false
    }
  }

  async function searchCustomers(query) {
    searchQuery.value = query
    page.value = 1
    await fetchCustomers({ page: 1 })
  }

  async function setPage(newPage) {
    page.value = newPage
    await fetchCustomers({ page: newPage })
  }

  async function setPageSize(newSize) {
    pageSize.value = newSize
    page.value = 1
    await fetchCustomers({ page: 1, pageSize: newSize })
  }

  async function registerCustomer(customerId, metadata = {}) {
    loading.value = true
    error.value = null

    try {
      const response = await fetch(`${appStore.apiUrl}/customers/register`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ customer_id: customerId, metadata })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || `HTTP ${response.status}`)
      }

      const customer = await response.json()
      // Refresh list to include new customer
      await fetchCustomers()
      return customer
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchCustomerDevices(customerId, options = {}) {
    detailsLoading.value = true

    const params = new URLSearchParams({
      page: options.page || 1,
      page_size: options.pageSize || 50
    })

    try {
      const response = await fetch(
        `${appStore.apiUrl}/customers/${customerId}/devices?${params}`,
        { headers: getHeaders() }
      )

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      selectedDevices.value = data.devices || data.items || []
      return {
        devices: selectedDevices.value,
        total: data.total || selectedDevices.value.length
      }
    } catch (err) {
      error.value = err.message
      selectedDevices.value = []
      throw err
    } finally {
      detailsLoading.value = false
    }
  }

  async function registerDevice(customerId, deviceData) {
    detailsLoading.value = true
    error.value = null

    try {
      const response = await fetch(`${appStore.apiUrl}/customers/${customerId}/devices`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(deviceData)
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || `HTTP ${response.status}`)
      }

      const device = await response.json()
      // Refresh device list
      await fetchCustomerDevices(customerId)
      return device
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      detailsLoading.value = false
    }
  }

  async function removeDevice(customerId, deviceId) {
    detailsLoading.value = true
    error.value = null

    try {
      const response = await fetch(
        `${appStore.apiUrl}/customers/${customerId}/devices/${deviceId}`,
        {
          method: 'DELETE',
          headers: getHeaders()
        }
      )

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || `HTTP ${response.status}`)
      }

      selectedDevices.value = selectedDevices.value.filter(d => d.device_id !== deviceId)
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      detailsLoading.value = false
    }
  }

  async function fetchCustomerCommitments(customerId, options = {}) {
    detailsLoading.value = true

    const params = new URLSearchParams({
      page: options.page || 1,
      page_size: options.pageSize || 50
    })

    try {
      const url = appStore.isOrgMode && appStore.orgId
        ? `${appStore.apiUrl}/organizations/${appStore.orgId}/customers/${customerId}/commitments?${params}`
        : `${appStore.apiUrl}/customers/${customerId}/commitments?${params}`

      const response = await fetch(url, { headers: getHeaders() })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const data = await response.json()
      selectedCommitments.value = data.commitments || data.items || []
      return {
        commitments: selectedCommitments.value,
        total: data.total || selectedCommitments.value.length
      }
    } catch (err) {
      error.value = err.message
      selectedCommitments.value = []
      throw err
    } finally {
      detailsLoading.value = false
    }
  }

  function selectCustomer(customer) {
    selectedCustomer.value = customer
    if (customer) {
      fetchCustomerDevices(customer.customer_id)
      fetchCustomerCommitments(customer.customer_id)
    } else {
      selectedDevices.value = []
      selectedCommitments.value = []
    }
  }

  function clearSelection() {
    selectedCustomer.value = null
    selectedDevices.value = []
    selectedCommitments.value = []
  }

  function clearError() {
    error.value = null
  }

  return {
    customers,
    loading,
    error,
    page,
    pageSize,
    total,
    searchQuery,
    selectedCustomer,
    selectedDevices,
    selectedCommitments,
    detailsLoading,
    totalPages,
    hasCustomers,
    fetchCustomers,
    searchCustomers,
    setPage,
    setPageSize,
    registerCustomer,
    fetchCustomerDevices,
    registerDevice,
    removeDevice,
    fetchCustomerCommitments,
    selectCustomer,
    clearSelection,
    clearError
  }
})
