<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useThrottleStore } from '../stores/throttle'
import ThrottleOverview from '../components/throttle/ThrottleOverview.vue'
import WarmupPhases from '../components/throttle/WarmupPhases.vue'
import TransportRules from '../components/throttle/TransportRules.vue'
import ThrottleSettings from '../components/throttle/ThrottleSettings.vue'
import t from '../i18n/de'

const store = useThrottleStore()

let refreshInterval: ReturnType<typeof setInterval>

onMounted(() => {
  store.fetchAll()
  refreshInterval = setInterval(() => store.fetchMetrics(), 30000)
})

onUnmounted(() => {
  clearInterval(refreshInterval)
})
</script>

<template>
  <div class="throttle-page">
    <h2>{{ t.throttling.title }}</h2>

    <ThrottleOverview
      :config="store.config"
      :warmup="store.warmup"
      :metrics="store.metrics"
    />

    <div class="throttle-grid">
      <WarmupPhases :phases="store.phases" :warmup="store.warmup" />
      <TransportRules :transports="store.transports" />
    </div>

    <ThrottleSettings :config="store.config" />
  </div>
</template>

<style scoped>
.throttle-page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.throttle-page h2 {
  font-size: 1.5rem;
  color: #1e293b;
}

.throttle-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 1200px) {
  .throttle-grid {
    grid-template-columns: 1fr;
  }
}
</style>
