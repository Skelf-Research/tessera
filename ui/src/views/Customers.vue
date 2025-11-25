<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Customer Management</h2>
        <p class="text-gray-500 dark:text-gray-400 mt-1">Manage customers, devices, and commitments</p>
      </div>

      <button @click="showRegisterModal = true" class="btn btn-primary">
        <UserPlusIcon class="w-4 h-4 mr-2" />
        Register Customer
      </button>
    </div>

    <!-- Stats with Live Counters -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card class="p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Total Customers</p>
            <LiveCounter
              :value="customersStore.total"
              format="compact"
              class="text-2xl font-bold text-gray-900 dark:text-white"
              show-delta
            />
          </div>
          <div class="p-3 rounded-xl bg-purple-100 dark:bg-purple-900/30">
            <UsersIcon class="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
        </div>
      </Card>

      <Card class="p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Selected Devices</p>
            <LiveCounter
              :value="customersStore.selectedDevices.length"
              format="compact"
              class="text-2xl font-bold text-gray-900 dark:text-white"
            />
          </div>
          <div class="p-3 rounded-xl bg-blue-100 dark:bg-blue-900/30">
            <DevicePhoneMobileIcon class="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </Card>

      <Card class="p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Active Commitments</p>
            <LiveCounter
              :value="activeCommitmentCount"
              format="compact"
              class="text-2xl font-bold text-gray-900 dark:text-white"
            />
          </div>
          <div class="p-3 rounded-xl bg-green-100 dark:bg-green-900/30">
            <KeyIcon class="w-6 h-6 text-green-600 dark:text-green-400" />
          </div>
        </div>
      </Card>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Customer List -->
      <div class="lg:col-span-1">
        <CustomerList
          :selected-id="selectedCustomerId"
          @select="handleSelectCustomer"
          @register="showRegisterModal = true"
        />
      </div>

      <!-- Customer Details -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Customer Info Card -->
        <Card v-if="customersStore.selectedCustomer">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-3">
                <div class="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                  <UserIcon class="w-6 h-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 class="text-lg font-semibold text-gray-900 dark:text-white truncate max-w-xs">
                    {{ customersStore.selectedCustomer.customer_id }}
                  </h3>
                  <p class="text-sm text-gray-500 dark:text-gray-400">
                    Registered {{ formatRelativeTime(customersStore.selectedCustomer.created_at) }}
                  </p>
                </div>
              </div>
              <StatusBadge status="active" label="Active" dot />
            </div>
          </template>

          <!-- Quick Stats -->
          <div class="grid grid-cols-2 gap-4">
            <div class="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
              <div class="flex items-center space-x-2">
                <DevicePhoneMobileIcon class="w-5 h-5 text-gray-400" />
                <span class="text-sm text-gray-600 dark:text-gray-400">Devices</span>
              </div>
              <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {{ customersStore.selectedDevices.length }}
              </p>
            </div>
            <div class="p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50">
              <div class="flex items-center space-x-2">
                <KeyIcon class="w-5 h-5 text-gray-400" />
                <span class="text-sm text-gray-600 dark:text-gray-400">Commitments</span>
              </div>
              <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
                {{ customersStore.selectedCommitments.length }}
              </p>
            </div>
          </div>
        </Card>

        <!-- No Customer Selected -->
        <Card v-else>
          <EmptyState
            title="Select a customer"
            description="Choose a customer from the list to view their details, devices, and commitments."
            :icon="UserIcon"
          />
        </Card>

        <!-- Device Manager -->
        <DeviceManager
          :customer="customersStore.selectedCustomer"
          :devices="customersStore.selectedDevices"
          :loading="customersStore.detailsLoading"
          @refresh="refreshCustomerData"
        />

        <!-- Commitment Tracker -->
        <CommitmentTracker
          :customer="customersStore.selectedCustomer"
          :commitments="customersStore.selectedCommitments"
          :loading="customersStore.detailsLoading"
        />
      </div>
    </div>

    <!-- Register Customer Modal -->
    <Modal v-model="showRegisterModal" title="Register Customer" size="md">
      <form @submit.prevent="registerCustomer" class="space-y-4">
        <div>
          <label class="label">Customer ID</label>
          <input
            v-model="newCustomerId"
            type="text"
            class="input"
            placeholder="Enter unique customer ID"
            required
          />
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            A unique identifier for this customer (e.g., phone number, email, UUID)
          </p>
        </div>

        <div v-if="registerError" class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-sm text-red-600 dark:text-red-400">
          {{ registerError }}
        </div>

        <div v-if="registerSuccess" class="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 text-sm text-green-600 dark:text-green-400">
          Customer registered successfully!
        </div>
      </form>

      <template #footer>
        <button @click="closeRegisterModal" class="btn btn-secondary">
          {{ registerSuccess ? 'Close' : 'Cancel' }}
        </button>
        <button
          v-if="!registerSuccess"
          @click="registerCustomer"
          :disabled="!newCustomerId || registering"
          class="btn btn-primary"
        >
          <span v-if="registering">Registering...</span>
          <span v-else>Register</span>
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useCustomersStore } from '../stores/customers'
import { useTime } from '../composables/useTime'
import Card from '../components/common/Card.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import Modal from '../components/common/Modal.vue'
import LiveCounter from '../components/common/LiveCounter.vue'
import CustomerList from '../components/org/CustomerList.vue'
import DeviceManager from '../components/org/DeviceManager.vue'
import CommitmentTracker from '../components/org/CommitmentTracker.vue'
import {
  UsersIcon,
  UserIcon,
  UserPlusIcon,
  DevicePhoneMobileIcon,
  KeyIcon
} from '@heroicons/vue/24/outline'

const customersStore = useCustomersStore()
const { formatRelativeTime } = useTime()

const selectedCustomerId = computed(() =>
  customersStore.selectedCustomer?.customer_id
)

const activeCommitmentCount = computed(() => {
  const now = Date.now() / 1000
  return customersStore.selectedCommitments.filter(c => c.expires_at > now).length
})

// Registration
const showRegisterModal = ref(false)
const newCustomerId = ref('')
const registering = ref(false)
const registerError = ref('')
const registerSuccess = ref(false)

function handleSelectCustomer(customer) {
  // Selection handled by CustomerList via store
}

async function registerCustomer() {
  if (!newCustomerId.value) return

  registering.value = true
  registerError.value = ''
  registerSuccess.value = false

  try {
    await customersStore.registerCustomer(newCustomerId.value)
    registerSuccess.value = true
    newCustomerId.value = ''

    // Auto close after success
    setTimeout(() => {
      closeRegisterModal()
    }, 1500)
  } catch (err) {
    registerError.value = err.message
  } finally {
    registering.value = false
  }
}

function closeRegisterModal() {
  showRegisterModal.value = false
  newCustomerId.value = ''
  registerError.value = ''
  registerSuccess.value = false
}

function refreshCustomerData() {
  if (customersStore.selectedCustomer) {
    customersStore.fetchCustomerDevices(customersStore.selectedCustomer.customer_id)
    customersStore.fetchCustomerCommitments(customersStore.selectedCustomer.customer_id)
  }
}

onMounted(() => {
  // Initial fetch is handled by CustomerList component
})
</script>
