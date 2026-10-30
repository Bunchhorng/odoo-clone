<script setup lang="ts">
withDefaults(defineProps<{ label?: string; activeCount?: number }>(), { label: 'Filters', activeCount: 0 })
</script>
<template>
  <details class="erp-filter-menu" open>
    <summary>{{ label }}<span v-if="activeCount"> ({{ activeCount }} active)</span></summary>
    <div class="catalog-filters"><slot /></div>
  </details>
</template>
