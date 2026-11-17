<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { api } from '../services/api'
import { allRecords, dateLabel, erp, useWorkspace } from '../composables/erp'
import { syncPage, useDirtyForm, usePage } from '../composables/forms'
import UiDialog from '../components/ui/UiDialog.vue'
import UiPagination from '../components/ui/UiPagination.vue'

const auth = useAuthStore(), route = useRoute(), router = useRouter()
const recordId = computed(() => route.params.recordId), projectId = computed(() => String(route.query.project_id || ''))
const status = ref(''), search = ref(''), active = ref('true'), mine = ref(false), overdue = ref(false)
const page = usePage([recordId, projectId, status, search, active, mine, overdue])
const dialog = ref(null), mode = ref(''), form = ref({}), editVersion = ref(null), actionError = ref(''), conflict = ref(false)
const { dirty, markClean } = useDirtyForm(form)
const { data, error, loading, refresh } = useWorkspace(async id => {
  const [record, contacts, projects, members, messages] = await Promise.all([
    erp(id, recordId.value ? `helpdesk/${recordId.value}/` : `helpdesk/?${new URLSearchParams({ q: search.value, status: status.value, active: active.value,
      mine: String(mine.value), overdue: String(overdue.value), project_id: projectId.value, page: String(page.value) })}`),
    allRecords(id, 'contacts'), allRecords(id, 'projects'), auth.canManage ? api(`companies/${id}/members/`) : Promise.resolve({ members: [] }),
    recordId.value ? erp(id, `helpdesk/${recordId.value}/messages/?page=${page.value}`) : Promise.resolve(null),
  ])
  return recordId.value ? { ticket: record, contacts, projects, members: members.members, messages, page: messages.page }
    : { ...record, contacts, projects, members: members.members }
}, [recordId, projectId, status, search, active, mine, overdue, page])
syncPage(page, data)
const editable = computed(() => auth.canManage || (data.value?.ticket?.created_by_id === auth.user?.id && data.value?.ticket?.status === 'new' && data.value?.ticket?.is_active))
const memberOptions = computed(() => data.value?.members.filter(item => item.is_active && item.user_is_active) || [])
function mayClose() { return !dirty.value || window.confirm('Discard your unsaved changes?') }
function closed() { form.value = {}; markClean(); actionError.value = ''; conflict.value = false }
watch([() => auth.activeCompanyId, recordId], () => { dialog.value?.close(); closed() })
function open(name) {
  mode.value = name; actionError.value = ''; conflict.value = false; editVersion.value = data.value?.ticket?.version
  const item = name === 'edit' ? data.value.ticket : null
  form.value = name === 'note' ? { body: '', request_id: crypto.randomUUID() } : name === 'resolve' ? { resolution: '' }
    : item ? Object.fromEntries(['title', 'description', 'contact_id', 'project_id', 'assignee_id', 'priority', 'due_date'].map(key => [key, item[key] ?? '']))
      : { title: '', description: '', contact_id: '', project_id: projectId.value, assignee_id: '', priority: 'normal', due_date: '', request_id: crypto.randomUUID() }
  markClean(); dialog.value.showModal()
}
async function transition(name) {
  auth.busy = true; actionError.value = ''; conflict.value = false
  try {
    await erp(auth.activeCompanyId, `helpdesk/${recordId.value}/actions/`, { method: 'POST', data: { action: name, expected_version: data.value.ticket.version } })
    await refresh()
  } catch (err) { actionError.value = err.message; conflict.value = err.status === 409 }
  finally { auth.busy = false }
}
async function save() {
  auth.busy = true; actionError.value = ''; conflict.value = false
  try {
    if (mode.value === 'note') await erp(auth.activeCompanyId, `helpdesk/${recordId.value}/messages/`, { method: 'POST', data: form.value })
    else if (mode.value === 'resolve') await erp(auth.activeCompanyId, `helpdesk/${recordId.value}/actions/`, { method: 'POST', data: { action: 'resolve', expected_version: editVersion.value, resolution: form.value.resolution } })
    else {
      const values = { ...form.value, contact_id: form.value.contact_id ? Number(form.value.contact_id) : null,
        project_id: form.value.project_id ? Number(form.value.project_id) : null, assignee_id: form.value.assignee_id ? Number(form.value.assignee_id) : null,
        due_date: form.value.due_date || null }
      if (mode.value === 'edit') values.expected_version = editVersion.value
      const result = await erp(auth.activeCompanyId, `helpdesk/${mode.value === 'edit' ? `${recordId.value}/` : ''}`, { method: mode.value === 'edit' ? 'PATCH' : 'POST', data: values })
      if (mode.value === 'create') { markClean(); dialog.value.close(); await router.push(`/helpdesk/${result.id}`); return }
    }
    markClean(); dialog.value.close(); await refresh()
  } catch (err) { actionError.value = err.message; conflict.value = err.status === 409 }
  finally { auth.busy = false }
}
async function reloadLatest() { if (!mayClose()) return; markClean(); dialog.value.close(); await refresh() }
</script>

