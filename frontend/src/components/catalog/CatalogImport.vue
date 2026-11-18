<script setup>
import { computed, ref, watch } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { erp } from '../../composables/erp'
import { useDirtyForm } from '../../composables/forms'
import { downloadText } from '../../composables/download'
import UiDialog from '../ui/UiDialog.vue'
import UiButton from '../ui/UiButton.vue'
import UiNotice from '../ui/UiNotice.vue'
const props = defineProps({ resource: String, title: String })
const emit = defineEmits(['imported'])
const auth = useAuthStore()
const dialog = ref(null)
const form = ref({ csv: '' })
const { dirty, markClean } = useDirtyForm(form)
const preview = ref(null)
const error = ref('')
const busy = ref(false)
const fileInput = ref(null)
const canImport = computed(() => preview.value?.can_import && !busy.value)
let generation = 0
watch(() => form.value.csv, () => { preview.value = null; error.value = '' }, { flush: 'sync' })
watch([() => auth.activeCompanyId, () => props.resource], () => { generation++; dialog.value?.close(); reset() })
function reset() { generation++; form.value = { csv: '' }; markClean(); preview.value = null; error.value = ''; if (fileInput.value) fileInput.value.value = '' }
function showModal() { reset(); dialog.value.showModal() }
function mayClose() { return !dirty.value || window.confirm('Discard this import file and preview?') }
async function readFile(event) {
  const file = event.target.files[0]
  if (!file) return
  const current = ++generation
  form.value.csv = ''; preview.value = null; error.value = ''
  if (file.size > 512 * 1024) { error.value = 'Choose a CSV file of at most 512 KiB.'; return }
  try {
    const text = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer())
    if (current === generation) form.value.csv = text
  } catch { if (current === generation) error.value = 'Cannot read this file. Choose a UTF-8 CSV file.' }
}
async function run(action) {
  if (busy.value || auth.busy) return
  busy.value = true; auth.busy = true; error.value = ''
  try {
    if (action === 'template') {
      const text = await erp(auth.activeCompanyId, `${props.resource}/export/?template=true`, { format: 'text' })
      downloadText(text, `${props.resource}-template.csv`)
    } else if (action === 'preview') {
      preview.value = await erp(auth.activeCompanyId, `${props.resource}/import/preview/`, { method: 'POST', data: { csv: form.value.csv } })
    } else {
      const result = await erp(auth.activeCompanyId, `${props.resource}/import/`, { method: 'POST', data: { csv: form.value.csv, token: preview.value.token } })
      markClean(); dialog.value.close(); emit('imported', result.created)
    }
  } catch (err) { error.value = err.message; if (action === 'commit' && err.status === 409) preview.value = null }
  finally { busy.value = false; auth.busy = false }
}
defineExpose({ showModal })
</script>
<template>
  <UiDialog ref="dialog" class="import-dialog" :title="`Import ${title.toLowerCase()}`" :busy="busy" :before-close="mayClose" @closed="reset" v-slot="{ requestClose }">
    <p class="muted">Create up to 200 new records from a UTF-8, comma-separated CSV file. Download the template, fill it in, then preview every row before importing. Existing records are never overwritten.</p>
    <UiButton :busy="busy" @click="run('template')">Download CSV template</UiButton>
    <form @submit.prevent="run('preview')">
      <fieldset :disabled="busy" class="import-fields"><label>CSV file<input ref="fileInput" type="file" accept=".csv,text/csv" name="csv_file" @change="readFile" /></label><label>CSV contents<textarea v-model="form.csv" name="csv_contents" rows="6" spellcheck="false" required maxlength="524288"></textarea></label></fieldset>
      <UiNotice v-if="error" tone="error">{{ error }}</UiNotice>
      <section v-if="preview" class="import-preview" aria-label="Import preview">
        <UiNotice :tone="preview.can_import ? 'success' : 'error'">{{ preview.can_import ? `${preview.count} records are ready to import. Preview expires after 10 minutes.` : 'Fix the rows below, then preview again. No records have been imported.' }}</UiNotice>
        <div class="table-wrap"><table class="data-table"><caption class="sr-only">CSV validation results</caption><thead><tr><th>Row</th><th v-for="header in preview.headers" :key="header">{{ header }}</th><th>Validation</th></tr></thead><tbody><tr v-for="row in preview.rows" :key="row.row"><td>{{ row.row }}</td><td v-for="header in preview.headers" :key="header"><div class="csv-value">{{ row.values[header] || '—' }}</div></td><td><span v-if="!row.errors.length && !row.warnings.length" class="positive">Ready</span><p v-for="message in row.errors" :key="message" class="negative">{{ message }}</p><p v-for="warning in row.warnings" :key="warning" class="warning-label">{{ warning }}</p></td></tr></tbody></table></div>
      </section>
      <footer class="dialog-footer"><UiButton type="submit" variant="primary" :busy="busy" :disabled="!form.csv.trim()">{{ busy ? 'Working…' : 'Preview CSV' }}</UiButton><UiButton :disabled="!canImport" :busy="busy" @click="run('commit')">Import records</UiButton><UiButton :disabled="busy" @click="requestClose">Discard</UiButton></footer>
    </form>
  </UiDialog>
</template>
