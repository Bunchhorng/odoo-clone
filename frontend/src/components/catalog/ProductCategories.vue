<script setup>
import { ref, watch } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { allRecords, erp } from '../../composables/erp'
import { useDirtyForm } from '../../composables/forms'
import UiDialog from '../ui/UiDialog.vue'
import UiButton from '../ui/UiButton.vue'
import UiNotice from '../ui/UiNotice.vue'
import UiField from '../ui/UiField.vue'
import UiBadge from '../ui/UiBadge.vue'
const emit = defineEmits(['changed'])
const auth = useAuthStore()
const dialog = ref(null)
const records = ref([])
const editing = ref(null)
const form = ref({ name: '' })
const { dirty, markClean } = useDirtyForm(form)
const busy = ref(false)
const loading = ref(false)
const error = ref('')
let generation = 0
watch(() => auth.activeCompanyId, () => { generation++; dialog.value?.close(); reset() })
function reset() { form.value = { name: '' }; markClean(); editing.value = null; error.value = '' }
function mayClose() { return !dirty.value || window.confirm('Discard your unsaved category?') }
async function load() {
  const current = ++generation
  loading.value = true; error.value = ''
  try {
    const result = await allRecords(auth.activeCompanyId, 'product-categories', { active: 'all', ordering: 'name' })
    if (current === generation) records.value = result
  } catch (err) { if (current === generation) error.value = err.message }
  finally { if (current === generation) loading.value = false }
}
async function showModal() { reset(); records.value = []; dialog.value.showModal(); await load() }
function edit(item) { if (dirty.value && !window.confirm('Discard your unsaved category?')) return; editing.value = item; form.value = { name: item.name }; markClean() }
async function save(item = null) {
  if (busy.value || auth.busy) return
  busy.value = true; auth.busy = true; error.value = ''
  try {
    const target = item || editing.value
    await erp(auth.activeCompanyId, `product-categories/${target ? `${target.id}/` : ''}`, { method: target ? 'PATCH' : 'POST', data: item ? { is_active: !item.is_active } : { name: form.value.name } })
    if (!item) reset()
    await load(); emit('changed')
  } catch (err) { error.value = err.message }
  finally { busy.value = false; auth.busy = false }
}
defineExpose({ showModal })
</script>
<template>
  <UiDialog ref="dialog" title="Product categories" :busy="busy" :before-close="mayClose" @closed="reset" v-slot="{ requestClose }">
    <p class="muted">Categories belong to this company. Archived categories stay on existing products and cannot be newly selected.</p>
    <UiNotice v-if="error" tone="error">{{ error }} <UiButton variant="text" @click="load">Retry</UiButton></UiNotice>
    <p v-if="loading" class="loading-state" role="status">Loading categories…</p>
    <ul v-else class="category-list"><li v-for="item in records" :key="item.id"><strong>{{ item.name }}</strong><UiBadge v-if="!item.is_active" tone="cancelled">Archived</UiBadge><UiButton v-if="auth.canManage" variant="text" :disabled="busy" @click="edit(item)">Edit</UiButton><UiButton v-if="auth.canManage" variant="text" :disabled="busy" @click="save(item)">{{ item.is_active ? 'Archive' : 'Restore' }}</UiButton></li><li v-if="!records.length" class="muted">No categories yet.</li></ul>
    <form v-if="auth.canManage" @submit.prevent="save()"><fieldset :disabled="busy" class="category-form"><UiField v-model="form.name" :field="{ key: 'category_name', label: editing ? 'Rename category' : 'New category', required: true, maxlength: 100 }" /><UiButton type="submit" variant="primary" :busy="busy">{{ editing ? 'Save category' : 'Add category' }}</UiButton><UiButton v-if="editing" :disabled="busy" @click="reset">Cancel edit</UiButton></fieldset></form>
    <footer class="dialog-footer"><UiButton :disabled="busy" @click="requestClose">Close</UiButton></footer>
  </UiDialog>
</template>
