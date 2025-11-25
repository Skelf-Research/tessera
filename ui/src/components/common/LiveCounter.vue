<template>
  <div class="flex items-baseline space-x-1">
    <span
      ref="counterRef"
      :class="[
        'tabular-nums transition-all duration-300',
        animating ? 'text-green-500 scale-105' : ''
      ]"
    >
      {{ displayValue }}
    </span>
    <span v-if="suffix" class="text-sm text-gray-500 dark:text-gray-400">{{ suffix }}</span>
    <span
      v-if="showDelta && delta !== 0"
      :class="[
        'text-xs font-medium',
        delta > 0 ? 'text-green-500' : 'text-red-500'
      ]"
    >
      {{ delta > 0 ? '+' : '' }}{{ formatDelta(delta) }}
    </span>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  value: { type: Number, required: true },
  format: { type: String, default: 'number' }, // number, compact, percent
  suffix: String,
  showDelta: Boolean,
  animateDuration: { type: Number, default: 500 }
})

const previousValue = ref(props.value)
const animating = ref(false)

const delta = computed(() => props.value - previousValue.value)

const displayValue = computed(() => {
  const val = props.value
  if (props.format === 'compact') {
    if (val >= 1000000000) return `${(val / 1000000000).toFixed(1)}B`
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`
    if (val >= 1000) return `${(val / 1000).toFixed(1)}K`
    return val.toLocaleString()
  }
  if (props.format === 'percent') {
    return `${val.toFixed(1)}%`
  }
  return val.toLocaleString()
})

function formatDelta(d) {
  const abs = Math.abs(d)
  if (abs >= 1000000) return `${(d / 1000000).toFixed(1)}M`
  if (abs >= 1000) return `${(d / 1000).toFixed(1)}K`
  return d.toLocaleString()
}

watch(() => props.value, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    previousValue.value = oldVal
    animating.value = true
    setTimeout(() => {
      animating.value = false
    }, props.animateDuration)
  }
})
</script>
