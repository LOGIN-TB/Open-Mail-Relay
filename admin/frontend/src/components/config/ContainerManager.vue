<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import api from '../../api/client'
import t from '../../i18n/de'

const toast = useToast()
const containers = ref<any[]>([])
const loading = ref(false)
const restartingMap = ref<Record<string, boolean>>({})

const LABELS: Record<string, string> = {
  'open-mail-relay': 'Mail-Server (Postfix + OpenDKIM)',
  'caddy': 'Webserver (Caddy)',
  'firewall': 'Firewall (iptables/ipset)',
}

const ICONS: Record<string, string> = {
  'open-mail-relay': 'pi pi-envelope',
  'caddy': 'pi pi-globe',
  'firewall': 'pi pi-shield',
}

async function fetchContainers() {
  loading.value = true
  try {
    const { data } = await api.get('/config/containers')
    containers.value = data
  } finally {
    loading.value = false
  }
}

async function restartContainer(name: string) {
  restartingMap.value[name] = true
  try {
    const { data } = await api.post(`/config/containers/${name}/restart`)
    toast.add({ severity: 'success', summary: t.common.success, detail: data.message, life: 3000 })
    // Wait briefly for container to come back up
    setTimeout(fetchContainers, 3000)
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    restartingMap.value[name] = false
  }
}

function formatTime(ts: string): string {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString('de-DE')
  } catch {
    return ts
  }
}

onMounted(fetchContainers)
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3>{{ t.config.containers }}</h3>
      <button class="btn btn-sm btn-secondary" @click="fetchContainers" :disabled="loading">
        <i :class="loading ? 'pi pi-spin pi-spinner' : 'pi pi-refresh'"></i>
      </button>
    </div>

    <div class="container-list">
      <div v-for="c in containers" :key="c.name" class="container-row">
        <div class="container-info">
          <i :class="ICONS[c.label] || 'pi pi-box'" class="container-icon"></i>
          <div class="container-details">
            <span class="container-name">{{ LABELS[c.label] || c.name }}</span>
            <span class="container-meta">{{ c.name }}</span>
          </div>
        </div>
        <div class="container-status">
          <span class="status-dot" :class="c.running ? 'dot-running' : 'dot-stopped'"></span>
          <span class="status-text">{{ c.running ? t.config.containerRunning : t.config.containerStopped }}</span>
        </div>
        <div class="container-started" v-if="c.started_at">
          {{ formatTime(c.started_at) }}
        </div>
        <button
          class="btn btn-sm btn-warning"
          @click="restartContainer(c.name)"
          :disabled="restartingMap[c.name]"
          :title="t.config.containerRestart"
        >
          <i :class="restartingMap[c.name] ? 'pi pi-spin pi-spinner' : 'pi pi-replay'"></i>
          {{ t.config.containerRestart }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.container-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.container-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.container-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.container-icon {
  font-size: 1.1rem;
  color: #475569;
  flex-shrink: 0;
}

.container-details {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.container-name {
  font-weight: 500;
  font-size: 0.9rem;
  color: #1e293b;
}

.container-meta {
  font-size: 0.75rem;
  color: #94a3b8;
  font-family: monospace;
}

.container-status {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-running {
  background: #22c55e;
  box-shadow: 0 0 4px rgba(34, 197, 94, 0.5);
}

.dot-stopped {
  background: #ef4444;
}

.status-text {
  font-size: 0.8rem;
  color: #64748b;
}

.container-started {
  font-size: 0.75rem;
  color: #94a3b8;
  flex-shrink: 0;
  display: none;
}

@media (min-width: 768px) {
  .container-started {
    display: block;
  }
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.65rem;
  border: none;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #e2e8f0;
  color: #475569;
}

.btn-secondary:hover:not(:disabled) {
  background: #cbd5e1;
}

.btn-warning {
  background: #f59e0b;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #d97706;
}

.btn-sm {
  padding: 0.35rem 0.65rem;
  font-size: 0.8rem;
}
</style>
