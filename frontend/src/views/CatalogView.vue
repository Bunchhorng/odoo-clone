<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { catalogDefinitions } from '../data/modules'
import { api } from '../services/api'
import { allRecords, erp, money, useWorkspace } from '../composables/erp'
import { syncPage, useDirtyForm, usePage } from '../composables/forms'
import { downloadText } from '../composables/download'
import AppIcon from '../components/AppIcon.vue'
import UiButton from '../components/ui/UiButton.vue'
import UiBadge from '../components/ui/UiBadge.vue'
import UiNotice from '../components/ui/UiNotice.vue'
import UiEmpty from '../components/ui/UiEmpty.vue'
import UiField from '../components/ui/UiField.vue'
import UiDialog from '../components/ui/UiDialog.vue'
import UiPagination from '../components/ui/UiPagination.vue'
import CatalogToolbar from '../components/catalog/CatalogToolbar.vue'
import RecordTable from '../components/catalog/RecordTable.vue'
import CatalogImport from '../components/catalog/CatalogImport.vue'
import ProductCategories from '../components/catalog/ProductCategories.vue'
import ERPListView from '../components/erp/ERPListView.vue'
import ERPFormView from '../components/erp/ERPFormView.vue'
import ERPKanbanView from '../components/erp/ERPKanbanView.vue'
import ERPGroupByMenu from '../components/erp/ERPGroupByMenu.vue'

const props = defineProps({ resource: { type: String, required: true } })
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const definition = computed(() => catalogDefinitions[props.resource])
const commercialCatalog = computed(() => ['contacts', 'products'].includes(props.resource))
const view = ref(definition.value.defaultView)
const search = ref('')
const query = ref('')
const archived = ref(['true', 'false', 'all'].includes(route.query.active) ? route.query.active : 'true')
const role = ref('all')
const kind = ref('all')
const category = ref('')
const stock = ref('all')
const ordering = ref('-id')
const categories = ref([])
const selected = ref([])
const groupBy = ref('')
const groupChoices = computed(() => props.resource === 'contacts'
  ? [{ value: 'organization', label: 'Organization' }, { value: 'country', label: 'Country' }]
  : [{ value: 'category_name', label: 'Category' }, { value: 'kind', label: 'Product type' }])
const page = usePage([query, archived, view, role, kind, category, stock, ordering, () => props.resource, () => route.query.project_id, () => route.query.stage, () => route.query.opportunity_id, () => route.query.department_id])
let timer
watch(search, value => { clearTimeout(timer); timer = setTimeout(() => { query.value = value }, 250) })
onUnmounted(() => clearTimeout(timer))
function filters() {
  const params = new URLSearchParams({ q: query.value, active: archived.value, ordering: ordering.value })
  if (props.resource === 'contacts') params.set('role', role.value)
  if (props.resource === 'employees' && route.query.department_id) params.set('department_id', route.query.department_id)
  if (props.resource === 'products') { params.set('kind', kind.value); params.set('category_id', category.value); params.set('stock', stock.value) }
  if (props.resource === 'tasks' && route.query.project_id) params.set('project_id', route.query.project_id)
  if (definition.value.stages && route.query.stage) params.set('stage', route.query.stage)
  if (props.resource === 'opportunities' && route.query.opportunity_id) params.set('opportunity_id', route.query.opportunity_id)
  return params
}
const { data, error, loading, refresh } = useWorkspace(async id => {
  const params = filters()
  params.set('page', String(page.value)); params.set('page_size', view.value === 'kanban' ? '100' : '24')
  const [result, settings] = await Promise.all([erp(id, `${props.resource}/?${params}`), erp(id, 'settings/')])
  return { ...result, currency: settings.currency }
}, [() => props.resource, query, archived, page, view, role, kind, category, stock, ordering, () => route.query.project_id, () => route.query.stage, () => route.query.opportunity_id, () => route.query.department_id])
syncPage(page, data)
const dialog = ref(null)
const importer = ref(null)
const categoryDialog = ref(null)
const editing = ref(null)
const form = ref({})
const { dirty, markClean } = useDirtyForm(form)
const options = ref({})
const formError = ref('')
const optionsLoading = ref(false)
const success = ref('')
let optionGeneration = 0
let categoryGeneration = 0
const hasFilters = computed(() => query.value || archived.value !== 'true' || role.value !== 'all' || kind.value !== 'all' || category.value || stock.value !== 'all' || route.query.stage || route.query.opportunity_id || route.query.department_id)
const sortChoices = computed(() => [
  { key: '-id', label: 'Newest first' }, { key: '-updated_at', label: 'Recently updated' },
  ...definition.value.columns.filter(column => column.sort !== false).flatMap(column => [
    { key: column.key, label: `${column.label}: ascending` }, { key: `-${column.key}`, label: `${column.label}: descending` },
  ]),
])

