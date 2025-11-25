<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Proof Verification</h2>
        <p class="text-gray-500 dark:text-gray-400 mt-1">Verify and manage proofs</p>
      </div>

      <div class="flex items-center space-x-3">
        <button
          @click="refreshData"
          :disabled="proofsStore.loading"
          class="btn btn-secondary"
        >
          <ArrowPathIcon :class="['w-4 h-4 mr-2', proofsStore.loading ? 'animate-spin' : '']" />
          Refresh
        </button>
        <button @click="showVerifyModal = true" class="btn btn-primary">
          <ShieldCheckIcon class="w-4 h-4 mr-2" />
          Verify Proof
        </button>
      </div>
    </div>

    <!-- Stats Row with Live Counters -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <Card class="p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Total Proofs</p>
            <LiveCounter
              :value="proofsStore.liveStats.totalProofs"
              format="compact"
              class="text-2xl font-bold text-gray-900 dark:text-white"
              show-delta
            />
          </div>
          <div class="p-3 rounded-xl bg-blue-100 dark:bg-blue-900/30">
            <DocumentIcon class="w-6 h-6 text-blue-600 dark:text-blue-400" />
          </div>
        </div>
      </Card>

      <Card class="p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Verified Today</p>
            <LiveCounter
              :value="proofsStore.liveStats.verifiedToday"
              format="compact"
              class="text-2xl font-bold text-gray-900 dark:text-white"
              show-delta
            />
          </div>
          <div class="p-3 rounded-xl bg-green-100 dark:bg-green-900/30">
            <ShieldCheckIcon class="w-6 h-6 text-green-600 dark:text-green-400" />
          </div>
        </div>
      </Card>

      <Card class="p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Proofs/min</p>
            <LiveCounter
              :value="proofsStore.liveStats.proofsPerMinute"
              format="compact"
              class="text-2xl font-bold text-gray-900 dark:text-white"
            />
          </div>
          <div class="p-3 rounded-xl bg-purple-100 dark:bg-purple-900/30">
            <BoltIcon class="w-6 h-6 text-purple-600 dark:text-purple-400" />
          </div>
        </div>
      </Card>

      <Card class="p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-gray-500 dark:text-gray-400">Pending</p>
            <LiveCounter
              :value="proofsStore.liveStats.pendingVerifications"
              format="compact"
              class="text-2xl font-bold text-gray-900 dark:text-white"
            />
          </div>
          <div class="p-3 rounded-xl bg-yellow-100 dark:bg-yellow-900/30">
            <ClockIcon class="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
          </div>
        </div>
      </Card>
    </div>

    <!-- Proofs List -->
    <Card noPadding>
      <!-- Search & Filter Header -->
      <div class="p-4 border-b border-gray-200 dark:border-gray-700">
        <div class="flex flex-col sm:flex-row sm:items-center gap-3">
          <div class="flex-1">
            <SearchInput
              v-model="searchQuery"
              placeholder="Search by proof ID..."
              :loading="proofsStore.loading"
              instant
              @search="onSearch"
            />
          </div>

          <!-- Status Filter -->
          <div class="flex items-center space-x-2">
            <button
              v-for="filter in statusFilters"
              :key="filter.value"
              @click="onFilterStatus(filter.value)"
              :class="[
                'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                proofsStore.statusFilter === filter.value
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              ]"
            >
              {{ filter.label }}
            </button>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="proofsStore.loading && !proofsStore.recentProofs.length" class="p-6">
        <div v-for="i in 5" :key="i" class="animate-pulse flex items-center space-x-4 py-4 border-b border-gray-100 dark:border-gray-700 last:border-0">
          <div class="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700" />
          <div class="flex-1 space-y-2">
            <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
            <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
          </div>
        </div>
      </div>

      <!-- Empty -->
      <EmptyState
        v-else-if="!proofsStore.recentProofs.length"
        :title="searchQuery ? 'No proofs found' : 'No proofs yet'"
        :description="searchQuery ? 'Try a different search term.' : 'Proofs will appear here once verified.'"
        :icon="ShieldCheckIcon"
        class="py-12"
      >
        <template #action v-if="!searchQuery">
          <button @click="showVerifyModal = true" class="btn btn-primary">
            Verify Proof
          </button>
        </template>
      </EmptyState>

      <!-- List -->
      <div v-else>
        <div class="divide-y divide-gray-100 dark:divide-gray-700">
          <div
            v-for="proof in proofsStore.recentProofs"
            :key="proof.proof_id"
            class="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
          >
            <div class="flex items-center space-x-4 min-w-0">
              <div
                :class="[
                  'w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0',
                  proof.verified
                    ? 'bg-green-100 dark:bg-green-900/30'
                    : 'bg-gray-100 dark:bg-gray-700'
                ]"
              >
                <ShieldCheckIcon
                  v-if="proof.verified"
                  class="w-5 h-5 text-green-600 dark:text-green-400"
                />
                <DocumentIcon v-else class="w-5 h-5 text-gray-400" />
              </div>

              <div class="min-w-0">
                <p class="text-sm font-mono font-medium text-gray-900 dark:text-white truncate">
                  {{ truncateId(proof.proof_id) }}
                </p>
                <p class="text-xs text-gray-500 dark:text-gray-400">
                  {{ formatRelativeTime(proof.timestamp) }}
                </p>
              </div>
            </div>

            <div class="flex items-center space-x-3 flex-shrink-0">
              <StatusBadge
                :status="proof.verified ? 'success' : 'default'"
                :label="proof.verified ? 'Verified' : 'Unverified'"
              />

              <button
                @click="showDetails(proof)"
                class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              >
                <EyeIcon class="w-4 h-4 text-gray-400" />
              </button>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <Pagination
          :current-page="proofsStore.page"
          :page-size="proofsStore.pageSize"
          :total="proofsStore.total"
          @update:current-page="proofsStore.setPage"
          @update:page-size="proofsStore.setPageSize"
        />
      </div>
    </Card>

    <!-- Verify Proof Modal -->
    <Modal v-model="showVerifyModal" title="Verify Proof" size="lg">
      <form @submit.prevent="verifyProof" class="space-y-4">
        <div>
          <label class="label">Proof Data (JSON)</label>
          <textarea
            v-model="proofInput"
            rows="8"
            class="input font-mono text-sm"
            placeholder='{"R": "...", "public_key": "...", "signature": "...", "commitment": "..."}'
          />
        </div>

        <div v-if="verifyError" class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20">
          <p class="text-sm text-red-600 dark:text-red-400">{{ verifyError }}</p>
        </div>

        <div v-if="verifyResult" class="p-4 rounded-lg" :class="verifyResult.valid ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'">
          <div class="flex items-center space-x-2">
            <ShieldCheckIcon v-if="verifyResult.valid" class="w-5 h-5 text-green-600" />
            <ShieldExclamationIcon v-else class="w-5 h-5 text-red-600" />
            <span :class="verifyResult.valid ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'" class="font-medium">
              {{ verifyResult.valid ? 'Proof is valid!' : 'Proof is invalid' }}
            </span>
          </div>
          <p v-if="verifyResult.message" class="text-sm mt-2" :class="verifyResult.valid ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
            {{ verifyResult.message }}
          </p>
        </div>
      </form>

      <template #footer>
        <button @click="closeVerifyModal" class="btn btn-secondary">Close</button>
        <button
          @click="verifyProof"
          :disabled="!proofInput || proofsStore.verifying"
          class="btn btn-primary"
        >
          <span v-if="proofsStore.verifying">Verifying...</span>
          <span v-else>Verify</span>
        </button>
      </template>
    </Modal>

    <!-- Details Modal -->
    <Modal v-model="showDetailsModal" title="Proof Details" size="lg">
      <div v-if="selectedProof" class="space-y-4">
        <div>
          <label class="label">Proof ID</label>
          <code class="block text-sm font-mono text-gray-700 dark:text-gray-300 break-all p-2 bg-gray-50 dark:bg-gray-700 rounded">
            {{ selectedProof.proof_id }}
          </code>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">Status</label>
            <StatusBadge
              :status="selectedProof.verified ? 'success' : 'default'"
              :label="selectedProof.verified ? 'Verified' : 'Unverified'"
            />
          </div>
          <div>
            <label class="label">Timestamp</label>
            <p class="text-sm text-gray-700 dark:text-gray-300">
              {{ formatTimestamp(selectedProof.timestamp) }}
            </p>
          </div>
        </div>

        <div v-if="selectedProof.metadata">
          <label class="label">Metadata</label>
          <pre class="text-xs bg-gray-50 dark:bg-gray-700 p-3 rounded-lg overflow-auto max-h-48">{{ JSON.stringify(selectedProof.metadata, null, 2) }}</pre>
        </div>
      </div>

      <template #footer>
        <button @click="showDetailsModal = false" class="btn btn-secondary">Close</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useProofsStore } from '../stores/proofs'
