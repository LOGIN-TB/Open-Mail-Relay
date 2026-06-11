<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import api from '../api/client'
import { useApi } from '../composables/useApi'
import NetworkList from '../components/networks/NetworkList.vue'
import NetworkForm from '../components/networks/NetworkForm.vue'
import t from '../i18n/de'

import type { Network } from '../types/api'

const { call, silent } = useApi()
const confirm = useConfirm()

const networks = ref<Network[]>([])
const loading = ref(false)

async function fetchNetworks() {
  loading.value = true
  const data = await silent(() => api.get<Network[]>('/networks'))
  if (data !== null) networks.value = data
  loading.value = false
}

async function addNetwork(payload: { cidr: string; owner: string }) {
  const result = await call(() => api.post<Network>('/networks', payload), { success: t.networks.networkAdded })
  if (result !== null) await fetchNetworks()
}

async function updateField(networkId: number, field: string, value: string) {
  const result = await call(
    () => api.put<Network>(`/networks/${networkId}`, { [field]: value }),
    { success: t.networks.networkUpdated },
  )
  if (result !== null) await fetchNetworks()
}

function confirmRemove(network: Network) {
  confirm.require({
    message: t.networks.confirmRemove,
    header: t.networks.remove,
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => removeNetwork(network),
  })
}

async function removeNetwork(network: Network) {
  const result = await call(
    () => api.delete<void>(`/networks/${network.id}`),
    { success: `Netzwerk ${network.cidr} entfernt` },
  )
  if (result !== null) await fetchNetworks()
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
