<script setup lang="ts">
import Button from 'primevue/button'
import t from '../../i18n/de'

defineProps<{
  tls: {
    enabled: boolean
    cert_exists: boolean
    cert_expiry: string | null
    cert_subject: string | null
    postfix_has_cert: boolean
  } | null
  loading: boolean
  syncing: boolean
}>()

const emit = defineEmits<{
  sync: []
}>()

function formatDate(ts: string | null): string {
  if (!ts) return '-'
  return new Date(ts).toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div class="card">
    <h3>{{ t.config.tls }}</h3>

    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <template v-else-if="tls">
      <div class="tls-status">
        <!-- Caddy cert status -->
        <div class="status-indicator" :class="tls.cert_exists ? 'status-ok' : 'status-warn'">
          <i :class="tls.cert_exists ? 'pi pi-lock' : 'pi pi-lock-open'" style="font-size: 1.5rem"></i>
          <div>
            <strong>Let's Encrypt</strong>
            <div class="status-text">{{ tls.cert_exists ? t.config.tlsEnabled : t.config.tlsDisabled }}</div>
          </div>
        </div>

        <template v-if="tls.cert_exists">
          <div class="info-row">
            <span class="info-label">{{ t.config.certExpiry }}:</span>
            <span>{{ formatDate(tls.cert_expiry) }}</span>
          </div>
          <div v-if="tls.cert_subject" class="info-row">
            <span class="info-label">{{ t.config.certSubject }}:</span>
            <span>{{ tls.cert_subject }}</span>
          </div>
        </template>
        <div v-else class="tls-info">
          <p>Caddy verwaltet TLS-Zertifikate automatisch via Let's Encrypt. Das Zertifikat fuer den Mail-Hostname wird automatisch beschafft, sobald DNS korrekt konfiguriert ist.</p>
        </div>

        <!-- Postfix cert status -->
        <div class="status-indicator postfix-status" :class="tls.postfix_has_cert ? 'status-ok' : 'status-warn'">
          <i :class="tls.postfix_has_cert ? 'pi pi-check-circle' : 'pi pi-exclamation-triangle'" style="font-size: 1.5rem"></i>
          <div>
            <strong>{{ t.config.postfixHasCert }}</strong>
            <div class="status-text">{{ tls.postfix_has_cert ? t.config.postfixCertYes : t.config.postfixCertNo }}</div>
          </div>
        </div>

        <!-- Sync button -->
        <Button
          :label="syncing ? t.config.certSyncing : t.config.certSync"
          icon="pi pi-sync"
          :loading="syncing"
          severity="info"
          class="sync-btn"
          @click="emit('sync')"
        />

        <div class="auto-renew-hint">
          <i class="pi pi-refresh"></i>
          <span>{{ t.config.certAutoRenew }}</span>
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

.card h3 {
  font-size: 1rem;
  color: #1e293b;
  margin-bottom: 1rem;
}

.loading {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 0.75rem;
}

.postfix-status {
  margin-top: 0.5rem;
}

.status-text {
  font-size: 0.8rem;
  margin-top: 2px;
}

.status-ok {
  background: #dcfce7;
  color: #166534;
}

.status-warn {
  background: #fef3c7;
  color: #92400e;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.9rem;
}

.info-label {
  color: #64748b;
}

.tls-info {
  padding: 0.5rem 0;
  color: #64748b;
  font-size: 0.85rem;
}

.sync-btn {
  width: 100%;
  margin-top: 0.75rem;
}

.auto-renew-hint {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  background: #eff6ff;
  border-radius: 8px;
  font-size: 0.78rem;
  color: #1e40af;
  line-height: 1.4;
  margin-top: 0.75rem;
}

.auto-renew-hint i {
  margin-top: 1px;
  flex-shrink: 0;
}
</style>
