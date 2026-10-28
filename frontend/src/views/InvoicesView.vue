<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { erp, money, today, useWorkspace } from '../composables/erp'
import { syncPage, useDirtyForm, usePage } from '../composables/forms'

const route = useRoute()
const auth = useAuthStore()
const recordId = computed(() => route.params.recordId)
const kind = ref('')
const status = ref('')
const search = ref('')
const page = usePage([kind, status, search])
const actionError = ref('')
const form = ref({})
const { dirty, markClean, discard } = useDirtyForm(form)
const paymentDialog = ref(null)
const payment = ref({})
const printDocument = () => window.print()
const { data, error, loading, refresh } = useWorkspace(id => recordId.value
  ? erp(id, `invoices/${recordId.value}/`)
  : erp(id, `invoices/?${new URLSearchParams({ kind: kind.value, status: status.value, q: search.value, page: String(page.value) })}`),
[recordId, kind, status, search, page])
syncPage(page, data)
watch(data, value => {
  if (value && recordId.value) {
    form.value = { date: value.date, due_date: value.due_date || '', notes: value.notes }
    markClean()
  }
})
watch([() => auth.activeCompanyId, recordId], () => { paymentDialog.value?.close(); actionError.value = '' })
async function action(name) {
  if (dirty.value) { actionError.value = 'Save or discard your changes before continuing.'; return }
  if (name === 'cancel' && !window.confirm('Cancel this invoice or bill? It will remain in your records.')) return
  auth.busy = true; actionError.value = ''
  try { await erp(auth.activeCompanyId, `invoices/${recordId.value}/actions/`, { method: 'POST', data: { action: name } }); await refresh() }
  catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
async function save() {
  auth.busy = true; actionError.value = ''
  try { await erp(auth.activeCompanyId, `invoices/${recordId.value}/`, { method: 'PATCH', data: form.value }); await refresh() }
  catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
function openPayment() {
  if (dirty.value) { actionError.value = 'Save or discard your changes before continuing.'; return }
  payment.value = { amount: data.value.balance, date: today(), method: 'bank', reference: '', request_id: crypto.randomUUID() }
  actionError.value = ''; paymentDialog.value.showModal()
}
async function pay() {
  auth.busy = true; actionError.value = ''
  try {
    await erp(auth.activeCompanyId, `invoices/${recordId.value}/payments/`, { method: 'POST', data: payment.value })
    paymentDialog.value.close(); await refresh()
  } catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
</script>

<template>
  <section class="business-page">
    <div class="module-tabs"><RouterLink to="/invoicing" class="active">Invoices & bills</RouterLink><RouterLink to="/sales">Sales</RouterLink><RouterLink to="/purchase">Purchase</RouterLink></div>
    <div class="control-panel"><div class="control-title"><RouterLink v-if="recordId" to="/invoicing" class="breadcrumb">Invoices & bills /</RouterLink><h1>{{ recordId ? data?.number || 'Invoice' : 'Invoices & bills' }}</h1></div><template v-if="!recordId"><form class="search-field" @submit.prevent="refresh"><input v-model.lazy="search" aria-label="Search invoices" placeholder="Search customer or number…" /><button aria-label="Search">⌕</button></form><div class="control-actions"><select v-model="kind" aria-label="Invoice kind" @change="page = 1"><option value="">Invoices & bills</option><option value="customer">Customer invoices</option><option value="vendor">Vendor bills</option></select><select v-model="status" aria-label="Invoice status" @change="page = 1"><option value="">All statuses</option><option value="draft">Draft</option><option value="issued">Issued</option><option value="paid">Paid</option><option value="cancelled">Cancelled</option></select></div></template><div v-else class="control-actions"><button v-if="auth.canManage && data?.status === 'draft'" class="button-primary" :disabled="auth.busy" @click="save">Save</button><button class="button-secondary" @click="printDocument()">Print / PDF</button><RouterLink to="/invoicing" class="button-secondary">Back</RouterLink></div></div>
    <div class="workspace-content">
      <p v-if="!auth.activeCompanyId" class="empty-state">Choose or <RouterLink to="/companies" class="text-link">create a company</RouterLink> to continue.</p>
      <p v-if="dirty" class="notice" role="status">You have unsaved changes. Save them before issuing this document. <button type="button" class="inline-button" :disabled="auth.busy" @click="discard(); actionError = ''">Discard changes</button></p>
      <p v-if="error || actionError" class="notice error" role="alert">{{ actionError || error }}</p><p v-if="loading" class="loading-state" role="status">Loading invoices…</p>
      <template v-else-if="data">
        <template v-if="!recordId"><div v-if="data.results.length" class="table-wrap"><table class="data-table"><thead><tr><th>Number</th><th>Type</th><th>Partner</th><th>Date</th><th>Total</th><th>Amount due</th><th>Status</th></tr></thead><tbody><tr v-for="invoice in data.results" :key="invoice.id"><td><RouterLink :to="`/invoicing/${invoice.id}`" class="text-link">{{ invoice.number }}</RouterLink></td><td>{{ invoice.kind === 'customer' ? 'Invoice' : 'Vendor bill' }}</td><td>{{ invoice.contact_name }}</td><td>{{ invoice.date }}</td><td class="numeric">{{ money(invoice.total, invoice.currency) }}</td><td class="numeric">{{ money(invoice.balance, invoice.currency) }}</td><td><span class="badge" :class="invoice.status">{{ invoice.status }}</span></td></tr></tbody></table></div><div v-else class="empty-state"><h2>Your invoices, connected to your orders</h2><p>Open a confirmed sales or purchase order and select Create invoice or Create bill.</p><RouterLink to="/sales" class="button-primary">Open sales</RouterLink> <RouterLink to="/purchase" class="button-secondary">Open purchase</RouterLink></div><div v-if="data.count > data.page_size" class="pagination"><span>{{ data.count }} records · page {{ page }}</span><button :disabled="page === 1" @click="page--">Previous</button><button :disabled="page * data.page_size >= data.count" @click="page++">Next</button></div></template>
        <template v-else>
          <div class="document-actions"><template v-if="auth.canManage"><button v-if="data.status === 'draft'" class="button-primary" :disabled="auth.busy" @click="action('issue')">{{ data.kind === 'customer' ? 'Issue invoice' : 'Confirm bill' }}</button><button v-if="data.status === 'issued'" class="button-primary" :disabled="auth.busy" @click="openPayment">Register payment</button><button v-if="['draft', 'issued'].includes(data.status) && !data.payments.length" class="inline-button" :disabled="auth.busy" @click="action('cancel')">Cancel</button></template><RouterLink :to="`${data.kind === 'customer' ? '/sales' : '/purchase'}/${data.order_id}`" class="button-secondary">{{ data.order_number }}</RouterLink><span class="badge state-label" :class="data.status">{{ data.status }}</span></div>
          <article class="document-sheet invoice-sheet"><div class="sheet-heading"><div><p class="eyebrow">{{ auth.activeCompany?.name }}</p><h2>{{ data.kind === 'customer' ? 'Invoice' : 'Vendor bill' }} {{ data.number }}</h2></div><span class="invoice-balance"><small>Amount due</small><strong>{{ money(data.balance, data.currency) }}</strong></span></div><div class="invoice-partner"><strong>{{ data.contact_name }}</strong><p>{{ data.contact_address }}</p><p>{{ data.contact_email }}</p></div><fieldset class="form-grid" :disabled="data.status !== 'draft' || !auth.canManage || auth.busy"><label>Invoice date<input v-model="form.date" type="date" name="invoice_date" required /></label><label>Due date<input v-model="form.due_date" type="date" name="due_date" /></label></fieldset><div class="table-wrap"><table class="data-table"><thead><tr><th>Description</th><th>Quantity</th><th>Unit price</th><th>Tax</th><th>Amount</th></tr></thead><tbody><tr v-for="line in data.lines" :key="line.id"><td>{{ line.description }}</td><td>{{ line.quantity }}</td><td>{{ money(line.unit_price, data.currency) }}</td><td>{{ line.tax_rate }}%</td><td class="numeric">{{ money(line.total, data.currency) }}</td></tr></tbody></table></div><div class="sheet-bottom"><label>Notes<textarea v-model="form.notes" maxlength="10000" rows="3" :disabled="data.status !== 'draft' || !auth.canManage || auth.busy"></textarea></label><dl class="totals"><div><dt>Untaxed amount</dt><dd>{{ money(data.subtotal, data.currency) }}</dd></div><div><dt>Tax</dt><dd>{{ money(data.tax_total, data.currency) }}</dd></div><div class="grand-total"><dt>Total</dt><dd>{{ money(data.total, data.currency) }}</dd></div><div><dt>Paid</dt><dd>{{ money(data.paid_amount, data.currency) }}</dd></div><div><dt>Remaining</dt><dd>{{ money(data.balance, data.currency) }}</dd></div></dl></div><section v-if="data.payments.length" class="payments-history"><h3>Payment history</h3><table class="data-table"><thead><tr><th>Date</th><th>Method</th><th>Reference</th><th>Amount</th></tr></thead><tbody><tr v-for="item in data.payments" :key="item.id"><td>{{ item.date }}</td><td>{{ item.method }}</td><td>{{ item.reference || '—' }}</td><td>{{ money(item.amount, data.currency) }}</td></tr></tbody></table></section></article>
        </template>
      </template>
    </div>
    <dialog ref="paymentDialog" class="record-dialog small-dialog" @cancel="auth.busy && $event.preventDefault()"><form @submit.prevent="pay"><header class="dialog-header"><h2>Register payment</h2><button type="button" :disabled="auth.busy" aria-label="Close" @click="paymentDialog.close()">×</button></header><p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p><fieldset :disabled="auth.busy"><label>Amount ({{ data?.currency }})<input v-model="payment.amount" name="payment_amount" type="number" min=".01" :max="data?.balance" step=".01" required /></label><label>Date<input v-model="payment.date" name="payment_date" type="date" :min="data?.date" required /></label><label>Method<select v-model="payment.method"><option value="bank">Bank</option><option value="cash">Cash</option></select></label><label>Reference<input v-model="payment.reference" maxlength="200" /></label></fieldset><footer class="dialog-footer"><button class="button-primary" :disabled="auth.busy">{{ auth.busy ? 'Recording…' : 'Record payment' }}</button><button type="button" class="button-secondary" :disabled="auth.busy" @click="paymentDialog.close()">Discard</button></footer></form></dialog>
  </section>
</template>

