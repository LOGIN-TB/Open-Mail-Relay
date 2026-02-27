<script setup lang="ts">
import { ref } from 'vue'
import t from '../../i18n/de'
import { formatTimeShort } from '../../utils/dateFormat'

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
    dsn: string | null
    size: number | null
    message: string | null
    client_ip: string | null
    sasl_username: string | null
  }[]
  bannedIps?: Set<string>
}>()

const expandedId = ref<number | null>(null)

function toggleExpand(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

function statusClass(status: string): string {
  const map: Record<string, string> = {
    sent: 'status-sent',
    deferred: 'status-deferred',
    bounced: 'status-bounced',
    rejected: 'status-rejected',
    auth_failed: 'status-auth-failed',
  }
  return map[status] ?? ''
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    sent: t.dashboard.sent,
    deferred: t.dashboard.deferred,
    bounced: t.dashboard.bounced,
    rejected: t.dashboard.rejected,
    auth_failed: t.dashboard.authFailed,
  }
  return map[status] ?? status
}

function formatTime(ts: string): string {
  return formatTimeShort(ts)
}

function sourceDisplay(event: { sasl_username: string | null; client_ip: string | null; status: string }) {
  if (event.status === 'auth_failed' && event.client_ip) {
    return { text: event.client_ip, cssClass: 'source-auth-failed', icon: 'pi-shield' }
  }
  if (event.sasl_username) {
    return { text: event.sasl_username, cssClass: 'source-smtp', icon: 'pi-user' }
  }
  if (event.client_ip) {
    if (event.status === 'rejected') {
      return { text: event.client_ip, cssClass: 'source-rejected', icon: 'pi-exclamation-triangle' }
    }
    return { text: event.client_ip, cssClass: 'source-ip', icon: 'pi-globe' }
  }
  return { text: '-', cssClass: '', icon: '' }
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
          <th>Quelle</th>
          <th>Absender</th>
          <th>Empfaenger</th>
          <th>Relay</th>
          <th>Delay</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="event in events" :key="event.id">
          <tr class="event-row" @click="toggleExpand(event.id)">
            <td class="time-col">{{ formatTime(event.timestamp) }}</td>
            <td><span class="status-badge" :class="statusClass(event.status)">{{ statusLabel(event.status) }}</span></td>
            <td>
              <span v-if="sourceDisplay(event).icon" class="source-badge" :class="sourceDisplay(event).cssClass">
                <i class="pi" :class="sourceDisplay(event).icon"></i>
                {{ sourceDisplay(event).text }}
              </span>
              <span v-else>-</span>
              <span v-if="event.status === 'auth_failed' && event.sasl_username" class="source-badge source-attempted-user">
                <i class="pi pi-user"></i> {{ event.sasl_username }}
              </span>
              <span v-if="event.client_ip && bannedIps?.has(event.client_ip)" class="source-badge source-banned">
                <i class="pi pi-ban"></i> {{ t.ipBans.banned }}
              </span>
            </td>
            <td class="truncate">{{ event.sender ?? '-' }}</td>
            <td class="truncate">{{ event.recipient ?? '-' }}</td>
            <td class="truncate">{{ event.relay ?? '-' }}</td>
            <td>{{ event.delay != null ? event.delay.toFixed(1) + 's' : '-' }}</td>
          </tr>
          <tr v-if="expandedId === event.id" class="detail-row">
            <td colspan="7">
              <div class="detail-grid">
                <div><strong>{{ t.protokoll.colQueueId }}:</strong> {{ event.queue_id ?? '-' }}</div>
                <div><strong>{{ t.protokoll.colSize }}:</strong> {{ event.size != null ? event.size + ' B' : '-' }}</div>
                <div><strong>{{ t.protokoll.colDsn }}:</strong> {{ event.dsn ?? '-' }}</div>
                <div v-if="event.client_ip"><strong>Client-IP:</strong> {{ event.client_ip }}</div>
                <div v-if="event.sasl_username"><strong>SMTP-Benutzer:</strong> {{ event.sasl_username }}</div>
                <div class="detail-full"><strong>{{ t.protokoll.colMessage }}:</strong> {{ event.message ?? '-' }}</div>
              </div>
            </td>
          </tr>
        </template>
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
  overflow-x: auto;
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

.event-row {
  cursor: pointer;
  transition: background 0.1s;
}

.event-row:hover {
  background: #f8fafc;
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
.status-auth-failed { background: #fecaca; color: #7f1d1d; }

/* Source badges */
.source-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.source-badge .pi {
  font-size: 0.7rem;
  flex-shrink: 0;
}

.source-smtp {
  background: #dbeafe;
  color: #1e40af;
}

.source-ip {
  background: #f1f5f9;
  color: #475569;
}

.source-rejected {
  background: #fee2e2;
  color: #991b1b;
}

.source-auth-failed {
  background: #fecaca;
  color: #7f1d1d;
}

.source-attempted-user {
  background: #fef3c7;
  color: #92400e;
}

.source-banned {
  background: #7f1d1d;
  color: #fecaca;
}

/* Detail row */
.detail-row td {
  background: #f8fafc;
  padding: 1rem;
}

.detail-grid {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
  font-size: 0.85rem;
}

.detail-full {
  width: 100%;
  word-break: break-all;
}
</style>
