<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { erp } from '../composables/erp'
import { useDirtyForm } from '../composables/forms'
import UiDialog from './ui/UiDialog.vue'

const props = defineProps({ order: { type: Object, required: true } })
const emit = defineEmits(['received'])
const auth = useAuthStore()
const dialog = ref(null)
const form = ref({ quantities: {}, notes: '' })
const { dirty, markClean } = useDirtyForm(form)
const error = ref('')
const conflict = ref(false)
const pending = computed(() => props.order.lines.filter(line => line.product_kind === 'goods' && Number(line.remaining_quantity) > 0))
let requestId
function reset() { form.value = { quantities: {}, notes: '' }; markClean(); error.value = ''; conflict.value = false }
function showModal() {
  form.value = { quantities: Object.fromEntries(pending.value.map(line => [line.id, line.remaining_quantity])), notes: '' }
  markClean(); error.value = ''; conflict.value = false; requestId = crypto.randomUUID(); dialog.value.showModal()
}
function mayClose() { return !dirty.value || window.confirm('Discard these receipt quantities and notes?') }
async function reload() {
  if (!mayClose()) return
  markClean(); dialog.value.close(); emit('received')
}
async function save() {
  if (auth.busy) return
  auth.busy = true; error.value = ''; conflict.value = false
  try {
    const lines = pending.value.filter(line => Number(form.value.quantities[line.id]) > 0)
      .map(line => ({ line_id: line.id, quantity: form.value.quantities[line.id] }))
    await erp(auth.activeCompanyId, `orders/${props.order.id}/receipts/`, { method: 'POST', data: {
      lines, notes: form.value.notes, request_id: requestId, expected_version: props.order.version,
    } })
    markClean(); dialog.value.close(); emit('received')
  } catch (err) { error.value = err.message; conflict.value = err.status === 409 }
  finally { auth.busy = false }
}
defineExpose({ showModal })
</script>
<template>
  <UiDialog ref="dialog" title="Receive products" :busy="auth.busy" :before-close="mayClose" @closed="reset" v-slot="{ requestClose }">
    <p class="muted">Record the quantities received now. Set a line to zero to leave it for a later receipt. Services do not change stock.</p>
    <p v-if="error" class="notice error" role="alert">{{ error }} <button v-if="conflict" type="button" class="inline-button" @click="reload">Reload purchase</button></p>
    <form @submit.prevent="save">
      <fieldset :disabled="auth.busy" class="receipt-fields">
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Product</th><th>Ordered</th><th>Received</th><th>Remaining</th><th>Receive now</th></tr></thead><tbody>
          <tr v-for="line in pending" :key="line.id"><td>{{ line.description }}</td><td>{{ line.quantity }}</td><td>{{ line.received_quantity }}</td><td>{{ line.remaining_quantity }}</td><td><input v-model="form.quantities[line.id]" :name="`receive_${line.id}`" :aria-label="`Receive ${line.description}`" type="number" min="0" :max="line.remaining_quantity" step=".001" required /></td></tr>
        </tbody></table></div>
        <label>Receipt notes<input v-model="form.notes" name="receipt_notes" maxlength="300" placeholder="Supplier delivery reference or notes" /></label>
      </fieldset>
      <footer class="dialog-footer"><button class="button-primary" :disabled="auth.busy || !pending.some(line => Number(form.quantities[line.id]) > 0)">Record receipt</button><button type="button" class="button-secondary" :disabled="auth.busy" @click="requestClose">Discard</button></footer>
    </form>
  </UiDialog>
</template>
