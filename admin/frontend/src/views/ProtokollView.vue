<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProtokollStore } from '../stores/protokoll'
import EventFilters from '../components/protokoll/EventFilters.vue'
import EventTable from '../components/protokoll/EventTable.vue'
import LiveLogPanel from '../components/protokoll/LiveLogPanel.vue'
import RetentionSettings from '../components/protokoll/RetentionSettings.vue'
import t from '../i18n/de'

const store = useProtokollStore()
const activeTab = ref<'events' | 'live'>('events')

onMounted(() => {
  store.fetchEvents()
})
</script>

<template>
  <div class="protokoll">
    <h2>{{ t.protokoll.title }}</h2>

    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'events' }"
        @click="activeTab = 'events'"
      >
        <i class="pi pi-list"></i> {{ t.protokoll.events }}
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'live' }"
        @click="activeTab = 'live'"
      >
        <i class="pi pi-bolt"></i> {{ t.protokoll.liveLog }}
      </button>
    </div>

    <template v-if="activeTab === 'events'">
      <EventFilters />
      <EventTable />
      <RetentionSettings />
    </template>

    <template v-if="activeTab === 'live'">
      <LiveLogPanel />
    </template>
  </div>
</template>

<style scoped>
.protokoll {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.protokoll h2 {
  font-size: 1.5rem;
  color: #1e293b;
}

.tabs {
  display: flex;
  gap: 0.25rem;
  background: #f1f5f9;
  border-radius: 10px;
  padding: 4px;
  width: fit-content;
}

.tab-btn {
  padding: 0.5rem 1.25rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  background: transparent;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s;
}

.tab-btn:hover {
  color: #334155;
}

.tab-btn.active {
  background: white;
  color: #1e293b;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
</style>
