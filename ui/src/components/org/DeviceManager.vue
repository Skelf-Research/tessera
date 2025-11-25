<template>
  <Card>
    <template #header>
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ customer ? `${customer.customer_id}'s Devices` : 'Devices' }}
          </h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            {{ devices.length }} registered
          </p>
        </div>
        <button
          v-if="customer"
          @click="showAddModal = true"
          class="btn btn-primary text-sm"
        >
          <PlusIcon class="w-4 h-4 mr-1" />
          Add Device
        </button>
      </div>
    </template>

    <!-- No Customer Selected -->
    <EmptyState
      v-if="!customer"
      title="Select a customer"
      description="Choose a customer from the list to manage their devices."
      :icon="DevicePhoneMobileIcon"
    />

    <!-- Loading -->
    <div v-else-if="loading" class="space-y-3">
      <div v-for="i in 2" :key="i" class="animate-pulse flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-600" />
        <div class="flex-1 space-y-2">
          <div class="h-4 bg-gray-200 dark:bg-gray-600 rounded w-1/3" />
          <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded w-1/2" />
        </div>
      </div>
    </div>

    <!-- Empty -->
    <EmptyState
      v-else-if="!devices.length"
      title="No devices"
      description="Register a device for this customer."
      :icon="DevicePhoneMobileIcon"
    >
      <template #action>
        <button @click="showAddModal = true" class="btn btn-primary">
          <PlusIcon class="w-4 h-4 mr-2" />
          Add Device
        </button>
      </template>
    </EmptyState>

    <!-- Device List -->
    <div v-else class="space-y-3">
      <div
        v-for="device in devices"
        :key="device.device_id"
        class="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/50"
      >
        <div class="flex items-center space-x-3">
          <div
            :class="[
              'w-10 h-10 rounded-lg flex items-center justify-center',
              device.active
                ? 'bg-green-100 dark:bg-green-900/30'
                : 'bg-gray-100 dark:bg-gray-700'
            ]"
          >
            <DevicePhoneMobileIcon
              :class="[
                'w-5 h-5',
                device.active
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-gray-400'
              ]"
            />
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900 dark:text-white">
              {{ device.device_name || device.device_id }}
            </p>
            <p class="text-xs text-gray-500 dark:text-gray-400">
              Registered {{ formatRelativeTime(device.registered_at) }}
            </p>
          </div>
        </div>

        <div class="flex items-center space-x-2">
          <StatusBadge
            :status="device.active ? 'active' : 'inactive'"
            :label="device.active ? 'Active' : 'Inactive'"
            size="sm"
          />
          <button
            @click="confirmRemove(device)"
            class="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
          >
            <TrashIcon class="w-4 h-4 text-red-500" />
          </button>
        </div>
      </div>
    </div>

    <!-- Add Device Modal -->
    <Modal v-model="showAddModal" title="Add Device" size="md">
      <form @submit.prevent="addDevice" class="space-y-4">
        <div>
          <label class="label">Device ID</label>
          <input
            v-model="newDevice.device_id"
            type="text"
            class="input"
            placeholder="Unique device identifier"
            required
          />
        </div>

        <div>
          <label class="label">Device Name (optional)</label>
          <input
            v-model="newDevice.device_name"
            type="text"
            class="input"
            placeholder="e.g., John's iPhone"
          />
        </div>

        <div>
          <label class="label">Commitment</label>
          <input
            v-model="newDevice.commitment"
            type="text"
            class="input font-mono text-sm"
            placeholder="Device commitment (base64)"
            required
          />
        </div>

        <div>
          <label class="label">Public Key</label>
          <input
            v-model="newDevice.public_key"
            type="text"
            class="input font-mono text-sm"
            placeholder="Device public key (base64)"
            required
          />
        </div>

        <div v-if="addError" class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-sm text-red-600 dark:text-red-400">
          {{ addError }}
        </div>
      </form>

      <template #footer>
        <button @click="closeAddModal" class="btn btn-secondary">Cancel</button>
        <button
          @click="addDevice"
          :disabled="!isValidDevice || adding"
          class="btn btn-primary"
        >
          <span v-if="adding">Adding...</span>
          <span v-else>Add Device</span>
        </button>
      </template>
    </Modal>

    <!-- Remove Confirmation Modal -->
    <Modal v-model="showRemoveModal" title="Remove Device" size="sm">
      <p class="text-gray-600 dark:text-gray-400">
        Are you sure you want to remove <strong class="text-gray-900 dark:text-white">{{ deviceToRemove?.device_name || deviceToRemove?.device_id }}</strong>?
      </p>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
        This action cannot be undone.
      </p>

      <template #footer>
        <button @click="showRemoveModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="removeDevice" :disabled="removing" class="btn btn-danger">
          <span v-if="removing">Removing...</span>
          <span v-else>Remove</span>
        </button>
      </template>
    </Modal>
  </Card>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useCustomersStore } from '../../stores/customers'
import { useTime } from '../../composables/useTime'
import Card from '../common/Card.vue'
import StatusBadge from '../common/StatusBadge.vue'
import EmptyState from '../common/EmptyState.vue'
import Modal from '../common/Modal.vue'
import {
  DevicePhoneMobileIcon,
  PlusIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  customer: Object,
  devices: { type: Array, default: () => [] },
  loading: Boolean
})

const emit = defineEmits(['refresh'])

const customersStore = useCustomersStore()
const { formatRelativeTime } = useTime()

// Add device
const showAddModal = ref(false)
const adding = ref(false)
const addError = ref('')
const newDevice = ref({
  device_id: '',
  device_name: '',
  commitment: '',
  public_key: ''
})

const isValidDevice = computed(() =>
  newDevice.value.device_id &&
  newDevice.value.commitment &&
  newDevice.value.public_key
)

// Remove device
const showRemoveModal = ref(false)
const removing = ref(false)
const deviceToRemove = ref(null)

async function addDevice() {
  if (!props.customer || !isValidDevice.value) return

  adding.value = true
  addError.value = ''

  try {
    await customersStore.registerDevice(props.customer.customer_id, newDevice.value)
    closeAddModal()
    emit('refresh')
  } catch (err) {
    addError.value = err.message
  } finally {
    adding.value = false
  }
}

function closeAddModal() {
  showAddModal.value = false
  newDevice.value = {
    device_id: '',
    device_name: '',
    commitment: '',
    public_key: ''
  }
  addError.value = ''
}

function confirmRemove(device) {
  deviceToRemove.value = device
  showRemoveModal.value = true
}

async function removeDevice() {
  if (!props.customer || !deviceToRemove.value) return

  removing.value = true

  try {
    await customersStore.removeDevice(
      props.customer.customer_id,
      deviceToRemove.value.device_id
    )
    showRemoveModal.value = false
    deviceToRemove.value = null
    emit('refresh')
  } catch (err) {
    console.error('Failed to remove device:', err)
  } finally {
    removing.value = false
  }
}
</script>
