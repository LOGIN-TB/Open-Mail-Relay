<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import t from '../../i18n/de'

const lines = ref<string[]>([])
const connected = ref(false)
const autoScroll = ref(true)
const logContainer = ref<HTMLElement | null>(null)

const MAX_LINES = 1000
let ws: WebSocket | null = null

function connect() {
  if (ws && ws.readyState <= WebSocket.OPEN) {
    ws.close()
  }

  const token = localStorage.getItem('token')
  if (!token) return

  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/api/logs/stream?token=${token}`)

  ws.onopen = () => {
    connected.value = true
  }

  ws.onmessage = (event) => {
    // Ignore keepalive pings (binary frames or empty strings)
    if (!event.data || typeof event.data !== 'string') return
    lines.value.push(event.data)
    if (lines.value.length > MAX_LINES) {
      lines.value = lines.value.slice(-MAX_LINES)
    }
    if (autoScroll.value) {
      nextTick(scrollToBottom)
    }
  }

  ws.onclose = () => {
    connected.value = false
  }

  ws.onerror = () => {
    connected.value = false
  }
}

function disconnect() {
  if (ws) {
    ws.close()
    ws = null
  }
}

function clearLog() {
  lines.value = []
}

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

onMounted(() => {
  connect()
})

onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <div class="live-log-panel">
    <div class="log-controls">
      <span class="connection-status" :class="connected ? 'conn-ok' : 'conn-off'">
        <i class="pi" :class="connected ? 'pi-circle-fill' : 'pi-circle'"></i>
        {{ connected ? t.protokoll.liveConnected : t.protokoll.liveDisconnected }}
      </span>

      <label class="auto-scroll-toggle">
        <input type="checkbox" v-model="autoScroll" />
        {{ t.protokoll.liveAutoScroll }}
      </label>

      <button class="ctrl-btn" @click="clearLog">
        <i class="pi pi-trash"></i> {{ t.protokoll.liveClear }}
      </button>
      <button class="ctrl-btn" @click="connect" :disabled="connected">
        <i class="pi pi-refresh"></i> {{ t.protokoll.liveReconnect }}
      </button>
    </div>

    <div ref="logContainer" class="log-output">
      <div v-if="lines.length === 0" class="log-empty">Waiting for log data...</div>
      <div v-for="(line, i) in lines" :key="i" class="log-line">{{ line }}</div>
    </div>
  </div>
</template>

<style scoped>
.live-log-panel {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.log-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.75rem 1rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}

.connection-status {
  font-size: 0.85rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.conn-ok { color: #16a34a; }
.conn-off { color: #dc2626; }

.auto-scroll-toggle {
  font-size: 0.85rem;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 0.3rem;
  cursor: pointer;
  margin-left: auto;
}

.ctrl-btn {
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  border: 1px solid #e2e8f0;
  background: #f1f5f9;
  color: #475569;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  transition: background 0.15s;
}

.ctrl-btn:hover:not(:disabled) {
  background: #e2e8f0;
}

.ctrl-btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.log-output {
  background: #0f172a;
  color: #e2e8f0;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.78rem;
  line-height: 1.5;
  padding: 1rem;
  border-radius: 12px;
  height: 500px;
  overflow-y: auto;
  overflow-x: auto;
  white-space: pre;
}

.log-empty {
  color: #64748b;
  font-style: italic;
}

.log-line {
  padding: 1px 0;
}

.log-line:hover {
  background: rgba(59, 130, 246, 0.1);
}
</style>
