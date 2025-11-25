<template>
  <div class="space-y-6">
    <!-- Stats Overview -->
    <StatsOverview />

    <!-- Main Content Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Node Status -->
      <NodeStatus />

      <!-- Recent Activity -->
      <RecentActivity />
    </div>

    <!-- Organization Section (Org Mode Only) -->
    <template v-if="appStore.isOrgMode">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Quick Actions -->
        <Card title="Quick Actions" subtitle="Common organization tasks">
          <div class="grid grid-cols-2 gap-3">
            <router-link
              to="/customers"
              class="flex items-center space-x-3 p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
                <UsersIcon class="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-white">Customers</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">Manage customers</p>
              </div>
            </router-link>

            <button
              @click="showRegisterCustomer = true"
              class="flex items-center space-x-3 p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left"
            >
              <div class="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                <UserPlusIcon class="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-white">Add Customer</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">Register new</p>
              </div>
            </button>

            <router-link
              to="/commitments"
              class="flex items-center space-x-3 p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <KeyIcon class="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-white">Commitments</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">View active</p>
              </div>
            </router-link>

            <router-link
              to="/settings"
              class="flex items-center space-x-3 p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div class="p-2 rounded-lg bg-gray-100 dark:bg-gray-700">
                <Cog6ToothIcon class="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-900 dark:text-white">Settings</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">Configure node</p>
              </div>
            </router-link>
          </div>
        </Card>

        <!-- Organization Info -->
        <Card title="Organization" subtitle="Your organization details">
          <div class="space-y-4">
            <div v-if="appStore.orgId" class="p-4 rounded-lg bg-purple-50 dark:bg-purple-900/20">
              <div class="flex items-center space-x-3">
                <BuildingOfficeIcon class="w-10 h-10 text-purple-600 dark:text-purple-400" />
                <div>
                  <p class="text-sm font-medium text-gray-900 dark:text-white">Organization ID</p>
                  <code class="text-xs text-gray-600 dark:text-gray-400 font-mono">
                    {{ appStore.orgId }}
                  </code>
                </div>
              </div>
            </div>

            <div v-else class="text-center py-6">
              <BuildingOfficeIcon class="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p class="text-sm text-gray-500 dark:text-gray-400 mb-3">
                No organization configured
              </p>
              <router-link to="/settings" class="btn btn-primary text-sm">
                Configure Organization
              </router-link>
            </div>

            <div v-if="appStore.apiKey" class="p-3 rounded-lg border border-gray-200 dark:border-gray-600">
              <div class="flex items-center justify-between">
                <span class="text-sm text-gray-600 dark:text-gray-400">API Key</span>
                <StatusBadge status="success" label="Configured" size="sm" />
              </div>
            </div>
          </div>
        </Card>
      </div>
    </template>

    <!-- Register Customer Modal -->
    <Modal v-model="showRegisterCustomer" title="Register Customer" size="md">
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
        </div>

        <div v-if="registerError" class="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-sm text-red-600 dark:text-red-400">
          {{ registerError }}
        </div>
      </form>

      <template #footer>
        <button @click="showRegisterCustomer = false" class="btn btn-secondary">Cancel</button>
        <button
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../stores/app'
import { useCustomersStore } from '../stores/customers'
import StatsOverview from '../components/regular/StatsOverview.vue'
import NodeStatus from '../components/regular/NodeStatus.vue'
import RecentActivity from '../components/regular/RecentActivity.vue'
import Card from '../components/common/Card.vue'
import StatusBadge from '../components/common/StatusBadge.vue'
import Modal from '../components/common/Modal.vue'
import {
  UsersIcon,
  UserPlusIcon,
  KeyIcon,
  Cog6ToothIcon,
  BuildingOfficeIcon
} from '@heroicons/vue/24/outline'

const router = useRouter()
const appStore = useAppStore()
const customersStore = useCustomersStore()

const showRegisterCustomer = ref(false)
const newCustomerId = ref('')
const registering = ref(false)
const registerError = ref('')

async function registerCustomer() {
  if (!newCustomerId.value) return

  registering.value = true
  registerError.value = ''

  try {
    await customersStore.registerCustomer(newCustomerId.value)
    showRegisterCustomer.value = false
    newCustomerId.value = ''
    router.push('/customers')
  } catch (err) {
    registerError.value = err.message
  } finally {
    registering.value = false
  }
}
</script>
