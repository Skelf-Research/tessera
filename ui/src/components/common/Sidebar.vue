<template>
  <aside
    :class="[
      'fixed top-0 left-0 h-full bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 transition-all duration-300 z-40',
      collapsed ? 'w-16' : 'w-64'
    ]"
  >
    <!-- Logo -->
    <div class="h-16 flex items-center justify-between px-4 border-b border-gray-200 dark:border-gray-700">
      <div v-if="!collapsed" class="flex items-center space-x-2">
        <div class="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
          </svg>
        </div>
        <span class="font-bold text-lg text-gray-900 dark:text-white">CallDNS</span>
      </div>
      <button
        @click="toggleSidebar"
        class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <ChevronLeftIcon v-if="!collapsed" class="w-5 h-5 text-gray-500" />
        <ChevronRightIcon v-else class="w-5 h-5 text-gray-500" />
      </button>
    </div>

    <!-- Mode badge -->
    <div v-if="!collapsed" class="px-4 py-3">
      <span
        :class="[
          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
          appStore.isOrgMode
            ? 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
            : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
        ]"
      >
        {{ appStore.isOrgMode ? 'Organization Node' : 'Regular Node' }}
      </span>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
      <router-link
        v-for="item in filteredNavItems"
        :key="item.name"
        :to="item.to"
        :class="[
          'group flex items-center px-3 py-2 rounded-lg transition-colors',
          isActive(item.to)
            ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
            : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
        ]"
        :title="collapsed ? item.name : ''"
      >
        <component
          :is="item.icon"
          :class="[
            'flex-shrink-0 w-5 h-5',
            isActive(item.to) ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400 group-hover:text-gray-500'
          ]"
        />
        <span v-if="!collapsed" class="ml-3">{{ item.name }}</span>
      </router-link>
    </nav>

    <!-- Status indicator -->
    <div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700">
      <div class="flex items-center" :title="collapsed ? statusText : ''">
        <span
          :class="[
            'flex-shrink-0 w-2 h-2 rounded-full animate-pulse-dot',
            statusColor
          ]"
        />
        <span v-if="!collapsed" class="ml-2 text-sm text-gray-500 dark:text-gray-400">
          {{ statusText }}
        </span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '../../stores/app'
import { useNodeStore } from '../../stores/node'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  HomeIcon,
  UsersIcon,
  KeyIcon,
  ShieldCheckIcon,
  Cog6ToothIcon
} from '@heroicons/vue/24/outline'

const route = useRoute()
const appStore = useAppStore()
const nodeStore = useNodeStore()

const collapsed = computed(() => appStore.sidebarCollapsed)

const navItems = [
  { name: 'Dashboard', to: '/', icon: HomeIcon, orgOnly: false },
  { name: 'Customers', to: '/customers', icon: UsersIcon, orgOnly: true },
  { name: 'Commitments', to: '/commitments', icon: KeyIcon, orgOnly: false },
  { name: 'Proofs', to: '/proofs', icon: ShieldCheckIcon, orgOnly: false },
  { name: 'Settings', to: '/settings', icon: Cog6ToothIcon, orgOnly: false }
]

const filteredNavItems = computed(() =>
  navItems.filter(item => !item.orgOnly || appStore.isOrgMode)
)

const statusText = computed(() => {
  if (nodeStore.healthLoading) return 'Checking...'
  if (nodeStore.healthError) return 'Offline'
  if (nodeStore.isHealthy) return 'Online'
  return 'Unknown'
})

const statusColor = computed(() => {
  if (nodeStore.healthLoading) return 'bg-gray-400'
  if (nodeStore.healthError) return 'bg-red-500'
  if (nodeStore.isHealthy) return 'bg-green-500'
  return 'bg-yellow-500'
})

function isActive(path) {
  return route.path === path
}

function toggleSidebar() {
  appStore.toggleSidebar()
}
</script>
