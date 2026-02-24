<script setup lang="ts">
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import t from '../../i18n/de'

const toast = useToast()

interface PortInfo {
  port: number
  protocol: string
  tls_mode: string
  tls_required: boolean
}

const props = defineProps<{
  connection: {
    smtp_host: string
    ports: PortInfo[]
    auth_required: boolean
    tls_available: boolean
    allowed_networks: string[]
    max_message_size_mb: number
  } | null
  loading: boolean
}>()

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  toast.add({ severity: 'info', summary: t.config.copied, life: 2000 })
}

function copyAllSettings() {
  if (!props.connection) return
  const c = props.connection
  const portLines = c.ports.map(p => `  Port ${p.port} (${p.protocol}): ${p.tls_mode}`)
  const text = [
    `SMTP-Server: ${c.smtp_host}`,
    `Ports:`,
    ...portLines,
    `Authentifizierung: ${c.auth_required ? 'Ja' : 'Keine (IP-basiert)'}`,
    `Max. Nachrichtengroesse: ${c.max_message_size_mb} MB`,
    `Erlaubte Netzwerke: ${c.allowed_networks.join(', ')}`,
  ].join('\n')
  copyToClipboard(text)
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3>{{ t.config.connection }}</h3>
      <Button
        v-if="connection"
        icon="pi pi-copy"
        severity="secondary"
        size="small"
        text
        title="Alle Einstellungen kopieren"
        @click="copyAllSettings"
      />
    </div>
    <p class="desc">{{ t.config.connectionDesc }}</p>

    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <template v-else-if="connection">
      <div class="settings-list">
        <div class="setting-row" @click="copyToClipboard(connection.smtp_host)">
          <div class="setting-label">{{ t.config.smtpHost }}</div>
          <div class="setting-value copyable">
            <code>{{ connection.smtp_host }}</code>
            <i class="pi pi-copy copy-icon"></i>
          </div>
        </div>

        <!-- Ports -->
        <div class="setting-row ports-row">
          <div class="setting-label">{{ t.config.ports }}</div>
          <div class="ports-list">
            <div
              v-for="p in connection.ports"
              :key="p.port"
              class="port-entry"
              @click="copyToClipboard(String(p.port))"
            >
              <div class="port-header">
                <code class="port-number">{{ p.port }}</code>
                <span class="port-protocol">{{ p.protocol }}</span>
              </div>
              <div class="port-tls">
                <span>{{ p.tls_mode }}</span>
                <span v-if="p.tls_required && connection.tls_available" class="tls-active">aktiv</span>
                <span v-else-if="p.tls_required && !connection.tls_available" class="tls-inactive">kein Zertifikat</span>
                <span v-else-if="connection.tls_available" class="tls-active">aktiv</span>
              </div>
            </div>
          </div>
          <div class="port-hint">
            <i class="pi pi-info-circle"></i>
            <span>{{ t.config.portHint }}</span>
          </div>
          <div v-if="!connection.tls_available" class="port-warning">
            <i class="pi pi-exclamation-triangle"></i>
            <span>{{ t.config.portNoCert }}</span>
          </div>
        </div>

        <div class="setting-row">
          <div class="setting-label">{{ t.config.authRequired }}</div>
          <div class="setting-value">
            <span class="auth-badge">{{ connection.auth_required ? 'Ja (SASL)' : t.config.noAuth }}</span>
          </div>
        </div>

        <div class="setting-row">
          <div class="setting-label">{{ t.config.maxSize }}</div>
          <div class="setting-value">{{ connection.max_message_size_mb }} MB</div>
        </div>

        <div class="setting-row networks-row">
          <div class="setting-label">{{ t.config.allowedNetworks }}</div>
          <div class="setting-value networks">
            <code
              v-for="net in connection.allowed_networks"
              :key="net"
              class="network-tag"
              @click.stop="copyToClipboard(net)"
            >{{ net }}</code>
          </div>
        </div>
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
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card h3 {
  font-size: 1rem;
  color: #1e293b;
}

.desc {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0.4rem 0 1rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.settings-list {
  display: flex;
  flex-direction: column;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 0;
  border-bottom: 1px solid #f1f5f9;
}

.setting-row:last-child {
  border-bottom: none;
}

.setting-label {
  font-size: 0.85rem;
  color: #64748b;
  font-weight: 500;
}

.setting-value {
  font-size: 0.9rem;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.setting-value code {
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
}

.copyable {
  cursor: pointer;
  transition: opacity 0.15s;
}

.copyable:hover {
  opacity: 0.7;
}

.copy-icon {
  font-size: 0.7rem;
  color: #94a3b8;
}

.auth-badge {
  background: #dcfce7;
  color: #166534;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.tls-active {
  background: #dcfce7;
  color: #166534;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
}

.tls-inactive {
  background: #fef3c7;
  color: #92400e;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
}

.ports-row {
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}

.ports-list {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.port-entry {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: #f8fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.port-entry:hover {
  background: #f1f5f9;
}

.port-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.port-number {
  background: #e2e8f0;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 700;
}

.port-protocol {
  font-size: 0.8rem;
  color: #64748b;
  font-weight: 500;
}

.port-tls {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
  color: #475569;
}

.port-hint {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  background: #eff6ff;
  border-radius: 8px;
  font-size: 0.78rem;
  color: #1e40af;
  line-height: 1.4;
}

.port-hint i {
  margin-top: 1px;
  flex-shrink: 0;
}

.port-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  background: #fef3c7;
  border-radius: 8px;
  font-size: 0.78rem;
  color: #92400e;
  line-height: 1.4;
}

.port-warning i {
  margin-top: 1px;
  flex-shrink: 0;
}

.networks-row {
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
}

.networks {
  flex-wrap: wrap;
  gap: 0.4rem;
}

.network-tag {
  cursor: pointer;
  transition: background 0.15s;
}

.network-tag:hover {
  background: #e2e8f0;
}
</style>