watch([() => auth.activeCompanyId, () => props.resource], () => {
  dialog.value?.close(); optionGeneration++; success.value = ''; options.value = {}; selected.value = []; form.value = {}; markClean()
  role.value = 'all'; kind.value = 'all'; category.value = ''; stock.value = 'all'; ordering.value = '-id'; groupBy.value = ''
  loadCategories()
}, { immediate: true })
watch(() => props.resource, () => { view.value = definition.value.defaultView; search.value = ''; query.value = ''; archived.value = route.query.active || 'true' })
watch(() => route.query.active, value => { archived.value = ['true', 'false', 'all'].includes(value) ? value : 'true' })
watch([data, page, view, query, archived, role, kind, category, stock, ordering], () => { selected.value = [] })
async function loadCategories() {
  const generation = ++categoryGeneration
  categories.value = []
  if (props.resource !== 'products' || !auth.activeCompanyId) return
  try {
    const result = await allRecords(auth.activeCompanyId, 'product-categories', { active: 'all', ordering: 'name' })
    if (generation === categoryGeneration) categories.value = result
  } catch (err) { if (generation === categoryGeneration) error.value = err.message }
}
function clearFilters() {
  search.value = ''; query.value = ''; archived.value = 'true'; role.value = 'all'; kind.value = 'all'; category.value = ''; stock.value = 'all'
  const remaining = { ...route.query }
  for (const key of ['stage', 'opportunity_id', 'department_id', 'active']) delete remaining[key]
  router.replace({ query: remaining })
}
function quotationLink(item, create = false) { return { path: create ? '/sales/new' : '/sales', query: { opportunity_id: item.id } } }
function changeStage(value) { router.replace({ query: { ...route.query, stage: value || undefined } }) }
function mayClose() { return !dirty.value || window.confirm('Discard your unsaved changes?') }
function closed() { optionGeneration++; form.value = {}; markClean(); optionsLoading.value = false }
async function open(item = null, stage = null) {
  editing.value = item
  formError.value = ''; options.value = {}
  form.value = Object.fromEntries(definition.value.fields.map(field => [field.key, item?.[field.key] ?? field.default ?? '']))
  if (stage) form.value.stage = stage
  if (!item && props.resource === 'tasks' && route.query.project_id) form.value.project_id = Number(route.query.project_id)
  markClean(); dialog.value.showModal()
  const generation = ++optionGeneration
  const companyId = auth.activeCompanyId
  optionsLoading.value = true
  try {
    const sources = [...new Set(definition.value.fields.filter(field => field.source).map(field => field.source))]
    const entries = await Promise.all(sources.map(async source => {
      const records = source === 'members'
        ? (await api(`companies/${companyId}/members/`)).members.filter(member => member.is_active && member.user_is_active).map(member => ({ id: member.user_id, name: member.name }))
        : await allRecords(companyId, source)
      for (const field of definition.value.fields.filter(field => field.source === source)) {
        const retained = item?.[field.key]
        if (retained && !records.some(record => record.id === retained)) {
          const name = item[({ contact_id: 'contact_name', project_id: 'project_name', assignee_id: 'assignee_name', category_id: 'category_name', department_id: 'department_name', user_id: 'user_name' })[field.key]] || 'Previous selection'
          records.push({ id: retained, name: `${name} (inactive)`, inactive: true })
        }
      }
      return [source, records]
    }))
    if (generation === optionGeneration) options.value = Object.fromEntries(entries)
  } catch (err) { if (generation === optionGeneration) formError.value = err.message }
  finally { if (generation === optionGeneration) optionsLoading.value = false }
}
function payload() {
  return Object.fromEntries(definition.value.fields.map(field => {
    let value = form.value[field.key]
    if (field.type === 'relation') value = value ? Number(value) : null
    if (field.integer) value = Number(value)
    if (field.type === 'date' && !value) value = null
    return [field.key, value]
  }))
}
async function save() {
  if (auth.busy) return
  auth.busy = true; formError.value = ''
  try {
    const values = payload()
    const changes = editing.value ? Object.fromEntries(Object.entries(values).filter(([key, value]) => {
      const field = definition.value.fields.find(field => field.key === key)
      const old = editing.value[key] ?? (['date', 'relation'].includes(field.type) ? null : '')
      return value !== old
    })) : values
    if (!editing.value || Object.keys(changes).length) await erp(auth.activeCompanyId, `${props.resource}/${editing.value ? `${editing.value.id}/` : ''}`, { method: editing.value ? 'PATCH' : 'POST', data: changes })
    markClean(); dialog.value.close(); success.value = `${definition.value.singular} saved.`; await refresh()
  } catch (err) { formError.value = err.message }
  finally { auth.busy = false }
}
async function update(item, fields) {
  if (auth.busy) return
  auth.busy = true; success.value = ''
  try { await erp(auth.activeCompanyId, `${props.resource}/${item.id}/`, { method: 'PATCH', data: fields }); await refresh() }
  catch (err) { error.value = err.message }
  finally { auth.busy = false }
}
function toggle(id) { selected.value = selected.value.includes(id) ? selected.value.filter(value => value !== id) : [...selected.value, id] }
function toggleAll() { selected.value = selected.value.length === data.value.results.length ? [] : data.value.results.map(item => item.id) }
async function bulk(action) {
  if (auth.busy || !selected.value.length || !window.confirm(`${action === 'archive' ? 'Archive' : 'Restore'} ${selected.value.length} selected records?`)) return
  auth.busy = true; success.value = ''
  try {
    const result = await erp(auth.activeCompanyId, `${props.resource}/bulk/`, { method: 'POST', data: { ids: selected.value, action } })
    success.value = `${result.changed} records ${action === 'archive' ? 'archived' : 'restored'}.`; selected.value = []; await refresh()
  } catch (err) { error.value = err.message }
  finally { auth.busy = false }
}
async function exportCSV() {
  if (auth.busy) return
  auth.busy = true; error.value = ''
  try { downloadText(await erp(auth.activeCompanyId, `${props.resource}/export/?${filters()}`, { format: 'text' }), `${props.resource}.csv`); success.value = 'CSV downloaded for all matching records.' }
  catch (err) { error.value = err.message }
  finally { auth.busy = false }
}
async function imported(count) { success.value = `${count} records imported.`; page.value = 1; await refresh() }
async function categoriesChanged() { await loadCategories(); await refresh() }
function drop(event, stage) {
  const id = Number(event.dataTransfer.getData('text/plain'))
  const item = data.value?.results.find(record => record.id === id)
  if (item && auth.canManage) update(item, { stage })
}
function stageTotal(stage) { return (data.value?.results || []).filter(item => item.stage === stage).reduce((sum, item) => sum + Number(item.expected_revenue || 0), 0) }
</script>

