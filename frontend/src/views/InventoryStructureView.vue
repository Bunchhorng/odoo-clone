<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { allRecords, erp, useWorkspace } from '../composables/erp'
import { syncPage, useDirtyForm, usePage } from '../composables/forms'
import ERPListView from '../components/erp/ERPListView.vue'
import ERPFormView from '../components/erp/ERPFormView.vue'
import ERPModal from '../components/erp/ERPModal.vue'
import ERPSearchBar from '../components/erp/ERPSearchBar.vue'
import UiPagination from '../components/ui/UiPagination.vue'
import { locationHierarchy } from '../composables/inventoryLocations'

const props = defineProps({ resource: { type: String, required: true } })
const auth = useAuthStore()
const route = useRoute()
const warehouses = computed(() => props.resource === 'warehouses')
const title = computed(() => warehouses.value ? 'Warehouses' : 'Stock locations')
const singular = computed(() => warehouses.value ? 'warehouse' : 'location')
const usages = { internal: 'Internal', supplier: 'Supplier', customer: 'Customer', inventory: 'Inventory adjustment', view: 'View / grouping' }
const search = ref(''), query = ref(''), active = ref('true'), usage = ref(''), view = ref('list')
const page = usePage([query, active, usage, view, () => props.resource, () => route.query.warehouse_id])
let searchTimer
watch(search, value => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { query.value = value.trim() }, 250) })
onUnmounted(() => { clearTimeout(searchTimer); formGeneration++ })
const { data, loading, error, refresh } = useWorkspace(async id => {
  const filters = { q: query.value, active: active.value, ...(!warehouses.value && usage.value ? { usage: usage.value } : {}) }
  if (!warehouses.value && route.query.warehouse_id) filters.warehouse_id = route.query.warehouse_id
  if (!warehouses.value && view.value === 'tree') {
    const rows = await allRecords(id, 'locations', filters)
    return { results: rows, count: rows.length, page: 1, page_size: Math.max(1, rows.length) }
  }
  return erp(id, `${props.resource}/?${new URLSearchParams({ ...filters, page: String(page.value), page_size: '25' })}`)
}, [query, active, usage, view, page, () => props.resource, () => route.query.warehouse_id])
syncPage(page, data)
const hierarchy = computed(() => locationHierarchy(data.value?.results || []))
const dialog = ref(null), editing = ref(null), form = ref({}), options = ref([])
const optionsLoading = ref(false), formError = ref(''), success = ref('')
const { dirty, markClean } = useDirtyForm(form)
let formGeneration = 0
function resetForm() { formGeneration++; form.value = {}; markClean(); options.value = []; optionsLoading.value = false }
function mayClose() { return !dirty.value || window.confirm('Discard your unsaved changes?') }
watch([() => auth.activeCompanyId, () => props.resource], () => {
  dialog.value?.close(); resetForm(); success.value = ''; search.value = ''; query.value = ''; active.value = 'true'; usage.value = ''; view.value = 'list'
})
const parentOptions = computed(() => options.value.filter(item => item.id !== editing.value?.id &&
  (item.is_active || item.id === form.value.parent_id) && (item.usage === 'view' || item.usage === form.value.usage)))
