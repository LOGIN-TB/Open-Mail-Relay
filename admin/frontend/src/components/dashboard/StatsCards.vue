<script setup lang="ts">
import t from '../../i18n/de'

defineProps<{
  stats: {
    sent_today: number
    deferred_today: number
    bounced_today: number
    rejected_today: number
    auth_failed_today: number
    queue_size: number
    success_rate: number
  } | null
  loading: boolean
}>()

const cards = [
  { key: 'sent_today', label: t.dashboard.sent, icon: 'pi pi-send', color: '#22c55e' },
  { key: 'deferred_today', label: t.dashboard.deferred, icon: 'pi pi-clock', color: '#f59e0b' },
  { key: 'bounced_today', label: t.dashboard.bounced, icon: 'pi pi-times-circle', color: '#ef4444' },
  { key: 'rejected_today', label: t.dashboard.rejected, icon: 'pi pi-ban', color: '#8b5cf6' },
  { key: 'auth_failed_today', label: t.dashboard.authFailed, icon: 'pi pi-shield', color: '#dc2626' },
  { key: 'queue_size', label: t.dashboard.queue, icon: 'pi pi-list', color: '#3b82f6' },
  { key: 'success_rate', label: t.dashboard.successRate, icon: 'pi pi-check-circle', color: '#06b6d4', suffix: '%' },
]
</script>

<template>
  <div class="stats-grid">
    <div v-for="card in cards" :key="card.key" class="stat-card">
      <div class="stat-icon" :style="{ background: card.color + '15', color: card.color }">
        <i :class="card.icon"></i>
      </div>
      <div class="stat-info">
        <div class="stat-value">
          <template v-if="stats">{{ (stats as any)[card.key] }}{{ card.suffix ?? '' }}</template>
          <template v-else>-</template>
        </div>
        <div class="stat-label">{{ card.label }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  flex-shrink: 0;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
}

.stat-label {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 2px;
}
</style>
