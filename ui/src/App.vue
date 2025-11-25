<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <Sidebar />

    <div
      :class="[
        'transition-all duration-300',
        appStore.sidebarCollapsed ? 'ml-16' : 'ml-64'
      ]"
    >
      <Header />

      <main class="p-6">
        <RouterView v-slot="{ Component }">
          <transition
            enter-active-class="transition-opacity duration-200"
            leave-active-class="transition-opacity duration-150"
            enter-from-class="opacity-0"
            leave-to-class="opacity-0"
            mode="out-in"
          >
            <component :is="Component" />
          </transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useAppStore } from './stores/app'
import { useNodeStore } from './stores/node'
import Sidebar from './components/common/Sidebar.vue'
import Header from './components/common/Header.vue'

const appStore = useAppStore()
const nodeStore = useNodeStore()

onMounted(() => {
  // Apply initial theme
  appStore.applyTheme()

  // Start polling for health/stats
  nodeStore.startPolling(10000)
})

onUnmounted(() => {
  nodeStore.stopPolling()
})
</script>