async function open(item = null) {
  editing.value = item; formError.value = ''; options.value = []
  form.value = warehouses.value
    ? { name: item?.name || '', code: item?.code || '', stock_location_id: item?.stock_location_id || '' }
    : { name: item?.name || '', code: item?.code || '', usage: item?.usage || 'internal', parent_id: item?.parent_id || '' }
  markClean(); optionsLoading.value = true; dialog.value.showModal()
  const current = ++formGeneration
  try {
    const locations = await allRecords(auth.activeCompanyId, 'locations', { active: 'all' })
    if (current === formGeneration) options.value = locations
  } catch (failure) { if (current === formGeneration) formError.value = failure.message }
  finally { if (current === formGeneration) optionsLoading.value = false }
}
async function save() {
  if (auth.busy || !auth.canManage || optionsLoading.value) return
  auth.busy = true; formError.value = ''
  const id = auth.activeCompanyId
  try {
    const payload = { name: form.value.name, code: form.value.code }
    if (!warehouses.value) { payload.usage = form.value.usage; payload.parent_id = form.value.parent_id ? Number(form.value.parent_id) : null }
    else if (!editing.value) payload.stock_location_id = form.value.stock_location_id ? Number(form.value.stock_location_id) : null
    await erp(id, `${props.resource}/${editing.value ? `${editing.value.id}/` : ''}`, { method: editing.value ? 'PATCH' : 'POST', data: payload })
    markClean(); dialog.value.close(); success.value = `${warehouses.value ? 'Warehouse' : 'Location'} saved.`; await refresh()
  } catch (failure) { formError.value = failure.message }
  finally { auth.busy = false }
}
async function archive(item) {
  if (auth.busy || !auth.canManage || !window.confirm(`${item.is_active ? 'Archive' : 'Restore'} ${item.name}?`)) return
  auth.busy = true; error.value = ''; success.value = ''
  try {
    await erp(auth.activeCompanyId, `${props.resource}/${item.id}/`, { method: 'PATCH', data: { is_active: !item.is_active } })
    success.value = `${warehouses.value ? 'Warehouse' : 'Location'} ${item.is_active ? 'archived' : 'restored'}.`; await refresh()
  } catch (failure) { error.value = failure.message }
  finally { auth.busy = false }
}
function canArchive(item) { return !item.is_default && !item.is_system && !item.warehouse_active }
</script>

