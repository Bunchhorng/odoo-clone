<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { allRecords, erp, money, today, useWorkspace } from '../composables/erp'
import { syncPage, useDirtyForm, usePage } from '../composables/forms'

const props = defineProps({ kind: String })
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const base = computed(() => props.kind === 'sale' ? '/sales' : '/purchase')
const title = computed(() => props.kind === 'sale' ? 'Quotations & orders' : 'Requests for quotation & orders')
const recordId = computed(() => route.params.recordId)
const isNew = computed(() => recordId.value === 'new')
const search = ref('')
const filter = ref('')
const page = usePage([search, filter, () => props.kind])
const form = ref({ contact_id: '', date: today(), notes: '', lines: [] })
const { dirty, markClean, discard } = useDirtyForm(form)
const actionError = ref('')
const { data, error, loading, refresh } = useWorkspace(async id => {
  if (!recordId.value) return erp(id, `orders/?${new URLSearchParams({ kind: props.kind, q: search.value, status: filter.value, page: String(page.value) })}`)
  const [settings, contacts, products, order] = await Promise.all([
    erp(id, 'settings/'), allRecords(id, 'contacts'), allRecords(id, 'products'),
    isNew.value ? Promise.resolve(null) : erp(id, `orders/${recordId.value}/`),
  ])
  if (order && order.kind !== props.kind) throw new Error('This order belongs to the other order app.')
  return { settings, contacts: contacts.filter(item => props.kind === 'sale' ? item.is_customer : item.is_supplier), products, order }
}, [recordId, () => props.kind, search, filter, page])
syncPage(page, data)
watch(data, value => {
  actionError.value = ''
  if (value && recordId.value) form.value = value.order
    ? { contact_id: value.order.contact_id, date: value.order.date, notes: value.order.notes, lines: value.order.lines.map(line => ({ ...line })) }
    : { contact_id: '', date: today(), notes: '', lines: [{ product_id: '', quantity: '1', unit_price: '0', tax_rate: '0' }] }
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
async function save() {
  auth.busy = true; actionError.value = ''
  try {
    const payload = { kind: props.kind, contact_id: Number(form.value.contact_id), date: form.value.date, notes: form.value.notes,
      lines: form.value.lines.map(line => ({ product_id: Number(line.product_id), quantity: line.quantity, unit_price: line.unit_price, tax_rate: line.tax_rate, ...(line.description ? { description: line.description } : {}) })) }
    const order = await erp(auth.activeCompanyId, `orders/${isNew.value ? '' : `${recordId.value}/`}`, { method: isNew.value ? 'POST' : 'PATCH', data: payload })
    markClean()
    if (isNew.value) await router.replace(`${base.value}/${order.id}`)
    else await refresh()
  } catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
async function action(name) {
  if (dirty.value) { actionError.value = 'Save or discard your changes before continuing.'; return }
  if (name === 'cancel' && !window.confirm('Cancel this order? It will remain in your records.')) return
  auth.busy = true; actionError.value = ''
  try {
    const result = await erp(auth.activeCompanyId, `orders/${recordId.value}/actions/`, { method: 'POST', data: { action: name } })
    if (name === 'invoice') await router.push(`/invoicing/${result.id}`)
    else await refresh()
  } catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
</script>

<template>
  <section class="business-page">
    <div class="module-tabs"><RouterLink :to="base" class="active">{{ kind === 'sale' ? 'Sales' : 'Purchase' }}</RouterLink><RouterLink to="/contacts">{{ kind === 'sale' ? 'Customers' : 'Suppliers' }}</RouterLink><RouterLink to="/inventory">Products</RouterLink></div>
    <div class="control-panel">
      <div class="control-title"><RouterLink v-if="recordId" :to="base" class="breadcrumb">{{ title }} /</RouterLink><h1>{{ recordId ? data?.order?.number || 'New' : title }}</h1></div>
      <template v-if="!recordId"><form class="search-field" @submit.prevent="page = 1; refresh()"><input v-model.lazy="search" aria-label="Search orders" placeholder="Search customer or reference…" /><button aria-label="Search">⌕</button></form><div class="control-actions"><RouterLink v-if="auth.canManage && auth.activeCompanyId" :to="`${base}/new`" class="button-primary">New</RouterLink><select v-model="filter" aria-label="Order status" @change="page = 1"><option value="">All orders</option><option value="draft">{{ kind === 'sale' ? 'Quotations' : 'RFQs' }}</option><option value="confirmed">Confirmed</option><option value="cancelled">Cancelled</option></select></div></template>
      <div v-else class="control-actions"><button v-if="editable" class="button-primary" :disabled="auth.busy || loading" form="order-form">{{ auth.busy ? 'Saving…' : 'Save' }}</button><RouterLink :to="base" class="button-secondary">Back</RouterLink><button v-if="data?.order" class="button-secondary" @click="printDocument">Print</button></div>
    </div>
    <div class="workspace-content">
      <p v-if="!auth.activeCompanyId" class="empty-state">Choose or <RouterLink to="/companies" class="text-link">create a company</RouterLink> to continue.</p>
      <p v-if="dirty" class="notice" role="status">You have unsaved changes. Save them before confirming this document. <button type="button" class="inline-button" :disabled="auth.busy" @click="discard(); actionError = ''">Discard changes</button></p>
      <p v-if="error || actionError" class="notice error" role="alert">{{ actionError || error }}</p>
      <p v-if="loading" class="loading-state" role="status">Loading orders…</p>
      <template v-else-if="data">
        <template v-if="!recordId">
          <div v-if="data.results.length" class="table-wrap"><table class="data-table"><thead><tr><th>Number</th><th>{{ kind === 'sale' ? 'Customer' : 'Supplier' }}</th><th>Date</th><th>Total</th><th>Status</th><th>{{ kind === 'sale' ? 'Delivery' : 'Receipt' }}</th></tr></thead><tbody><tr v-for="order in data.results" :key="order.id"><td><RouterLink :to="`${base}/${order.id}`" class="text-link">{{ order.number }}</RouterLink></td><td>{{ order.contact_name }}</td><td>{{ order.date }}</td><td class="numeric">{{ money(order.total, order.currency) }}</td><td><span class="badge" :class="order.status">{{ order.status === 'draft' ? kind === 'sale' ? 'Quotation' : 'RFQ' : order.status }}</span></td><td>{{ order.fulfilled_at ? 'Completed' : 'Pending' }}</td></tr></tbody></table></div>
          <div v-else class="empty-state"><h2>{{ kind === 'sale' ? 'Your next sale starts here' : 'Keep your purchases organized' }}</h2><p>Create a {{ kind === 'sale' ? 'quotation for a customer' : 'request for quotation for a supplier' }}.</p><RouterLink v-if="auth.canManage" :to="`${base}/new`" class="button-primary">New {{ kind === 'sale' ? 'quotation' : 'RFQ' }}</RouterLink></div>
          <div v-if="data.count > data.page_size" class="pagination"><span>{{ data.count }} orders · page {{ page }}</span><button :disabled="page === 1" @click="page--">Previous</button><button :disabled="page * data.page_size >= data.count" @click="page++">Next</button></div>
        </template>
        <template v-else>
          <div v-if="data.order" class="document-actions"><template v-if="auth.canManage"><button v-if="data.order.status === 'draft'" class="button-primary" :disabled="auth.busy" @click="action('confirm')">Confirm {{ kind === 'sale' ? 'sale' : 'purchase' }}</button><button v-if="data.order.status === 'confirmed' && !data.order.fulfilled_at" class="button-primary" :disabled="auth.busy" @click="action('fulfill')">{{ kind === 'sale' ? 'Validate delivery' : 'Receive products' }}</button><button v-if="data.order.status === 'confirmed' && !data.order.invoice_id" class="button-secondary" :disabled="auth.busy" @click="action('invoice')">Create {{ kind === 'sale' ? 'invoice' : 'bill' }}</button><button v-if="data.order.status !== 'cancelled' && !data.order.fulfilled_at && !data.order.invoice_id" class="inline-button" :disabled="auth.busy" @click="action('cancel')">Cancel order</button></template><RouterLink v-if="data.order.invoice_id" :to="`/invoicing/${data.order.invoice_id}`" class="button-secondary">View {{ kind === 'sale' ? 'invoice' : 'bill' }}</RouterLink><span class="badge state-label" :class="data.order.status">{{ data.order.status }}</span><span v-if="data.order.fulfilled_at" class="badge confirmed">{{ kind === 'sale' ? 'Delivered' : 'Received' }}</span></div>
          <form id="order-form" class="document-sheet" @submit.prevent="save">
            <div class="sheet-heading"><div><span class="eyebrow">{{ auth.activeCompany?.name }}</span><h2>{{ data.order?.number || (kind === 'sale' ? 'New quotation' : 'New request for quotation') }}</h2></div><span>{{ data.order?.currency || data.settings.currency }}</span></div>
            <fieldset :disabled="!editable || auth.busy" class="form-grid"><label>{{ kind === 'sale' ? 'Customer' : 'Supplier' }}<select v-model="form.contact_id" name="contact_id" required><option value="">Choose a {{ kind === 'sale' ? 'customer' : 'supplier' }}…</option><option v-for="contact in data.contacts" :key="contact.id" :value="contact.id">{{ contact.name }}</option><option v-if="data.order && !data.contacts.some(item => item.id === form.contact_id)" :value="form.contact_id">{{ data.order.contact_name }} (archived)</option></select></label><label>Order date<input v-model="form.date" name="date" type="date" required /></label></fieldset>
            <p v-if="!data.contacts.length && editable" class="notice">First <RouterLink to="/contacts" class="text-link">create a contact</RouterLink> marked as {{ kind === 'sale' ? 'a customer' : 'a supplier' }}.</p>
            <div class="table-wrap order-lines"><table class="data-table"><thead><tr><th>Product / description</th><th>Quantity</th><th>Unit price</th><th>Tax %</th><th>Subtotal</th><th v-if="editable"></th></tr></thead><tbody><tr v-for="(line, index) in form.lines" :key="index"><td><template v-if="editable"><select v-model="line.product_id" :name="`product_${index}`" required :disabled="auth.busy" @change="pickProduct(line)"><option value="">Choose a product…</option><option v-for="product in data.products" :key="product.id" :value="product.id">[{{ product.sku }}] {{ product.name }}</option></select><input v-if="line.product_id" v-model="line.description" :aria-label="`Description for line ${index + 1}`" maxlength="300" :disabled="auth.busy" /></template><template v-else>{{ line.description }}</template></td><td><input v-if="editable" v-model="line.quantity" :name="`quantity_${index}`" type="number" min=".001" step=".001" required :disabled="auth.busy" /><span v-else>{{ line.quantity }}</span></td><td><input v-if="editable" v-model="line.unit_price" :name="`price_${index}`" type="number" min="0" step=".01" required :disabled="auth.busy" /><span v-else>{{ money(line.unit_price, data.settings.currency) }}</span></td><td><input v-if="editable" v-model="line.tax_rate" :name="`tax_${index}`" type="number" min="0" max="100" step=".01" required :disabled="auth.busy" /><span v-else>{{ line.tax_rate }}%</span></td><td class="numeric">{{ money(Number(line.quantity) * Number(line.unit_price), data.settings.currency) }}</td><td v-if="editable"><button type="button" class="inline-button" :disabled="auth.busy || form.lines.length === 1" :aria-label="`Remove line ${index + 1}`" @click="form.lines.splice(index, 1)">×</button></td></tr></tbody></table></div>
            <button v-if="editable" type="button" class="text-link add-line" :disabled="auth.busy || form.lines.length >= 100" @click="form.lines.push({ product_id: '', quantity: '1', unit_price: '0', tax_rate: '0' })">+ Add a product</button>
            <div class="sheet-bottom"><label>Terms & notes<textarea v-model="form.notes" name="notes" maxlength="10000" rows="4" :disabled="!editable || auth.busy"></textarea></label><dl class="totals"><div><dt>Untaxed amount</dt><dd>{{ money(editable ? preview.subtotal : data.order.subtotal, data.settings.currency) }}</dd></div><div><dt>Tax</dt><dd>{{ money(editable ? preview.tax : data.order.tax_total, data.settings.currency) }}</dd></div><div class="grand-total"><dt>Total</dt><dd>{{ money(editable ? preview.total : data.order.total, data.settings.currency) }}</dd></div><p v-if="editable" class="form-help">Preview. Final amounts are calculated by the server when saved.</p></dl></div>
          </form>
        </template>
      </template>
    </div>
  </section>
</template>
