<script setup lang="ts">
import t from '../../i18n/de'

export interface BillingItem {
  smtp_user_id: number
  username: string
  company: string | null
  package_name: string | null
  package_limit: number | null
  sent_count: number
  overage_count: number
  overage_emails: number
}

export interface BillingData {
  year_month: string
  items: BillingItem[]
  total_sent: number
  total_overage_units: number
}

defineProps<{
  data: BillingData | null
  loading: boolean
}>()

function fmt(n: number): string {
  return n.toLocaleString('de-DE')
}
</script>

<template>
  <div class="card">
    <div v-if="loading" class="loading">{{ t.common.loading }}</div>
    <div v-else-if="!data || data.items.length === 0" class="no-data">{{ t.billing.noData }}</div>
    <table v-else class="billing-table">
      <thead>
        <tr>
          <th>{{ t.billing.username }}</th>
          <th>{{ t.billing.company }}</th>
          <th>{{ t.billing.package }}</th>
          <th style="text-align: right">{{ t.billing.limit }}</th>
          <th style="text-align: right">{{ t.billing.sent }}</th>
          <th style="text-align: right">{{ t.billing.overageEmails }}</th>
          <th>{{ t.billing.overageUnits }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in data.items" :key="item.smtp_user_id">
          <td><strong>{{ item.username }}</strong></td>
          <td class="cell-text">{{ item.company || '-' }}</td>
          <td>
            <span v-if="item.package_name" class="package-badge">{{ item.package_name }}</span>
            <span v-else class="cell-muted">{{ t.billing.noPackage }}</span>
          </td>
          <td style="text-align: right" class="cell-text">
            {{ item.package_limit != null ? fmt(item.package_limit) : '-' }}
          </td>
          <td style="text-align: right" :class="{ 'overage-highlight': item.overage_count > 0 }">
            {{ fmt(item.sent_count) }}
          </td>
          <td style="text-align: right" class="cell-text">
            {{ item.overage_emails > 0 ? fmt(item.overage_emails) : '-' }}
          </td>
          <td>
            <span v-if="item.overage_count > 0" class="overage-badge">
              {{ item.overage_count }}x Ext-1K
            </span>
            <span v-else class="cell-muted">-</span>
          </td>
        </tr>
      </tbody>
      <tfoot>
        <tr class="total-row">
          <td colspan="4"><strong>{{ t.billing.totalSent }}</strong></td>
          <td style="text-align: right"><strong>{{ fmt(data.total_sent) }}</strong></td>
          <td></td>
          <td>
            <strong v-if="data.total_overage_units > 0">
              {{ data.total_overage_units }}x Ext-1K
            </strong>
          </td>
        </tr>
      </tfoot>
    </table>
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

.loading,
.no-data {
  text-align: center;
  padding: 2rem;
  color: #94a3b8;
}

.billing-table {
  width: 100%;
  border-collapse: collapse;
}

.billing-table th {
  text-align: left;
  padding: 0.6rem 0.75rem;
  border-bottom: 2px solid #e2e8f0;
  color: #64748b;
  font-weight: 600;
  font-size: 0.85rem;
}

.billing-table td {
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.85rem;
}

.cell-text {
  color: #475569;
}

.cell-muted {
  color: #94a3b8;
  font-size: 0.8rem;
}

.package-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #f1f5f9;
  color: #334155;
  font-size: 0.75rem;
  border-radius: 12px;
  font-weight: 600;
}

.overage-highlight {
  color: #dc2626;
  font-weight: 600;
}

.overage-badge {
  display: inline-block;
  padding: 2px 8px;
  background: #fef3c7;
  color: #92400e;
  font-size: 0.75rem;
  border-radius: 12px;
  font-weight: 600;
}

.total-row {
  background: #f8fafc;
}

.total-row td {
  border-bottom: none;
  border-top: 2px solid #e2e8f0;
}
</style>
