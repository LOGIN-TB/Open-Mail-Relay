<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import StatsCards from '../components/dashboard/StatsCards.vue'
import DeliveryChart from '../components/dashboard/DeliveryChart.vue'
import QueueStatus from '../components/dashboard/QueueStatus.vue'
import RecentActivity from '../components/dashboard/RecentActivity.vue'
import WarmupStatusCard from '../components/dashboard/WarmupStatusCard.vue'
import t from '../i18n/de'

const dashboard = useDashboardStore()

let refreshInterval: ReturnType<typeof setInterval>

onMounted(() => {
  dashboard.fetchAll()
  refreshInterval = setInterval(() => dashboard.fetchAll(), 30000)
})

onUnmounted(() => {
  clearInterval(refreshInterval)
})
</script>

<template>
  <div class="dashboard">
    <h2>{{ t.dashboard.title }}</h2>

    <WarmupStatusCard />

    <StatsCards :stats="dashboard.stats" :loading="dashboard.loading" />

    <div class="dashboard-grid">
      <div class="chart-section">
        <DeliveryChart :data="dashboard.chartData" />
      </div>
      <div class="queue-section">
        <QueueStatus :queue="dashboard.queue" />
      </div>
    </div>

    <RecentActivity :events="dashboard.activity" />
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.dashboard h2 {
  font-size: 1.5rem;
  color: #1e293b;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
