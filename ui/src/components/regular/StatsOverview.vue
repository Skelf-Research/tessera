<template>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <StatCard
      label="Active Commitments"
      :value="nodeStore.activeCommitments"
      :loading="nodeStore.statsLoading"
      :icon="KeyIcon"
      color="blue"
    />

    <StatCard
      label="Verified Proofs"
      :value="nodeStore.verifiedProofs"
      :loading="nodeStore.statsLoading"
      :icon="ShieldCheckIcon"
      color="green"
    />

    <StatCard
      label="Total Verifications"
      :value="nodeStore.totalVerifications"
      :loading="nodeStore.statsLoading"
      :icon="ChartBarIcon"
      color="purple"
    />

    <StatCard
      label="WebSocket Clients"
      :value="nodeStore.wsClients"
      :loading="nodeStore.healthLoading"
      :icon="UsersIcon"
      color="yellow"
      :subtext="nodeStore.wsConnected ? 'Connected' : 'Disconnected'"
    />
  </div>
</template>

<script setup>
import { useNodeStore } from '../../stores/node'
import StatCard from '../common/StatCard.vue'
import {
  KeyIcon,
  ShieldCheckIcon,
  ChartBarIcon,
  UsersIcon
} from '@heroicons/vue/24/outline'

const nodeStore = useNodeStore()
</script>
