<template>
  <Card noPadding>
    <template #header>
      <div class="p-4 border-b border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Customers</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400">
              <LiveCounter :value="customersStore.total" format="compact" /> total
            </p>
          </div>
          <button @click="$emit('register')" class="btn btn-primary text-sm">
            <UserPlusIcon class="w-4 h-4 mr-1" />
            Add
          </button>
        </div>

        <!-- Search -->
        <SearchInput
          v-model="searchQuery"
          placeholder="Search customers..."
          :loading="customersStore.loading"
          instant
          @search="onSearch"
        />
      </div>
    </template>

    <!-- Loading -->
    <div v-if="customersStore.loading && !customersStore.customers.length" class="p-4 space-y-3">
      <div v-for="i in 5" :key="i" class="animate-pulse flex items-center space-x-3">
        <div class="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700" />
        <div class="flex-1 space-y-2">
          <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
          <div class="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/4" />
        </div>
      </div>
    </div>

    <!-- Empty -->
    <EmptyState
      v-else-if="!customersStore.customers.length && !customersStore.loading"
      :title="searchQuery ? 'No customers found' : 'No customers'"
      :description="searchQuery ? 'Try a different search term.' : 'Register your first customer to get started.'"
      :icon="UsersIcon"
      class="py-12"
    >
      <template #action v-if="!searchQuery">
        <button @click="$emit('register')" class="btn btn-primary">
          <UserPlusIcon class="w-4 h-4 mr-2" />
          Register Customer
        </button>
      </template>
    </EmptyState>

    <!-- List -->
    <div v-else>
      <div class="divide-y divide-gray-100 dark:divide-gray-700 max-h-[500px] overflow-y-auto">
        <div
          v-for="customer in customersStore.customers"
          :key="customer.customer_id"
          :class="[
            'flex items-center justify-between p-4 cursor-pointer transition-colors',
            selectedId === customer.customer_id
              ? 'bg-primary-50 dark:bg-primary-900/20'
              : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
          ]"
          @click="selectCustomer(customer)"
        >
          <div class="flex items-center space-x-3 min-w-0">
            <div class="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
              <UserIcon class="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
                {{ customer.customer_id }}
              </p>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {{ formatRelativeTime(customer.created_at) }}
              </p>
            </div>
          </div>

          <ChevronRightIcon class="w-5 h-5 text-gray-400 flex-shrink-0" />
        </div>
      </div>

      <!-- Pagination -->
      <Pagination
        v-if="customersStore.total > customersStore.pageSize"
        :current-page="customersStore.page"
        :page-size="customersStore.pageSize"
        :total="customersStore.total"
        :page-sizes="[25, 50, 100]"
        @update:current-page="customersStore.setPage"
        @update:page-size="customersStore.setPageSize"
      />
    </div>
  </Card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCustomersStore } from '../../stores/customers'
import { useTime } from '../../composables/useTime'
import Card from '../common/Card.vue'
import EmptyState from '../common/EmptyState.vue'
import SearchInput from '../common/SearchInput.vue'
import Pagination from '../common/Pagination.vue'
import LiveCounter from '../common/LiveCounter.vue'
import {
  UsersIcon,
  UserIcon,
  UserPlusIcon,
  ChevronRightIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  selectedId: String
})

const emit = defineEmits(['select', 'register'])

const customersStore = useCustomersStore()
const { formatRelativeTime } = useTime()

const searchQuery = ref('')

function selectCustomer(customer) {
  customersStore.selectCustomer(customer)
  emit('select', customer)
}

function onSearch(query) {
  customersStore.searchCustomers(query)
}

onMounted(() => {
  customersStore.fetchCustomers()
})
</script>
