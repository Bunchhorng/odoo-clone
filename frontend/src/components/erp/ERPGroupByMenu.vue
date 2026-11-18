<script setup lang="ts">
import type { SelectOption } from '../../types/erp'
defineProps<{ modelValue: string; options: SelectOption[]; disabled?: boolean }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
<template>
  <div class="erp-group-control"><label>Group this page<select :value="modelValue" aria-label="Group this page by" :disabled="disabled" @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"><option value="">No grouping</option><option v-for="option in options" :key="option.value" :value="option.value">{{ option.label }}</option></select></label></div>
</template>
