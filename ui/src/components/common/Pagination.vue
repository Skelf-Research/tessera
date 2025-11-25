<template>
  <div class="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
    <!-- Mobile view -->
    <div class="flex flex-1 justify-between sm:hidden">
      <button
        @click="goToPage(currentPage - 1)"
        :disabled="currentPage <= 1"
        class="btn btn-secondary text-sm"
      >
        Previous
      </button>
      <button
        @click="goToPage(currentPage + 1)"
        :disabled="currentPage >= totalPages"
        class="btn btn-secondary text-sm"
      >
        Next
      </button>
    </div>

    <!-- Desktop view -->
    <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
      <div class="flex items-center space-x-4">
        <p class="text-sm text-gray-700 dark:text-gray-300">
          Showing
          <span class="font-medium">{{ startItem }}</span>
          to
          <span class="font-medium">{{ endItem }}</span>
          of
          <span class="font-medium">{{ formatNumber(total) }}</span>
          results
        </p>

        <!-- Page size selector -->
        <select
          :value="pageSize"
          @change="changePageSize($event.target.value)"
          class="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300"
        >
          <option v-for="size in pageSizes" :key="size" :value="size">
            {{ size }} / page
          </option>
        </select>
      </div>

      <nav class="flex items-center space-x-1">
        <!-- First page -->
        <button
          @click="goToPage(1)"
          :disabled="currentPage <= 1"
          class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="First page"
        >
          <ChevronDoubleLeftIcon class="w-4 h-4 text-gray-500" />
        </button>

        <!-- Previous page -->
        <button
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage <= 1"
          class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Previous page"
        >
          <ChevronLeftIcon class="w-4 h-4 text-gray-500" />
        </button>

        <!-- Page numbers -->
        <template v-for="page in visiblePages" :key="page">
          <span v-if="page === '...'" class="px-2 text-gray-400">...</span>
          <button
            v-else
            @click="goToPage(page)"
            :class="[
              'min-w-[2.5rem] px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              page === currentPage
                ? 'bg-primary-600 text-white'
                : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'
            ]"
          >
            {{ page }}
          </button>
        </template>

        <!-- Next page -->
        <button
          @click="goToPage(currentPage + 1)"
          :disabled="currentPage >= totalPages"
          class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Next page"
        >
          <ChevronRightIcon class="w-4 h-4 text-gray-500" />
        </button>

        <!-- Last page -->
        <button
          @click="goToPage(totalPages)"
          :disabled="currentPage >= totalPages"
          class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          title="Last page"
        >
          <ChevronDoubleRightIcon class="w-4 h-4 text-gray-500" />
        </button>
      </nav>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDoubleLeftIcon,
  ChevronDoubleRightIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  currentPage: { type: Number, required: true },
  pageSize: { type: Number, default: 50 },
  total: { type: Number, required: true },
  pageSizes: { type: Array, default: () => [25, 50, 100, 250] }
})

const emit = defineEmits(['update:currentPage', 'update:pageSize'])

const totalPages = computed(() => Math.ceil(props.total / props.pageSize) || 1)

const startItem = computed(() => {
  if (props.total === 0) return 0
  return (props.currentPage - 1) * props.pageSize + 1
})

const endItem = computed(() => {
  return Math.min(props.currentPage * props.pageSize, props.total)
})

const visiblePages = computed(() => {
  const pages = []
  const total = totalPages.value
  const current = props.currentPage
  const maxVisible = 7

  if (total <= maxVisible) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)

    if (current > 3) pages.push('...')

    const start = Math.max(2, current - 1)
    const end = Math.min(total - 1, current + 1)

    for (let i = start; i <= end; i++) pages.push(i)

    if (current < total - 2) pages.push('...')

    pages.push(total)
  }

  return pages
})

function formatNumber(num) {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toLocaleString()
}

function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) {
    emit('update:currentPage', page)
  }
}

function changePageSize(size) {
  emit('update:pageSize', parseInt(size))
  emit('update:currentPage', 1)
}
</script>
