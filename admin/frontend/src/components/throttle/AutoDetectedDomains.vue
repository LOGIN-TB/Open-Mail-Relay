<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { ThrottleConfig } from '../../stores/throttle'
import { useThrottleStore } from '../../stores/throttle'
import t from '../../i18n/de'

const props = defineProps<{
  config: ThrottleConfig | null
}>()

const toast = useToast()
const store = useThrottleStore()
const expanded = ref(false)
const togglingAutodetect = ref(false)

const enabled = computed(() => props.config?.mx_autodetect ?? false)

// Count per provider, e.g. { microsoft: 230, google: 19, yahoo: 4 }
const byProvider = computed(() => {
  const counts: Record<string, number> = {}
  for (const d of store.autoDetected) {
    counts[d.provider] = (counts[d.provider] ?? 0) + 1
  }
  return counts
})

const providerLabels: Record<string, string> = {
  microsoft: 'Microsoft 365',
  google: 'Google Workspace',
  yahoo: 'Yahoo',
}

onMounted(() => {
  if (enabled.value) store.fetchAutoDetected()
})

async function toggleAutodetect() {
  togglingAutodetect.value = true
  try {
    const next = !enabled.value
    await store.updateConfig({ mx_autodetect: next })
    if (next) {
      await store.fetchAutoDetected()
    } else {
      store.autoDetected.length = 0
    }
    toast.add({ severity: 'success', summary: t.common.success, detail: t.throttling.settingsSaved, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    togglingAutodetect.value = false
  }
}

async function refresh() {
  try {
    await store.fetchAutoDetected()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3>{{ t.throttling.autoDetected }}</h3>
      <label class="switch">
        <input type="checkbox" :checked="enabled" :disabled="togglingAutodetect" @change="toggleAutodetect" />
        <span class="slider"></span>
        <span class="switch-label">{{ t.throttling.autoDetectToggle }}</span>
      </label>
    </div>
    <div class="card-body">
      <div class="info-box">
        <i class="pi pi-info-circle"></i>
        <span>{{ t.throttling.autoDetectInfo }}</span>
      </div>

      <p v-if="!enabled" class="muted">{{ t.throttling.autoDetectDisabled }}</p>

      <template v-else>
        <div class="summary">
          <span v-for="(count, prov) in byProvider" :key="prov" class="provider-chip" :class="prov">
            {{ providerLabels[prov] ?? prov }}: <strong>{{ count }}</strong>
          </span>
          <button class="btn btn-sm refresh-btn" :disabled="store.autoDetectedLoading" @click="refresh">
            <i class="pi" :class="store.autoDetectedLoading ? 'pi-spin pi-spinner' : 'pi-refresh'"></i>
            {{ t.throttling.refresh }}
          </button>
          <button v-if="store.autoDetected.length" class="btn btn-sm" @click="expanded = !expanded">
            <i class="pi" :class="expanded ? 'pi-chevron-up' : 'pi-chevron-down'"></i>
            {{ store.autoDetected.length }}
          </button>
        </div>

        <p v-if="!store.autoDetectedLoading && !store.autoDetected.length" class="muted">
          {{ t.throttling.autoDetectEmpty }}
        </p>

        <div v-if="expanded && store.autoDetected.length" class="table-wrap">
          <table class="transport-table">
            <thead>
              <tr>
                <th>{{ t.throttling.domain }}</th>
                <th>{{ t.throttling.transport }}</th>
                <th>{{ t.throttling.source }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in store.autoDetected" :key="d.domain">
                <td class="domain">{{ d.domain }}</td>
                <td>{{ d.transport_name }}</td>
                <td><span class="source-badge" :class="d.source">{{ d.source }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.card-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #1e293b;
}

.card-body {
  padding: 1rem 1.25rem;
}

.info-box {
  padding: 0.75rem 1rem;
  background: #eff6ff;
  border-radius: 8px;
  font-size: 0.85rem;
  color: #1e40af;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.info-box i {
  margin-top: 2px;
  flex-shrink: 0;
}

.muted {
  color: #64748b;
  font-size: 0.875rem;
  margin: 1rem 0 0;
}

.summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
}

.provider-chip {
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  font-size: 0.8rem;
  background: #f1f5f9;
  color: #475569;
}

.provider-chip.microsoft {
  background: #e0ecff;
  color: #1e40af;
}

.provider-chip.google {
  background: #e6f4ea;
  color: #1e7e34;
}

.provider-chip.yahoo {
  background: #f3e8ff;
  color: #7e22ce;
}

.refresh-btn {
  margin-left: auto;
}

.table-wrap {
  margin-top: 1rem;
  max-height: 420px;
  overflow: auto;
}

.transport-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.transport-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  color: #64748b;
  font-weight: 600;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
  position: sticky;
  top: 0;
  background: white;
}

.transport-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.domain {
  font-weight: 600;
  font-family: monospace;
}

.source-badge {
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 600;
  background: #f1f5f9;
  color: #64748b;
}

.source-badge.mx {
  background: #dcfce7;
  color: #16a34a;
}

.source-badge.relay {
  background: #fef9c3;
  color: #a16207;
}

.source-badge.cache {
  background: #e0f2fe;
  color: #0369a1;
}

.switch {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  white-space: nowrap;
}

.switch input {
  display: none;
}

.slider {
  width: 38px;
  height: 20px;
  background: #cbd5e1;
  border-radius: 999px;
  position: relative;
  transition: background 0.15s;
  flex-shrink: 0;
}

.slider::before {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  left: 2px;
  top: 2px;
  background: white;
  border-radius: 50%;
  transition: transform 0.15s;
}

.switch input:checked + .slider {
  background: #3b82f6;
}

.switch input:checked + .slider::before {
  transform: translateX(18px);
}

.switch-label {
  font-size: 0.85rem;
  color: #475569;
  font-weight: 600;
}

.btn {
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: white;
  color: #475569;
  cursor: pointer;
  font-size: 0.8rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.btn-sm {
  padding: 0.25rem 0.6rem;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
