<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { TransportRule } from '../../stores/throttle'
import t from '../../i18n/de'

const props = defineProps<{
  rule: TransportRule | null
}>()

const emit = defineEmits<{
  save: [data: any]
  cancel: []
}>()

const form = ref({
  domain_pattern: '',
  transport_name: '',
  concurrency_limit: 5,
  rate_delay_seconds: 1,
  is_active: true,
  description: '',
})

onMounted(() => {
  if (props.rule) {
    form.value = {
      domain_pattern: props.rule.domain_pattern,
      transport_name: props.rule.transport_name,
      concurrency_limit: props.rule.concurrency_limit,
      rate_delay_seconds: props.rule.rate_delay_seconds,
      is_active: props.rule.is_active,
      description: props.rule.description || '',
    }
  }
})

function submit() {
  emit('save', { ...form.value })
}
</script>

<template>
  <div class="form-overlay" @click.self="emit('cancel')">
    <div class="form-card">
      <h4>{{ rule ? t.throttling.editTransport : t.throttling.addTransport }}</h4>
      <form @submit.prevent="submit">
        <div class="form-group">
          <label>{{ t.throttling.domain }}</label>
          <input v-model="form.domain_pattern" type="text" placeholder="z.B. gmail.com" required />
        </div>
        <div class="form-group">
          <label>{{ t.throttling.transport }}</label>
          <input v-model="form.transport_name" type="text" placeholder="z.B. gmail_throttled" required />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>{{ t.throttling.concurrency }}</label>
            <input v-model.number="form.concurrency_limit" type="number" min="1" max="50" required />
          </div>
          <div class="form-group">
            <label>{{ t.throttling.delay }}</label>
            <input v-model.number="form.rate_delay_seconds" type="number" min="0" max="60" required />
          </div>
        </div>
        <div class="form-group">
          <label>{{ t.throttling.description }}</label>
          <input v-model="form.description" type="text" />
        </div>
        <div class="form-group checkbox">
          <label>
            <input v-model="form.is_active" type="checkbox" />
            {{ t.throttling.active }}
          </label>
        </div>
        <div class="form-actions">
          <button type="button" class="btn" @click="emit('cancel')">{{ t.common.cancel }}</button>
          <button type="submit" class="btn btn-primary">{{ t.common.save }}</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.form-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.form-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.form-card h4 {
  margin: 0 0 1.25rem;
  font-size: 1.1rem;
  color: #1e293b;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.35rem;
}

.form-group input[type="text"],
.form-group input[type="number"] {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  box-sizing: border-box;
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1.5rem;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: white;
  color: #475569;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.btn-primary:hover {
  background: #2563eb;
}
</style>
