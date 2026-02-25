<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../../api/client'
import t from '../../i18n/de'

interface WarmupInfo {
  enabled: boolean
  phase_name: string
  percent_complete: number
  days_remaining: number
  is_established: boolean
  held_count: number
}

const info = ref<WarmupInfo | null>(null)

async function fetchInfo() {
  try {
    const [configRes, warmupRes, metricsRes] = await Promise.all([
      api.get('/throttling/config'),
      api.get('/throttling/warmup'),
      api.get('/throttling/metrics'),
    ])
    if (!configRes.data.enabled) {
      info.value = null
      return
    }
    info.value = {
      enabled: true,
      phase_name: warmupRes.data.phase_name,
      percent_complete: warmupRes.data.percent_complete,
      days_remaining: warmupRes.data.days_remaining,
      is_established: warmupRes.data.is_established,
      held_count: metricsRes.data.held_count,
    }
  } catch {
    info.value = null
  }
}

onMounted(fetchInfo)
</script>

<template>
  <div v-if="info" class="warmup-card">
    <div class="warmup-icon">
      <i class="pi pi-gauge"></i>
    </div>
    <div class="warmup-content">
      <div class="warmup-header">
        <span class="warmup-title">{{ t.throttling.warmupStatus }}</span>
        <span class="warmup-phase">{{ info.phase_name }}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: info.percent_complete + '%' }"></div>
      </div>
      <div class="warmup-footer">
        <span v-if="!info.is_established">{{ info.days_remaining }} {{ t.throttling.daysRemainingShort }}</span>
        <span v-else class="established">{{ t.throttling.established }}</span>
        <span v-if="info.held_count > 0" class="held-count">
          {{ info.held_count }} {{ t.throttling.held }}
        </span>
      </div>
    </div>
    <router-link to="/drosselung" class="warmup-link">
      <i class="pi pi-arrow-right"></i>
    </router-link>
  </div>
</template>

<style scoped>
.warmup-card {
  background: white;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  border-left: 4px solid #3b82f6;
}

.warmup-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #eff6ff;
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  flex-shrink: 0;
}

.warmup-content {
  flex: 1;
  min-width: 0;
}

.warmup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.warmup-title {
  font-weight: 600;
  color: #1e293b;
  font-size: 0.9rem;
}

.warmup-phase {
  font-size: 0.8rem;
  color: #3b82f6;
  font-weight: 600;
}

.progress-track {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #22c55e);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.warmup-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 0.35rem;
  font-size: 0.75rem;
  color: #64748b;
}

.established {
  color: #22c55e;
  font-weight: 600;
}

.held-count {
  color: #d97706;
  font-weight: 600;
}

.warmup-link {
  color: #94a3b8;
  font-size: 1.1rem;
  padding: 0.25rem;
  flex-shrink: 0;
}

.warmup-link:hover {
  color: #3b82f6;
}
</style>
