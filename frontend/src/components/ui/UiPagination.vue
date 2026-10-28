<script setup>
defineProps({ count: { type: Number, default: 0 }, page: { type: Number, default: 1 }, pageSize: { type: Number, default: 24 }, busy: Boolean })
defineEmits(['update:page'])
</script>
<template>
  <nav v-if="count > pageSize" class="pagination" aria-label="Record pages">
    <span role="status">{{ (page - 1) * pageSize + 1 }}–{{ Math.min(page * pageSize, count) }} of {{ count }}</span>
    <button type="button" :disabled="page === 1 || busy" @click="$emit('update:page', page - 1)">Previous</button>
    <button type="button" :disabled="page * pageSize >= count || busy" @click="$emit('update:page', page + 1)">Next</button>
  </nav>
</template>
