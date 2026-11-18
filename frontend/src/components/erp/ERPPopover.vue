<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, useId, watch } from 'vue'
import { useRoute } from 'vue-router'

defineProps<{ label: string; panelClass?: string }>()
const emit = defineEmits<{ opened: [] }>()
const route = useRoute()
const id = useId()
const root = ref<HTMLElement>()
const trigger = ref<HTMLButtonElement>()
const panel = ref<HTMLElement>()
const opened = ref(false)
watch(opened, value => { if (value) emit('opened') })
function close(restoreFocus = false) {
  opened.value = false
  if (restoreFocus) trigger.value?.focus()
}
function controls() {
  return [...(panel.value?.querySelectorAll<HTMLElement>('a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled)') || [])]
    .filter(item => item.tabIndex >= 0 && !item.closest('[hidden]'))
}
async function openWithFocus() {
  opened.value = true
  await nextTick()
  controls()[0]?.focus()
}
function keyboard(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true); return }
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) || (event.target as HTMLElement).matches('input, select, textarea')) return
  const items = controls()
  if (!items.length) return
  const index = items.indexOf(document.activeElement as HTMLElement)
  const target = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (index + (event.key === 'ArrowUp' ? -1 : 1) + items.length) % items.length
  event.preventDefault()
  items[target]?.focus()
}
function outside(event: Event) { if (!root.value?.contains(event.target as Node)) close() }
function focusOutside(event: FocusEvent) {
  if (event.relatedTarget && !root.value?.contains(event.relatedTarget as Node)) close()
}
watch(() => route.fullPath, () => close())
onMounted(() => { document.addEventListener('pointerdown', outside); document.addEventListener('focusin', outside) })
onUnmounted(() => { document.removeEventListener('pointerdown', outside); document.removeEventListener('focusin', outside) })
defineExpose({ close })
</script>

<template>
  <div ref="root" class="erp-popover" @keydown="keyboard" @focusout="focusOutside">
    <button ref="trigger" type="button" class="shell-button" :aria-label="label" :aria-expanded="opened" :aria-controls="id" @click="opened = !opened" @keydown.down.prevent.stop="openWithFocus">
      <slot name="trigger" />
    </button>
    <div v-if="opened" :id="id" ref="panel" class="erp-popover-panel" :class="panelClass" :aria-label="label">
      <slot :close="close" />
    </div>
  </div>
</template>
