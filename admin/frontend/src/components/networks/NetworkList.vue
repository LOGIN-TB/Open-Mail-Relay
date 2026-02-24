<script setup lang="ts">
import Button from 'primevue/button'
import t from '../../i18n/de'

const PROTECTED = ['127.0.0.0/8', '172.16.0.0/12']

defineProps<{
  networks: string[]
  loading: boolean
}>()

const emit = defineEmits<{
  remove: [cidr: string]
}>()

function isProtected(cidr: string): boolean {
  return PROTECTED.includes(cidr)
}
</script>

<template>
  <div class="card">
    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <table v-else class="network-table">
      <thead>
        <tr>
          <th>{{ t.networks.cidr }}</th>
          <th style="width: 150px">Aktion</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="cidr in networks" :key="cidr">
          <td>
            <code>{{ cidr }}</code>
            <span v-if="isProtected(cidr)" class="protected-badge">{{ t.networks.protected }}</span>
          </td>
          <td>
            <Button
              v-if="!isProtected(cidr)"
              :label="t.networks.remove"
              icon="pi pi-trash"
              severity="danger"
              size="small"
              text
              @click="emit('remove', cidr)"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.network-table {
  width: 100%;
  border-collapse: collapse;
}

.network-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.85rem;
}

.network-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.network-table code {
  font-size: 0.9rem;
  color: #1e293b;
  font-weight: 500;
}

.protected-badge {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 2px 8px;
  background: #e2e8f0;
  color: #64748b;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}
</style>
