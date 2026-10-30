<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { erp, money, today, useWorkspace } from '../composables/erp'
import { syncPage, usePage } from '../composables/forms'
import { downloadText } from '../composables/download'
import UiPagination from '../components/ui/UiPagination.vue'
import UiDialog from '../components/ui/UiDialog.vue'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const invoiceId = computed(() => String(route.query.invoice_id || ''))
const orderId = computed(() => String(route.query.order_id || ''))
const source = computed(() => invoiceId.value || orderId.value)
const view = ref(source.value ? 'entries' : 'reports')
const dateFrom = ref(source.value ? '1000-01-01' : `${today().slice(0, 4)}-01-01`)
const dateTo = ref(source.value ? '9999-12-31' : today())
const account = ref(''), journal = ref(''), search = ref('')
const page = usePage([dateFrom, dateTo, account, journal, search, invoiceId, orderId])
const actionError = ref(''), message = ref(''), lockDate = ref(today()), lockDialog = ref(null)
const canClose = computed(() => auth.activeCompany?.role === 'owner')
const { data, error, loading, refresh } = useWorkspace(async id => {
  const dates = { date_from: dateFrom.value, date_to: dateTo.value }
  const [settings, report, entries] = await Promise.all([
    erp(id, 'accounting/settings/'), erp(id, `accounting/reports/?${new URLSearchParams(dates)}`),
    erp(id, `accounting/entries/?${new URLSearchParams({ ...dates, account: account.value, journal: journal.value,
      q: search.value, page: String(page.value), invoice_id: invoiceId.value, order_id: orderId.value })}`),
  ])
  return { settings, report, entries, page: entries.page }
}, [dateFrom, dateTo, account, journal, search, page, invoiceId, orderId])
syncPage(page, data)
watch([invoiceId, orderId], () => { if (source.value) { dateFrom.value = '1000-01-01'; dateTo.value = '9999-12-31'; view.value = 'entries' } })
watch(() => auth.activeCompanyId, () => {
  lockDialog.value?.close(); actionError.value = ''; message.value = ''
  if (source.value) router.replace({ path: '/accounting', query: {} })
})
function drill(code) { account.value = code; view.value = 'entries' }
async function synchronize() {
  auth.busy = true; actionError.value = ''; message.value = ''
  try {
    const result = await erp(auth.activeCompanyId, 'accounting/sync/', { method: 'POST', data: {} })
    message.value = `Imported ${result.created} historical postings.`
    await refresh()
  } catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
async function closeDates() {
  auth.busy = true; actionError.value = ''
  try {
    await erp(auth.activeCompanyId, 'accounting/settings/', { method: 'PATCH', data: {
      locked_through: lockDate.value, expected_version: data.value.settings.version,
    } })
    lockDialog.value.close(); message.value = `Accounting closed through ${lockDate.value}.`; await refresh()
  } catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
function exportReport() {
  const report = data.value.report
  const rows = [['Code', 'Account', 'Type', 'Opening debit minus credit', 'Period debit', 'Period credit', 'Closing debit', 'Closing credit'],
    ...report.accounts.map(row => [row.code, row.name, row.kind, row.opening, row.debit, row.credit, row.closing_debit, row.closing_credit]),
    ['', 'Total', '', '', report.debit, report.credit, report.closing_debit, report.closing_credit]]
  downloadText(rows.map(row => row.map(cell => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\r\n'),
    `trial-balance-${auth.activeCompanyId}-${report.date_from}-${report.date_to}-${report.currency}.csv`)
}
</script>

<template>
  <section class="business-page accounting-page">
    <div class="control-panel">
      <div class="control-title"><h1>Accounting</h1><span class="muted">{{ auth.activeCompany?.name }}</span></div>
      <div class="control-actions">
        <button v-if="canClose && data" class="button-secondary" :disabled="auth.busy || loading" @click="actionError = ''; lockDialog.showModal()">Close dates</button>
        <button class="button-secondary" :disabled="loading || auth.busy" @click="refresh">Refresh</button>
      </div>
      <div class="catalog-filters">
        <label>From<input v-model="dateFrom" name="accounting_from" type="date" required /></label>
        <label>Through<input v-model="dateTo" name="accounting_to" type="date" required /></label>
        <label v-if="view === 'entries'">Account<select v-model="account" name="ledger_account"><option value="">All accounts</option><option v-for="item in data?.settings.accounts" :key="item.code" :value="item.code">{{ item.code }} {{ item.name }}</option></select></label>
        <label v-if="view === 'entries'">Journal<select v-model="journal" name="ledger_journal"><option value="">All journals</option><option value="sales">Sales</option><option value="purchases">Purchases</option><option value="bank">Bank</option><option value="cash">Cash</option></select></label>
        <label v-if="view === 'entries'">Search<input v-model="search" name="ledger_search" placeholder="Entry, invoice, order or partner" type="search" maxlength="200" /></label>
      </div>
    </div>
    <div class="workspace-content dashboard-content">
      <p v-if="!auth.activeCompanyId" class="empty-state">Choose a company to view its accounts.</p>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p>
      <p v-if="message" class="notice success" role="status">{{ message }}</p>
      <p v-if="loading" class="loading-state" role="status">Loading accounting…</p>
      <template v-if="data">
        <p class="muted accounting-policy">Accrual basis · {{ data.settings.currency }} · {{ data.settings.locked_through ? `Locked through ${data.settings.locked_through}` : 'No closed dates' }}. Purchases are expensed on bill issue; stock quantities are managed separately.</p>
        <div v-if="data.settings.unposted_invoices || data.settings.unposted_payments" class="notice accounting-missing" role="status">
          Reports are incomplete: {{ data.settings.unposted_invoices }} issued documents and {{ data.settings.unposted_payments }} payments need historical postings.
          <button v-if="auth.canManage" class="button-secondary" :disabled="auth.busy" @click="synchronize">Import historical postings</button>
          <span v-else>Ask an owner or administrator to import them.</span>
        </div>
        <div class="accounting-tabs" aria-label="Accounting views">
          <button class="button-secondary" :aria-pressed="view === 'reports'" @click="view = 'reports'">Financial reports</button>
          <button class="button-secondary" :aria-pressed="view === 'entries'" @click="view = 'entries'">Journal entries</button>
        </div>
        <template v-if="view === 'reports'">
          <div class="metrics-grid accounting-metrics">
            <article class="metric-card"><span>Revenue · selected period</span><strong>{{ money(data.report.revenue, data.report.currency) }}</strong></article>
            <article class="metric-card orange"><span>Expenses · selected period</span><strong>{{ money(data.report.expenses, data.report.currency) }}</strong></article>
            <article class="metric-card teal"><span>Profit / loss · selected period</span><strong>{{ money(data.report.profit, data.report.currency) }}</strong></article>
          </div>
          <div class="dashboard-columns">
            <section class="panel"><h2>Profit &amp; loss</h2><p class="muted">{{ data.report.date_from }} to {{ data.report.date_to }}</p><dl class="accounting-totals"><div><dt>Sales revenue</dt><dd>{{ money(data.report.revenue, data.report.currency) }}</dd></div><div><dt>Purchases expense</dt><dd>{{ money(data.report.expenses, data.report.currency) }}</dd></div><div><dt>Profit / loss</dt><dd>{{ money(data.report.profit, data.report.currency) }}</dd></div></dl></section>
            <section class="panel"><h2>Balance sheet</h2><p class="muted">As of {{ data.report.date_to }} · balances since inception</p><dl class="accounting-totals"><div><dt>Assets</dt><dd>{{ money(data.report.assets, data.report.currency) }}</dd></div><div><dt>Liabilities</dt><dd>{{ money(data.report.liabilities, data.report.currency) }}</dd></div><div><dt>Accumulated earnings</dt><dd>{{ money(data.report.accumulated_earnings, data.report.currency) }}</dd></div><div><dt>Assets − liabilities − earnings</dt><dd>{{ money(data.report.balance_check, data.report.currency) }}</dd></div></dl></section>
          </div>
          <section class="panel trial-balance">
            <div class="section-heading"><h2>Trial balance</h2><button class="button-secondary" @click="exportReport">Export CSV</button></div>
            <p class="muted">Opening and closing balances include earlier entries. Click an account to inspect its entries in the selected period.</p>
            <div class="table-wrap" role="region" aria-label="Accounting records" tabindex="0"><table class="data-table"><thead><tr><th>Account</th><th class="numeric">Opening Dr − Cr</th><th class="numeric">Period debit</th><th class="numeric">Period credit</th><th class="numeric">Closing debit</th><th class="numeric">Closing credit</th></tr></thead><tbody>
              <tr v-for="row in data.report.accounts" :key="row.code"><td><button class="inline-button" @click="drill(row.code)">{{ row.code }} {{ row.name }}</button></td><td class="numeric">{{ money(row.opening, data.report.currency) }}</td><td class="numeric">{{ money(row.debit, data.report.currency) }}</td><td class="numeric">{{ money(row.credit, data.report.currency) }}</td><td class="numeric">{{ money(row.closing_debit, data.report.currency) }}</td><td class="numeric">{{ money(row.closing_credit, data.report.currency) }}</td></tr>
            </tbody><tfoot><tr><th>Total</th><td></td><td class="numeric">{{ money(data.report.debit, data.report.currency) }}</td><td class="numeric">{{ money(data.report.credit, data.report.currency) }}</td><td class="numeric">{{ money(data.report.closing_debit, data.report.currency) }}</td><td class="numeric">{{ money(data.report.closing_credit, data.report.currency) }}</td></tr></tfoot></table></div>
          </section>
        </template>
        <template v-else>
          <p v-if="source" class="notice">Showing entries for {{ invoiceId ? 'invoice' : 'order' }} #{{ source }}. <RouterLink to="/accounting" class="text-link">Clear source filter</RouterLink></p>
          <p class="muted">{{ data.entries.count }} entries. Each entry shows both sides, including when filtered by account. Recorded bank and cash payments have no bank statement matching.</p>
          <p v-if="!data.entries.count" class="empty-state">No entries match these filters. Issue an invoice or bill to create a posting.</p>
          <details v-for="entry in data.entries.results" :key="entry.id" class="panel journal-entry">
            <summary><strong>{{ entry.number }}</strong><span>{{ entry.date }}</span><span>{{ entry.description }}</span><span class="badge">{{ entry.journal }}</span><span v-if="entry.reversal_id" class="badge">Reversed</span></summary>
            <div class="crm-links"><RouterLink :to="`/invoicing/${entry.invoice_id}`" class="text-link">{{ entry.invoice_number }}</RouterLink><RouterLink :to="`${entry.order_kind === 'sale' ? '/sales' : '/purchase'}/${entry.order_id}`" class="text-link">{{ entry.order_number }}</RouterLink><span>{{ entry.contact_name }}</span><span v-if="entry.payment_id">Payment #{{ entry.payment_id }}</span><span v-if="entry.reversal_of_id">Reverses entry #{{ entry.reversal_of_id }}</span></div>
            <div class="table-wrap" role="region" aria-label="Accounting records" tabindex="0"><table class="data-table"><thead><tr><th>Account</th><th class="numeric">Debit</th><th class="numeric">Credit</th></tr></thead><tbody><tr v-for="line in entry.lines" :key="line.account_code"><td>{{ line.account_code }} {{ line.account_name }}</td><td class="numeric">{{ money(line.debit, entry.currency) }}</td><td class="numeric">{{ money(line.credit, entry.currency) }}</td></tr></tbody></table></div><p v-if="!entry.lines.length" class="muted">Zero-value document; no monetary lines.</p><p class="muted">Recorded {{ entry.created_at.slice(0, 10) }} · {{ entry.actor_email || 'Historical posting' }}</p>
          </details>
          <UiPagination :count="data.entries.count" :page="page" :page-size="data.entries.page_size" :busy="loading" @update:page="page = $event" />
        </template>
      </template>
    </div>
    <UiDialog ref="lockDialog" title="Close accounting dates" :busy="auth.busy" v-slot="{ requestClose }">
      <form @submit.prevent="closeDates">
        <p>Entries dated on or before this date will be blocked. The lock can only move forward. Existing entries and documents remain available to read.</p>
        <p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p>
        <label>Close through<input v-model="lockDate" name="locked_through" type="date" :max="today()" required :disabled="auth.busy" /></label>
        <footer class="dialog-footer"><button class="button-primary" :disabled="auth.busy">Close dates permanently</button><button type="button" class="button-secondary" :disabled="auth.busy" @click="requestClose">Discard</button></footer>
      </form>
    </UiDialog>
  </section>
</template>
