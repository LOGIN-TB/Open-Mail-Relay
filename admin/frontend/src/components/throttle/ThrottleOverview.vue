<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { ThrottleConfig, WarmupStatus, ThrottleMetrics } from '../../stores/throttle'
import { useThrottleStore } from '../../stores/throttle'
import t from '../../i18n/de'

defineProps<{
  config: ThrottleConfig | null
  warmup: WarmupStatus | null
  metrics: ThrottleMetrics | null
}>()

const toast = useToast()
const store = useThrottleStore()
const toggling = ref(false)

async function toggleEnabled() {
  if (!store.config) return
  toggling.value = true
  try {
    const result = await store.updateConfig({ enabled: !store.config.enabled })
    await store.fetchAll()
    const steps = result.steps || []
    const allOk = steps.every((s: any) => s.success)
    toast.add({
      severity: allOk ? 'success' : 'warn',
      summary: t.common.success,
      detail: result.message,
      life: 5000,
    })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  } finally {
    toggling.value = false
  }
}
</script>

<template>
  <div class="card overview-card">
    <div class="card-header">
      <h3>{{ t.throttling.overview }}</h3>
    </div>
    <div class="overview-content" v-if="config">
      <div class="toggle-row">
        <label class="toggle-label">{{ t.throttling.enabled }}</label>
        <button
          class="toggle-btn"
          :class="{ active: config.enabled }"
          :disabled="toggling"
          @click="toggleEnabled"
        >
          {{ config.enabled ? t.throttling.active : t.throttling.inactive }}
        </button>
      </div>

      <template v-if="warmup">
        <div class="warmup-bar">
          <div class="warmup-bar-header">
            <span class="phase-name">{{ warmup.phase_name }}</span>
            <span class="phase-percent">{{ warmup.percent_complete }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: warmup.percent_complete + '%' }"></div>
          </div>
          <div class="warmup-info">
            <span>{{ t.throttling.daysElapsed }}: {{ warmup.days_elapsed }}</span>
            <span v-if="!warmup.is_established">{{ t.throttling.daysRemaining }}: {{ warmup.days_remaining }}</span>
            <span v-else class="established">{{ t.throttling.established }}</span>
          </div>
        </div>
      </template>

      <div class="metrics-row" v-if="metrics">
        <div class="metric">
          <div class="metric-value">{{ metrics.sent_today }}</div>
          <div class="metric-label">{{ t.throttling.sentToday }}</div>
          <div class="metric-limit" v-if="metrics.limits">/ {{ metrics.limits.max_per_day }}</div>
        </div>
        <div class="metric">
          <div class="metric-value">{{ metrics.sent_this_hour }}</div>
          <div class="metric-label">{{ t.throttling.sentThisHour }}</div>
          <div class="metric-limit" v-if="metrics.limits">/ {{ metrics.limits.max_per_hour }}</div>
        </div>
        <div class="metric" :class="{ warn: metrics.held_count > 0 }">
          <div class="metric-value">{{ metrics.held_count }}</div>
          <div class="metric-label">{{ t.throttling.held }}</div>
        </div>
      </div>
    </div>
    <div v-else class="loading">{{ t.common.loading }}</div>
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
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #1e293b;
}

.overview-content {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.toggle-label {
  font-weight: 600;
  color: #1e293b;
}

.toggle-btn {
  padding: 0.5rem 1.25rem;
  border-radius: 8px;
  border: 2px solid #e2e8f0;
  background: #f8fafc;
  color: #64748b;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.toggle-btn.active {
  background: #22c55e;
  border-color: #22c55e;
  color: white;
}

.toggle-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.warmup-bar-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.phase-name {
  font-weight: 600;
  color: #1e293b;
}

.phase-percent {
  color: #3b82f6;
  font-weight: 600;
}

.progress-track {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #22c55e);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.warmup-info {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #64748b;
}

.established {
  color: #22c55e;
  font-weight: 600;
}

.metrics-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.metric {
  text-align: center;
  padding: 0.75rem;
  background: #f8fafc;
  border-radius: 8px;
}

.metric.warn {
  background: #fef3c7;
}

.metric-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
}

.metric.warn .metric-value {
  color: #d97706;
}

.metric-label {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 2px;
}

.metric-limit {
  font-size: 0.75rem;
  color: #94a3b8;
}

.loading {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}
</style>
