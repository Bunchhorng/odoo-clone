<script setup lang="ts">
withDefaults(defineProps<{ loading?: boolean; error?: string; empty?: boolean; hasCompany?: boolean; title?: string; emptyTitle?: string }>(), { error: '', hasCompany: true, title: 'Records', emptyTitle: 'No matching records' })
defineEmits<{ retry: [] }>()
</script>
<template>
  <div class="workspace-content erp-list-view" :aria-busy="loading">
    <slot name="feedback" />
    <div v-if="!hasCompany" class="empty-state"><h2>Choose a company</h2><p>Choose or create a company to start.</p><RouterLink to="/companies" class="text-link">Manage companies</RouterLink></div>
    <div v-else-if="error" class="notice error" role="alert">{{ error }} <button type="button" class="inline-button" @click="$emit('retry')">Retry</button></div>
    <p v-else-if="loading" class="loading-state" role="status">Loading {{ title.toLowerCase() }}…</p>
    <div v-else-if="empty" class="empty-state"><h2>{{ emptyTitle }}</h2><slot name="empty" /></div>
    <slot v-else />
  </div>
</template>
