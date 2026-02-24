<script setup lang="ts">
import Button from 'primevue/button'
import t from '../../i18n/de'

defineProps<{
  users: {
    id: number
    username: string
    is_admin: boolean
    created_at: string | null
    last_login: string | null
  }[]
  loading: boolean
}>()

const emit = defineEmits<{
  edit: [user: any]
  delete: [user: any]
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
    <table v-else class="user-table">
      <thead>
        <tr>
          <th>{{ t.users.username }}</th>
          <th>Rolle</th>
          <th>{{ t.users.created }}</th>
          <th>{{ t.users.lastLogin }}</th>
          <th style="width: 160px">Aktionen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td><strong>{{ user.username }}</strong></td>
          <td>
            <span v-if="user.is_admin" class="admin-badge">Admin</span>
            <span v-else class="user-badge">Benutzer</span>
          </td>
          <td class="date-col">{{ formatDate(user.created_at) }}</td>
          <td class="date-col">{{ formatDate(user.last_login) }}</td>
          <td>
            <div class="actions">
              <Button icon="pi pi-pencil" severity="secondary" size="small" text @click="emit('edit', user)" />
              <Button icon="pi pi-trash" severity="danger" size="small" text @click="emit('delete', user)" />
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

.loading {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.user-table {
  width: 100%;
  border-collapse: collapse;
}

.user-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.85rem;
}

.user-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
}

.date-col {
  font-size: 0.8rem;
  color: #64748b;
}

.admin-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #3b82f6;
  color: white;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}

.user-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #e2e8f0;
  color: #475569;
  font-size: 0.7rem;
  border-radius: 12px;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 0.25rem;
}
</style>
