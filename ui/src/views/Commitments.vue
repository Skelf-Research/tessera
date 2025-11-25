<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Commitments</h2>
        <p class="text-gray-500 dark:text-gray-400 mt-1">Manage proof commitments</p>
      </div>

      <div class="flex items-center space-x-3">
        <button @click="showRegisterModal = true" class="btn btn-primary">
          <PlusIcon class="w-4 h-4 mr-2" />
          Register Commitment
        </button>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatCard
        label="Active Commitments"
        :value="commitmentsStore.activeCommitments.length"
        :icon="KeyIcon"
        color="green"
      />
      <StatCard
        label="Expired"
        :value="commitmentsStore.expiredCommitments.length"
        :icon="ClockIcon"
        color="yellow"
      />
      <StatCard
        label="Total Registered"
        :value="commitmentsStore.commitments.length"
        :icon="DocumentIcon"
        color="blue"
      />
    </div>

    <!-- Lookup Card -->
    <Card title="Lookup Commitment" subtitle="Find commitment by ID">
      <form @submit.prevent="lookupCommitment" class="flex space-x-3">
        <input
          v-model="lookupId"
          type="text"
          class="input flex-1"
          placeholder="Enter commitment ID..."
        />
        <button
          type="submit"
          :disabled="!lookupId || commitmentsStore.loading"
          class="btn btn-primary"
        >
          <MagnifyingGlassIcon class="w-4 h-4 mr-2" />
          Lookup
        </button>
      </form>

      <!-- Lookup Result -->
      <div v-if="lookupResult" class="mt-4 p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">Session ID</label>
            <p class="text-sm font-mono text-gray-700 dark:text-gray-300">
              {{ lookupResult.session_id }}
            </p>
          </div>
          <div>
            <label class="label">Status</label>
            <StatusBadge
              :status="lookupResult.time_remaining > 0 ? 'active' : 'inactive'"
              :label="lookupResult.time_remaining > 0 ? 'Active' : 'Expired'"
            />
          </div>
          <div>
            <label class="label">Created At</label>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              {{ formatTimestamp(lookupResult.created_at) }}
            </p>
          </div>
          <div>
            <label class="label">Time Remaining</label>
            <p class="text-sm text-gray-600 dark:text-gray-400">
              {{ formatTimeRemaining(lookupResult.expires_at) }}
            </p>
          </div>
        </div>
      </div>

      <div v-if="lookupNotFound" class="mt-4 p-4 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 text-sm text-yellow-700 dark:text-yellow-300">
        Commitment not found
      </div>
    </Card>

    <!-- Commitments List -->
    <Card title="Registered Commitments" noPadding>
      <EmptyState
        v-if="!commitmentsStore.commitments.length"
        title="No commitments"
        description="Register a commitment to get started."
        :icon="KeyIcon"
        class="py-12"
      >
        <template #action>
          <button @click="showRegisterModal = true" class="btn btn-primary">
            Register Commitment
          </button>
        </template>
      </EmptyState>

      <div v-else class="divide-y divide-gray-100 dark:divide-gray-700">
        <div
          v-for="commitment in sortedCommitments"
          :key="commitment.commitment_id"
          class="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
        >
          <div class="flex items-center space-x-4">
            <div
              :class="[
                'w-10 h-10 rounded-full flex items-center justify-center',
                isActive(commitment)
                  ? 'bg-green-100 dark:bg-green-900/30'
                  : 'bg-gray-100 dark:bg-gray-700'
              ]"
            >
              <KeyIcon
                :class="[
                  'w-5 h-5',
                  isActive(commitment)
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-gray-400'
                ]"
              />
            </div>

            <div>
              <p class="text-sm font-mono font-medium text-gray-900 dark:text-white">
                {{ truncateId(commitment.commitment_id) }}
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                Session: {{ commitment.session_id }}
              </p>
            </div>
          </div>

          <div class="flex items-center space-x-4">
            <div class="text-right">
              <StatusBadge
                :status="isActive(commitment) ? 'active' : 'inactive'"
                :label="isActive(commitment) ? 'Active' : 'Expired'"
                size="sm"
              />
              <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {{ formatTimeRemaining(commitment.expires_at) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>

    <!-- Register Modal -->
    <Modal v-model="showRegisterModal" title="Register Commitment" size="md">
      <form @submit.prevent="registerCommitment" class="space-y-4">
        <div>
          <label class="label">Session ID</label>
          <input
            v-model="newSessionId"
            type="text"
            class="input"
            placeholder="Enter unique session ID"
            required
          />
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            A unique identifier for this session/call
          </p>
        </div>

        <div>
          <label class="label">Public Key (optional)</label>
          <input
            v-model="newPublicKey"
            type="text"
            class="input font-mono text-sm"
            placeholder="Optional: hex-encoded public key"
          />
        </div>

        <div v-if="registerError" class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-sm text-red-600 dark:text-red-400">
          {{ registerError }}
        </div>

        <div v-if="registerSuccess" class="p-3 rounded-lg bg-green-50 dark:bg-green-900/20">
          <p class="text-sm text-green-700 dark:text-green-300 font-medium">Commitment registered!</p>
          <code class="text-xs text-green-600 dark:text-green-400 font-mono block mt-1 break-all">
            {{ registerSuccess.commitment_id }}
          </code>
        </div>
      </form>

      <template #footer>
        <button @click="closeRegisterModal" class="btn btn-secondary">
          {{ registerSuccess ? 'Close' : 'Cancel' }}
        </button>
        <button
          v-if="!registerSuccess"
          @click="registerCommitment"
          :disabled="!newSessionId || commitmentsStore.registering"
          class="btn btn-primary"
        >
          <span v-if="commitmentsStore.registering">Registering...</span>
          <span v-else>Register</span>
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useCommitmentsStore } from '../stores/commitments'
import { useTime } from '../composables/useTime'
import Card from '../components/common/Card.vue'
import StatCard from '../components/common/StatCard.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import Modal from '../components/common/Modal.vue'
import {
  KeyIcon,
  ClockIcon,
  DocumentIcon,
  PlusIcon,
  MagnifyingGlassIcon
} from '@heroicons/vue/24/outline'

const commitmentsStore = useCommitmentsStore()
const { formatTimestamp, formatTimeRemaining } = useTime()

// Lookup
const lookupId = ref('')
const lookupResult = ref(null)
const lookupNotFound = ref(false)

// Register
const showRegisterModal = ref(false)
const newSessionId = ref('')
const newPublicKey = ref('')
const registerError = ref('')
const registerSuccess = ref(null)

const sortedCommitments = computed(() => {
  return [...commitmentsStore.commitments].sort((a, b) => {
    // Active first, then by created_at
    const aActive = isActive(a)
    const bActive = isActive(b)
    if (aActive !== bActive) return bActive ? 1 : -1
    return (b.created_at || 0) - (a.created_at || 0)
  })
})

function isActive(commitment) {
  const now = Date.now() / 1000
  return commitment.expires_at > now
}

function truncateId(id) {
  if (!id) return '-'
  if (id.length <= 24) return id
  return `${id.slice(0, 12)}...${id.slice(-12)}`
}

async function lookupCommitment() {
  if (!lookupId.value) return

  lookupResult.value = null
  lookupNotFound.value = false

  try {
    const result = await commitmentsStore.lookupCommitment(lookupId.value)
    if (result) {
      lookupResult.value = result
    } else {
      lookupNotFound.value = true
    }
  } catch (err) {
    lookupNotFound.value = true
  }
}

async function registerCommitment() {
  if (!newSessionId.value) return

  registerError.value = ''
  registerSuccess.value = null

  try {
    const result = await commitmentsStore.registerCommitment(
      newSessionId.value,
      newPublicKey.value || null
    )
    registerSuccess.value = result
  } catch (err) {
    registerError.value = err.message
  }
}

function closeRegisterModal() {
  showRegisterModal.value = false
  newSessionId.value = ''
  newPublicKey.value = ''
  registerError.value = ''
  registerSuccess.value = null
}
</script>
