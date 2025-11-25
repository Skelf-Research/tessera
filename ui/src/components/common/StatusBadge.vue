<template>
  <span
    :class="[
      'inline-flex items-center rounded-full text-xs font-medium',
      sizeClasses,
      colorClasses
    ]"
  >
    <span
      v-if="dot"
      :class="[
        'w-1.5 h-1.5 rounded-full mr-1.5',
        dotColor,
        pulse ? 'animate-pulse-dot' : ''
      ]"
    />
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'default',
    validator: v => ['success', 'warning', 'danger', 'info', 'default', 'active', 'inactive', 'pending'].includes(v)
  },
  label: String,
  size: {
    type: String,
    default: 'md',
    validator: v => ['sm', 'md', 'lg'].includes(v)
  },
  dot: Boolean,
  pulse: Boolean
})

const sizeClasses = computed(() => {
  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm'
  }
  return sizes[props.size]
})

const colorMap = {
  success: 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300',
  active: 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-300',
  warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/50 dark:text-yellow-300',
  danger: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300',
  inactive: 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-300',
  info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-300',
  default: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
}

const dotColorMap = {
  success: 'bg-green-500',
  active: 'bg-green-500',
  warning: 'bg-yellow-500',
  pending: 'bg-yellow-500',
  danger: 'bg-red-500',
  inactive: 'bg-red-500',
  info: 'bg-blue-500',
  default: 'bg-gray-500'
}

const colorClasses = computed(() => colorMap[props.status] || colorMap.default)
const dotColor = computed(() => dotColorMap[props.status] || dotColorMap.default)
</script>
