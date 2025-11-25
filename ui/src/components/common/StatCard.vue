<template>
  <div class="card p-6">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm font-medium text-gray-500 dark:text-gray-400">
          {{ label }}
        </p>
        <p class="text-2xl font-bold text-gray-900 dark:text-white mt-1">
          <span v-if="loading" class="animate-pulse">...</span>
          <span v-else>{{ formattedValue }}</span>
        </p>
        <p v-if="subtext" class="text-xs text-gray-400 dark:text-gray-500 mt-1">
          {{ subtext }}
        </p>
      </div>
      <div
        :class="[
          'p-3 rounded-xl',
          iconBgColor
        ]"
      >
        <slot name="icon">
          <component :is="icon" :class="['w-6 h-6', iconColor]" />
        </slot>
      </div>
    </div>
    <div v-if="trend !== undefined" class="mt-3 flex items-center text-sm">
      <ArrowUpIcon v-if="trend > 0" class="w-4 h-4 text-green-500 mr-1" />
      <ArrowDownIcon v-else-if="trend < 0" class="w-4 h-4 text-red-500 mr-1" />
      <span
        :class="[
          trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500'
        ]"
      >
        {{ Math.abs(trend) }}% {{ trend > 0 ? 'increase' : trend < 0 ? 'decrease' : 'no change' }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/vue/24/solid'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: 0 },
  subtext: String,
  icon: Object,
  color: { type: String, default: 'blue' },
  loading: Boolean,
  trend: Number,
  format: { type: String, default: 'number' }
})

const formattedValue = computed(() => {
  if (props.format === 'percent') {
    return `${props.value}%`
  }
  if (props.format === 'number' && typeof props.value === 'number') {
    return props.value.toLocaleString()
  }
  return props.value
})

const colorMap = {
  blue: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    icon: 'text-blue-600 dark:text-blue-400'
  },
  green: {
    bg: 'bg-green-100 dark:bg-green-900/30',
    icon: 'text-green-600 dark:text-green-400'
  },
  yellow: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/30',
    icon: 'text-yellow-600 dark:text-yellow-400'
  },
  red: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    icon: 'text-red-600 dark:text-red-400'
  },
  purple: {
    bg: 'bg-purple-100 dark:bg-purple-900/30',
    icon: 'text-purple-600 dark:text-purple-400'
  }
}

const iconBgColor = computed(() => colorMap[props.color]?.bg || colorMap.blue.bg)
const iconColor = computed(() => colorMap[props.color]?.icon || colorMap.blue.icon)
</script>
