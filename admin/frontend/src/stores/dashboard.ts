import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client'

interface DashboardStats {
  sent_today: number
  deferred_today: number
  bounced_today: number
  rejected_today: number
  queue_size: number
  success_rate: number
}

interface ChartData {
  labels: string[]
  sent: number[]
  deferred: number[]
  bounced: number[]
  rejected: number[]
}

interface MailEvent {
  id: number
  timestamp: string
  queue_id: string | null
  sender: string | null
  recipient: string | null
  status: string
  relay: string | null
  delay: number | null
  dsn: string | null
  size: number | null
  message: string | null
  client_ip: string | null
  sasl_username: string | null
}

interface QueueEntry {
  queue_id: string
  size: string
  arrival_time: string
  sender: string
  recipients: string[]
}

export const useDashboardStore = defineStore('dashboard', () => {
  const stats = ref<DashboardStats | null>(null)
  const chartData = ref<ChartData | null>(null)
  const activity = ref<MailEvent[]>([])
  const queue = ref<QueueEntry[]>([])
  const loading = ref(false)

  async function fetchStats() {
    const { data } = await api.get('/dashboard/stats')
    stats.value = data
  }

  async function fetchChart(hours = 24) {
    const { data } = await api.get('/dashboard/chart', { params: { hours } })
    chartData.value = data
  }

  async function fetchActivity(page = 1) {
    const { data } = await api.get('/dashboard/activity', { params: { page, per_page: 50 } })
    activity.value = data
  }

  async function fetchQueue() {
    const { data } = await api.get('/dashboard/queue')
    queue.value = data
  }

  async function fetchAll() {
    loading.value = true
    try {
      await Promise.all([fetchStats(), fetchChart(), fetchActivity(), fetchQueue()])
    } finally {
      loading.value = false
    }
  }

  return { stats, chartData, activity, queue, loading, fetchStats, fetchChart, fetchActivity, fetchQueue, fetchAll }
})
