<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'
import api from '../api/client'
import StatsCards from '../components/dashboard/StatsCards.vue'
import DeliveryChart from '../components/dashboard/DeliveryChart.vue'
import QueueStatus from '../components/dashboard/QueueStatus.vue'
import RecentActivity from '../components/dashboard/RecentActivity.vue'
import WarmupStatusCard from '../components/dashboard/WarmupStatusCard.vue'
import t from '../i18n/de'

const router = useRouter()
const dashboard = useDashboardStore()
const bannedIps = ref<Set<string>>(new Set())
const rblStatus = ref<{ enabled: boolean; last_check_time: string; total_listings: number; all_clean: boolean } | null>(null)
const dnsStatus = ref<{ checked: boolean; all_ok: boolean; issues: number; last_check_time: string } | null>(null)

async function fetchBannedIps() {
  try {
    const { data } = await api.get('/ip-bans')
    bannedIps.value = new Set(data.filter((b: any) => b.is_active).map((b: any) => b.ip_address))
  } catch {
    // ignore – badge simply won't show
  }
}

async function fetchRblStatus() {
  try {
    const { data } = await api.get('/rbl/status')
    rblStatus.value = data
  } catch {
    // ignore
  }
}

async function fetchDnsStatus() {
  try {
    const { data } = await api.get('/dns-check/status')
    dnsStatus.value = data
  } catch {
    // ignore
  }
}

const dnsCheckTime = computed(() => {
  if (!dnsStatus.value?.last_check_time) return ''
  try {
    return new Date(dnsStatus.value.last_check_time).toLocaleString('de-DE')
  } catch {
    return dnsStatus.value.last_check_time
  }
})

const rblCheckTime = computed(() => {
  if (!rblStatus.value?.last_check_time) return ''
  try {
    return new Date(rblStatus.value.last_check_time).toLocaleString('de-DE')
  } catch {
    return rblStatus.value.last_check_time
  }
})

let refreshInterval: ReturnType<typeof setInterval>

onMounted(() => {
  dashboard.fetchAll()
  fetchBannedIps()
  fetchRblStatus()
  fetchDnsStatus()
  refreshInterval = setInterval(() => {
    dashboard.fetchAll()
    fetchBannedIps()
    fetchRblStatus()
    fetchDnsStatus()
  }, 30000)
})

onUnmounted(() => {
  clearInterval(refreshInterval)
})
</script>

<template>
  <div class="dashboard">
    <h2>{{ t.dashboard.title }}</h2>

    <WarmupStatusCard />

    <!-- RBL Status Card -->
    <div class="rbl-status-card" :class="rblStatus?.last_check_time ? (rblStatus.all_clean ? 'rbl-clean' : 'rbl-warn') : 'rbl-neutral'" @click="router.push('/rbl-pruefung')">
      <div class="rbl-status-icon">
        <i v-if="!rblStatus?.last_check_time" class="pi pi-shield" style="color: #94a3b8"></i>
        <i v-else-if="rblStatus.all_clean" class="pi pi-check-circle" style="color: #166534"></i>
        <i v-else class="pi pi-exclamation-triangle" style="color: #991b1b"></i>
      </div>
      <div class="rbl-status-text">
        <span class="rbl-status-label">{{ t.dashboard.rblCheck }}</span>
        <span v-if="!rblStatus?.last_check_time" class="rbl-status-detail">{{ t.dashboard.rblNoCheck }}</span>
        <span v-else-if="rblStatus.all_clean" class="rbl-status-detail">{{ t.dashboard.rblClean }}</span>
        <span v-else class="rbl-status-detail">{{ rblStatus.total_listings }} {{ t.dashboard.rblListings }}</span>
      </div>
      <div v-if="rblCheckTime" class="rbl-status-time">{{ rblCheckTime }}</div>
      <i class="pi pi-angle-right rbl-status-arrow"></i>
    </div>

    <!-- DNS Status Card -->
    <div class="rbl-status-card" :class="dnsStatus?.checked ? (dnsStatus.all_ok ? 'rbl-clean' : 'rbl-warn') : 'rbl-neutral'" @click="router.push('/dns-pruefung')">
      <div class="rbl-status-icon">
        <i v-if="!dnsStatus?.checked" class="pi pi-globe" style="color: #94a3b8"></i>
        <i v-else-if="dnsStatus.all_ok" class="pi pi-check-circle" style="color: #166534"></i>
        <i v-else class="pi pi-exclamation-triangle" style="color: #991b1b"></i>
      </div>
      <div class="rbl-status-text">
        <span class="rbl-status-label">{{ t.dashboard.dnsCheck }}</span>
        <span v-if="!dnsStatus?.checked" class="rbl-status-detail">{{ t.dashboard.dnsNoCheck }}</span>
        <span v-else-if="dnsStatus.all_ok" class="rbl-status-detail">{{ t.dashboard.dnsAllOk }}</span>
        <span v-else class="rbl-status-detail">{{ dnsStatus.issues }} {{ t.dashboard.dnsIssues }}</span>
      </div>
      <div v-if="dnsCheckTime" class="rbl-status-time">{{ dnsCheckTime }}</div>
      <i class="pi pi-angle-right rbl-status-arrow"></i>
    </div>

    <StatsCards :stats="dashboard.stats" :loading="dashboard.loading" />

    <div class="dashboard-grid">
      <div class="chart-section">
        <DeliveryChart :data="dashboard.chartData" />
      </div>
      <div class="queue-section">
        <QueueStatus :queue="dashboard.queue" />
      </div>
    </div>

    <RecentActivity :events="dashboard.activity" :banned-ips="bannedIps" />
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.dashboard h2 {
  font-size: 1.5rem;
  color: #1e293b;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

/* RBL Status Card */
.rbl-status-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 10px;
  cursor: pointer;
  transition: box-shadow 0.15s;
}

.rbl-status-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.rbl-clean {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.rbl-warn {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.rbl-neutral {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.rbl-status-icon i {
  font-size: 1.25rem;
}

.rbl-status-text {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.rbl-status-label {
  font-weight: 600;
  font-size: 0.85rem;
  color: #334155;
}

.rbl-status-detail {
  font-size: 0.8rem;
  color: #64748b;
}

.rbl-status-time {
  font-size: 0.75rem;
  color: #94a3b8;
}

.rbl-status-arrow {
  color: #94a3b8;
  font-size: 1rem;
}

@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
