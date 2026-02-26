<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import api from '../api/client'
import IpBanList from '../components/ip-bans/IpBanList.vue'
import IpBanForm from '../components/ip-bans/IpBanForm.vue'
import IpBanSettings from '../components/ip-bans/IpBanSettings.vue'
import t from '../i18n/de'

import type { IpBanItem } from '../components/ip-bans/IpBanList.vue'
import type { BanSettingsData } from '../components/ip-bans/IpBanSettings.vue'

const toast = useToast()
const confirm = useConfirm()

const bans = ref<IpBanItem[]>([])
const loading = ref(false)
const showForm = ref(false)
const banSettings = ref<BanSettingsData>({
  max_attempts: 5,
  time_window_minutes: 10,
  ban_durations: [30, 360, 1440, 10080],
})

let refreshInterval: ReturnType<typeof setInterval>

async function fetchBans() {
  loading.value = true
  try {
    const { data } = await api.get('/ip-bans')
    bans.value = data
  } finally {
    loading.value = false
  }
}

async function fetchSettings() {
  try {
    const { data } = await api.get('/ip-bans/settings')
    banSettings.value = data
  } catch {
    // Use defaults
  }
}

async function createBan(payload: { ip_address: string; reason: string; notes: string }) {
  try {
    await api.post('/ip-bans', payload)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.ipBans.banCreated, life: 3000 })
    showForm.value = false
    await fetchBans()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function updateNotes(banId: number, notes: string) {
  try {
    await api.put(`/ip-bans/${banId}`, { notes })
    toast.add({ severity: 'success', summary: t.common.success, detail: t.ipBans.banUpdated, life: 3000 })
    await fetchBans()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

function confirmUnban(ban: IpBanItem) {
  confirm.require({
    message: t.ipBans.confirmUnban,
    header: t.ipBans.unban,
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-success',
    accept: () => doUnban(ban.id),
  })
}

async function doUnban(banId: number) {
  try {
    await api.delete(`/ip-bans/${banId}`)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.ipBans.unbanned, life: 3000 })
    await fetchBans()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function saveSettings(settings: BanSettingsData) {
  try {
    await api.put('/ip-bans/settings', settings)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.ipBans.settingsSaved, life: 3000 })
    await fetchSettings()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

onMounted(() => {
  fetchBans()
  fetchSettings()
  refreshInterval = setInterval(fetchBans, 30000)
})

onUnmounted(() => {
  clearInterval(refreshInterval)
})
</script>

<template>
  <div class="ip-bans-page">
    <div class="page-header">
      <h2>{{ t.ipBans.title }}</h2>
      <button class="btn-primary" @click="showForm = true">
        <i class="pi pi-plus"></i> {{ t.ipBans.addBan }}
      </button>
    </div>

    <IpBanForm
      v-if="showForm"
      @save="createBan"
      @cancel="showForm = false"
    />

    <IpBanList
      :bans="bans"
      :loading="loading"
      @unban="confirmUnban"
      @update-notes="updateNotes"
    />

    <IpBanSettings
      :settings="banSettings"
      @save="saveSettings"
    />
  </div>
</template>

<style scoped>
.ip-bans-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  font-size: 1.5rem;
  color: #1e293b;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.2rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background 0.15s;
}

.btn-primary:hover {
  background: #2563eb;
}
</style>
