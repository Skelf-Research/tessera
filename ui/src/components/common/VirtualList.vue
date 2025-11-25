<template>
  <div
    ref="containerRef"
    class="overflow-auto"
    :style="{ height: containerHeight }"
    @scroll="onScroll"
  >
    <div :style="{ height: `${totalHeight}px`, position: 'relative' }">
      <div
        :style="{
          position: 'absolute',
          top: `${offsetY}px`,
          left: 0,
          right: 0
        }"
      >
        <slot
          v-for="(item, index) in visibleItems"
          :key="getKey(item, startIndex + index)"
          :item="item"
          :index="startIndex + index"
        />
      </div>
    </div>

    <!-- Loading indicator at bottom -->
    <div v-if="loading" class="flex items-center justify-center py-4">
      <ArrowPathIcon class="w-5 h-5 text-gray-400 animate-spin" />
      <span class="ml-2 text-sm text-gray-500">Loading more...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  items: { type: Array, required: true },
  itemHeight: { type: Number, default: 64 },
  containerHeight: { type: String, default: '400px' },
  buffer: { type: Number, default: 5 },
  keyField: { type: String, default: 'id' },
  loading: Boolean
})

const emit = defineEmits(['loadMore'])

const containerRef = ref(null)
const scrollTop = ref(0)

const totalHeight = computed(() => props.items.length * props.itemHeight)

const startIndex = computed(() => {
  const start = Math.floor(scrollTop.value / props.itemHeight) - props.buffer
  return Math.max(0, start)
})

const endIndex = computed(() => {
  if (!containerRef.value) return props.buffer * 2
  const visibleCount = Math.ceil(containerRef.value.clientHeight / props.itemHeight)
  const end = startIndex.value + visibleCount + props.buffer * 2
  return Math.min(props.items.length, end)
})

const visibleItems = computed(() => {
  return props.items.slice(startIndex.value, endIndex.value)
})

const offsetY = computed(() => startIndex.value * props.itemHeight)

function getKey(item, index) {
  return item[props.keyField] || index
}

function onScroll(event) {
  scrollTop.value = event.target.scrollTop

  // Check if near bottom for infinite scroll
  const { scrollHeight, clientHeight } = event.target
  if (scrollTop.value + clientHeight >= scrollHeight - props.itemHeight * 2) {
    emit('loadMore')
  }
}

// Reset scroll on items change
watch(() => props.items.length, () => {
  if (containerRef.value && scrollTop.value > totalHeight.value) {
    containerRef.value.scrollTop = 0
    scrollTop.value = 0
  }
})
</script>
