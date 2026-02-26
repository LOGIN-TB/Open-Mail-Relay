<script setup lang="ts">
import { ref, nextTick } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import t from '../../i18n/de'
import { formatDateTimeShort } from '../../utils/dateFormat'

export interface IpBanItem {
  id: number
  ip_address: string
  reason: string
  ban_count: number
  fail_count: number
  banned_at: string | null
  expires_at: string | null
  is_active: boolean
  created_at: string | null
  notes: string
}

defineProps<{
  bans: IpBanItem[]
  loading: boolean
}>()

const emit = defineEmits<{
  unban: [ban: IpBanItem]
  delete: [ban: IpBanItem]
  updateNotes: [banId: number, notes: string]
}>()

const editingId = ref<number | null>(null)
const editValue = ref('')

async function startEdit(ban: IpBanItem) {
  editingId.value = ban.id
  editValue.value = ban.notes || ''
  await nextTick()
  const input = document.querySelector('.inline-edit input') as HTMLInputElement | null
  input?.focus()
}

function commitEdit(banId: number) {
  emit('updateNotes', banId, editValue.value.trim())
  editingId.value = null
}

function formatDate(ts: string | null): string {
  return formatDateTimeShort(ts)
}

function reasonLabel(reason: string): string {
  const labels: Record<string, string> = {
    sasl_auth_failed: t.ipBans.reasonSasl,
    relay_rejected: t.ipBans.reasonRelay,
    manual: t.ipBans.reasonManual,
  }
  return labels[reason] || reason
}

function expiresLabel(ban: IpBanItem): string {
  if (!ban.is_active) return '-'
  if (!ban.expires_at) return t.ipBans.permanent
  const now = new Date()
  const exp = new Date(ban.expires_at)
  if (exp <= now) return t.ipBans.expired
  const diffMin = Math.round((exp.getTime() - now.getTime()) / 60000)
  if (diffMin < 60) return `${diffMin} Min`
  if (diffMin < 1440) return `${Math.round(diffMin / 60)} Std`
  return `${Math.round(diffMin / 1440)} Tage`
}
</script>

<template>
  <div class="card">
    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <div v-else-if="bans.length === 0" class="no-data">{{ t.ipBans.noBans }}</div>
    <table v-else class="ban-table">
      <thead>
        <tr>
          <th>{{ t.ipBans.ipAddress }}</th>
          <th>{{ t.ipBans.reason }}</th>
          <th>{{ t.ipBans.failCount }}</th>
          <th>{{ t.ipBans.banCount }}</th>
          <th>{{ t.ipBans.bannedAt }}</th>
          <th>{{ t.ipBans.expiresIn }}</th>
          <th>{{ t.ipBans.status }}</th>
          <th>{{ t.ipBans.notes }}</th>
          <th style="width: 80px">{{ t.ipBans.actions }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="ban in bans" :key="ban.id" :class="{ 'row-active': ban.is_active }">
          <td><strong>{{ ban.ip_address }}</strong></td>
          <td><span class="reason-badge" :class="'reason-' + ban.reason">{{ reasonLabel(ban.reason) }}</span></td>
          <td>{{ ban.fail_count }}</td>
          <td>{{ ban.ban_count }}</td>
          <td class="date-col">{{ ban.banned_at ? formatDate(ban.banned_at) : '-' }}</td>
          <td>{{ expiresLabel(ban) }}</td>
          <td>
            <span v-if="ban.is_active" class="badge-active">{{ t.ipBans.active }}</span>
            <span v-else class="badge-expired">{{ t.ipBans.expired }}</span>
          </td>
          <td class="editable-cell" @click="editingId !== ban.id && startEdit(ban)">
            <InputText
              v-if="editingId === ban.id"
              v-model="editValue"
              size="small"
              class="inline-edit"
              :placeholder="t.ipBans.notesPlaceholder"
              @blur="commitEdit(ban.id)"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
            <span v-else class="cell-text">{{ ban.notes || '-' }}</span>
          </td>
          <td>
            <div class="actions">
              <Button
                v-if="ban.is_active"
                icon="pi pi-lock-open"
                severity="success"
                size="small"
                text
                :title="t.ipBans.unban"
                @click="emit('unban', ban)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                size="small"
                text
                :title="t.ipBans.delete"
                @click="emit('delete', ban)"
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

.ban-table {
  width: 100%;
  border-collapse: collapse;
}

.ban-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.85rem;
  position: sticky;
  top: 0;
  background: white;
}

.ban-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.85rem;
}

.row-active {
  background: #fef2f2;
}

.date-col {
  font-size: 0.8rem;
  color: #64748b;
}

.reason-badge {
  display: inline-block;
  padding: 2px 8px;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}

.reason-sasl_auth_failed {
  background: #fef3c7;
  color: #92400e;
}

.reason-relay_rejected {
  background: #fee2e2;
  color: #991b1b;
}

.reason-manual {
  background: #e0e7ff;
  color: #3730a3;
}

.badge-active {
  display: inline-block;
  padding: 2px 8px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}

.badge-expired {
  display: inline-block;
  padding: 2px 8px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}

.editable-cell {
  cursor: pointer;
  min-width: 120px;
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

.actions {
  display: flex;
  gap: 0.25rem;
}
</style>
