import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import api from '../api/client'

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

interface RetentionSettings {
  retention_days: number
  stats_retention_days: number
}

export const useProtokollStore = defineStore('protokoll', () => {
  const events = ref<MailEvent[]>([])
  const total = ref(0)
  const page = ref(1)
  const perPage = ref(50)
  const pages = ref(1)
  const loading = ref(false)

  const filters = reactive({
    status: '' as string,
    search: '' as string,
    dateFrom: '' as string,
    dateTo: '' as string,
  })

  const retention = ref<RetentionSettings>({ retention_days: 30, stats_retention_days: 365 })

  function _buildParams() {
    const params: Record<string, string | number> = {
      page: page.value,
      per_page: perPage.value,
    }
    if (filters.status) params.status = filters.status
    if (filters.search) params.search = filters.search
    if (filters.dateFrom) params.date_from = filters.dateFrom
    if (filters.dateTo) params.date_to = filters.dateTo
    return params
  }

  async function fetchEvents() {
    loading.value = true
    try {
      const { data } = await api.get('/logs/events', { params: _buildParams() })
      events.value = data.items
      total.value = data.total
      pages.value = data.pages
      page.value = data.page
    } finally {
      loading.value = false
    }
  }

  function applyFilters() {
    page.value = 1
    return fetchEvents()
  }

  function resetFilters() {
    filters.status = ''
    filters.search = ''
    filters.dateFrom = ''
    filters.dateTo = ''
    page.value = 1
    return fetchEvents()
  }

  function setPage(p: number) {
    page.value = p
    return fetchEvents()
  }

  async function exportCsv() {
    const params: Record<string, string> = {}
    if (filters.status) params.status = filters.status
    if (filters.search) params.search = filters.search
    if (filters.dateFrom) params.date_from = filters.dateFrom
    if (filters.dateTo) params.date_to = filters.dateTo

    const { data } = await api.get('/logs/events/export', {
      params,
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'mail_events.csv'
    a.click()
    window.URL.revokeObjectURL(url)
  }

  async function fetchRetention() {
    const { data } = await api.get('/logs/retention')
    retention.value = data
  }

  async function updateRetention(vals: { retention_days?: number; stats_retention_days?: number }) {
    const { data } = await api.put('/logs/retention', vals)
    retention.value = data
  }

  return {
    events, total, page, perPage, pages, loading, filters, retention,
    fetchEvents, applyFilters, resetFilters, setPage, exportCsv,
    fetchRetention, updateRetention,
  }
})
