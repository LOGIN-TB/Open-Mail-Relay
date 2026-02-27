<script setup lang="ts">
import { computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import t from '../../i18n/de'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const props = defineProps<{
  data: {
    labels: string[]
    sent: number[]
    deferred: number[]
    bounced: number[]
    rejected: number[]
    auth_failed: number[]
  } | null
}>()

const chartData = computed(() => {
  if (!props.data) {
    return { labels: [], datasets: [] }
  }
  return {
    labels: props.data.labels,
    datasets: [
      { label: t.dashboard.sent, data: props.data.sent, backgroundColor: '#22c55e' },
      { label: t.dashboard.deferred, data: props.data.deferred, backgroundColor: '#f59e0b' },
      { label: t.dashboard.bounced, data: props.data.bounced, backgroundColor: '#ef4444' },
      { label: t.dashboard.rejected, data: props.data.rejected, backgroundColor: '#8b5cf6' },
      { label: t.dashboard.authFailed, data: props.data.auth_failed, backgroundColor: '#dc2626' },
    ],
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' as const },
  },
  scales: {
    x: { stacked: true },
    y: { stacked: true, beginAtZero: true },
  },
}
</script>

<template>
  <div class="card">
    <h3>{{ t.dashboard.deliveryChart }}</h3>
    <div class="chart-container">
      <Bar v-if="data && data.labels.length > 0" :data="chartData" :options="chartOptions" />
      <div v-else class="no-data">{{ t.dashboard.noData }}</div>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.card h3 {
  font-size: 1rem;
  color: #1e293b;
  margin-bottom: 1rem;
}

.chart-container {
  height: 300px;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}
</style>
