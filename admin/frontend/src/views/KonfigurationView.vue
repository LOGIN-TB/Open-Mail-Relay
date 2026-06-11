<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import api from '../api/client'
import { useApi, apiErrorDetail } from '../composables/useApi'
import ServerConfigCard from '../components/config/ServerConfig.vue'
import TlsStatusCard from '../components/config/TlsStatus.vue'
import ConnectionInfoCard from '../components/config/ConnectionInfo.vue'
import RetentionSettings from '../components/config/RetentionSettings.vue'
import TimezoneSettings from '../components/config/TimezoneSettings.vue'
import AbusePageSettings from '../components/config/AbusePageSettings.vue'
import PortalApiSettings from '../components/config/PortalApiSettings.vue'
import ContainerManager from '../components/config/ContainerManager.vue'
import t from '../i18n/de'

interface StepStatus {
  step: string
  success: boolean
  detail: string
}

interface ServerConfigData {
  hostname: string
  domain: string
  relay_domains: string
  message_size_limit: number
  mynetworks_count: number
}

interface TlsCertInfo {
  name: string
  role: string
  exists: boolean
  subject: string | null
  issuer: string | null
  expiry: string | null
  days_remaining: number | null
  status: string
  is_postfix_cert: boolean
}

interface TlsStatusData {
  enabled: boolean
  cert_exists: boolean
  cert_expiry: string | null
  cert_subject: string | null
  postfix_has_cert: boolean
  certs: TlsCertInfo[]
}

interface PortInfo {
  port: number
  protocol: string
  tls_mode: string
  tls_required: boolean
}

interface ConnectionInfoData {
  smtp_host: string
  ports: PortInfo[]
  auth_required: boolean
  tls_available: boolean
  allowed_networks: string[]
  max_message_size_mb: number
}

interface ConfigUpdateResult {
  message: string
  steps?: StepStatus[]
}

const toast = useToast()
const { call } = useApi()

const config = ref<ServerConfigData | null>(null)
const tls = ref<TlsStatusData | null>(null)
const connection = ref<ConnectionInfoData | null>(null)
const loading = ref(false)
const syncing = ref(false)
const renewing = ref(false)
const saving = ref(false)
const savingSteps = ref<StepStatus[]>([])

async function fetchConfig() {
  loading.value = true
  try {
    const [configRes, tlsRes, connRes] = await Promise.all([
      api.get<ServerConfigData>('/config'),
      api.get<TlsStatusData>('/config/tls'),
      api.get<ConnectionInfoData>('/config/connection'),
    ])
    config.value = configRes.data
    tls.value = tlsRes.data
    connection.value = connRes.data
  } finally {
    loading.value = false
  }
}

async function updateConfig(data: { hostname?: string; domain?: string }) {
  saving.value = true
  savingSteps.value = []
  const res = await call(() => api.put<ConfigUpdateResult>('/config', data))
  if (res !== null) {
    const steps = res.steps || []
    savingSteps.value = steps

    const allOk = steps.every((s) => s.success)
    if (allOk) {
      toast.add({ severity: 'success', summary: t.common.success, detail: res.message, life: 5000 })
    } else {
      toast.add({ severity: 'warn', summary: t.common.success, detail: res.message, life: 8000 })
    }
    await fetchConfig()
  }
  saving.value = false
}

async function reloadPostfix() {
  await call(() => api.post('/config/reload'), { success: 'Postfix neu geladen' })
}

async function syncTlsCert() {
  syncing.value = true
  const data = await call(() => api.post<{ message: string }>('/config/tls/sync'))
  if (data !== null) {
    toast.add({ severity: 'success', summary: t.common.success, detail: data.message, life: 5000 })
    await fetchConfig()
  }
  syncing.value = false
}

async function renewTlsCert() {
  renewing.value = true
  try {
    const { data } = await api.post<{ message: string }>('/config/tls/renew')
    toast.add({ severity: 'success', summary: t.common.success, detail: data.message, life: 6000 })
    await fetchConfig()
  } catch (e) {
    toast.add({ severity: 'error', summary: t.common.error, detail: apiErrorDetail(e), life: 8000 })
  } finally {
    renewing.value = false
  }
}

onMounted(fetchConfig)
</script>

<template>
  <div class="config-page">
    <h2>{{ t.config.title }}</h2>

    <!-- Verbindungseinstellungen oben, volle Breite -->
    <ConnectionInfoCard :connection="connection" :loading="loading" />

    <div class="config-grid">
      <ServerConfigCard
        :config="config"
        :loading="loading"
        :saving="saving"
        :savingSteps="savingSteps"
        @update="updateConfig"
        @reload="reloadPostfix"
      />
      <TlsStatusCard
        :tls="tls"
        :loading="loading"
        :syncing="syncing"
        :renewing="renewing"
        @sync="syncTlsCert"
        @renew="renewTlsCert"
      />
      <RetentionSettings />
      <TimezoneSettings />
    </div>

    <AbusePageSettings />
    <PortalApiSettings />
    <ContainerManager />
  </div>
</template>

<style scoped>
.config-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-page h2 {
  font-size: 1.5rem;
  color: #1e293b;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 1024px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
