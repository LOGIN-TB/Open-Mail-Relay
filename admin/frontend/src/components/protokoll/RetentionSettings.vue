<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProtokollStore } from '../../stores/protokoll'
import t from '../../i18n/de'

const store = useProtokollStore()
const localDays = ref(30)
const localStatsDays = ref(365)
const saved = ref(false)

onMounted(async () => {
  await store.fetchRetention()
  localDays.value = store.retention.retention_days
  localStatsDays.value = store.retention.stats_retention_days
})

async function save() {
  await store.updateRetention({
    retention_days: localDays.value,
    stats_retention_days: localStatsDays.value,
  })
  localDays.value = store.retention.retention_days
  localStatsDays.value = store.retention.stats_retention_days
  saved.value = true
  setTimeout(() => { saved.value = false }, 3000)
}
</script>

<template>
  <div class="card retention-card">
    <h3>{{ t.protokoll.retention }}</h3>
    <div class="retention-fields">
      <label class="field">
        <span>{{ t.protokoll.retentionEvents }}</span>
        <input type="number" v-model.number="localDays" min="1" max="3650" class="num-input" />
      </label>
      <label class="field">
        <span>{{ t.protokoll.retentionStats }}</span>
        <input type="number" v-model.number="localStatsDays" min="1" max="3650" class="num-input" />
      </label>
      <button class="btn btn-primary" @click="save">{{ t.protokoll.retentionSave }}</button>
    </div>
    <div v-if="saved" class="saved-msg">{{ t.protokoll.retentionSaved }}</div>
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

.retention-fields {
  display: flex;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.85rem;
  color: #475569;
}

.num-input {
  width: 100px;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.85rem;
}

.num-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}

.saved-msg {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: #16a34a;
  font-weight: 600;
}
</style>