import { useTime } from '../composables/useTime'
import Card from '../components/common/Card.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import EmptyState from '../components/common/EmptyState.vue'
import Modal from '../components/common/Modal.vue'
import SearchInput from '../components/common/SearchInput.vue'
import Pagination from '../components/common/Pagination.vue'
import LiveCounter from '../components/common/LiveCounter.vue'
import {
  ShieldCheckIcon,
  ShieldExclamationIcon,
  DocumentIcon,
  ArrowPathIcon,
  ClockIcon,
  EyeIcon,
  BoltIcon
} from '@heroicons/vue/24/outline'

const proofsStore = useProofsStore()
const { formatRelativeTime, formatTimestamp } = useTime()

const searchQuery = ref('')
const showVerifyModal = ref(false)
const showDetailsModal = ref(false)
const proofInput = ref('')
const verifyError = ref('')
const verifyResult = ref(null)
const selectedProof = ref(null)

let statsInterval = null

const statusFilters = [
  { value: 'all', label: 'All' },
  { value: 'verified', label: 'Verified' },
  { value: 'unverified', label: 'Unverified' }
]

function truncateId(id) {
  if (!id) return '-'
  if (id.length <= 20) return id
  return `${id.slice(0, 10)}...${id.slice(-10)}`
}

function onSearch(query) {
  proofsStore.searchProofs(query)
}

function onFilterStatus(status) {
  proofsStore.filterByStatus(status)
}

function refreshData() {
  proofsStore.fetchRecentProofs()
  proofsStore.fetchLiveStats()
}

async function verifyProof() {
  if (!proofInput.value) return

  verifyError.value = ''
  verifyResult.value = null

  try {
    const proof = JSON.parse(proofInput.value)
    const result = await proofsStore.verifyProof(proof)
    verifyResult.value = result
  } catch (err) {
    if (err instanceof SyntaxError) {
      verifyError.value = 'Invalid JSON format'
    } else {
      verifyError.value = err.message
    }
  }
}

function closeVerifyModal() {
  showVerifyModal.value = false
  proofInput.value = ''
  verifyError.value = ''
  verifyResult.value = null
}

function showDetails(proof) {
  selectedProof.value = proof
  showDetailsModal.value = true
}

onMounted(() => {
  proofsStore.fetchRecentProofs()
  proofsStore.fetchLiveStats()

  // Poll for live stats every 5 seconds
  statsInterval = setInterval(() => {
    proofsStore.fetchLiveStats()
  }, 5000)
})

onUnmounted(() => {
  if (statsInterval) {
    clearInterval(statsInterval)
  }
})
</script>
