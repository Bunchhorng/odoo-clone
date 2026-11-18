<script setup lang="ts">
withDefaults(defineProps<{ busy?: boolean; error?: string; readonly?: boolean }>(), { error: '' })
defineEmits<{ submit: [] }>()
</script>
<template>
  <form class="erp-form-view" :aria-busy="busy" @submit.prevent="$emit('submit')">
    <div v-if="error" class="notice error" role="alert">{{ error }}</div>
    <slot name="context" />
    <p v-if="readonly" class="muted">You have read-only access to this record.</p>
    <fieldset :disabled="busy || readonly" class="form-grid"><slot /></fieldset>
    <footer v-if="$slots.actions" class="dialog-footer"><slot name="actions" /></footer>
  </form>
</template>
