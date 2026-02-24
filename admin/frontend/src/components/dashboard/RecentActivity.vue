<script setup lang="ts">
import t from '../../i18n/de'

defineProps<{
  events: {
    id: number
    timestamp: string
    queue_id: string | null
    sender: string | null
    recipient: string | null
    status: string
    relay: string | null
    delay: number | null
  }[]
}>()

function statusClass(status: string): string {
  const map: Record<string, string> = {
    sent: 'status-sent',
    deferred: 'status-deferred',
    bounced: 'status-bounced',
    rejected: 'status-rejected',
  }
  return map[status] ?? ''
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    sent: t.dashboard.sent,
    deferred: t.dashboard.deferred,
    bounced: t.dashboard.bounced,
    rejected: t.dashboard.rejected,
  }
  return map[status] ?? status
}

function formatTime(ts: string): string {
  return new Date(ts).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}
</script>

<template>
  <div class="card">
    <h3>{{ t.dashboard.recentActivity }}</h3>
    <div v-if="events.length === 0" class="no-data">{{ t.dashboard.noData }}</div>
    <div v-else class="table-scroll">
    <table class="activity-table">
      <thead>
        <tr>
          <th>Zeit</th>
          <th>Status</th>
          <th>Absender</th>
          <th>Empfaenger</th>
          <th>Relay</th>
          <th>Delay</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="event in events" :key="event.id">
          <td class="time-col">{{ formatTime(event.timestamp) }}</td>
          <td><span class="status-badge" :class="statusClass(event.status)">{{ statusLabel(event.status) }}</span></td>
          <td class="truncate">{{ event.sender ?? '-' }}</td>
          <td class="truncate">{{ event.recipient ?? '-' }}</td>
          <td class="truncate">{{ event.relay ?? '-' }}</td>
          <td>{{ event.delay != null ? event.delay.toFixed(1) + 's' : '-' }}</td>
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
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  max-height: 500px;
  display: flex;
  flex-direction: column;
}

.card h3 {
  font-size: 1rem;
  color: #1e293b;
  margin-bottom: 1rem;
  flex-shrink: 0;
}

.table-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.no-data {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.activity-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.activity-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.8rem;
  position: sticky;
  top: 0;
  background: white;
  z-index: 1;
}

.activity-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  color: #334155;
}

.time-col {
  white-space: nowrap;
  font-size: 0.8rem;
  color: #64748b;
}

.truncate {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.status-sent { background: #dcfce7; color: #166534; }
.status-deferred { background: #fef3c7; color: #92400e; }
.status-bounced { background: #fee2e2; color: #991b1b; }
.status-rejected { background: #ede9fe; color: #5b21b6; }
</style>
