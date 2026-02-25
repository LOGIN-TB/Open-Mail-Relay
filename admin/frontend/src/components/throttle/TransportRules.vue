<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { TransportRule } from '../../stores/throttle'
import { useThrottleStore } from '../../stores/throttle'
import TransportRuleForm from './TransportRuleForm.vue'
import t from '../../i18n/de'

defineProps<{
  transports: TransportRule[]
}>()

const toast = useToast()
const store = useThrottleStore()
const showForm = ref(false)
const editingRule = ref<TransportRule | null>(null)

function openAdd() {
  editingRule.value = null
  showForm.value = true
}

function openEdit(rule: TransportRule) {
  editingRule.value = { ...rule }
  showForm.value = true
}

async function onSave(data: any) {
  try {
    if (editingRule.value) {
      await store.updateTransport(editingRule.value.id, data)
      toast.add({ severity: 'success', summary: t.common.success, detail: t.throttling.transportUpdated, life: 3000 })
    } else {
      await store.createTransport(data)
      toast.add({ severity: 'success', summary: t.common.success, detail: t.throttling.transportCreated, life: 3000 })
    }
    showForm.value = false
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function onDelete(id: number) {
  if (!confirm(t.throttling.confirmDeleteTransport)) return
  try {
    await store.deleteTransport(id)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.throttling.transportDeleted, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function toggleActive(rule: TransportRule) {
  try {
    await store.updateTransport(rule.id, { is_active: !rule.is_active })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3>{{ t.throttling.transportRules }}</h3>
      <button class="btn btn-primary btn-sm" @click="openAdd">
        <i class="pi pi-plus"></i> {{ t.throttling.addTransport }}
      </button>
    </div>
    <div class="card-body">
      <table class="transport-table">
        <thead>
          <tr>
            <th>{{ t.throttling.domain }}</th>
            <th>{{ t.throttling.transport }}</th>
            <th>{{ t.throttling.concurrency }}</th>
            <th>{{ t.throttling.delay }}</th>
            <th>{{ t.throttling.statusLabel }}</th>
            <th>{{ t.throttling.actions }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rule in transports" :key="rule.id" :class="{ inactive: !rule.is_active }">
            <td class="domain">{{ rule.domain_pattern }}</td>
            <td>{{ rule.transport_name }}</td>
            <td>{{ rule.concurrency_limit }}</td>
            <td>{{ rule.rate_delay_seconds }}s</td>
            <td>
              <button class="status-badge" :class="rule.is_active ? 'active' : 'disabled'" @click="toggleActive(rule)">
                {{ rule.is_active ? t.throttling.active : t.throttling.inactive }}
              </button>
            </td>
            <td class="actions">
              <button class="btn btn-sm" @click="openEdit(rule)" title="Bearbeiten">
                <i class="pi pi-pencil"></i>
              </button>
              <button class="btn btn-sm btn-danger" @click="onDelete(rule.id)" title="Loeschen">
                <i class="pi pi-trash"></i>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <TransportRuleForm
        v-if="showForm"
        :rule="editingRule"
        @save="onSave"
        @cancel="showForm = false"
      />
    </div>
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #1e293b;
}

.card-body {
  padding: 1rem;
  overflow-x: auto;
}

.transport-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.transport-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  color: #64748b;
  font-weight: 600;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.transport-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.transport-table tr.inactive {
  opacity: 0.5;
}

.domain {
  font-weight: 600;
  font-family: monospace;
}

.status-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.status-badge.active {
  background: #dcfce7;
  color: #16a34a;
}

.status-badge.disabled {
  background: #f1f5f9;
  color: #64748b;
}

.actions {
  display: flex;
  gap: 0.25rem;
}

.btn {
  padding: 0.35rem 0.75rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: white;
  color: #475569;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
}

.btn-primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-danger {
  color: #ef4444;
}

.btn-danger:hover {
  background: #fef2f2;
  border-color: #fecaca;
}
</style>
