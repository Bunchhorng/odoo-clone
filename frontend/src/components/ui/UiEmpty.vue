<script setup>
import AppIcon from '../AppIcon.vue'
defineProps({ title: String, description: String, icon: { type: String, default: 'box' } })
</script>
<template><div class="empty-state"><AppIcon :name="icon" /><h2>{{ title }}</h2><p>{{ description }}</p><slot /></div></template>
