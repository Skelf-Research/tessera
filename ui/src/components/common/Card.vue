<template>
  <div :class="['card', padding, className]">
    <div v-if="title || $slots.header" class="flex items-center justify-between mb-4">
      <slot name="header">
        <div>
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
            {{ title }}
          </h3>
          <p v-if="subtitle" class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {{ subtitle }}
          </p>
        </div>
      </slot>
      <slot name="actions" />
    </div>
    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  subtitle: String,
  noPadding: Boolean,
  className: String
})

const padding = computed(() => props.noPadding ? '' : 'p-6')
</script>
