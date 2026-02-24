<script setup lang="ts">
import Button from 'primevue/button'
import t from '../../i18n/de'

export interface SmtpUserItem {
  id: number
  username: string
  is_active: boolean
  created_at: string | null
  created_by: number | null
}

defineProps<{
  users: SmtpUserItem[]
  loading: boolean
}>()

const emit = defineEmits<{
  toggleActive: [user: SmtpUserItem]
  regeneratePassword: [user: SmtpUserItem]
  downloadPdf: [user: SmtpUserItem]
  delete: [user: SmtpUserItem]
}>()

function formatDate(ts: string | null): string {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="card">
    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <div v-else-if="users.length === 0" class="no-data">{{ t.smtpUsers.noUsers }}</div>
    <table v-else class="smtp-table">
      <thead>
        <tr>
          <th>{{ t.smtpUsers.username }}</th>
          <th>{{ t.smtpUsers.status }}</th>
          <th>{{ t.smtpUsers.created }}</th>
          <th style="width: 220px">{{ t.smtpUsers.actions }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td><strong>{{ user.username }}</strong></td>
          <td>
            <span v-if="user.is_active" class="badge-active">{{ t.smtpUsers.active }}</span>
            <span v-else class="badge-inactive">{{ t.smtpUsers.inactive }}</span>
          </td>
          <td class="date-col">{{ formatDate(user.created_at) }}</td>
          <td>
            <div class="actions">
              <Button
                :icon="user.is_active ? 'pi pi-ban' : 'pi pi-check'"
                :severity="user.is_active ? 'warn' : 'success'"
                size="small"
                text
                :title="user.is_active ? t.smtpUsers.deactivate : t.smtpUsers.activate"
                @click="emit('toggleActive', user)"
              />
              <Button
                icon="pi pi-refresh"
                severity="secondary"
                size="small"
                text
                :title="t.smtpUsers.regeneratePassword"
                @click="emit('regeneratePassword', user)"
              />
              <Button
                icon="pi pi-file-pdf"
                severity="info"
                size="small"
                text
                :title="t.smtpUsers.downloadPdf"
                @click="emit('downloadPdf', user)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                size="small"
                text
                :title="t.smtpUsers.delete"
                @click="emit('delete', user)"
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

.smtp-table {
  width: 100%;
  border-collapse: collapse;
}

.smtp-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.85rem;
}

.smtp-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.date-col {
  font-size: 0.8rem;
  color: #64748b;
}

.badge-active {
  display: inline-block;
  padding: 2px 8px;
  background: #dcfce7;
  color: #166534;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}

.badge-inactive {
  display: inline-block;
  padding: 2px 8px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 0.25rem;
}
</style>
