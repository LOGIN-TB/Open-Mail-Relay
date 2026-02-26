<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import api from '../api/client'
import NetworkList from '../components/networks/NetworkList.vue'
import NetworkForm from '../components/networks/NetworkForm.vue'
import t from '../i18n/de'

import type { NetworkItem } from '../components/networks/NetworkList.vue'

const toast = useToast()
const confirm = useConfirm()

const networks = ref<NetworkItem[]>([])
const loading = ref(false)

async function fetchNetworks() {
  loading.value = true
  try {
    const { data } = await api.get('/networks')
    networks.value = data
  } finally {
    loading.value = false
  }
}

async function addNetwork(payload: { cidr: string; owner: string }) {
  try {
    await api.post('/networks', payload)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.networks.networkAdded, life: 3000 })
    await fetchNetworks()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function updateField(networkId: number, field: string, value: string) {
  try {
    await api.put(`/networks/${networkId}`, { [field]: value })
    toast.add({ severity: 'success', summary: t.common.success, detail: t.networks.networkUpdated, life: 3000 })
    await fetchNetworks()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

function confirmRemove(network: NetworkItem) {
  confirm.require({
    message: t.networks.confirmRemove,
    header: t.networks.remove,
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => removeNetwork(network),
  })
}

async function removeNetwork(network: NetworkItem) {
  try {
    await api.delete(`/networks/${network.id}`)
    toast.add({ severity: 'success', summary: t.common.success, detail: `Netzwerk ${network.cidr} entfernt`, life: 3000 })
    await fetchNetworks()
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

onMounted(fetchNetworks)
</script>

<template>
  <div class="networks-page">
    <h2>{{ t.networks.title }}</h2>

    <NetworkForm @add="addNetwork" />
    <NetworkList :networks="networks" :loading="loading" @remove="confirmRemove" @update-field="updateField" />
  </div>
</template>

<style scoped>
.networks-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.networks-page h2 {
  font-size: 1.5rem;
  color: #1e293b;
}
</style>
