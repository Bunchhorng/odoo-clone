<script setup>
defineProps({ tone: { type: String, default: 'success' } })
</script>
<template><div class="notice" :class="tone" :role="tone === 'error' ? 'alert' : 'status'"><slot /></div></template>
