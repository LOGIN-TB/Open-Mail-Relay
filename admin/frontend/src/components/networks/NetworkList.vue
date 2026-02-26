<script setup lang="ts">
import { ref, nextTick } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'
import { formatDateTimeShort } from '../../utils/dateFormat'

export interface NetworkItem {
  id: number
  cidr: string
  owner: string
  is_protected: boolean
  created_at: string | null
}

defineProps<{
  networks: NetworkItem[]
  loading: boolean
}>()

const emit = defineEmits<{
  remove: [network: NetworkItem]
  updateField: [networkId: number, field: string, value: string]
}>()

const editingCell = ref<{ networkId: number; field: string } | null>(null)
const editValue = ref('')

async function startEdit(networkId: number, field: string, currentValue: string | null) {
  editingCell.value = { networkId, field }
  editValue.value = currentValue || ''
  await nextTick()
  const input = document.querySelector('.inline-edit input') as HTMLInputElement | null
  input?.focus()
}

function commitEdit(networkId: number, field: string) {
  emit('updateField', networkId, field, editValue.value.trim())
  editingCell.value = null
}

function isEditing(networkId: number, field: string): boolean {
  return editingCell.value?.networkId === networkId && editingCell.value?.field === field
}

function formatDate(ts: string | null): string {
  return formatDateTimeShort(ts)
}
</script>

<template>
  <div class="card">
    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <div v-else-if="networks.length === 0" class="no-data">{{ t.networks.noNetworks }}</div>
    <table v-else class="network-table">
      <thead>
        <tr>
          <th>{{ t.networks.cidr }}</th>
          <th>{{ t.networks.owner }}</th>
          <th>{{ t.networks.created }}</th>
          <th style="width: 120px">Aktion</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="net in networks" :key="net.id">
          <td>
            <code>{{ net.cidr }}</code>
            <span v-if="net.is_protected" class="protected-badge">{{ t.networks.protected }}</span>
          </td>
          <td class="editable-cell" @click="!isEditing(net.id, 'owner') && startEdit(net.id, 'owner', net.owner)">
            <InputText
              v-if="isEditing(net.id, 'owner')"
              v-model="editValue"
              size="small"
              class="inline-edit"
              :placeholder="t.networks.ownerPlaceholder"
              @blur="commitEdit(net.id, 'owner')"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
            <span v-else class="cell-text">{{ net.owner || '-' }}</span>
          </td>
          <td class="date-col">{{ formatDate(net.created_at) }}</td>
          <td>
            <Button
              v-if="!net.is_protected"
              :label="t.networks.remove"
              icon="pi pi-trash"
              severity="danger"
              size="small"
              text
              @click="emit('remove', net)"
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

.loading,
.no-data {
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

.editable-cell {
  cursor: pointer;
  min-width: 140px;
}

.editable-cell:hover .cell-text {
  color: #3b82f6;
  text-decoration: underline dotted;
}

.cell-text {
  font-size: 0.85rem;
  color: #475569;
}

.inline-edit {
  width: 100%;
}

.date-col {
  font-size: 0.8rem;
  color: #64748b;
}
</style>
