<template>
  <header class="h-16 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between px-6">
    <div class="flex items-center space-x-4">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-white">
        {{ pageTitle }}
      </h1>
    </div>

    <div class="flex items-center space-x-4">
      <!-- Connection status -->
      <div class="flex items-center space-x-2 text-sm">
        <span
          :class="[
            'w-2 h-2 rounded-full',
            nodeStore.wsConnected ? 'bg-green-500 animate-pulse-dot' : 'bg-gray-400'
          ]"
        />
        <span class="text-gray-500 dark:text-gray-400">
          {{ nodeStore.wsConnected ? `${nodeStore.wsClients} connected` : 'Disconnected' }}
        </span>
      </div>

      <!-- Theme toggle -->
      <button
        @click="toggleTheme"
        class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        :title="themeTitle"
      >
        <SunIcon v-if="appStore.isDarkMode" class="w-5 h-5 text-gray-500" />
        <MoonIcon v-else class="w-5 h-5 text-gray-500" />
      </button>

      <!-- Mode toggle -->
      <div class="flex items-center space-x-2">
        <span class="text-sm text-gray-500 dark:text-gray-400">Mode:</span>
        <button
          @click="toggleMode"
          :class="[
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
            appStore.isOrgMode ? 'bg-purple-600' : 'bg-blue-600'
          ]"
        >
          <span
            :class="[
              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
              appStore.isOrgMode ? 'translate-x-6' : 'translate-x-1'
            ]"
          />
        </button>
        <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
          {{ appStore.isOrgMode ? 'Org' : 'Regular' }}
        </span>
      </div>

      <!-- Refresh button -->
      <button
        @click="refresh"
        :disabled="nodeStore.healthLoading"
        class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50"
        title="Refresh data"
      >
        <ArrowPathIcon
          :class="[
            'w-5 h-5 text-gray-500',
            nodeStore.healthLoading ? 'animate-spin' : ''
          ]"
        />
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../../stores/app'
import { useNodeStore } from '../../stores/node'
import {
  SunIcon,
  MoonIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const appStore = useAppStore()
const nodeStore = useNodeStore()

const pageTitles = {
  '/': 'Dashboard',
  '/customers': 'Customer Management',
  '/commitments': 'Commitments',
  '/proofs': 'Proof Verification',
  '/settings': 'Settings'
}

const pageTitle = computed(() => pageTitles[route.path] || 'CallDNS')

const themeTitle = computed(() =>
  appStore.isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'
)

function toggleTheme() {
  const newTheme = appStore.isDarkMode ? 'light' : 'dark'
  appStore.setTheme(newTheme)
}

function toggleMode() {
  const newMode = appStore.isOrgMode ? 'regular' : 'organization'
  appStore.setMode(newMode)
}

function refresh() {
  nodeStore.fetchHealth()
  nodeStore.fetchStats()
}
</script>
