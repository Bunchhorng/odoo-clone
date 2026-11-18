<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { allRecords, dateLabel, erp, useWorkspace } from '../composables/erp'
import { syncPage, useDirtyForm, usePage } from '../composables/forms'
import UiDialog from '../components/ui/UiDialog.vue'
import UiPagination from '../components/ui/UiPagination.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const search = ref('')
const kind = ref('all')
const productId = ref(route.query.product_id || '')
const orderId = computed(() => route.query.order_id || '')
const locationId = computed(() => route.query.location_id || '')
const dateFrom = ref('')
const dateTo = ref('')
const page = usePage([search, kind, productId, orderId, locationId, dateFrom, dateTo])
const dialog = ref(null)
const products = ref([])
const form = ref({ product_id: '', quantity: '', reason: '' })
const { dirty, markClean } = useDirtyForm(form)
const actionError = ref('')
const success = ref('')
const optionsLoading = ref(false)
const mode = ref('adjustment')
const target = ref(null)
let requestId
let generation = 0
const labels = { adjustment: 'Adjustment', receipt: 'Receipt', delivery: 'Delivery', return: 'Supplier return', reversal: 'Reversal' }
const title = computed(() => mode.value === 'return' ? 'Return to supplier' : mode.value === 'reversal' ? 'Reverse adjustment' : 'Adjust stock')
const hasFilters = computed(() => search.value || kind.value !== 'all' || productId.value || orderId.value || locationId.value || dateFrom.value || dateTo.value)
const { data, error, loading, refresh } = useWorkspace(id => erp(id, `stock/?${new URLSearchParams({
  q: search.value, kind: kind.value, product_id: productId.value, order_id: orderId.value, location_id: locationId.value,
  date_from: dateFrom.value, date_to: dateTo.value, page: String(page.value),
})}`), [page, search, kind, productId, orderId, locationId, dateFrom, dateTo])
syncPage(page, data)
watch(() => route.query.product_id, value => { productId.value = value || '' })
watch(() => auth.activeCompanyId, async (companyId, previous) => {
  const current = ++generation
  dialog.value?.close(); reset(); products.value = []; success.value = ''
  if (previous !== undefined) clearFilters()
  if (!companyId) return
  optionsLoading.value = true
  try {
    const result = await allRecords(companyId, 'products', { active: 'all', ordering: 'name' })
    if (current === generation) products.value = result.filter(item => item.kind === 'goods')
  } catch (err) { if (current === generation) error.value = err.message }
  finally { if (current === generation) optionsLoading.value = false }
}, { immediate: true })
function clearFilters() {
  search.value = ''; kind.value = 'all'; productId.value = ''; dateFrom.value = ''; dateTo.value = ''
  router.replace({ query: {} })
}
function reset() { form.value = { product_id: '', quantity: '', reason: '' }; markClean(); actionError.value = ''; target.value = null }
function mayClose() { return !dirty.value || window.confirm('Discard this unsaved stock operation?') }
function open() {
  mode.value = 'adjustment'; target.value = null; actionError.value = ''
  form.value = { product_id: '', quantity: '', reason: '' }; markClean()
  requestId = crypto.randomUUID(); dialog.value.showModal()
}
function correct(item, nextMode) {
  mode.value = nextMode; target.value = item; actionError.value = ''
  form.value = { product_id: item.product_id, quantity: nextMode === 'return' ? item.returnable_quantity : String(-Number(item.quantity)), reason: '' }
  markClean(); requestId = crypto.randomUUID(); dialog.value.showModal()
}
async function save() {
  if (auth.busy) return
  auth.busy = true; actionError.value = ''; success.value = ''
  try {
    const endpoint = mode.value === 'adjustment' ? 'stock/' : `stock/${target.value.id}/${mode.value === 'return' ? 'return' : 'reverse'}/`
    const body = { reason: form.value.reason, request_id: requestId,
      ...(mode.value === 'reversal' ? {} : { quantity: form.value.quantity }),
      ...(mode.value === 'adjustment' ? { product_id: Number(form.value.product_id) } : {}) }
    const result = await erp(auth.activeCompanyId, endpoint, { method: 'POST', data: body })
    success.value = `${labels[result.kind]} recorded. Current stock: ${result.stock_quantity} ${result.unit}.`
    markClean(); dialog.value.close(); await refresh()
  } catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
</script>

<template>
  <section class="business-page">

    <div class="control-panel">
      <div class="control-title"><h1>Stock movements</h1><span class="muted">Receipts, deliveries, returns, and adjustments</span></div>
      <form class="search-field" role="search" @submit.prevent="refresh"><input v-model.lazy="search" aria-label="Search stock movements" placeholder="Search product, SKU, order, receipt, or reason" /><button aria-label="Search">Search</button></form>
      <button v-if="auth.canManage && auth.activeCompanyId" class="button-primary" :disabled="auth.busy" @click="open">Adjust stock</button>
      <div class="catalog-filters">
        <label>Movement type<select v-model="kind" aria-label="Movement type"><option value="all">All movements</option><option v-for="(label, key) in labels" :key="key" :value="key">{{ label }}</option></select></label>
        <label>Product<select v-model="productId" aria-label="Movement product"><option value="">All products</option><option v-for="product in products" :key="product.id" :value="String(product.id)">{{ product.name }}{{ product.is_active ? '' : ' (archived)' }}</option></select></label>
        <label>From<input v-model="dateFrom" aria-label="Movements from" type="date" /></label><label>To<input v-model="dateTo" aria-label="Movements to" type="date" /></label>
        <button v-if="hasFilters" type="button" class="inline-button" :disabled="auth.busy" @click="clearFilters">Clear filters</button>
      </div>
    </div>
    <div class="workspace-content">
      <p v-if="orderId" class="notice">Showing movements for {{ data?.results[0]?.order_number || `order ${orderId}` }}. <button type="button" class="inline-button" @click="clearFilters">Show all movements</button></p>
      <p v-if="locationId" class="notice">Showing movements touching location #{{ locationId }}. <button type="button" class="inline-button" @click="clearFilters">Show all movements</button></p>
      <p v-if="!auth.activeCompanyId" class="empty-state">Choose a company to view its stock.</p>
      <p v-if="error" class="notice error" role="alert">{{ error }} <button class="inline-button" @click="refresh">Retry</button></p>
      <p v-if="success" class="notice success" role="status">{{ success }}</p>
      <p v-if="loading" class="loading-state" role="status">Loading stock movements…</p>
      <template v-if="data">
        <div v-if="data.results.length" class="table-wrap" role="region" aria-label="Stock records" tabindex="0"><table class="data-table"><thead><tr><th>Product</th><th>Type</th><th>Reference</th><th>Quantity change</th><th>Reason</th><th>Locations</th><th>Date / by</th><th v-if="auth.canManage">Actions</th></tr></thead><tbody>
          <tr v-for="item in data.results" :key="item.id">
            <td>{{ item.product_name }}<small class="block muted">{{ item.sku }}</small></td>
            <td>{{ labels[item.kind] }}<small v-if="item.return_of_id" class="block muted">Returns #{{ item.return_of_id }}</small><small v-if="item.reversal_of_id" class="block muted">Reverses #{{ item.reversal_of_id }}</small><small v-if="item.reversed_by_id" class="block muted">Reversed by #{{ item.reversed_by_id }}</small></td>
            <td><RouterLink v-if="item.order_id" :to="`${item.order_kind === 'purchase' ? '/purchase' : '/sales'}/${item.order_id}`" class="text-link">{{ item.order_number }}</RouterLink><span v-else>Adjustment #{{ item.id }}</span><small v-if="item.receipt_number" class="block muted">{{ item.receipt_number }}</small></td>
            <td class="numeric" :class="Number(item.quantity) > 0 ? 'positive' : 'negative'">{{ Number(item.quantity) > 0 ? '+' : '' }}{{ item.quantity }} {{ item.unit }}<small v-if="item.kind === 'receipt'" class="block muted">Unreturned: {{ item.returnable_quantity }}</small></td>
            <td>{{ item.reason }}<small v-if="item.receipt_notes" class="block muted">{{ item.receipt_notes }}</small></td><td>{{ item.source_location_code }} &rarr; {{ item.destination_location_code }}<small v-if="item.location_inferred" class="record-detail">Inferred legacy locations</small></td><td>{{ dateLabel(item.created_at) }}<small class="block muted">{{ item.actor_email }}</small></td>
            <td v-if="auth.canManage"><button v-if="item.kind === 'receipt' && Number(item.returnable_quantity) > 0" type="button" class="inline-button" :disabled="auth.busy" @click="correct(item, 'return')">Return to supplier</button><button v-if="item.can_reverse" type="button" class="inline-button" :disabled="auth.busy" @click="correct(item, 'reversal')">Reverse adjustment</button></td>
          </tr>
        </tbody></table></div>
        <div v-else class="empty-state"><h2>{{ hasFilters ? 'No matching movements' : 'Every stock change, in one place' }}</h2><p>{{ hasFilters ? 'Change or clear the filters to see more movements.' : 'Receive a purchase, deliver a sale, or record an opening stock adjustment.' }}</p></div>
        <UiPagination v-model:page="page" :count="data.count" :page-size="data.page_size" :busy="loading || auth.busy" />
      </template>
    </div>
    <UiDialog ref="dialog" :title="title" :busy="auth.busy" :before-close="mayClose" @closed="reset" v-slot="{ requestClose }">
      <form @submit.prevent="save">
        <p v-if="mode === 'adjustment'" class="muted">Enter a quantity change: positive to add stock, negative to reduce it. A reason is required.</p>
        <p v-else-if="mode === 'return'" class="muted">Return goods from this receipt. The quantity must be within its unreturned amount and your current stock. The purchase order will show the quantity still awaiting replacement. Vendor bills and payments remain unchanged.</p>
        <p v-else class="muted">Record an opposite movement for this adjustment. The original entry stays in history. The reversal must not make stock negative.</p>
        <p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p>
        <fieldset :disabled="auth.busy || optionsLoading" class="receipt-fields">
          <label v-if="mode === 'adjustment'">Product<select v-model="form.product_id" name="stock_product" required><option value="">Choose a product…</option><option v-for="product in products.filter(item => item.is_active)" :key="product.id" :value="product.id">{{ product.name }}</option></select></label>
          <p v-else><strong>{{ target?.product_name }}</strong> · {{ target?.receipt_number || `Adjustment #${target?.id}` }}</p>
          <label v-if="mode !== 'reversal'">{{ mode === 'return' ? 'Quantity to return' : 'Quantity change' }}<input v-model="form.quantity" name="stock_quantity" type="number" :min="mode === 'return' ? '.001' : undefined" :max="mode === 'return' ? target?.returnable_quantity : undefined" step=".001" required /></label>
          <p v-else>Quantity change: <strong>{{ form.quantity }} {{ target?.unit }}</strong></p>
          <label>Reason<input v-model="form.reason" name="stock_reason" maxlength="300" required /></label>
        </fieldset>
        <footer class="dialog-footer"><button class="button-primary" :disabled="auth.busy || optionsLoading">{{ mode === 'return' ? 'Record return' : mode === 'reversal' ? 'Record reversal' : 'Record adjustment' }}</button><button type="button" class="button-secondary" :disabled="auth.busy" @click="requestClose">Discard</button></footer>
      </form>
    </UiDialog>
  </section>
</template>