<template>
  <section class="business-page">



    <CatalogToolbar v-model:search="search" v-model:active="archived" v-model:view="view" :title="definition.title" :count="data?.count" :default-view="definition.defaultView" :can-create="auth.canManage" :busy="auth.busy" :disabled="!auth.activeCompanyId" @create="open()" @search="query = search">
      <template #subtitle><span v-if="route.query.department_id"> · filtered by department <RouterLink to="/employees" class="text-link">Clear</RouterLink></span><span v-if="route.query.project_id"> · filtered by project</span></template>
      <template v-if="commercialCatalog" #actions><ERPGroupByMenu v-if="view === 'list'" v-model="groupBy" :options="groupChoices" :disabled="loading || auth.busy" /><UiButton v-if="resource === 'products'" :disabled="auth.busy || !auth.activeCompanyId" @click="categoryDialog.showModal()">Categories</UiButton><UiButton v-if="auth.canManage" :disabled="auth.busy || !auth.activeCompanyId" @click="importer.showModal()">Import</UiButton><UiButton :disabled="auth.busy || loading || !auth.activeCompanyId" @click="exportCSV">Export CSV</UiButton></template>
      <template v-if="commercialCatalog" #filters>
        <label v-if="resource === 'contacts'">Contact role<select v-model="role" aria-label="Contact role"><option value="all">Customers and suppliers</option><option value="customer">Customers</option><option value="supplier">Suppliers</option><option value="both">Both roles</option></select></label>
        <template v-if="resource === 'products'"><label>Product type<select v-model="kind" aria-label="Product type"><option value="all">All types</option><option value="goods">Goods</option><option value="service">Services</option></select></label><label>Category<select v-model="category" aria-label="Product category"><option value="">All categories</option><option value="none">Uncategorized</option><option v-for="item in categories" :key="item.id" :value="String(item.id)">{{ item.name }}{{ item.is_active ? '' : ' (archived)' }}</option></select></label><label>Availability<select v-model="stock" aria-label="Stock availability"><option value="all">Any stock</option><option value="low">At or below threshold</option><option value="out">Out of stock</option></select></label></template>
        <label>Sort by<select v-model="ordering" aria-label="Sort records"><option v-for="choice in sortChoices" :key="choice.key" :value="choice.key">{{ choice.label }}</option></select></label>
        <UiButton v-if="hasFilters" variant="text" :disabled="auth.busy" @click="clearFilters">Clear filters</UiButton>
      </template>
      <template v-else-if="resource === 'opportunities'" #filters>
        <label>Stage<select :value="route.query.stage || ''" aria-label="Opportunity stage" @change="changeStage($event.target.value)"><option value="">All stages</option><option v-for="[value, label] in definition.stages" :key="value" :value="value">{{ label }}</option></select></label>
        <span v-if="route.query.opportunity_id" class="muted">Showing the linked opportunity</span>
        <UiButton v-if="hasFilters" variant="text" :disabled="auth.busy" @click="clearFilters">Clear filters</UiButton>
      </template>
    </CatalogToolbar>
    <ERPListView :loading="loading" :error="error" :has-company="Boolean(auth.activeCompanyId)" :title="definition.title" @retry="refresh">
      <template #feedback><UiNotice v-if="success">{{ success }}</UiNotice></template>
      <template v-if="data">
        <div v-if="commercialCatalog && auth.canManage && data.results.length" class="selection-bar"><label class="checkbox-label"><input type="checkbox" aria-label="Select all records on this page" :checked="selected.length === data.results.length" :indeterminate="selected.length > 0 && selected.length < data.results.length" :disabled="auth.busy" @change="toggleAll" />{{ selected.length }} selected on this page</label><template v-if="selected.length"><UiButton :disabled="auth.busy" @click="bulk('archive')">Archive selected</UiButton><UiButton :disabled="auth.busy" @click="bulk('restore')">Restore selected</UiButton><UiButton variant="text" :disabled="auth.busy" @click="selected = []">Clear selection</UiButton></template></div>
        <ERPKanbanView v-if="view === 'kanban'" :stages="definition.stages" :rows="data.results" :title="definition.title" :can-create="auth.canManage" :busy="auth.busy" @create="open(null, $event)" @drop="drop">
          <template #column-header="{ stage }"><p v-if="resource === 'opportunities'" class="column-total">{{ money(stageTotal(stage), data.currency) }}</p></template>
          <template #card="{ row: item }">            <article class="kanban-card" :draggable="auth.canManage && !auth.busy" @dragstart="$event.dataTransfer.setData('text/plain', String(item.id))"><button class="record-title" @click="open(item)">{{ item.title }}</button><strong v-if="resource === 'opportunities'">{{ money(item.expected_revenue, data.currency) }}</strong><p class="muted">{{ item.contact_name || item.project_name || 'No customer selected' }}</p><div class="card-meta"><UiBadge v-if="resource === 'tasks'" :tone="item.priority">{{ item.priority }}</UiBadge><span v-else>{{ item.probability }}%</span><span>{{ item.due_date || item.expected_date || '' }}</span></div><select v-if="auth.canManage" :value="item.stage" :aria-label="`Stage for ${item.title}`" :disabled="auth.busy" @change="update(item, { stage: $event.target.value })"><option v-for="[value, text] in definition.stages" :key="value" :value="value">{{ text }}</option></select><div v-if="resource === 'tasks'" class="crm-links"><RouterLink :to="`/timesheets?task_id=${item.id}`" class="text-link">Time entries</RouterLink><RouterLink v-if="item.helpdesk_ticket_id" :to="`/helpdesk/${item.helpdesk_ticket_id}`" class="text-link">{{ item.helpdesk_ticket_number }}</RouterLink></div><div v-if="resource === 'opportunities'" class="crm-links"><RouterLink :to="quotationLink(item)" class="text-link">Quotations &amp; orders ({{ item.quotation_count }})</RouterLink><RouterLink v-if="auth.canManage && item.is_active" :to="quotationLink(item, true)" class="text-link">New quotation</RouterLink></div></article></template>
        </ERPKanbanView>
        <div v-else-if="view === 'cards' && data.results.length" class="record-grid">
          <article v-for="item in data.results" :key="item.id" class="record-card" :class="{ selected: selected.includes(item.id) }">
            <label v-if="commercialCatalog && auth.canManage" class="card-selection"><input type="checkbox" :aria-label="`Select ${item.name}`" :checked="selected.includes(item.id)" :disabled="auth.busy" @change="toggle(item.id)" /><span class="sr-only">Select {{ item.name }}</span></label>
            <button class="record-card-main" @click="open(item)"><span class="record-avatar" :class="resource"><AppIcon v-if="resource !== 'contacts'" :name="definition.icon" /><span v-else>{{ item.name[0].toUpperCase() }}</span></span><div><h2>{{ item.name }}</h2><p class="muted">{{ item.organization || item.sku || item.job_title || item.contact_name || (resource === 'projects' ? 'Internal project' : '') }}</p><p v-if="resource === 'contacts'" class="muted">{{ item.email || item.phone || 'No contact details yet' }}</p><p v-if="resource === 'employees'" class="muted">{{ item.department_name || 'No department' }} · {{ item.employee_code }}</p><p v-if="resource === 'employees'" class="muted">{{ item.work_email || item.work_phone }}</p><template v-if="resource === 'products'"><p class="price">{{ money(item.sale_price, data.currency) }}</p><p class="muted">{{ item.kind === 'goods' ? `${item.stock_quantity} ${item.unit} on hand` : 'Service' }}</p><p v-if="item.category_name" class="muted">{{ item.category_name }}</p></template></div></button>
            <div class="record-card-footer"><template v-if="resource === 'contacts'"><UiBadge v-if="item.is_customer">Customer</UiBadge><UiBadge v-if="item.is_supplier" tone="blue">Supplier</UiBadge></template><RouterLink v-if="resource === 'products' && item.kind === 'goods'" :to="`/inventory/movements?product_id=${item.id}`" class="text-link">Movements</RouterLink><RouterLink v-if="resource === 'projects'" :to="`/tasks?project_id=${item.id}`" class="text-link">Open tasks →</RouterLink><RouterLink v-if="resource === 'projects'" :to="`/timesheets?project_id=${item.id}`" class="text-link">Time entries</RouterLink><RouterLink v-if="resource === 'employees' && (auth.canManage || item.user_id === auth.user.id)" :to="`/timesheets?employee_id=${item.id}`" class="text-link">Time entries</RouterLink><UiBadge v-if="!item.is_active" tone="cancelled">Archived</UiBadge><UiButton v-if="auth.canManage" variant="text" class="archive-button" :disabled="auth.busy" @click="update(item, { is_active: !item.is_active })">{{ item.is_active ? 'Archive' : 'Restore' }}</UiButton></div>
          </article>
        </div>
        <RecordTable v-else-if="view === 'list' && data.results.length" :rows="data.results" :columns="definition.columns" :group-by="commercialCatalog ? groupBy : ''" :title="definition.title" :currency="data.currency" :ordering="ordering" :sortable="commercialCatalog" :selectable="commercialCatalog && auth.canManage" :selected="selected" :busy="auth.busy" @open="open" @sort="ordering = $event" @toggle="toggle" @toggle-all="toggleAll"><template v-if="auth.canManage || ['opportunities', 'products', 'projects', 'tasks', 'employees', 'departments'].includes(resource)" #actions="{ row }"><RouterLink v-if="['projects', 'tasks'].includes(resource)" :to="`/timesheets?${resource === 'projects' ? 'project_id' : 'task_id'}=${row.id}`" class="text-link">Time entries</RouterLink><RouterLink v-if="resource === 'tasks' && row.helpdesk_ticket_id" :to="`/helpdesk/${row.helpdesk_ticket_id}`" class="text-link">{{ row.helpdesk_ticket_number }}</RouterLink><RouterLink v-if="resource === 'departments'" :to="`/employees?department_id=${row.id}`" class="text-link">Employees</RouterLink><RouterLink v-if="resource === 'employees' && (auth.canManage || row.user_id === auth.user.id)" :to="`/timesheets?employee_id=${row.id}`" class="text-link">Time entries</RouterLink><RouterLink v-if="resource === 'products' && row.kind === 'goods'" :to="`/inventory/movements?product_id=${row.id}`" class="text-link">Movements</RouterLink><template v-if="resource === 'opportunities'"><RouterLink :to="quotationLink(row)" class="text-link">Quotations ({{ row.quotation_count }})</RouterLink><RouterLink v-if="auth.canManage && row.is_active" :to="quotationLink(row, true)" class="text-link">New quotation</RouterLink></template><UiButton v-if="auth.canManage" variant="text" :disabled="auth.busy" @click="update(row, { is_active: !row.is_active })">{{ row.is_active ? 'Archive' : 'Restore' }}</UiButton></template></RecordTable>
        <UiEmpty v-else :icon="definition.icon" :title="hasFilters ? 'No matching records' : `No ${definition.title.toLowerCase()} yet`" :description="hasFilters ? 'Try a different search or clear your filters.' : `Create your first ${definition.singular.toLowerCase()} to get started.`"><UiButton v-if="hasFilters" @click="clearFilters">Clear filters</UiButton><UiButton v-else-if="auth.canManage" variant="primary" @click="open()">New {{ definition.singular.toLowerCase() }}</UiButton></UiEmpty>
        <UiPagination v-model:page="page" :count="data.count" :page-size="data.page_size" :busy="loading || auth.busy" />
      </template>
    </ERPListView>
    <UiDialog ref="dialog" :title="editing ? definition.singular : `New ${definition.singular.toLowerCase()}`" :busy="auth.busy" :before-close="mayClose" @closed="closed" v-slot="{ requestClose }">
      <div v-if="resource === 'tasks' && editing" class="crm-links"><RouterLink :to="`/timesheets?task_id=${editing.id}`" class="text-link">Time entries</RouterLink><RouterLink v-if="editing.helpdesk_ticket_id" :to="`/helpdesk/${editing.helpdesk_ticket_id}`" class="text-link">{{ editing.helpdesk_ticket_number }}</RouterLink></div><div v-if="resource === 'opportunities' && editing" class="crm-links"><RouterLink :to="quotationLink(editing)" class="text-link">Quotations &amp; orders ({{ editing.quotation_count }})</RouterLink><RouterLink v-if="auth.canManage && editing.is_active" :to="quotationLink(editing, true)" class="text-link">New quotation</RouterLink></div>
      <ERPFormView :error="formError" :busy="auth.busy || optionsLoading" :readonly="!auth.canManage" @submit="save">
        <template #context><p v-if="optionsLoading" class="muted" role="status">Loading available records…</p></template>
        <UiField v-for="field in definition.fields" :key="field.key" v-model="form[field.key]" :field="field" :options="options[field.source] || []" />
        <template #actions><UiButton v-if="auth.canManage" type="submit" variant="primary" :disabled="optionsLoading" :busy="auth.busy">{{ auth.busy ? 'Saving…' : 'Save' }}</UiButton><UiButton :disabled="auth.busy" @click="requestClose">{{ auth.canManage ? 'Discard' : 'Close' }}</UiButton></template>
      </ERPFormView>
    </UiDialog>
    <CatalogImport v-if="commercialCatalog && auth.canManage" ref="importer" :resource="resource" :title="definition.title" @imported="imported" />
    <ProductCategories v-if="resource === 'products'" ref="categoryDialog" @changed="categoriesChanged" />
  </section>
</template>
