<script setup lang="ts">
import t from '../../i18n/de'

defineProps<{
  queue: {
    queue_id: string
    size: string
    arrival_time: string
    sender: string
    recipients: string[]
  }[]
}>()
</script>

<template>
  <div class="card">
    <h3>{{ t.dashboard.queueStatus }}</h3>
    <div v-if="queue.length === 0" class="empty">
      <i class="pi pi-check-circle" style="font-size: 2rem; color: #22c55e"></i>
      <p>Warteschlange ist leer</p>
    </div>
    <div v-else class="queue-list">
      <div v-for="entry in queue" :key="entry.queue_id" class="queue-item">
        <div class="queue-header">
          <code>{{ entry.queue_id }}</code>
          <span class="queue-size">{{ entry.size }} B</span>
        </div>
        <div class="queue-detail">
          <span><i class="pi pi-user"></i> {{ entry.sender }}</span>
        </div>
        <div class="queue-detail">
          <span><i class="pi pi-arrow-right"></i> {{ entry.recipients.join(', ') }}</span>
        </div>
        <div class="queue-time">{{ entry.arrival_time }}</div>
      </div>
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
}

.card h3 {
  font-size: 1rem;
  color: #1e293b;
  margin-bottom: 1rem;
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem;
  color: #64748b;
}

.queue-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 300px;
  overflow-y: auto;
}

.queue-item {
  padding: 0.75rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}

.queue-header code {
  font-size: 0.8rem;
  font-weight: 600;
  color: #3b82f6;
}

.queue-size {
  font-size: 0.75rem;
  color: #64748b;
}

.queue-detail {
  font-size: 0.8rem;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.2rem;
}

.queue-time {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-top: 0.4rem;
}
</style>