<template>
  <section class="business-page inventory-structure">
    <div class="control-panel">
      <div class="control-title"><h1>{{ title }}</h1><span class="muted">{{ data?.count || 0 }} records · {{ auth.activeCompany?.name || 'Choose a company' }}</span></div>
      <ERPSearchBar v-model="search" :label="`Search ${title.toLowerCase()}`" @search="query = search.trim()" />
      <div class="control-actions">
        <button v-if="auth.canManage" type="button" class="button-primary" :disabled="auth.busy || !auth.activeCompanyId" @click="open()">New {{ singular }}</button>
        <select v-model="active" aria-label="Structure active records"><option value="true">Active</option><option value="false">Archived</option><option value="all">All records</option></select>
        <select v-if="!warehouses" v-model="usage" aria-label="Location type filter"><option value="">All location types</option><option v-for="(label, value) in usages" :key="value" :value="value">{{ label }}</option></select>
        <div v-if="!warehouses" class="view-switch" role="group" aria-label="Location view"><button type="button" :aria-pressed="view === 'list'" :class="{ active: view === 'list' }" @click="view = 'list'">List</button><button type="button" :aria-pressed="view === 'tree'" :class="{ active: view === 'tree' }" @click="view = 'tree'">Hierarchy</button></div>
      </div>
    </div>
    <ERPListView :loading="loading" :error="error" :has-company="Boolean(auth.activeCompanyId)" :title="title" @retry="refresh">
      <template #feedback><p v-if="success" class="notice success" role="status">{{ success }}</p></template>
      <p class="muted inventory-scope">Existing receipts, deliveries and adjustments use the default warehouse. Additional warehouses and locations are configuration only in INV-01; transfers and reservations are not available.</p>
      <p v-if="route.query.warehouse_id && !warehouses" class="notice">Showing this warehouse's location hierarchy. <RouterLink to="/inventory/locations" class="text-link">Show all locations</RouterLink></p>
      <div v-if="data && !data.results.length" class="empty-state"><h2>No {{ warehouses ? 'warehouses' : 'locations' }} found</h2><p>Try another search or active-state filter.</p><button v-if="auth.canManage" type="button" class="button-secondary" @click="open()">New {{ singular }}</button></div>
      <template v-else-if="data">
        <template v-if="!warehouses && view === 'tree'">
          <p class="muted">All matching locations are included. A filtered-out parent is shown in the location's parent label.</p>
          <ol class="location-hierarchy" aria-label="Location hierarchy"><li v-for="entry in hierarchy" :key="entry.row.id" :style="{ '--location-depth': Math.min(entry.depth, 4) }"><div><button type="button" class="text-link" @click="open(entry.row)"><strong>{{ entry.row.code }}</strong> · {{ entry.row.name }}</button><small class="muted">{{ usages[entry.row.usage] }}<span v-if="entry.row.parent_id"> · Parent: {{ entry.row.parent_code }}</span><span v-if="!entry.row.is_active"> · Archived</span></small></div><RouterLink :to="`/inventory/movements?location_id=${entry.row.id}`" class="text-link">Movements</RouterLink></li></ol>
        </template>
        <div v-else class="table-wrap" role="region" :aria-label="`${title} table`" tabindex="0"><table class="data-table"><caption class="sr-only">{{ title }}</caption><thead><tr><th scope="col">Code</th><th scope="col">Name</th><th scope="col">{{ warehouses ? 'Internal stock location' : 'Type' }}</th><th scope="col">{{ warehouses ? 'Posting context' : 'Parent location' }}</th><th scope="col">Status</th><th scope="col">Actions</th></tr></thead><tbody><tr v-for="item in data.results" :key="item.id"><td><button type="button" class="text-link" @click="open(item)">{{ item.code }}</button></td><td>{{ item.name }}</td><td>{{ warehouses ? item.stock_location_code : usages[item.usage] }}</td><td>{{ warehouses ? item.is_default ? 'Default for existing APIs' : 'Additional warehouse' : item.parent_code || 'Root location' }}</td><td><span class="badge" :class="item.is_active ? 'confirmed' : 'cancelled'">{{ item.is_active ? 'Active' : 'Archived' }}</span><span v-if="!warehouses && item.is_system" class="record-detail">Default posting location</span></td><td><div class="row-actions"><RouterLink v-if="warehouses" :to="`/inventory/locations?warehouse_id=${item.id}`" class="text-link">Locations</RouterLink><RouterLink v-else :to="`/inventory/movements?location_id=${item.id}`" class="text-link">Movements</RouterLink><button v-if="auth.canManage && (!item.is_active || canArchive(item))" type="button" class="inline-button" :disabled="auth.busy" @click="archive(item)">{{ item.is_active ? 'Archive' : 'Restore' }}</button></div></td></tr></tbody></table></div>
        <UiPagination v-model:page="page" :count="data.count" :page-size="data.page_size" :busy="loading || auth.busy" />
      </template>
    </ERPListView>
    <ERPModal ref="dialog" :title="`${editing ? 'Edit' : 'New'} ${singular}`" :busy="auth.busy" :before-close="mayClose" @closed="resetForm" v-slot="{ requestClose }">
      <ERPFormView :busy="auth.busy || optionsLoading" :readonly="!auth.canManage" :error="formError" @submit="save">
        <template #context><p v-if="optionsLoading" class="muted" role="status">Loading location choices…</p><p v-if="editing?.is_default || editing?.is_system" class="notice">This default posting record must remain active. Its location type and parent are protected.</p></template>
        <label>Name<input v-model="form.name" name="structure_name" maxlength="100" required /></label>
        <label>{{ warehouses ? 'Warehouse short code' : 'Location code' }}<input v-model="form.code" name="structure_code" :maxlength="warehouses ? 16 : 64" :pattern="warehouses ? '[A-Za-z][A-Za-z0-9_-]{0,15}' : undefined" required /></label>
        <template v-if="warehouses"><label class="full-width">Internal stock location<select v-model="form.stock_location_id" name="warehouse_stock_location" :disabled="Boolean(editing)"><option value="">Create an internal stock location automatically</option><option v-for="location in options.filter(item => item.usage === 'internal' && !item.parent_id && (!item.warehouse_id || item.id === editing?.stock_location_id))" :key="location.id" :value="location.id">{{ location.code }} · {{ location.name }}</option></select><small class="field-help">Company and stock-location identity stay fixed after creation.</small></label></template>
        <template v-else><label>Location type<select v-model="form.usage" name="location_usage" :disabled="editing?.is_system || Boolean(editing?.warehouse_id)"><option v-for="(label, value) in usages" :key="value" :value="value">{{ label }}</option></select></label><label>Parent location<select v-model="form.parent_id" name="location_parent" :disabled="editing?.is_system || Boolean(editing?.warehouse_id)"><option value="">Root location</option><option v-for="location in parentOptions" :key="location.id" :value="location.id">{{ location.code }} · {{ location.name }}</option></select></label></template>
        <template #actions><button v-if="auth.canManage" type="submit" class="button-primary" :disabled="auth.busy || optionsLoading">{{ auth.busy ? 'Saving…' : 'Save' }}</button><button type="button" class="button-secondary" :disabled="auth.busy" @click="requestClose">{{ auth.canManage ? 'Discard' : 'Close' }}</button></template>
      </ERPFormView>
    </ERPModal>
  </section>
</template>
