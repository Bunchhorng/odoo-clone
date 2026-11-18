<script setup>
import ERPStatusBar from '../components/erp/ERPStatusBar.vue'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { allRecords, dateLabel, erp, money, today, useWorkspace } from '../composables/erp'
import { syncPage, useDirtyForm, usePage } from '../composables/forms'
import PurchaseReceiptDialog from '../components/PurchaseReceiptDialog.vue'

const props = defineProps({ kind: String })
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const base = computed(() => props.kind === 'sale' ? '/sales' : '/purchase')
const title = computed(() => props.kind === 'sale' ? 'Quotations & orders' : 'Requests for quotation & orders')
const recordId = computed(() => route.params.recordId)
const isNew = computed(() => recordId.value === 'new')
const opportunityId = computed(() => props.kind === 'sale' ? route.query.opportunity_id || '' : '')
const newLink = computed(() => `${base.value}/new${opportunityId.value ? `?opportunity_id=${encodeURIComponent(opportunityId.value)}` : ''}`)
const search = ref('')
const filter = ref('')
const page = usePage([search, filter, () => props.kind, opportunityId])
const form = ref({ contact_id: '', date: today(), notes: '', lines: [] })
const { dirty, markClean, discard } = useDirtyForm(form)
const actionError = ref('')
const conflict = ref(false)
const receiptDialog = ref(null)
const { data, error, loading, refresh } = useWorkspace(async id => {
  const opportunity = opportunityId.value ? await erp(id, `opportunities/${opportunityId.value}/`) : null
  if (!recordId.value) return { ...await erp(id, `orders/?${new URLSearchParams({ kind: props.kind, q: search.value, status: filter.value, page: String(page.value), opportunity_id: opportunityId.value })}`), opportunity }
  const [settings, contacts, products, order, receipts] = await Promise.all([
    erp(id, 'settings/'), allRecords(id, 'contacts'), allRecords(id, 'products'),
    isNew.value ? Promise.resolve(null) : erp(id, `orders/${recordId.value}/`),
    props.kind === 'purchase' && !isNew.value ? erp(id, `orders/${recordId.value}/receipts/`) : Promise.resolve(null),
  ])
  if (order && order.kind !== props.kind) throw new Error('This order belongs to the other order app.')
  return { settings, contacts: contacts.filter(item => props.kind === 'sale' ? item.is_customer : item.is_supplier), products, order, opportunity, receipts }
}, [recordId, () => props.kind, search, filter, page, opportunityId])
syncPage(page, data)
function orderForm(order) {
  return { contact_id: order.contact_id, date: order.date, notes: order.notes,
    lines: order.lines.map(line => ({ id: line.id, product_id: line.product_id, description: line.description,
      quantity: line.quantity, unit_price: line.unit_price, tax_rate: line.tax_rate })) }
}
watch(data, value => {
  actionError.value = ''
  conflict.value = false
  if (value && recordId.value) form.value = value.order
    ? orderForm(value.order)
    : { contact_id: value.contacts.some(contact => contact.id === value.opportunity?.contact_id) ? value.opportunity.contact_id : '', date: today(), notes: value.opportunity?.notes || '', lines: [{ product_id: '', quantity: '1', unit_price: '0', tax_rate: '0' }] }
  if (value && recordId.value) markClean()
})
watch([() => auth.activeCompanyId, () => props.kind], () => { actionError.value = '' })
const editable = computed(() => auth.canManage && (isNew.value || data.value?.order?.status === 'draft'))
const preview = computed(() => form.value.lines.reduce((totals, line) => {
  const subtotal = Math.round(Number(line.quantity || 0) * Number(line.unit_price || 0) * 100) / 100
  const tax = Math.round(subtotal * Number(line.tax_rate || 0)) / 100
  return { subtotal: totals.subtotal + subtotal, tax: totals.tax + tax, total: totals.total + subtotal + tax }
}, { subtotal: 0, tax: 0, total: 0 }))
function pickProduct(line) {
  const product = data.value.products.find(item => item.id === Number(line.product_id))
  if (product) { line.description = product.name; line.unit_price = props.kind === 'sale' ? product.sale_price : product.cost_price }
}
function printDocument() { window.print() }
function receive() {
  if (dirty.value) { actionError.value = 'Save or discard your changes before continuing.'; return }
  if (data.value.order.lines.some(line => line.product_kind === 'goods' && Number(line.remaining_quantity) > 0)) receiptDialog.value.showModal()
  else action('fulfill')
}
function progress(line) { return data.value.order.lines.find(item => item.id === line.id) }
async function reloadDocument() {
  if (dirty.value && !window.confirm('Discard your changes and load the latest document?')) return
  await refresh()
}
async function save() {
  auth.busy = true; actionError.value = ''
  try {
    let payload = { contact_id: Number(form.value.contact_id), date: form.value.date, notes: form.value.notes,
      lines: form.value.lines.map(line => ({ ...(line.id ? { id: line.id } : {}), product_id: Number(line.product_id), ...(line.description ? { description: line.description } : {}), quantity: line.quantity, unit_price: line.unit_price, tax_rate: line.tax_rate })) }
    if (isNew.value) payload = { ...payload, kind: props.kind, ...(opportunityId.value ? { opportunity_id: Number(opportunityId.value) } : {}) }
    else {
      const original = orderForm(data.value.order)
      payload = Object.fromEntries(Object.entries(payload).filter(([key, value]) => JSON.stringify(value) !== JSON.stringify(original[key])))
      if (!Object.keys(payload).length) { markClean(); return }
      payload.expected_version = data.value.order.version
    }
    const order = await erp(auth.activeCompanyId, `orders/${isNew.value ? '' : `${recordId.value}/`}`, { method: isNew.value ? 'POST' : 'PATCH', data: payload })
    markClean()
    if (isNew.value) await router.replace(`${base.value}/${order.id}`)
    else await refresh()
  } catch (err) { actionError.value = err.message; conflict.value = err.status === 409 }
  finally { auth.busy = false }
}
async function action(name) {
  if (dirty.value) { actionError.value = 'Save or discard your changes before continuing.'; return }
  if (name === 'cancel' && !window.confirm('Cancel this order? It will remain in your records.')) return
  auth.busy = true; actionError.value = ''
  try {
    const result = await erp(auth.activeCompanyId, `orders/${recordId.value}/actions/`, { method: 'POST', data: { action: name, expected_version: data.value.order.version } })
    if (name === 'invoice') await router.push(`/invoicing/${result.id}`)
    else await refresh()
  } catch (err) { actionError.value = err.message; conflict.value = err.status === 409 }
  finally { auth.busy = false }
}
</script>

