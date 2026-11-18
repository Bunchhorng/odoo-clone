<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { allRecords, erp, today, useWorkspace } from '../composables/erp'
import { syncPage, useDirtyForm, usePage } from '../composables/forms'
import { downloadText } from '../composables/download'
import UiDialog from '../components/ui/UiDialog.vue'
import UiPagination from '../components/ui/UiPagination.vue'

const auth = useAuthStore(), route = useRoute()
const status = ref(''), search = ref(''), dateFrom = ref(''), dateTo = ref('')
const context = computed(() => Object.fromEntries(['project_id', 'task_id', 'ticket_id', 'employee_id'].filter(key => route.query[key]).map(key => [key, String(route.query[key])])))
const page = usePage([status, search, dateFrom, dateTo, context])
const dialog = ref(null), mode = ref(''), target = ref(null), form = ref({}), actionError = ref(''), conflict = ref(false), message = ref('')
const { dirty, markClean } = useDirtyForm(form)
function params() { return new URLSearchParams({ ...context.value, status: status.value, q: search.value, date_from: dateFrom.value, date_to: dateTo.value }) }
const { data, error, loading, refresh } = useWorkspace(async id => {
  const query = params(); query.set('page', String(page.value))
  const [entries, employees, projects, tasks, tickets, ticket] = await Promise.all([
    erp(id, `timesheets/?${query}`), allRecords(id, 'employees'), allRecords(id, 'projects'), allRecords(id, 'tasks'), allRecords(id, 'helpdesk'),
    context.value.ticket_id ? erp(id, `helpdesk/${context.value.ticket_id}/`) : Promise.resolve(null),
  ])
  return { ...entries, employees, projects, tasks, tickets, ticket }
}, [context, status, search, dateFrom, dateTo, page])
syncPage(page, data)
const employeeOptions = computed(() => data.value?.employees.filter(item => auth.canManage || item.user_id === auth.user.id) || [])
const taskOptions = computed(() => data.value?.tasks.filter(item => item.project_id === Number(form.value.project_id)) || [])
const ticketOptions = computed(() => data.value?.tickets.filter(item => item.project_id === Number(form.value.project_id)) || [])
function duration(minutes) { return `${Math.floor(Number(minutes) / 60)}h ${Number(minutes) % 60}m` }
function mayClose() { return !dirty.value || window.confirm('Discard your unsaved changes?') }
function closed() { form.value = {}; markClean(); actionError.value = ''; conflict.value = false }
watch(() => auth.activeCompanyId, () => { dialog.value?.close(); closed(); message.value = '' })
function open(item = null) {
  mode.value = item ? 'edit' : 'create'; target.value = item; actionError.value = ''; conflict.value = false
  const sourceTicket = data.value.ticket
  const sourceTask = data.value.tasks.find(task => task.id === Number(context.value.task_id))
  form.value = item ? Object.fromEntries(['employee_id', 'project_id', 'task_id', 'ticket_id', 'date', 'minutes', 'description'].map(key => [key, item[key] ?? '']))
    : { employee_id: context.value.employee_id || employeeOptions.value.find(employee => employee.user_id === auth.user.id)?.id || employeeOptions.value[0]?.id || '',
      project_id: sourceTicket?.project_id || sourceTask?.project_id || context.value.project_id || '', task_id: sourceTicket?.task_id || sourceTask?.id || '',
      ticket_id: sourceTicket?.id || '', date: today(), minutes: '60', description: '', request_id: crypto.randomUUID() }
  markClean(); dialog.value.showModal()
}
function projectChanged() { form.value.task_id = ''; form.value.ticket_id = '' }
function ticketChanged() {
  const ticket = data.value.tickets.find(item => item.id === Number(form.value.ticket_id))
  if (ticket?.task_id) form.value.task_id = ticket.task_id
}
async function action(item, name, reason = '') {
  auth.busy = true; actionError.value = ''; conflict.value = false
  try {
    await erp(auth.activeCompanyId, `timesheets/${item.id}/actions/`, { method: 'POST', data: { action: name, expected_version: item.version, ...(reason ? { reason } : {}) } })
    message.value = 'Time entry updated.'; return true
  } catch (err) { actionError.value = err.message; conflict.value = err.status === 409; return false }
  finally { auth.busy = false }
}
async function transition(item, name) { if (await action(item, name)) await refresh() }
function review(item, name) { mode.value = name; target.value = item; form.value = { reason: '' }; markClean(); actionError.value = ''; conflict.value = false; dialog.value.showModal() }
async function save() {
  if (['reject', 'void', 'discard'].includes(mode.value)) {
    if (await action(target.value, mode.value, form.value.reason)) { markClean(); dialog.value.close(); await refresh() }
    return
  }
  auth.busy = true; actionError.value = ''; conflict.value = false
  const values = { ...form.value, employee_id: Number(form.value.employee_id), project_id: Number(form.value.project_id),
    task_id: form.value.task_id ? Number(form.value.task_id) : null, ticket_id: form.value.ticket_id ? Number(form.value.ticket_id) : null, minutes: Number(form.value.minutes) }
  if (target.value) values.expected_version = target.value.version
  try {
    await erp(auth.activeCompanyId, `timesheets/${target.value ? `${target.value.id}/` : ''}`, { method: target.value ? 'PATCH' : 'POST', data: values })
    markClean(); dialog.value.close(); message.value = 'Draft time entry saved.'; await refresh()
  } catch (err) { actionError.value = err.message; conflict.value = err.status === 409 }
  finally { auth.busy = false }
}
async function reloadLatest() { if (!mayClose()) return; markClean(); dialog.value.close(); await refresh() }
async function exportCSV() {
  auth.busy = true; actionError.value = ''
  try { downloadText(await erp(auth.activeCompanyId, `timesheets/export/?${params()}`, { format: 'text' }), `timesheets-${auth.activeCompanyId}.csv`) }
  catch (err) { actionError.value = err.message }
  finally { auth.busy = false }
}
</script>

