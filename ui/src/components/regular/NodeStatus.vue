<template>
  <Card title="Node Status" subtitle="Health and connection status">
    <div class="space-y-4">
      <!-- Overall Status -->
      <div class="flex items-center justify-between p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50">
        <div class="flex items-center space-x-3">
          <div
            :class="[
              'w-12 h-12 rounded-full flex items-center justify-center',
              statusBgColor
            ]"
          >
            <CheckCircleIcon v-if="nodeStore.isHealthy" :class="['w-7 h-7', statusIconColor]" />
            <ExclamationCircleIcon v-else-if="nodeStore.healthError" :class="['w-7 h-7', statusIconColor]" />
            <ArrowPathIcon v-else class="w-7 h-7 text-gray-400 animate-spin" />
          </div>
          <div>
            <h4 class="font-semibold text-gray-900 dark:text-white">
              {{ statusText }}
            </h4>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              {{ statusDescription }}
            </p>
          </div>
        </div>
        <StatusBadge
          :status="nodeStore.isHealthy ? 'success' : nodeStore.healthError ? 'danger' : 'pending'"
          :label="nodeStore.isHealthy ? 'Online' : nodeStore.healthError ? 'Offline' : 'Checking'"
          dot
          :pulse="nodeStore.isHealthy"
        />
      </div>

      <!-- Details Grid -->
      <div class="grid grid-cols-2 gap-4">
        <!-- WebSocket Status -->
        <div class="p-3 rounded-lg border border-gray-200 dark:border-gray-600">
          <div class="flex items-center space-x-2 mb-1">
            <SignalIcon class="w-4 h-4 text-gray-400" />
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">WebSocket</span>
          </div>
          <div class="flex items-center space-x-2">
            <span
              :class="[
                'w-2 h-2 rounded-full',
                nodeStore.wsConnected ? 'bg-green-500' : 'bg-gray-400'
              ]"
            />
            <span class="text-sm text-gray-600 dark:text-gray-400">
              {{ nodeStore.wsConnected ? `${nodeStore.wsClients} clients` : 'Disconnected' }}
            </span>
          </div>
        </div>

        <!-- Last Check -->
        <div class="p-3 rounded-lg border border-gray-200 dark:border-gray-600">
          <div class="flex items-center space-x-2 mb-1">
            <ClockIcon class="w-4 h-4 text-gray-400" />
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Last Check</span>
          </div>
          <span class="text-sm text-gray-600 dark:text-gray-400">
            {{ formatRelativeTime(nodeStore.lastHealthCheck) }}
          </span>
        </div>

        <!-- API Endpoint -->
        <div class="p-3 rounded-lg border border-gray-200 dark:border-gray-600 col-span-2">
          <div class="flex items-center space-x-2 mb-1">
            <GlobeAltIcon class="w-4 h-4 text-gray-400" />
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">API Endpoint</span>
          </div>
          <code class="text-sm text-gray-600 dark:text-gray-400 font-mono">
            {{ appStore.apiUrl }}
          </code>
        </div>
      </div>

      <!-- Error Message -->
      <div
        v-if="nodeStore.healthError"
        class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
      >
        <div class="flex items-start space-x-2">
          <ExclamationTriangleIcon class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p class="text-sm font-medium text-red-800 dark:text-red-300">Connection Error</p>
            <p class="text-sm text-red-600 dark:text-red-400 mt-1">{{ nodeStore.healthError }}</p>
          </div>
        </div>
      </div>
    </div>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import { useAppStore } from '../../stores/app'
import { useNodeStore } from '../../stores/node'
import { useTime } from '../../composables/useTime'
import Card from '../common/Card.vue'
import StatusBadge from '../common/StatusBadge.vue'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  SignalIcon,
  ClockIcon,
  GlobeAltIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const nodeStore = useNodeStore()
const { formatRelativeTime } = useTime()

const statusText = computed(() => {
  if (nodeStore.healthLoading) return 'Checking Status...'
  if (nodeStore.healthError) return 'Connection Failed'
  if (nodeStore.isHealthy) return 'Node Operational'
  return 'Status Unknown'
})

const statusDescription = computed(() => {
  if (nodeStore.healthLoading) return 'Connecting to node...'
  if (nodeStore.healthError) return 'Unable to reach the node'
  if (nodeStore.isHealthy) return 'All systems running normally'
  return 'Please check configuration'
})

const statusBgColor = computed(() => {
  if (nodeStore.isHealthy) return 'bg-green-100 dark:bg-green-900/30'
  if (nodeStore.healthError) return 'bg-red-100 dark:bg-red-900/30'
  return 'bg-gray-100 dark:bg-gray-700'
})

const statusIconColor = computed(() => {
  if (nodeStore.isHealthy) return 'text-green-600 dark:text-green-400'
  if (nodeStore.healthError) return 'text-red-600 dark:text-red-400'
  return 'text-gray-400'
})
</script>
