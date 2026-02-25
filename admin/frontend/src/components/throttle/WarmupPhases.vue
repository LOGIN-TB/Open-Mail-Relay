<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import type { WarmupPhase, WarmupStatus } from '../../stores/throttle'
import { useThrottleStore } from '../../stores/throttle'
import t from '../../i18n/de'

defineProps<{
  phases: WarmupPhase[]
  warmup: WarmupStatus | null
}>()

const toast = useToast()
const store = useThrottleStore()
const editingId = ref<number | null>(null)
const editData = ref<Partial<WarmupPhase>>({})

function startEdit(phase: WarmupPhase) {
  editingId.value = phase.id
  editData.value = {
    max_per_hour: phase.max_per_hour,
    max_per_day: phase.max_per_day,
    burst_limit: phase.burst_limit,
  }
}

function cancelEdit() {
  editingId.value = null
  editData.value = {}
}

async function saveEdit(id: number) {
  try {
    await store.updatePhase(id, editData.value)
    editingId.value = null
    toast.add({ severity: 'success', summary: t.common.success, detail: t.throttling.phaseUpdated, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function resetWarmup() {
  try {
    await store.resetWarmup()
    toast.add({ severity: 'success', summary: t.common.success, detail: t.throttling.warmupReset, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}

async function setPhase(phaseNumber: number) {
  try {
    await store.setWarmupPhase(phaseNumber)
    toast.add({ severity: 'success', summary: t.common.success, detail: t.throttling.phaseSet, life: 3000 })
  } catch (e: any) {
    toast.add({ severity: 'error', summary: t.common.error, detail: e.response?.data?.detail ?? 'Fehler', life: 5000 })
  }
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3>{{ t.throttling.warmupPhases }}</h3>
      <div class="header-actions">
        <button class="btn btn-sm" @click="resetWarmup">{{ t.throttling.resetWarmup }}</button>
      </div>
    </div>
    <div class="card-body">
      <table class="phases-table">
        <thead>
          <tr>
            <th>{{ t.throttling.phase }}</th>
            <th>{{ t.throttling.duration }}</th>
            <th>{{ t.throttling.maxPerHour }}</th>
            <th>{{ t.throttling.maxPerDay }}</th>
            <th>{{ t.throttling.burst }}</th>
            <th>{{ t.throttling.actions }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="phase in phases"
            :key="phase.id"
            :class="{ active: warmup && warmup.current_phase === phase.phase_number }"
          >
            <td>
              <span class="phase-name">{{ phase.name }}</span>
              <span v-if="warmup && warmup.current_phase === phase.phase_number" class="current-badge">aktiv</span>
            </td>
            <td>{{ phase.duration_days > 0 ? phase.duration_days + 'd' : '\u221E' }}</td>
            <td>
              <template v-if="editingId === phase.id">
                <input v-model.number="editData.max_per_hour" type="number" class="inline-input" />
              </template>
              <template v-else>{{ phase.max_per_hour }}</template>
            </td>
            <td>
              <template v-if="editingId === phase.id">
                <input v-model.number="editData.max_per_day" type="number" class="inline-input" />
              </template>
              <template v-else>{{ phase.max_per_day }}</template>
            </td>
            <td>
              <template v-if="editingId === phase.id">
                <input v-model.number="editData.burst_limit" type="number" class="inline-input" />
              </template>
              <template v-else>{{ phase.burst_limit }}</template>
            </td>
            <td class="actions">
              <template v-if="editingId === phase.id">
                <button class="btn btn-sm btn-primary" @click="saveEdit(phase.id)">{{ t.common.save }}</button>
                <button class="btn btn-sm" @click="cancelEdit">{{ t.common.cancel }}</button>
              </template>
              <template v-else>
                <button class="btn btn-sm" @click="startEdit(phase)" title="Bearbeiten">
                  <i class="pi pi-pencil"></i>
                </button>
                <button class="btn btn-sm" @click="setPhase(phase.phase_number)" title="Phase setzen">
                  <i class="pi pi-arrow-right"></i>
                </button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
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

.phases-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.phases-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  color: #64748b;
  font-weight: 600;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}

.phases-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.phases-table tr.active {
  background: #eff6ff;
}

.phase-name {
  font-weight: 600;
  color: #1e293b;
}

.current-badge {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.1rem 0.4rem;
  background: #3b82f6;
  color: white;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 600;
}

.inline-input {
  width: 80px;
  padding: 0.25rem 0.5rem;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 0.85rem;
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
}

.btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
}

.btn-primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}
</style>
