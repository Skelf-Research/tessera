<template>
  <div class="text-center py-12">
    <div class="mx-auto w-24 h-24 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center mb-4">
      <slot name="icon">
        <component :is="icon" class="w-12 h-12 text-gray-400 dark:text-gray-500" />
      </slot>
    </div>
    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-1">
      {{ title }}
    </h3>
    <p class="text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
      {{ description }}
    </p>
    <div v-if="$slots.action" class="mt-6">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
import { InboxIcon } from '@heroicons/vue/24/outline'

defineProps({
  title: { type: String, default: 'No data' },
  description: { type: String, default: 'There is nothing here yet.' },
  icon: { type: Object, default: () => InboxIcon }
})
</script>