<template>
  <section class="business-page">

    <div class="control-panel">
      <div class="control-title"><RouterLink v-if="recordId" :to="base" class="breadcrumb">{{ title }} /</RouterLink><h1>{{ recordId ? data?.order?.number || 'New' : title }}</h1></div>
      <template v-if="!recordId"><form class="search-field" @submit.prevent="page = 1; refresh()"><input v-model.lazy="search" aria-label="Search orders" placeholder="Search customer or reference…" /><button aria-label="Search">⌕</button></form><div class="control-actions"><RouterLink v-if="auth.canManage && auth.activeCompanyId" :to="newLink" class="button-primary">New</RouterLink><select v-model="filter" aria-label="Order status" @change="page = 1"><option value="">All orders</option><option value="draft">{{ kind === 'sale' ? 'Quotations' : 'RFQs' }}</option><option value="confirmed">Confirmed</option><option value="cancelled">Cancelled</option></select></div></template>
      <div v-else class="control-actions"><button v-if="editable" class="button-primary" :disabled="auth.busy || loading" form="order-form">{{ auth.busy ? 'Saving…' : 'Save' }}</button><RouterLink :to="base" class="button-secondary">Back</RouterLink><button v-if="data?.order" class="button-secondary" @click="printDocument">Print</button></div>
    </div>
    <div class="workspace-content">
      <p v-if="data?.order?.opportunity_id || data?.opportunity" class="notice opportunity-context">From opportunity <RouterLink class="text-link" :to="{ path: '/crm', query: { opportunity_id: data.order?.opportunity_id || data.opportunity.id, active: 'all' } }">{{ data.order?.opportunity_title || data.opportunity.title }}</RouterLink><RouterLink v-if="!recordId" :to="base" class="text-link">Show all sales</RouterLink></p>
      <p v-if="isNew && data?.opportunity?.contact_id && !form.contact_id" class="notice">Choose an active customer for this quotation. The opportunity's previous contact is unavailable for new sales.</p>
      <p v-if="!auth.activeCompanyId" class="empty-state">Choose or <RouterLink to="/companies" class="text-link">create a company</RouterLink> to continue.</p>
      <p v-if="dirty" class="notice" role="status">You have unsaved changes. Save them before confirming this document. <button type="button" class="inline-button" :disabled="auth.busy" @click="discard(); actionError = ''">Discard changes</button></p>
      <p v-if="error || actionError" class="notice error" role="alert">{{ actionError || error }} <button v-if="conflict" type="button" class="inline-button" :disabled="auth.busy" @click="reloadDocument">Reload document</button></p>
      <p v-if="loading" class="loading-state" role="status">Loading orders…</p>
      <template v-else-if="data">
        <template v-if="!recordId">
          <div v-if="data.results.length" class="table-wrap" role="region" aria-label="Orders records" tabindex="0"><table class="data-table"><thead><tr><th>Number</th><th>{{ kind === 'sale' ? 'Customer' : 'Supplier' }}</th><th>Date</th><th>Total</th><th>Status</th><th>{{ kind === 'sale' ? 'Delivery' : 'Receipt' }}</th></tr></thead><tbody><tr v-for="order in data.results" :key="order.id"><td><RouterLink :to="`${base}/${order.id}`" class="text-link">{{ order.number }}</RouterLink></td><td>{{ order.contact_name }}</td><td>{{ order.date }}</td><td class="numeric">{{ money(order.total, order.currency) }}</td><td><span class="badge" :class="order.status">{{ order.status === 'draft' ? kind === 'sale' ? 'Quotation' : 'RFQ' : order.status }}</span></td><td>{{ order.fulfilled_at ? 'Completed' : kind === 'purchase' && order.receipt_status === 'partial' ? 'Partially received' : 'Pending' }}</td></tr></tbody></table></div>
          <div v-else class="empty-state"><h2>{{ kind === 'sale' ? 'Your next sale starts here' : 'Keep your purchases organized' }}</h2><p>Create a {{ kind === 'sale' ? 'quotation for a customer' : 'request for quotation for a supplier' }}.</p><RouterLink v-if="auth.canManage" :to="newLink" class="button-primary">New {{ kind === 'sale' ? 'quotation' : 'RFQ' }}</RouterLink></div>
          <div v-if="data.count > data.page_size" class="pagination"><span>{{ data.count }} orders · page {{ page }}</span><button :disabled="page === 1" @click="page--">Previous</button><button :disabled="page * data.page_size >= data.count" @click="page++">Next</button></div>
        </template>
        <template v-else>
          <div v-if="data.order" class="document-actions"><template v-if="auth.canManage"><button v-if="data.order.status === 'draft'" class="button-primary" :disabled="auth.busy" @click="action('confirm')">Confirm {{ kind === 'sale' ? 'sale' : 'purchase' }}</button><button v-if="data.order.status === 'confirmed' && !data.order.fulfilled_at" class="button-primary" :disabled="auth.busy" @click="kind === 'purchase' ? receive() : action('fulfill')">{{ kind === 'sale' ? 'Validate delivery' : 'Receive products' }}</button><button v-if="data.order.status === 'confirmed' && !data.order.invoice_id" class="button-secondary" :disabled="auth.busy" @click="action('invoice')">Create {{ kind === 'sale' ? 'invoice' : 'bill' }}</button><button v-if="data.order.status !== 'cancelled' && !data.order.fulfilled_at && !data.order.has_stock_movements && !data.order.invoice_id" class="inline-button" :disabled="auth.busy" @click="action('cancel')">Cancel order</button></template><RouterLink v-if="data.order.invoice_id" :to="`/invoicing/${data.order.invoice_id}`" class="button-secondary">View {{ kind === 'sale' ? 'invoice' : 'bill' }}</RouterLink><RouterLink v-if="data.order.has_stock_movements" :to="`/inventory/movements?order_id=${data.order.id}`" class="button-secondary">Stock movements</RouterLink><span v-if="kind === 'purchase' && data.order.receipt_status === 'partial'" class="badge">Partially received</span><span v-if="data.order.fulfilled_at" class="badge confirmed">{{ kind === 'sale' ? 'Delivered' : 'Received' }}</span></div>
          <ERPStatusBar v-if="data.order" :value="data.order.status" :steps="[{ value: 'draft', label: kind === 'sale' ? 'Quotation' : 'RFQ' }, { value: 'confirmed', label: 'Confirmed' }, { value: 'cancelled', label: 'Cancelled' }]" />
          <form id="order-form" class="document-sheet" @submit.prevent="save">
            <div class="sheet-heading"><div><span class="eyebrow">{{ auth.activeCompany?.name }}</span><h2>{{ data.order?.number || (kind === 'sale' ? 'New quotation' : 'New request for quotation') }}</h2></div><span>{{ data.order?.currency || data.settings.currency }}</span></div>
            <fieldset :disabled="!editable || auth.busy" class="form-grid"><label>{{ kind === 'sale' ? 'Customer' : 'Supplier' }}<select v-model="form.contact_id" name="contact_id" required><option value="">Choose a {{ kind === 'sale' ? 'customer' : 'supplier' }}…</option><option v-for="contact in data.contacts" :key="contact.id" :value="contact.id">{{ contact.name }}</option><option v-if="data.order && !data.contacts.some(item => item.id === form.contact_id)" :value="form.contact_id">{{ data.order.contact_name }} (archived)</option></select></label><label>Order date<input v-model="form.date" name="date" type="date" required /></label></fieldset>
            <p v-if="!data.contacts.length && editable" class="notice">First <RouterLink to="/contacts" class="text-link">create a contact</RouterLink> marked as {{ kind === 'sale' ? 'a customer' : 'a supplier' }}.</p>
            <div class="table-wrap order-lines" role="region" aria-label="Orders records" tabindex="0"><table class="data-table"><thead><tr><th>Product / description</th><th>Quantity</th><template v-if="kind === 'purchase' && data.order?.status === 'confirmed'"><th>Received</th><th>Remaining</th></template><th>Unit price</th><th>Tax %</th><th>Subtotal</th><th v-if="editable"></th></tr></thead><tbody><tr v-for="(line, index) in form.lines" :key="index"><td><template v-if="editable"><select v-model="line.product_id" :name="`product_${index}`" :aria-label="`Product for line ${index + 1}`" required :disabled="auth.busy" @change="pickProduct(line)"><option value="">Choose a product…</option><option v-for="product in data.products" :key="product.id" :value="product.id">[{{ product.sku }}] {{ product.name }}</option><option v-if="line.id && !data.products.some(product => product.id === Number(line.product_id))" :value="line.product_id">{{ line.description }} (archived)</option></select><input v-if="line.product_id" v-model="line.description" :aria-label="`Description for line ${index + 1}`" maxlength="300" :disabled="auth.busy" /></template><template v-else>{{ line.description }}</template></td><td><input v-if="editable" v-model="line.quantity" :name="`quantity_${index}`" :aria-label="`Quantity for line ${index + 1}`" type="number" min=".001" step=".001" required :disabled="auth.busy" /><span v-else>{{ line.quantity }}</span></td><template v-if="kind === 'purchase' && data.order?.status === 'confirmed'"><td>{{ line.product_kind === 'service' || progress(line)?.product_kind === 'service' ? '—' : progress(line)?.received_quantity }}</td><td>{{ progress(line)?.product_kind === 'service' ? '—' : progress(line)?.remaining_quantity }}</td></template><td><input v-if="editable" v-model="line.unit_price" :name="`price_${index}`" :aria-label="`Unit price for line ${index + 1}`" type="number" min="0" step=".01" required :disabled="auth.busy" /><span v-else>{{ money(line.unit_price, data.settings.currency) }}</span></td><td><input v-if="editable" v-model="line.tax_rate" :name="`tax_${index}`" :aria-label="`Tax rate for line ${index + 1}`" type="number" min="0" max="100" step=".01" required :disabled="auth.busy" /><span v-else>{{ line.tax_rate }}%</span></td><td class="numeric">{{ money(Number(line.quantity) * Number(line.unit_price), data.settings.currency) }}</td><td v-if="editable"><button type="button" class="inline-button" :disabled="auth.busy || form.lines.length === 1" :aria-label="`Remove line ${index + 1}`" @click="form.lines.splice(index, 1)">×</button></td></tr></tbody></table></div>
            <button v-if="editable" type="button" class="text-link add-line" :disabled="auth.busy || form.lines.length >= 100" @click="form.lines.push({ product_id: '', quantity: '1', unit_price: '0', tax_rate: '0' })">+ Add a product</button>
            <div class="sheet-bottom"><label>Terms & notes<textarea v-model="form.notes" name="notes" maxlength="10000" rows="4" :disabled="!editable || auth.busy"></textarea></label><dl class="totals"><div><dt>Untaxed amount</dt><dd>{{ money(editable ? preview.subtotal : data.order.subtotal, data.settings.currency) }}</dd></div><div><dt>Tax</dt><dd>{{ money(editable ? preview.tax : data.order.tax_total, data.settings.currency) }}</dd></div><div class="grand-total"><dt>Total</dt><dd>{{ money(editable ? preview.total : data.order.total, data.settings.currency) }}</dd></div><p v-if="editable" class="form-help">Preview. Final amounts are calculated by the server when saved.</p></dl></div>
          </form>
          <section v-if="data.order?.invoice_summary" class="process-summary panel">
            <div class="section-heading"><h3>Billing &amp; accounting</h3><div class="crm-links"><RouterLink :to="`/invoicing/${data.order.invoice_summary.id}`" class="text-link">{{ data.order.invoice_summary.number }}</RouterLink><RouterLink :to="`/accounting?order_id=${data.order.id}`" class="text-link">Journal entries ({{ data.order.invoice_summary.journal_entry_count }})</RouterLink></div></div>
            <dl><div><dt>Document status</dt><dd>{{ data.order.invoice_summary.status }}</dd></div><div><dt>Document total</dt><dd>{{ money(data.order.invoice_summary.total, data.settings.currency) }}</dd></div><div><dt>Payments</dt><dd>{{ money(data.order.invoice_summary.paid, data.settings.currency) }}</dd></div><div><dt>Remaining balance</dt><dd>{{ money(data.order.invoice_summary.balance, data.settings.currency) }}</dd></div></dl>
            <p v-if="kind === 'purchase'" class="muted">This bill covers the full order. Receipts and supplier returns for replacement do not change its amount.</p>
          </section>
          <section v-if="kind === 'purchase' && data.order?.status === 'confirmed'" class="receipt-history panel">
            <div class="section-heading"><h3>Recent receipts</h3><RouterLink :to="`/inventory/movements?order_id=${data.order.id}`" class="text-link">View all movements</RouterLink></div>
            <p v-if="!data.receipts?.count" class="muted">No receipts recorded yet.</p>
            <template v-else><p class="muted">Latest {{ data.receipts.results.length }} of {{ data.receipts.count }} receipts. Supplier returns and replacements remain in the movement history.</p>
              <div class="table-wrap" role="region" aria-label="Orders records" tabindex="0"><table class="data-table"><thead><tr><th>Receipt</th><th>Date</th><th>Product</th><th>Received</th><th>Unreturned</th><th>Notes</th></tr></thead><tbody>
                <template v-for="receipt in data.receipts.results" :key="receipt.id"><tr v-for="movement in (receipt.movements.length ? receipt.movements : [null])" :key="`${receipt.id}-${movement?.id || 'service'}`"><td>{{ receipt.number }}</td><td>{{ dateLabel(receipt.created_at) }}</td><td>{{ movement?.product_name || 'Services — no stock movement' }}</td><td>{{ movement?.quantity || '—' }}</td><td>{{ movement?.returnable_quantity || '—' }}</td><td>{{ receipt.notes }}</td></tr></template>
              </tbody></table></div>
            </template>
          </section>
        </template>
      </template>
    </div>
    <PurchaseReceiptDialog v-if="kind === 'purchase' && data?.order" ref="receiptDialog" :order="data.order" @received="refresh" />
  </section>
</template>
