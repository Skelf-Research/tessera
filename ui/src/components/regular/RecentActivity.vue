<template>
  <Card title="Recent Activity" subtitle="Latest proof verifications and events">
    <template #actions>
      <button
        @click="proofsStore.fetchRecentProofs()"
        :disabled="proofsStore.loading"
        class="btn btn-secondary text-sm"
      >
        <ArrowPathIcon
          :class="['w-4 h-4 mr-1', proofsStore.loading ? 'animate-spin' : '']"
        />
        Refresh
      </button>
    </template>

    <!-- Loading State -->
    <div v-if="proofsStore.loading && !proofsStore.recentProofs.length" class="space-y-3">
      <div v-for="i in 5" :key="i" class="animate-pulse flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-600" />
        <div class="flex-1 space-y-2">
          <div class="h-4 bg-gray-200 dark:bg-gray-600 rounded w-1/3" />
          <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded w-1/2" />
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <EmptyState
      v-else-if="!proofsStore.recentProofs.length"
      title="No recent activity"
      description="Proof verifications will appear here as they occur."
      :icon="ShieldCheckIcon"
    />

    <!-- Activity List -->
    <div v-else class="space-y-2">
      <div
        v-for="proof in proofsStore.recentProofs"
        :key="proof.proof_id"
        class="flex items-center space-x-3 p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div
          :class="[
            'w-10 h-10 rounded-full flex items-center justify-center',
            proof.verified ? 'bg-green-100 dark:bg-green-900/30' : 'bg-gray-100 dark:bg-gray-700'
          ]"
        >
          <ShieldCheckIcon
            v-if="proof.verified"
            class="w-5 h-5 text-green-600 dark:text-green-400"
          />
          <ShieldExclamationIcon
            v-else
            class="w-5 h-5 text-gray-400"
          />
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex items-center space-x-2">
            <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
              {{ truncateId(proof.proof_id) }}
            </p>
            <StatusBadge
              :status="proof.verified ? 'success' : 'default'"
              :label="proof.verified ? 'Verified' : 'Pending'"
              size="sm"
            />
          </div>
          <p class="text-xs text-gray-500 dark:text-gray-400">
            {{ formatRelativeTime(proof.timestamp) }}
          </p>
        </div>

        <button
          @click="showProofDetails(proof)"
          class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
        >
          <EyeIcon class="w-4 h-4 text-gray-400" />
        </button>
      </div>
    </div>

    <!-- View All Link -->
    <div v-if="proofsStore.recentProofs.length >= 10" class="mt-4 text-center">
      <router-link
        to="/proofs"
        class="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
      >
        View all proofs &rarr;
      </router-link>
    </div>
  </Card>

  <!-- Proof Details Modal -->
  <Modal v-model="showModal" title="Proof Details" size="md">
    <div v-if="selectedProof" class="space-y-4">
      <div>
        <label class="label">Proof ID</label>
        <code class="text-sm font-mono text-gray-700 dark:text-gray-300 break-all">
          {{ selectedProof.proof_id }}
        </code>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="label">Status</label>
          <StatusBadge
            :status="selectedProof.verified ? 'success' : 'default'"
            :label="selectedProof.verified ? 'Verified' : 'Pending'"
          />
        </div>
        <div>
          <label class="label">Timestamp</label>
          <p class="text-sm text-gray-700 dark:text-gray-300">
            {{ formatTimestamp(selectedProof.timestamp) }}
          </p>
        </div>
      </div>

      <div v-if="selectedProof.metadata && Object.keys(selectedProof.metadata).length">
        <label class="label">Metadata</label>
        <pre class="text-xs bg-gray-100 dark:bg-gray-700 p-3 rounded-lg overflow-x-auto">{{ JSON.stringify(selectedProof.metadata, null, 2) }}</pre>
      </div>
    </div>

    <template #footer>
      <button @click="showModal = false" class="btn btn-secondary">Close</button>
    </template>
  </Modal>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProofsStore } from '../../stores/proofs'
import { useTime } from '../../composables/useTime'
import Card from '../common/Card.vue'
import StatusBadge from '../common/StatusBadge.vue'
import EmptyState from '../common/EmptyState.vue'
import Modal from '../common/Modal.vue'
import {
  ShieldCheckIcon,
  ShieldExclamationIcon,
  ArrowPathIcon,
  EyeIcon
} from '@heroicons/vue/24/outline'

const proofsStore = useProofsStore()
const { formatRelativeTime, formatTimestamp } = useTime()

const showModal = ref(false)
const selectedProof = ref(null)

function truncateId(id) {
  if (!id) return '-'
  if (id.length <= 16) return id
  return `${id.slice(0, 8)}...${id.slice(-8)}`
}

function showProofDetails(proof) {
  selectedProof.value = proof
  showModal.value = true
}

onMounted(() => {
  proofsStore.fetchRecentProofs()
})
</script>
