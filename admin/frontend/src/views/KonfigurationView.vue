<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import api from '../api/client'
import ServerConfigCard from '../components/config/ServerConfig.vue'
import TlsStatusCard from '../components/config/TlsStatus.vue'
import ConnectionInfoCard from '../components/config/ConnectionInfo.vue'
import RetentionSettings from '../components/config/RetentionSettings.vue'
import t from '../i18n/de'

const toast = useToast()

const config = ref<any>(null)
const tls = ref<any>(null)
const connection = ref<any>(null)
const loading = ref(false)
const syncing = ref(false)
const saving = ref(false)
const savingSteps = ref<{ step: string; success: boolean; detail: string }[]>([])

async function fetchConfig() {
  loading.value = true
  try {
    const [configRes, tlsRes, connRes] = await Promise.all([
      api.get('/config'),
      api.get('/config/tls'),
      api.get('/config/connection'),
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
  try {
    const { data: res } = await api.put('/config', data)
    const steps = res.steps || []
    savingSteps.value = steps

    const allOk = steps.every((s: any) => s.success)
    if (allOk) {
      toast.add({ severity: 'success', summary: t.common.success, detail: res.message, life: 5000 })
    } else {
      toast.add({ severity: 'warn', summary: t.common.success, detail: res.message, life: 8000 })
    }
    await fetchConfig()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    saving.value = false
  }
}

async function reloadPostfix() {
  try {
    await api.post('/config/reload')
    toast.add({ severity: 'success', summary: t.common.success, detail: 'Postfix neu geladen', life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function syncTlsCert() {
  syncing.value = true
  try {
    const { data } = await api.post('/config/tls/sync')
    toast.add({ severity: 'success', summary: t.common.success, detail: data.message, life: 5000 })
    await fetchConfig()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    syncing.value = false
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
        @sync="syncTlsCert"
      />
      <RetentionSettings />
    </div>
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
