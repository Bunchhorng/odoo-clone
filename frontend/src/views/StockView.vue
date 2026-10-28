<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { allRecords, dateLabel, erp, useWorkspace } from '../composables/erp'
import { syncPage, usePage } from '../composables/forms'
const auth = useAuthStore()
const page = usePage()
const dialog = ref(null)
const products = ref([])
const form = ref({ product_id: '', quantity: '', reason: '' })
const actionError = ref('')
const optionsLoading = ref(false)
let generation = 0
const { data, error, loading, refresh } = useWorkspace(id => erp(id, `stock/?page=${page.value}`), [page])
syncPage(page, data)
watch(() => auth.activeCompanyId, () => { generation++; dialog.value?.close(); products.value = []; actionError.value = '' })
async function open() {
  const current = ++generation
  form.value = { product_id: '', quantity: '', reason: '' }; actionError.value = ''; products.value = []
  dialog.value.showModal(); optionsLoading.value = true
  try { const result = await allRecords(auth.activeCompanyId, 'products'); if (current === generation) products.value = result.filter(item => item.kind === 'goods') }
  catch (err) { if (current === generation) actionError.value = err.message }
  finally { if (current === generation) optionsLoading.value = false }
}
async function save() {
  auth.busy = true; actionError.value = ''
  try { await erp(auth.activeCompanyId, 'stock/', { method: 'POST', data: { ...form.value, product_id: Number(form.value.product_id) } }); dialog.value.close(); await refresh() }
  catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
</script>
<template>
  <section class="business-page"><div class="module-tabs"><RouterLink to="/inventory">Products</RouterLink><RouterLink to="/inventory/movements" class="active">Stock movements</RouterLink></div><div class="control-panel"><div class="control-title"><h1>Stock movements</h1><span class="muted">Receipts, deliveries, and adjustments</span></div><button v-if="auth.canManage && auth.activeCompanyId" class="button-primary" :disabled="auth.busy" @click="open">Adjust stock</button></div><div class="workspace-content"><p v-if="!auth.activeCompanyId" class="empty-state">Choose a company to view its stock.</p><p v-if="error || actionError" class="notice error" role="alert">{{ actionError || error }}</p><p v-if="loading" class="loading-state" role="status">Loading stock movements…</p><template v-if="data"><div v-if="data.results.length" class="table-wrap"><table class="data-table"><thead><tr><th>Product</th><th>Reference</th><th>Quantity change</th><th>Reason</th><th>Date</th><th>By</th></tr></thead><tbody><tr v-for="item in data.results" :key="item.id"><td>{{ item.product_name }}<small class="block muted">{{ item.sku }}</small></td><td>{{ item.order_number }}</td><td class="numeric" :class="Number(item.quantity) > 0 ? 'positive' : 'negative'">{{ Number(item.quantity) > 0 ? '+' : '' }}{{ item.quantity }}</td><td>{{ item.reason }}</td><td>{{ dateLabel(item.created_at) }}</td><td>{{ item.actor_email }}</td></tr></tbody></table></div><div v-else class="empty-state"><h2>Every stock change, in one place</h2><p>Receive a purchase, deliver a sale, or record an opening stock adjustment.</p></div><div v-if="data.count > data.page_size" class="pagination"><span>{{ data.count }} movements · page {{ page }}</span><button :disabled="page === 1" @click="page--">Previous</button><button :disabled="page * data.page_size >= data.count" @click="page++">Next</button></div></template></div><dialog ref="dialog" class="record-dialog small-dialog" @cancel="auth.busy && $event.preventDefault()"><form @submit.prevent="save"><header class="dialog-header"><h2>Adjust stock</h2><button type="button" aria-label="Close" :disabled="auth.busy" @click="dialog.close()">×</button></header><p class="muted">Enter a quantity change: positive to add stock, negative to reduce it. A reason is required.</p><p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p><fieldset :disabled="auth.busy || optionsLoading"><label>Product<select v-model="form.product_id" name="stock_product" required><option value="">Choose a product…</option><option v-for="product in products" :key="product.id" :value="product.id">{{ product.name }} — {{ product.stock_quantity }} {{ product.unit }}</option></select></label><label>Quantity change<input v-model="form.quantity" name="stock_quantity" type="number" step=".001" required /></label><label>Reason<input v-model="form.reason" name="stock_reason" maxlength="300" required /></label></fieldset><footer class="dialog-footer"><button class="button-primary" :disabled="auth.busy || optionsLoading">Record adjustment</button><button type="button" class="button-secondary" :disabled="auth.busy" @click="dialog.close()">Discard</button></footer></form></dialog></section>
</template>
