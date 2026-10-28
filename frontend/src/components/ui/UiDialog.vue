<script setup>
import { ref, useId } from 'vue'
const props = defineProps({ title: String, busy: Boolean, beforeClose: Function })
const emit = defineEmits(['closed'])
const element = ref(null)
const titleId = useId()
function showModal() { if (!element.value.open) element.value.showModal() }
function close() { element.value?.close() }
function requestClose() { if (!props.busy && (!props.beforeClose || props.beforeClose())) close() }
function trapFocus(event) {
  const controls = [...element.value.querySelectorAll('button, [href], input, select, textarea, [tabindex]')]
    .filter(control => control.tabIndex >= 0 && !control.matches(':disabled') && control.getClientRects().length)
  const first = controls[0], last = controls.at(-1)
  if (!first) { event.preventDefault(); element.value.focus(); return }
  if (event.shiftKey && (document.activeElement === first || !element.value.contains(document.activeElement))) {
    event.preventDefault(); last.focus()
  } else if (!event.shiftKey && (document.activeElement === last || !element.value.contains(document.activeElement))) {
    event.preventDefault(); first.focus()
  }
}
defineExpose({ showModal, close })
</script>
<template>
  <dialog ref="element" class="record-dialog" :aria-labelledby="titleId" @keydown.tab="trapFocus" @keydown.esc.prevent.stop="requestClose" @cancel.prevent="requestClose" @close="emit('closed')">
    <header class="dialog-header"><h2 :id="titleId">{{ title }}</h2><button type="button" aria-label="Close" :disabled="busy" @click="requestClose">×</button></header>
    <slot :request-close="requestClose" />
  </dialog>
</template>
