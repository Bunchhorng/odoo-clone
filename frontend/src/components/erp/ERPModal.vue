<script setup lang="ts">
import { ref, useId } from 'vue'
const props = defineProps<{ title: string; busy?: boolean; beforeClose?: () => boolean }>()
const emit = defineEmits<{ closed: [] }>()
const element = ref<HTMLDialogElement>()
const titleId = useId()
let opener: HTMLElement | null = null
function showModal() {
  if (!element.value?.open) {
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    element.value?.showModal()
  }
}
function close() { element.value?.close() }
function requestClose() { if (!props.busy && (!props.beforeClose || props.beforeClose())) close() }
function closed() {
  emit('closed')
  if (opener?.isConnected && !opener.matches(':disabled')) opener.focus({ preventScroll: true })
  else document.getElementById('main-content')?.focus({ preventScroll: true })
}
function trapFocus(event: KeyboardEvent) {
  const controls = [...(element.value?.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]') || [])]
    .filter(control => control.tabIndex >= 0 && !control.matches(':disabled') && control.getClientRects().length)
  const first = controls[0], last = controls.at(-1)
  if (!first) { event.preventDefault(); element.value?.focus(); return }
  if (event.shiftKey && (document.activeElement === first || !element.value?.contains(document.activeElement))) {
    event.preventDefault(); last?.focus()
  } else if (!event.shiftKey && (document.activeElement === last || !element.value?.contains(document.activeElement))) {
    event.preventDefault(); first.focus()
  }
}
defineExpose({ showModal, close })
</script>
<template>
  <dialog ref="element" class="record-dialog" :aria-labelledby="titleId" tabindex="-1" @keydown.tab="trapFocus" @keydown.esc.prevent.stop="requestClose" @cancel.prevent="requestClose" @close="closed">
    <header class="dialog-header"><h2 :id="titleId">{{ title }}</h2><button type="button" aria-label="Close" :disabled="busy" @click="requestClose">×</button></header>
    <slot :request-close="requestClose" />
  </dialog>
</template>
