<script setup lang="ts">
import { useProtokollStore } from '../../stores/protokoll'
import t from '../../i18n/de'

const store = useProtokollStore()
</script>

<template>
  <div class="filters">
    <div class="filter-row">
      <select v-model="store.filters.status" class="filter-input">
        <option value="">{{ t.protokoll.allStatuses }}</option>
        <option value="sent">{{ t.protokoll.sent }}</option>
        <option value="deferred">{{ t.protokoll.deferred }}</option>
        <option value="bounced">{{ t.protokoll.bounced }}</option>
        <option value="rejected">{{ t.protokoll.rejected }}</option>
        <option value="auth_failed">{{ t.protokoll.authFailed }}</option>
      </select>

      <input
        v-model="store.filters.search"
        type="text"
        class="filter-input search-input"
        :placeholder="t.protokoll.filterSearch"
        @keyup.enter="store.applyFilters()"
      />

      <input
        v-model="store.filters.dateFrom"
        type="date"
        class="filter-input"
      />
      <input
        v-model="store.filters.dateTo"
        type="date"
        class="filter-input"
      />

      <button class="btn btn-primary" @click="store.applyFilters()">
        <i class="pi pi-search"></i> {{ t.protokoll.filterApply }}
      </button>
      <button class="btn btn-secondary" @click="store.resetFilters()">
        {{ t.protokoll.filterReset }}
      </button>
      <button class="btn btn-secondary" @click="store.exportCsv()">
        <i class="pi pi-download"></i> {{ t.protokoll.exportCsv }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.filters {
  background: white;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.filter-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}

.filter-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.85rem;
  background: white;
  color: #334155;
}

.filter-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.search-input {
  flex: 1;
  min-width: 200px;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  white-space: nowrap;
  transition: background 0.15s;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.btn-secondary {
  background: #f1f5f9;
  color: #475569;
}

.btn-secondary:hover {
  background: #e2e8f0;
}
</style>