<template>
  <section class="business-page timesheets-page">
    
    <div class="control-panel"><div class="control-title"><h1>Timesheets</h1><span class="muted">{{ auth.canManage ? 'Team time & approvals' : 'Your project time' }}</span></div><div class="control-actions"><button v-if="data?.can_log" class="button-primary" :disabled="auth.busy || loading" @click="open()">Log time</button><button class="button-secondary" :disabled="!data || auth.busy || loading" @click="exportCSV">Export CSV</button><button class="button-secondary" :disabled="loading || auth.busy" @click="refresh">Refresh</button></div>
      <div class="catalog-filters"><label>Status<select v-model="status" name="time_status"><option value="">All statuses</option><option value="draft">Draft</option><option value="submitted">Submitted</option><option value="approved">Approved</option><option value="voided">Voided</option></select></label><label>From<input v-model="dateFrom" name="time_from" type="date" /></label><label>Through<input v-model="dateTo" name="time_to" type="date" /></label><label>Search<input v-model="search" name="time_search" type="search" maxlength="200" placeholder="Person, project or description" /></label></div>
    </div>
    <div class="workspace-content dashboard-content">
      <p v-if="error" class="notice error" role="alert">{{ error }}</p><p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p><p v-if="message" class="notice success" role="status">{{ message }}</p><p v-if="loading" class="loading-state" role="status">Loading time entries…</p>
      <template v-if="data">
        <p v-if="Object.keys(context).length" class="notice">Filtered by linked {{ Object.keys(context).map(key => key.replace('_id', '')).join(', ') }}. <RouterLink to="/timesheets" class="text-link">Clear source filters</RouterLink></p>
        <p v-if="!data.can_log" class="notice">Ask an owner or administrator to link your Team account to an active Employee record before logging time.</p>
        <div class="metrics-grid accounting-metrics time-summary"><article class="metric-card"><span>Logged · matching entries</span><strong>{{ duration(data.summary.total_minutes) }}</strong><small>Excludes voided entries</small></article><article class="metric-card orange"><span>Awaiting approval</span><strong>{{ duration(data.summary.submitted_minutes) }}</strong></article><article class="metric-card teal"><span>Approved time</span><strong>{{ duration(data.summary.approved_minutes) }}</strong><small>{{ auth.canManage ? 'Team' : 'Your' }} approved hours</small></article></div>
        <p class="muted">Record whole minutes, up to 24 hours per employee per day. Approved entries are locked; a manager can void an incorrect entry with a reason. Time is not billed automatically.</p>
        <p v-if="!data.count" class="empty-state">No time entries match these filters.</p>
        <div v-else class="table-wrap" role="region" aria-label="Timesheets records" tabindex="0"><table class="data-table timesheet-table"><thead><tr><th>Date / employee</th><th>Project / task</th><th>Description</th><th>Time</th><th>Status / review</th><th>Actions</th></tr></thead><tbody><tr v-for="item in data.results" :key="item.id"><td>{{ item.date }}<small class="record-detail">{{ item.employee_name }}</small></td><td><RouterLink :to="`/tasks?project_id=${item.project_id}`" class="text-link">{{ item.project_name }}</RouterLink><small class="record-detail">{{ item.task_title }}</small><RouterLink v-if="item.ticket_id" :to="`/helpdesk/${item.ticket_id}`" class="text-link">{{ item.ticket_number }}</RouterLink></td><td>{{ item.description }}</td><td class="numeric">{{ duration(item.minutes) }}</td><td><span class="badge" :class="item.status">{{ item.status }}</span><small v-if="item.review_note" class="record-detail">{{ item.review_note }}</small><small v-if="item.reviewed_by" class="record-detail">{{ item.reviewed_by }}</small></td><td><div class="row-actions"><template v-if="item.status === 'draft'"><button class="inline-button" :disabled="auth.busy" @click="open(item)">Edit</button><button class="inline-button" :disabled="auth.busy" @click="transition(item, 'submit')">Submit</button><button class="inline-button" :disabled="auth.busy" @click="review(item, 'discard')">Discard draft</button></template><template v-if="item.status === 'submitted'"><button class="inline-button" :disabled="auth.busy" @click="transition(item, 'withdraw')">Withdraw</button><template v-if="auth.canManage"><button class="inline-button" :disabled="auth.busy" @click="transition(item, 'approve')">Approve</button><button class="inline-button" :disabled="auth.busy" @click="review(item, 'reject')">Return for correction</button></template></template><button v-if="auth.canManage && item.status === 'approved'" class="inline-button" :disabled="auth.busy" @click="review(item, 'void')">Void</button></div></td></tr></tbody></table></div>
        <UiPagination :count="data.count" :page="page" :page-size="data.page_size" :busy="loading || auth.busy" @update:page="page = $event" />
      </template>
    </div>
    <UiDialog ref="dialog" :title="mode === 'reject' ? 'Return time for correction' : mode === 'void' ? 'Void approved time' : mode === 'discard' ? 'Discard draft time' : target ? 'Edit draft time' : 'Log project time'" :busy="auth.busy" :before-close="mayClose" @closed="closed" v-slot="{ requestClose }">
      <form @submit.prevent="save"><p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p><button v-if="conflict" type="button" class="button-secondary" :disabled="auth.busy" @click="reloadLatest">Reload latest</button>
        <fieldset class="form-grid service-fields" :disabled="auth.busy">
          <label v-if="['reject', 'void', 'discard'].includes(mode)" class="full-width">Reason<textarea v-model="form.reason" name="time_reason" maxlength="500" required rows="4"></textarea></label>
          <template v-else>
            <label>Employee<select v-model="form.employee_id" name="time_employee" required><option value="">Choose an employee</option><option v-for="item in employeeOptions" :key="item.id" :value="item.id">{{ item.name }}</option><option v-if="target && !employeeOptions.some(item => item.id === target.employee_id)" :value="target.employee_id">{{ target.employee_name }} (inactive)</option></select></label>
            <label>Work date<input v-model="form.date" name="time_date" type="date" :max="today()" required /></label>
            <label>Project<select v-model="form.project_id" name="time_project" required @change="projectChanged"><option value="">Choose a project</option><option v-for="item in data?.projects" :key="item.id" :value="item.id">{{ item.name }}</option><option v-if="target && !data?.projects.some(item => item.id === target.project_id)" :value="target.project_id">{{ target.project_name }} (inactive)</option></select></label>
            <label>Task<select v-model="form.task_id" name="time_task"><option value="">No task</option><option v-for="item in taskOptions" :key="item.id" :value="item.id">{{ item.title }}</option><option v-if="target?.task_id && !taskOptions.some(item => item.id === target.task_id)" :value="target.task_id">{{ target.task_title }} (inactive)</option></select></label>
            <label>Support ticket<select v-model="form.ticket_id" name="time_ticket" @change="ticketChanged"><option value="">No ticket</option><option v-for="item in ticketOptions" :key="item.id" :value="item.id">{{ item.number }} {{ item.title }}</option><option v-if="data?.ticket && !ticketOptions.some(item => item.id === data.ticket.id)" :value="data.ticket.id">{{ data.ticket.number }}</option><option v-if="target?.ticket_id && !ticketOptions.some(item => item.id === target.ticket_id) && target.ticket_id !== data?.ticket?.id" :value="target.ticket_id">{{ target.ticket_number }} (inactive)</option></select></label>
            <label>Minutes<input v-model="form.minutes" name="time_minutes" type="number" min="1" max="1440" step="1" required /></label><label class="full-width">Work description<textarea v-model="form.description" name="time_description" maxlength="300" rows="3" required></textarea></label>
          </template>
        </fieldset><footer class="dialog-footer"><button class="button-primary" :disabled="auth.busy">{{ auth.busy ? 'Saving…' : ['reject', 'void', 'discard'].includes(mode) ? 'Confirm' : 'Save draft' }}</button><button type="button" class="button-secondary" :disabled="auth.busy" @click="requestClose">Discard</button></footer>
      </form>
    </UiDialog>
  </section>
</template>
