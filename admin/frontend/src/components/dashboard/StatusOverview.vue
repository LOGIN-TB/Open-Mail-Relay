<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import t from '../../i18n/de'

const router = useRouter()

const props = defineProps<{
  rblStatus: { enabled: boolean; last_check_time: string; total_listings: number; all_clean: boolean } | null
  dnsStatus: { checked: boolean; all_ok: boolean; issues: number; last_check_time: string } | null
}>()

// Warmup data (fetched internally like the old WarmupStatusCard)
const warmup = ref<{
  enabled: boolean
  phase_name: string
  percent_complete: number
  days_remaining: number
  is_established: boolean
  held_count: number
} | null>(null)

async function fetchWarmup() {
  try {
    const [configRes, warmupRes, metricsRes] = await Promise.all([
      api.get('/throttling/config'),
      api.get('/throttling/warmup'),
      api.get('/throttling/metrics'),
    ])
    if (!configRes.data.enabled) {
      warmup.value = null
      return
    }
    warmup.value = {
      enabled: true,
      phase_name: warmupRes.data.phase_name,
      percent_complete: warmupRes.data.percent_complete,
      days_remaining: warmupRes.data.days_remaining,
      is_established: warmupRes.data.is_established,
      held_count: metricsRes.data.held_count,
    }
  } catch {
    warmup.value = null
  }
}

// Computed helpers
function formatTime(ts: string): string {
  if (!ts) return ''
  try {
    return new Date(ts).toLocaleString('de-DE')
  } catch {
    return ts
  }
}

const warmupBorder = computed(() => {
  if (!warmup.value) return '#94a3b8'
  if (warmup.value.is_established) return '#22c55e'
  return '#3b82f6'
})

const rblBorder = computed(() => {
  if (!props.rblStatus?.last_check_time) return '#94a3b8'
  return props.rblStatus.all_clean ? '#22c55e' : '#ef4444'
})

const dnsBorder = computed(() => {
  if (!props.dnsStatus?.checked) return '#94a3b8'
  return props.dnsStatus.all_ok ? '#22c55e' : '#ef4444'
})

onMounted(fetchWarmup)

defineExpose({ fetchWarmup })
</script>

<template>
  <div class="status-grid">
    <!-- Warmup -->
    <div
      class="status-card"
      :style="{ borderLeftColor: warmupBorder }"
      @click="router.push('/drosselung')"
    >
      <div class="status-icon" :style="{ background: warmup ? '#eff6ff' : '#f8fafc', color: warmup ? '#3b82f6' : '#94a3b8' }">
        <i class="pi pi-gauge"></i>
      </div>
      <div class="status-body">
        <span class="status-label">{{ t.throttling.warmupStatus }}</span>
        <template v-if="warmup">
          <span class="status-detail">{{ warmup.phase_name }}</span>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: warmup.percent_complete + '%' }"></div>
          </div>
          <span class="status-meta">
            <template v-if="!warmup.is_established">{{ warmup.days_remaining }} {{ t.throttling.daysRemainingShort }}</template>
            <template v-else>{{ t.throttling.established }}</template>
            <span v-if="warmup.held_count > 0" class="held-badge">{{ warmup.held_count }} {{ t.throttling.held }}</span>
          </span>
        </template>
        <span v-else class="status-detail muted">{{ t.throttling.inactive }}</span>
      </div>
      <i class="pi pi-angle-right status-arrow"></i>
    </div>

    <!-- RBL -->
    <div
      class="status-card"
      :style="{ borderLeftColor: rblBorder }"
      @click="router.push('/rbl-pruefung')"
    >
      <div class="status-icon" :style="{
        background: !rblStatus?.last_check_time ? '#f8fafc' : rblStatus.all_clean ? '#f0fdf4' : '#fef2f2',
        color: !rblStatus?.last_check_time ? '#94a3b8' : rblStatus.all_clean ? '#166534' : '#991b1b'
      }">
        <i :class="!rblStatus?.last_check_time ? 'pi pi-shield' : rblStatus.all_clean ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'"></i>
      </div>
      <div class="status-body">
        <span class="status-label">{{ t.dashboard.rblCheck }}</span>
        <span v-if="!rblStatus?.last_check_time" class="status-detail muted">{{ t.dashboard.rblNoCheck }}</span>
        <span v-else-if="rblStatus.all_clean" class="status-detail ok">{{ t.dashboard.rblClean }}</span>
        <span v-else class="status-detail warn">{{ rblStatus.total_listings }} {{ t.dashboard.rblListings }}</span>
        <span v-if="rblStatus?.last_check_time" class="status-meta">{{ formatTime(rblStatus.last_check_time) }}</span>
      </div>
      <i class="pi pi-angle-right status-arrow"></i>
    </div>

    <!-- DNS -->
    <div
      class="status-card"
      :style="{ borderLeftColor: dnsBorder }"
      @click="router.push('/dns-pruefung')"
    >
      <div class="status-icon" :style="{
        background: !dnsStatus?.checked ? '#f8fafc' : dnsStatus.all_ok ? '#f0fdf4' : '#fef2f2',
        color: !dnsStatus?.checked ? '#94a3b8' : dnsStatus.all_ok ? '#166534' : '#991b1b'
      }">
        <i :class="!dnsStatus?.checked ? 'pi pi-globe' : dnsStatus.all_ok ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'"></i>
      </div>
      <div class="status-body">
        <span class="status-label">{{ t.dashboard.dnsCheck }}</span>
        <span v-if="!dnsStatus?.checked" class="status-detail muted">{{ t.dashboard.dnsNoCheck }}</span>
        <span v-else-if="dnsStatus.all_ok" class="status-detail ok">{{ t.dashboard.dnsAllOk }}</span>
        <span v-else class="status-detail warn">{{ dnsStatus.issues }} {{ t.dashboard.dnsIssues }}</span>
        <span v-if="dnsStatus?.last_check_time" class="status-meta">{{ formatTime(dnsStatus.last_check_time) }}</span>
      </div>
      <i class="pi pi-angle-right status-arrow"></i>
    </div>
  </div>
</template>

<style scoped>
.status-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.status-card {
  background: white;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  border-left: 4px solid #94a3b8;
  cursor: pointer;
  transition: box-shadow 0.15s;
}

.status-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.status-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.status-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 0.15rem;
}

.status-label {
  font-weight: 600;
  font-size: 0.85rem;
  color: #1e293b;
}

.status-detail {
  font-size: 0.8rem;
  color: #334155;
}

.status-detail.muted {
  color: #94a3b8;
}

.status-detail.ok {
  color: #166534;
}

.status-detail.warn {
  color: #991b1b;
}

.status-meta {
  font-size: 0.7rem;
  color: #94a3b8;
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.held-badge {
  color: #d97706;
  font-weight: 600;
}

.progress-track {
  height: 4px;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
  margin-top: 0.1rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #22c55e);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.status-arrow {
  color: #cbd5e1;
  font-size: 1rem;
  flex-shrink: 0;
}

@media (max-width: 900px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
