import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client'

interface ThrottleConfig {
  enabled: boolean
  warmup_start_date: string
  batch_interval_minutes: number
}

interface WarmupLimits {
  max_per_hour: number
  max_per_day: number
  burst_limit: number
}

interface WarmupStatus {
  current_phase: number
  phase_name: string
  days_elapsed: number
  days_remaining: number
  percent_complete: number
  limits: WarmupLimits
  is_established: boolean
}

interface WarmupPhase {
  id: number
  phase_number: number
  name: string
  duration_days: number
  max_per_hour: number
  max_per_day: number
  burst_limit: number
}

interface TransportRule {
  id: number
  domain_pattern: string
  transport_name: string
  concurrency_limit: number
  rate_delay_seconds: number
  is_active: boolean
  description: string | null
}

interface ThrottleMetrics {
  sent_today: number
  sent_this_hour: number
  held_count: number
  limits: WarmupLimits | null
}

export type { ThrottleConfig, WarmupStatus, WarmupPhase, TransportRule, ThrottleMetrics, WarmupLimits }

export const useThrottleStore = defineStore('throttle', () => {
  const config = ref<ThrottleConfig | null>(null)
  const warmup = ref<WarmupStatus | null>(null)
  const phases = ref<WarmupPhase[]>([])
  const transports = ref<TransportRule[]>([])
  const metrics = ref<ThrottleMetrics | null>(null)
  const loading = ref(false)

  async function fetchConfig() {
    const { data } = await api.get('/throttling/config')
    config.value = data
  }

  async function updateConfig(body: { enabled?: boolean; batch_interval_minutes?: number }) {
    const { data } = await api.put('/throttling/config', body)
    await fetchConfig()
    return data
  }

  async function fetchWarmup() {
    const { data } = await api.get('/throttling/warmup')
    warmup.value = data
  }

  async function setWarmupPhase(phaseNumber: number) {
    await api.put('/throttling/warmup/phase', null, { params: { phase_number: phaseNumber } })
    await fetchWarmup()
  }

  async function resetWarmup() {
    await api.put('/throttling/warmup/reset')
    await fetchWarmup()
  }

  async function fetchPhases() {
    const { data } = await api.get('/throttling/warmup/phases')
    phases.value = data
  }

  async function updatePhase(id: number, body: Partial<WarmupPhase>) {
    const { data } = await api.put(`/throttling/warmup/phases/${id}`, body)
    await fetchPhases()
    return data
  }

  async function fetchTransports() {
    const { data } = await api.get('/throttling/transports')
    transports.value = data
  }

  async function createTransport(body: Omit<TransportRule, 'id'>) {
    const { data } = await api.post('/throttling/transports', body)
    await fetchTransports()
    return data
  }

  async function updateTransport(id: number, body: Partial<TransportRule>) {
    const { data } = await api.put(`/throttling/transports/${id}`, body)
    await fetchTransports()
    return data
  }

  async function deleteTransport(id: number) {
    await api.delete(`/throttling/transports/${id}`)
    await fetchTransports()
  }

  async function fetchMetrics() {
    const { data } = await api.get('/throttling/metrics')
    metrics.value = data
  }

  async function fetchAll() {
    loading.value = true
    try {
      await Promise.all([fetchConfig(), fetchWarmup(), fetchPhases(), fetchTransports(), fetchMetrics()])
    } finally {
      loading.value = false
    }
  }

  return {
    config, warmup, phases, transports, metrics, loading,
    fetchConfig, updateConfig,
    fetchWarmup, setWarmupPhase, resetWarmup,
    fetchPhases, updatePhase,
    fetchTransports, createTransport, updateTransport, deleteTransport,
    fetchMetrics, fetchAll,
  }
})
