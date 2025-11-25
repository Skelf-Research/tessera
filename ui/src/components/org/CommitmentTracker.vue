<template>
  <Card>
    <template #header>
      <div>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
          {{ customer ? `${customer.customer_id}'s Commitments` : 'Commitments' }}
        </h3>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          {{ activeCount }} active, {{ expiredCount }} expired
        </p>
      </div>
    </template>

    <!-- No Customer Selected -->
    <EmptyState
      v-if="!customer"
      title="Select a customer"
      description="Choose a customer from the list to view their commitments."
      :icon="KeyIcon"
    />

    <!-- Loading -->
    <div v-else-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="animate-pulse flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
        <div class="w-8 h-8 rounded bg-gray-200 dark:bg-gray-600" />
        <div class="flex-1 space-y-2">
          <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded w-2/3" />
          <div class="h-3 bg-gray-200 dark:bg-gray-600 rounded w-1/3" />
        </div>
      </div>
    </div>

    <!-- Empty -->
    <EmptyState
      v-else-if="!commitments.length"
      title="No commitments"
      description="This customer has no registered commitments."
      :icon="KeyIcon"
    />

    <!-- Commitments List -->
    <div v-else class="space-y-3">
      <div
        v-for="commitment in sortedCommitments"
        :key="commitment.commitment_id"
        class="p-3 rounded-lg border transition-colors"
        :class="isActive(commitment) ? 'border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/10' : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50'"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-2">
              <KeyIcon :class="['w-4 h-4', isActive(commitment) ? 'text-green-600 dark:text-green-400' : 'text-gray-400']" />
              <code class="text-xs font-mono text-gray-600 dark:text-gray-400 truncate">
                {{ truncateId(commitment.commitment_id) }}
              </code>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Session: {{ commitment.session_id || '-' }}
            </p>
          </div>

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

        <!-- Expanded details -->
        <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600 grid grid-cols-2 gap-2 text-xs">
          <div>
            <span class="text-gray-500 dark:text-gray-400">Created:</span>
            <span class="ml-1 text-gray-700 dark:text-gray-300">{{ formatRelativeTime(commitment.created_at) }}</span>
          </div>
          <div>
            <span class="text-gray-500 dark:text-gray-400">Expires:</span>
            <span class="ml-1 text-gray-700 dark:text-gray-300">{{ formatTimestamp(commitment.expires_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Summary Footer -->
    <div v-if="commitments.length" class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between text-sm">
      <span class="text-gray-500 dark:text-gray-400">
        Total: {{ commitments.length }} commitments
      </span>
      <router-link to="/commitments" class="text-primary-600 hover:text-primary-700 dark:text-primary-400">
        View all &rarr;
      </router-link>
    </div>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import { useTime } from '../../composables/useTime'
import Card from '../common/Card.vue'
import StatusBadge from '../common/StatusBadge.vue'
import EmptyState from '../common/EmptyState.vue'
import { KeyIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  customer: Object,
  commitments: { type: Array, default: () => [] },
  loading: Boolean
})

const { formatRelativeTime, formatTimestamp, formatTimeRemaining } = useTime()

const activeCount = computed(() =>
  props.commitments.filter(c => isActive(c)).length
)

const expiredCount = computed(() =>
  props.commitments.filter(c => !isActive(c)).length
)

const sortedCommitments = computed(() =>
  [...props.commitments].sort((a, b) => {
    // Active first
    const aActive = isActive(a)
    const bActive = isActive(b)
    if (aActive !== bActive) return bActive ? 1 : -1
    // Then by expiry (newest first)
    return (b.expires_at || 0) - (a.expires_at || 0)
  })
)

function isActive(commitment) {
  const now = Date.now() / 1000
  return commitment.expires_at > now
}

function truncateId(id) {
  if (!id) return '-'
  if (id.length <= 20) return id
  return `${id.slice(0, 10)}...${id.slice(-10)}`
}
</script>
