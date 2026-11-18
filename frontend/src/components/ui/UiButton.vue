<script setup>
defineProps({ variant: { type: String, default: 'secondary' }, busy: Boolean, disabled: Boolean, type: { type: String, default: 'button' } })
</script>
<template><button :type="type" :class="variant === 'text' ? 'inline-button' : `button-${variant}`" :disabled="disabled || busy" :aria-busy="busy || undefined"><slot /></button></template>
