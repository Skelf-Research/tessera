<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Settings</h2>
      <p class="text-gray-500 dark:text-gray-400 mt-1">Configure your CallDNS node</p>
    </div>

    <!-- Mode Selection -->
    <Card title="Node Mode" subtitle="Switch between regular and organization mode">
      <div class="space-y-4">
        <div class="flex items-center justify-between p-4 rounded-lg border-2 transition-colors cursor-pointer"
          :class="!appStore.isOrgMode ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'"
          @click="appStore.setMode('regular')"
        >
          <div class="flex items-center space-x-4">
            <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
              <ServerIcon class="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h4 class="font-medium text-gray-900 dark:text-white">Regular Node</h4>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Basic node for verification and status monitoring
              </p>
            </div>
          </div>
          <div v-if="!appStore.isOrgMode" class="w-5 h-5 rounded-full bg-primary-500 flex items-center justify-center">
            <CheckIcon class="w-3 h-3 text-white" />
          </div>
        </div>

        <div class="flex items-center justify-between p-4 rounded-lg border-2 transition-colors cursor-pointer"
          :class="appStore.isOrgMode ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'"
          @click="appStore.setMode('organization')"
        >
          <div class="flex items-center space-x-4">
            <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
              <BuildingOfficeIcon class="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h4 class="font-medium text-gray-900 dark:text-white">Organization Node</h4>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Full management features for organizations
              </p>
            </div>
          </div>
          <div v-if="appStore.isOrgMode" class="w-5 h-5 rounded-full bg-purple-500 flex items-center justify-center">
            <CheckIcon class="w-3 h-3 text-white" />
          </div>
        </div>
      </div>
    </Card>

    <!-- API Configuration -->
    <Card title="API Configuration" subtitle="Configure API endpoint and authentication">
      <form @submit.prevent="saveApiConfig" class="space-y-4">
        <div>
          <label class="label">API Endpoint</label>
          <input
            v-model="apiUrl"
            type="text"
            class="input"
            placeholder="http://localhost:8000"
          />
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
            The CallDNS node API endpoint
          </p>
        </div>

        <div v-if="appStore.isOrgMode">
          <label class="label">Organization ID</label>
          <input
            v-model="orgId"
            type="text"
            class="input"
            placeholder="your-organization-id"
          />
        </div>

        <div v-if="appStore.isOrgMode">
          <label class="label">API Key</label>
          <div class="relative">
            <input
              v-model="apiKey"
              :type="showApiKey ? 'text' : 'password'"
              class="input pr-10"
              placeholder="Enter API key..."
            />
            <button
              type="button"
              @click="showApiKey = !showApiKey"
              class="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-600"
            >
              <EyeIcon v-if="!showApiKey" class="w-4 h-4 text-gray-400" />
              <EyeSlashIcon v-else class="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>

        <div class="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            type="button"
            @click="testConnection"
            :disabled="testing"
            class="btn btn-secondary"
          >
            <ArrowPathIcon :class="['w-4 h-4 mr-2', testing ? 'animate-spin' : '']" />
            Test Connection
          </button>

          <button type="submit" class="btn btn-primary">
            Save Configuration
          </button>
        </div>

        <!-- Connection Test Result -->
        <div v-if="connectionStatus" class="p-3 rounded-lg" :class="connectionStatus.success ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'">
          <div class="flex items-center space-x-2">
            <CheckCircleIcon v-if="connectionStatus.success" class="w-5 h-5 text-green-600" />
            <ExclamationCircleIcon v-else class="w-5 h-5 text-red-600" />
            <span :class="connectionStatus.success ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'">
              {{ connectionStatus.message }}
            </span>
          </div>
        </div>
      </form>
    </Card>

    <!-- Theme Settings -->
    <Card title="Appearance" subtitle="Customize the look and feel">
      <div class="space-y-4">
        <div>
          <label class="label">Theme</label>
          <div class="grid grid-cols-3 gap-3">
            <button
              v-for="t in themes"
              :key="t.value"
              @click="appStore.setTheme(t.value)"
              :class="[
                'flex items-center justify-center space-x-2 p-3 rounded-lg border-2 transition-colors',
                appStore.theme === t.value
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
              ]"
            >
              <component :is="t.icon" class="w-5 h-5 text-gray-600 dark:text-gray-400" />
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ t.label }}</span>
            </button>
          </div>
        </div>
      </div>
    </Card>

    <!-- About -->
    <Card title="About" subtitle="CallDNS Node Information">
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="label">Version</label>
            <p class="text-sm text-gray-700 dark:text-gray-300">0.1.0</p>
          </div>
          <div>
            <label class="label">Node Type</label>
            <StatusBadge
              :status="appStore.isOrgMode ? 'info' : 'default'"
              :label="appStore.isOrgMode ? 'Organization' : 'Regular'"
            />
          </div>
        </div>

        <div>
          <label class="label">Documentation</label>
          <a href="https://github.com/calldns" target="_blank" rel="noopener" class="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400">
            View on GitHub &rarr;
          </a>
        </div>
      </div>
    </Card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAppStore } from '../stores/app'
import { useNodeStore } from '../stores/node'
import Card from '../components/common/Card.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import {
  ServerIcon,
  BuildingOfficeIcon,
  CheckIcon,
  EyeIcon,
  EyeSlashIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon
} from '@heroicons/vue/24/outline'

const appStore = useAppStore()
const nodeStore = useNodeStore()

const apiUrl = ref(appStore.apiUrl)
const orgId = ref(appStore.orgId)
const apiKey = ref(appStore.apiKey)
const showApiKey = ref(false)
const testing = ref(false)
const connectionStatus = ref(null)

const themes = [
  { value: 'light', label: 'Light', icon: SunIcon },
  { value: 'dark', label: 'Dark', icon: MoonIcon },
  { value: 'system', label: 'System', icon: ComputerDesktopIcon }
]

function saveApiConfig() {
  appStore.setApiConfig({
    url: apiUrl.value,
    organizationId: orgId.value,
    key: apiKey.value
  })
  connectionStatus.value = { success: true, message: 'Configuration saved!' }
  setTimeout(() => {
    connectionStatus.value = null
  }, 3000)
}

async function testConnection() {
  testing.value = true
  connectionStatus.value = null

  try {
    // Temporarily update the URL for testing
    const originalUrl = appStore.apiUrl
    appStore.setApiConfig({ url: apiUrl.value })

    await nodeStore.fetchHealth()

    if (nodeStore.isHealthy) {
      connectionStatus.value = { success: true, message: 'Connection successful!' }
    } else if (nodeStore.healthError) {
      connectionStatus.value = { success: false, message: nodeStore.healthError }
    } else {
      connectionStatus.value = { success: false, message: 'Unknown status' }
    }
  } catch (err) {
    connectionStatus.value = { success: false, message: err.message }
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  apiUrl.value = appStore.apiUrl
  orgId.value = appStore.orgId
  apiKey.value = appStore.apiKey
})
</script>