<template>
  <section class="business-page helpdesk-page">
    <div class="control-panel"><div class="control-title"><h1>{{ data?.ticket?.number || 'Helpdesk' }}</h1><RouterLink v-if="recordId" to="/helpdesk" class="text-link">All tickets</RouterLink><span v-else class="muted">{{ data?.count || 0 }} support tickets</span></div><div class="control-actions"><button v-if="auth.activeCompanyId && !recordId" class="button-primary" :disabled="loading || auth.busy" @click="open('create')">New ticket</button><button v-if="recordId && editable && data?.ticket" class="button-secondary" :disabled="auth.busy" @click="open('edit')">Edit ticket</button><button class="button-secondary" :disabled="loading || auth.busy" @click="refresh">Refresh</button></div>
      <div v-if="!recordId" class="catalog-filters"><label>Search<input v-model="search" name="ticket_search" type="search" maxlength="200" placeholder="Reference, title or customer" /></label><label>Status<select v-model="status" name="ticket_status"><option value="">All statuses</option><option value="new">New</option><option value="in_progress">In progress</option><option value="waiting">Waiting</option><option value="resolved">Resolved</option><option value="cancelled">Cancelled</option></select></label><label>Records<select v-model="active" name="ticket_active"><option value="true">Active</option><option value="false">Archived</option><option value="all">All records</option></select></label><label class="checkbox-label"><input v-model="mine" type="checkbox" name="ticket_mine" /> Created by or assigned to me</label><label class="checkbox-label"><input v-model="overdue" type="checkbox" name="ticket_overdue" /> Overdue</label></div>
    </div>
    <div class="workspace-content dashboard-content">
      <p v-if="error" class="notice error" role="alert">{{ error }}</p><p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p><p v-if="loading" class="loading-state" role="status">Loading helpdesk…</p>
      <template v-if="data">
        <template v-if="!recordId"><p v-if="projectId" class="notice">Filtered by project. <RouterLink to="/helpdesk" class="text-link">Clear filter</RouterLink></p><p v-if="!data.count" class="empty-state">No tickets match these filters.</p><div v-else class="table-wrap" role="region" aria-label="Helpdesk records" tabindex="0"><table class="data-table"><thead><tr><th>Ticket</th><th>Customer / project</th><th>Assigned to</th><th>Priority</th><th>Status</th><th>Due</th></tr></thead><tbody><tr v-for="item in data.results" :key="item.id"><td><RouterLink :to="`/helpdesk/${item.id}`" class="text-link">{{ item.number }} · {{ item.title }}</RouterLink></td><td>{{ item.contact_name || 'Internal request' }}<small class="record-detail">{{ item.project_name }}</small></td><td>{{ item.assignee_name }}</td><td><span class="badge" :class="item.priority">{{ item.priority }}</span></td><td><span class="badge" :class="item.status">{{ item.status.replace('_', ' ') }}</span></td><td :class="{ 'warning-label': item.overdue }">{{ item.due_date || '—' }}</td></tr></tbody></table></div><UiPagination :count="data.count" :page="page" :page-size="data.page_size" :busy="loading || auth.busy" @update:page="page = $event" /></template>
        <template v-else-if="data.ticket">
          <div class="document-actions ticket-actions"><template v-if="auth.canManage"><template v-if="data.ticket.is_active && !['resolved', 'cancelled'].includes(data.ticket.status)"><button class="button-primary" :disabled="auth.busy" @click="transition('start')">Start work</button><button class="button-secondary" :disabled="auth.busy" @click="transition('wait')">Waiting</button><button class="button-primary" :disabled="auth.busy" @click="open('resolve')">Resolve</button><button class="inline-button" :disabled="auth.busy" @click="transition('cancel')">Cancel ticket</button><button v-if="!data.ticket.task_id && data.ticket.project_id" class="button-secondary" :disabled="auth.busy" @click="transition('create_task')">Create project task</button></template><button v-if="data.ticket.is_active && ['resolved', 'cancelled'].includes(data.ticket.status)" class="button-primary" :disabled="auth.busy" @click="transition('reopen')">Reopen</button><button class="inline-button" :disabled="auth.busy" @click="transition(data.ticket.is_active ? 'archive' : 'restore')">{{ data.ticket.is_active ? 'Archive' : 'Restore' }}</button></template><span class="badge ticket-state" :class="data.ticket.status">{{ data.ticket.status.replace('_', ' ') }}</span><span v-if="!data.ticket.is_active" class="badge cancelled">Archived</span></div>
          <article class="panel ticket-details"><div class="sheet-heading"><div><p class="eyebrow">{{ data.ticket.number }} · {{ data.ticket.priority }} priority</p><h2>{{ data.ticket.title }}</h2></div></div><p class="ticket-description">{{ data.ticket.description || 'No description provided.' }}</p><dl class="ticket-facts"><div><dt>Customer</dt><dd>{{ data.ticket.contact_name || 'Internal request' }}</dd></div><div><dt>Assigned to</dt><dd>{{ data.ticket.assignee_name }}</dd></div><div><dt>Created by</dt><dd>{{ data.ticket.created_by_name }}</dd></div><div><dt>Due date</dt><dd :class="{ 'warning-label': data.ticket.overdue }">{{ data.ticket.due_date || 'No due date' }}</dd></div></dl>
            <div class="crm-links"><RouterLink v-if="data.ticket.project_id" :to="`/tasks?project_id=${data.ticket.project_id}`" class="text-link">{{ data.ticket.project_name }}</RouterLink><RouterLink v-if="data.ticket.task_id" :to="`/tasks?project_id=${data.ticket.project_id}`" class="text-link">Task: {{ data.ticket.task_title }}</RouterLink><RouterLink v-if="data.ticket.project_id" :to="`/timesheets?ticket_id=${data.ticket.id}`" class="text-link">Support time · {{ data.ticket.approved_minutes }} approved minutes</RouterLink></div><p v-if="data.ticket.resolution" class="notice resolution-text"><strong>Latest resolution</strong><br />{{ data.ticket.resolution }}</p>
          </article>
          <div class="dashboard-columns service-history"><section class="panel"><div class="section-heading"><h2>Internal notes &amp; resolutions</h2><button v-if="data.ticket.is_active" class="button-secondary" :disabled="auth.busy" @click="open('note')">Add note</button></div><p class="muted">Visible to this company's members. Notes stay in the ticket; no email is sent.</p><p v-if="!data.messages.count" class="muted">No notes yet.</p><article v-for="item in data.messages.results" :key="item.id" class="ticket-note"><strong>{{ item.kind === 'resolution' ? 'Resolution · ' : '' }}{{ item.actor_email }}</strong><small>{{ dateLabel(item.created_at) }}</small><p>{{ item.body }}</p></article><UiPagination :count="data.messages.count" :page="page" :page-size="data.messages.page_size" :busy="loading || auth.busy" @update:page="page = $event" /></section><section class="panel activity-panel"><h2>Recent activity</h2><div v-for="item in data.ticket.activities" :key="item.id" class="activity-item"><span class="activity-dot"></span><div><span>{{ item.summary }}</span><small>{{ item.actor_email }} · {{ dateLabel(item.created_at) }}</small></div></div><p class="muted">Latest 20 activity events. Notes and full resolution text remain in the paginated history.</p></section></div>
        </template>
      </template>
    </div>
    <UiDialog ref="dialog" :title="mode === 'note' ? 'Add internal note' : mode === 'resolve' ? 'Resolve ticket' : mode === 'edit' ? 'Edit ticket' : 'New support ticket'" :busy="auth.busy" :before-close="mayClose" @closed="closed" v-slot="{ requestClose }">
      <form @submit.prevent="save"><p v-if="actionError" class="notice error" role="alert">{{ actionError }}</p><button v-if="conflict" type="button" class="button-secondary" :disabled="auth.busy" @click="reloadLatest">Reload latest</button><fieldset class="form-grid service-fields" :disabled="auth.busy">
        <label v-if="mode === 'note'" class="full-width">Internal note<textarea v-model="form.body" name="ticket_note" maxlength="2000" rows="5" required></textarea></label><label v-else-if="mode === 'resolve'" class="full-width">Resolution<textarea v-model="form.resolution" name="ticket_resolution" maxlength="2000" rows="5" required></textarea></label>
        <template v-else><label class="full-width">Title<input v-model="form.title" name="ticket_title" maxlength="200" required /></label><label>Customer<select v-model="form.contact_id" name="ticket_contact"><option value="">Internal request</option><option v-for="item in data?.contacts" :key="item.id" :value="item.id">{{ item.name }}</option><option v-if="mode === 'edit' && data?.ticket.contact_id && !data.contacts.some(item => item.id === data.ticket.contact_id)" :value="data.ticket.contact_id">{{ data.ticket.contact_name }} (inactive)</option></select></label><label>Project<select v-model="form.project_id" name="ticket_project"><option value="">No project</option><option v-for="item in data?.projects" :key="item.id" :value="item.id">{{ item.name }}</option><option v-if="mode === 'edit' && data?.ticket.project_id && !data.projects.some(item => item.id === data.ticket.project_id)" :value="data.ticket.project_id">{{ data.ticket.project_name }} (inactive)</option></select></label><label>Assigned to<select v-model="form.assignee_id" name="ticket_assignee" :disabled="!auth.canManage"><option value="">Unassigned</option><option v-for="item in memberOptions" :key="item.user_id" :value="item.user_id">{{ item.name }}</option><option v-if="mode === 'edit' && data?.ticket.assignee_id && !memberOptions.some(item => item.user_id === data.ticket.assignee_id)" :value="data.ticket.assignee_id">{{ data.ticket.assignee_name }} (inactive)</option></select></label><label>Priority<select v-model="form.priority" name="ticket_priority"><option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option></select></label><label>Due date<input v-model="form.due_date" name="ticket_due" type="date" /></label><label class="full-width">Description<textarea v-model="form.description" name="ticket_description" maxlength="10000" rows="5"></textarea></label></template>
      </fieldset><footer class="dialog-footer"><button class="button-primary" :disabled="auth.busy">{{ auth.busy ? 'Saving…' : mode === 'note' ? 'Save note' : mode === 'resolve' ? 'Resolve ticket' : 'Save ticket' }}</button><button type="button" class="button-secondary" :disabled="auth.busy" @click="requestClose">Discard</button></footer></form>
    </UiDialog>
  </section>
</template>
