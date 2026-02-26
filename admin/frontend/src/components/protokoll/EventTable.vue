<script setup lang="ts">
import { ref } from 'vue'
import { useProtokollStore } from '../../stores/protokoll'
import t from '../../i18n/de'
import { formatDateTime } from '../../utils/dateFormat'

defineProps<{
  bannedIps?: Set<string>
}>()

const store = useProtokollStore()
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
  }
  return map[status] ?? ''
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    sent: t.protokoll.sent,
    deferred: t.protokoll.deferred,
    bounced: t.protokoll.bounced,
    rejected: t.protokoll.rejected,
  }
  return map[status] ?? status
}

function formatTime(ts: string): string {
  return formatDateTime(ts)
}

function sourceDisplay(event: { sasl_username: string | null; client_ip: string | null; status: string }) {
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
    <div v-if="store.loading" class="no-data">{{ t.common.loading }}</div>
    <div v-else-if="store.events.length === 0" class="no-data">{{ t.protokoll.noEvents }}</div>
    <template v-else>
      <div class="table-scroll">
      <table class="event-table">
        <thead>
          <tr>
            <th>{{ t.protokoll.colTime }}</th>
            <th>{{ t.protokoll.colStatus }}</th>
            <th>{{ t.protokoll.colSource }}</th>
            <th>{{ t.protokoll.colSender }}</th>
            <th>{{ t.protokoll.colRecipient }}</th>
            <th>{{ t.protokoll.colRelay }}</th>
            <th>{{ t.protokoll.colDelay }}</th>
            <th>{{ t.protokoll.colDsn }}</th>
            <th>{{ t.protokoll.colMessage }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="event in store.events" :key="event.id">
            <tr class="event-row" @click="toggleExpand(event.id)">
              <td class="time-col">{{ formatTime(event.timestamp) }}</td>
              <td><span class="status-badge" :class="statusClass(event.status)">{{ statusLabel(event.status) }}</span></td>
              <td>
                <span v-if="sourceDisplay(event).icon" class="source-badge" :class="sourceDisplay(event).cssClass">
                  <i class="pi" :class="sourceDisplay(event).icon"></i>
                  {{ sourceDisplay(event).text }}
                </span>
                <span v-else>-</span>
                <span v-if="event.client_ip && bannedIps?.has(event.client_ip)" class="source-badge source-banned">
                  <i class="pi pi-ban"></i> {{ t.ipBans.banned }}
                </span>
              </td>
              <td class="truncate">{{ event.sender ?? '-' }}</td>
              <td class="truncate">{{ event.recipient ?? '-' }}</td>
              <td class="truncate">{{ event.relay ?? '-' }}</td>
              <td>{{ event.delay != null ? event.delay.toFixed(1) + 's' : '-' }}</td>
              <td>{{ event.dsn ?? '-' }}</td>
              <td class="truncate msg-col">{{ event.message ?? '-' }}</td>
            </tr>
            <tr v-if="expandedId === event.id" class="detail-row">
              <td colspan="9">
                <div class="detail-grid">
                  <div><strong>{{ t.protokoll.colQueueId }}:</strong> {{ event.queue_id ?? '-' }}</div>
                  <div><strong>{{ t.protokoll.colSize }}:</strong> {{ event.size != null ? event.size + ' B' : '-' }}</div>
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

      <div class="pagination">
        <button class="page-btn" :disabled="store.page <= 1" @click="store.setPage(store.page - 1)">
          <i class="pi pi-chevron-left"></i>
        </button>
        <span class="page-info">
          {{ t.protokoll.page }} {{ store.page }} {{ t.protokoll.of }} {{ store.pages }}
          ({{ t.protokoll.total }}: {{ store.total }})
        </span>
        <button class="page-btn" :disabled="store.page >= store.pages" @click="store.setPage(store.page + 1)">
          <i class="pi pi-chevron-right"></i>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.card {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
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

.event-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

.event-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.8rem;
  white-space: nowrap;
  position: sticky;
  top: 0;
  background: white;
  z-index: 1;
}

.event-table td {
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
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.msg-col {
  max-width: 200px;
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

.source-banned {
  background: #7f1d1d;
  color: #fecaca;
}

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

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding-top: 1rem;
}

.page-btn {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.4rem 0.7rem;
  cursor: pointer;
  color: #475569;
  transition: background 0.15s;
}

.page-btn:hover:not(:disabled) {
  background: #e2e8f0;
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.page-info {
  font-size: 0.85rem;
  color: #64748b;
}
</style>
