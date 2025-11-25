<template>
  <div class="relative">
    <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
    <input
      :value="modelValue"
      @input="onInput"
      @keydown.enter="onSearch"
      type="text"
      :placeholder="placeholder"
      class="input pl-10 pr-10"
    />
    <div class="absolute right-2 top-1/2 -translate-y-1/2 flex items-center space-x-1">
      <button
        v-if="modelValue"
        @click="clear"
        class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-600"
        title="Clear"
      >
        <XMarkIcon class="w-4 h-4 text-gray-400" />
      </button>
      <button
        v-if="!instant"
        @click="onSearch"
        :disabled="loading"
        class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-600"
        title="Search"
      >
        <ArrowPathIcon v-if="loading" class="w-4 h-4 text-gray-400 animate-spin" />
        <ArrowRightIcon v-else class="w-4 h-4 text-gray-400" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import {
  MagnifyingGlassIcon,
  XMarkIcon,
  ArrowRightIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Search...' },
  loading: Boolean,
  instant: Boolean,
  debounce: { type: Number, default: 300 }
})

const emit = defineEmits(['update:modelValue', 'search'])

let debounceTimer = null

function onInput(event) {
  const value = event.target.value
  emit('update:modelValue', value)

  if (props.instant) {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      emit('search', value)
    }, props.debounce)
  }
}

function onSearch() {
  emit('search', props.modelValue)
}

function clear() {
  emit('update:modelValue', '')
  emit('search', '')
}
</script>
