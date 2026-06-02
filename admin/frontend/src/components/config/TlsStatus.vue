<script setup lang="ts">
import Button from 'primevue/button'
import t from '../../i18n/de'
import { formatDateTimeShort } from '../../utils/dateFormat'

interface CertInfo {
  name: string
  role: string
  exists: boolean
  subject: string | null
  issuer: string | null
  expiry: string | null
  days_remaining: number | null
  status: string
  is_postfix_cert: boolean
}

defineProps<{
  tls: {
    enabled: boolean
    cert_exists: boolean
    cert_expiry: string | null
    cert_subject: string | null
    postfix_has_cert: boolean
    certs: CertInfo[]
  } | null
  loading: boolean
  syncing: boolean
  renewing: boolean
}>()

const emit = defineEmits<{
  sync: []
  renew: []
}>()

function formatDate(ts: string | null): string {
  return formatDateTimeShort(ts)
}

function statusClass(status: string): string {
  if (status === 'valid') return 'status-ok'
  if (status === 'expiring') return 'status-warn'
  return 'status-err' // expired | missing
}

function statusLabel(status: string): string {
  if (status === 'valid') return t.config.certStatusValid
  if (status === 'expiring') return t.config.certStatusExpiring
  if (status === 'expired') return t.config.certStatusExpired
  return t.config.certStatusMissing
}

function statusIcon(status: string): string {
  if (status === 'valid') return 'pi pi-lock'
  if (status === 'expiring') return 'pi pi-clock'
  return 'pi pi-lock-open'
}

function roleLabel(role: string): string {
  if (role === 'mail') return t.config.roleMail
  if (role === 'admin') return t.config.roleAdmin
  return t.config.roleOther
}

function daysText(cert: CertInfo): string {
  if (cert.days_remaining === null) return ''
  if (cert.status === 'expired') {
    return `${Math.abs(cert.days_remaining)} ${t.config.certDaysExpired}`
  }
  return `${cert.days_remaining} ${t.config.certDaysRemaining}`
}
</script>

<template>
  <div class="card">
    <h3>{{ t.config.tls }}</h3>

    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <template v-else-if="tls">
      <div class="tls-status">
        <!-- Liste aller von Caddy verwalteten Zertifikate -->
        <template v-if="tls.certs && tls.certs.length">
          <div v-for="cert in tls.certs" :key="cert.name" class="cert-block">
            <div class="status-indicator" :class="statusClass(cert.status)">
              <i :class="statusIcon(cert.status)" style="font-size: 1.5rem"></i>
              <div class="cert-head">
                <strong>{{ cert.name }}</strong>
                <div class="status-text">
                  {{ roleLabel(cert.role) }} · {{ statusLabel(cert.status) }}
                  <span v-if="cert.days_remaining !== null"> ({{ daysText(cert) }})</span>
                </div>
              </div>
              <span v-if="cert.is_postfix_cert" class="postfix-badge">
                <i class="pi pi-check-circle"></i> {{ t.config.postfixCertInUse }}
              </span>
            </div>

            <template v-if="cert.exists">
              <div class="info-row">
                <span class="info-label">{{ t.config.certExpiry }}:</span>
                <span>{{ formatDate(cert.expiry) }}</span>
              </div>
              <div v-if="cert.issuer" class="info-row">
                <span class="info-label">{{ t.config.certIssuer }}:</span>
                <span class="info-val">{{ cert.issuer }}</span>
              </div>
              <div v-if="cert.subject" class="info-row">
                <span class="info-label">{{ t.config.certSubject }}:</span>
                <span class="info-val">{{ cert.subject }}</span>
              </div>
            </template>
          </div>
        </template>

        <div v-else class="tls-info">
          <p>{{ t.config.certNoneFound }}</p>
          <p>Caddy verwaltet TLS-Zertifikate automatisch via Let's Encrypt. Das Zertifikat fuer den Mail-Hostname wird automatisch beschafft, sobald DNS korrekt konfiguriert ist.</p>
        </div>

        <!-- Aktionen -->
        <div class="cert-actions">
          <Button
            :label="syncing ? t.config.certSyncing : t.config.certSync"
            icon="pi pi-sync"
            :loading="syncing"
            :disabled="renewing"
            severity="info"
            class="action-btn"
            @click="emit('sync')"
          />
          <Button
            :label="renewing ? t.config.certRenewing : t.config.certRenew"
            icon="pi pi-refresh"
            :loading="renewing"
            :disabled="syncing"
            severity="warning"
            class="action-btn"
            @click="emit('renew')"
          />
        </div>

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

.cert-block {
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.cert-block:last-of-type {
  border-bottom: none;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 0.5rem;
}

.cert-head {
  flex: 1;
  min-width: 0;
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

.status-err {
  background: #fee2e2;
  color: #991b1b;
}

.postfix-badge {
  font-size: 0.7rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.6);
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.info-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.4rem 0;
  font-size: 0.9rem;
}

.info-label {
  color: #64748b;
  flex-shrink: 0;
}

.info-val {
  text-align: right;
  word-break: break-all;
}

.tls-info {
  padding: 0.5rem 0;
  color: #64748b;
  font-size: 0.85rem;
}

.cert-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.75rem;
}

.action-btn {
  flex: 1;
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
