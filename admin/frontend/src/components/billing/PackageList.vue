<script setup lang="ts">
import { ref, nextTick } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'

export interface PackageItem {
  id: number
  name: string
  category: string
  monthly_limit: number
  description: string | null
  is_active: boolean
  created_at: string | null
}

defineProps<{
  packages: PackageItem[]
  loading: boolean
}>()

const emit = defineEmits<{
  delete: [pkg: PackageItem]
  updateField: [packageId: number, field: string, value: string | number]
}>()

const editingCell = ref<{ id: number; field: string } | null>(null)
const editValue = ref('')

async function startEdit(id: number, field: string, currentValue: string | number | null) {
  editingCell.value = { id, field }
  editValue.value = String(currentValue ?? '')
  await nextTick()
  const input = document.querySelector('.inline-edit input') as HTMLInputElement | null
  input?.focus()
}

function commitEdit(id: number, field: string) {
  const val = field === 'monthly_limit' ? parseInt(editValue.value) || 0 : editValue.value.trim()
  emit('updateField', id, field, val)
  editingCell.value = null
}

function isEditing(id: number, field: string): boolean {
  return editingCell.value?.id === id && editingCell.value?.field === field
}

function categoryLabel(cat: string): string {
  if (cat === 'transaction') return t.billing.transaction
  if (cat === 'newsletter') return t.billing.newsletter
  if (cat === 'overage') return t.billing.overage
  return cat
}

function categoryClass(cat: string): string {
  if (cat === 'transaction') return 'badge-transaction'
  if (cat === 'newsletter') return 'badge-newsletter'
  if (cat === 'overage') return 'badge-overage'
  return ''
}

function formatLimit(limit: number): string {
  return limit.toLocaleString('de-DE')
}
</script>

<template>
  <div class="card">
    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <div v-else-if="packages.length === 0" class="no-data">{{ t.billing.noPackages }}</div>
    <table v-else class="pkg-table">
      <thead>
        <tr>
          <th>{{ t.billing.packageName }}</th>
          <th>{{ t.billing.category }}</th>
          <th style="text-align: right">{{ t.billing.monthlyLimit }}</th>
          <th>{{ t.billing.description }}</th>
          <th style="width: 80px">{{ t.smtpUsers.actions }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pkg in packages" :key="pkg.id">
          <td class="editable-cell" @click="!isEditing(pkg.id, 'name') && startEdit(pkg.id, 'name', pkg.name)">
            <InputText
              v-if="isEditing(pkg.id, 'name')"
              v-model="editValue"
              size="small"
              class="inline-edit"
              @blur="commitEdit(pkg.id, 'name')"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
            <strong v-else class="cell-text">{{ pkg.name }}</strong>
          </td>
          <td>
            <span class="category-badge" :class="categoryClass(pkg.category)">
              {{ categoryLabel(pkg.category) }}
            </span>
          </td>
          <td
            class="editable-cell"
            style="text-align: right"
            @click="!isEditing(pkg.id, 'monthly_limit') && startEdit(pkg.id, 'monthly_limit', pkg.monthly_limit)"
          >
            <InputText
              v-if="isEditing(pkg.id, 'monthly_limit')"
              v-model="editValue"
              size="small"
              class="inline-edit"
              type="number"
              @blur="commitEdit(pkg.id, 'monthly_limit')"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
            <span v-else class="cell-text">{{ formatLimit(pkg.monthly_limit) }}</span>
          </td>
          <td class="editable-cell" @click="!isEditing(pkg.id, 'description') && startEdit(pkg.id, 'description', pkg.description)">
            <InputText
              v-if="isEditing(pkg.id, 'description')"
              v-model="editValue"
              size="small"
              class="inline-edit"
              @blur="commitEdit(pkg.id, 'description')"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
            <span v-else class="cell-text">{{ pkg.description || '-' }}</span>
          </td>
          <td>
            <div class="actions">
              <Button
                icon="pi pi-trash"
                severity="danger"
                size="small"
                text
                :title="t.billing.deletePackage"
                @click="emit('delete', pkg)"
              />
            </div>
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

.pkg-table {
  width: 100%;
  border-collapse: collapse;
}

.pkg-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.85rem;
}

.pkg-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.editable-cell {
  cursor: pointer;
  min-width: 100px;
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

.category-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}

.badge-transaction {
  background: #dbeafe;
  color: #1e40af;
}

.badge-newsletter {
  background: #dcfce7;
  color: #166534;
}

.badge-overage {
  background: #fef3c7;
  color: #92400e;
}

.actions {
  display: flex;
  gap: 0.25rem;
}
</style>
