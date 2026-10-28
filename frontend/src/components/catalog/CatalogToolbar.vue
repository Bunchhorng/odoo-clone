<script setup>
import AppIcon from '../AppIcon.vue'
import UiButton from '../ui/UiButton.vue'
defineProps({ title: String, count: Number, search: String, active: String, view: String, defaultView: String, canCreate: Boolean, busy: Boolean, disabled: Boolean })
defineEmits(['update:search', 'update:active', 'update:view', 'search', 'create'])
</script>
<template>
  <div class="control-panel">
    <div class="control-title"><h1>{{ title }}</h1><span class="muted">{{ count ?? 0 }} records<slot name="subtitle" /></span></div>
    <form class="search-field" role="search" @submit.prevent="$emit('search')"><AppIcon name="search" /><input :value="search" type="search" :aria-label="`Search ${title}`" placeholder="Search…" @input="$emit('update:search', $event.target.value)" /></form>
    <div class="control-actions">
      <UiButton v-if="canCreate" variant="primary" :disabled="busy || disabled" @click="$emit('create')">New</UiButton>
      <slot name="actions" />
      <select :value="active" aria-label="Active records" @change="$emit('update:active', $event.target.value)"><option value="true">Active</option><option value="false">Archived</option><option value="all">All records</option></select>
      <div class="view-switch" role="group" aria-label="View">
        <button type="button" :class="{ active: view !== 'list' }" :aria-pressed="view !== 'list'" :aria-label="defaultView === 'kanban' ? 'Kanban view' : 'Card view'" @click="$emit('update:view', defaultView)"><AppIcon name="grid" /></button>
        <button type="button" :class="{ active: view === 'list' }" :aria-pressed="view === 'list'" aria-label="List view" @click="$emit('update:view', 'list')"><AppIcon name="list" /></button>
      </div>
    </div>
    <div v-if="$slots.filters" class="catalog-filters"><slot name="filters" /></div>
  </div>
</template>
