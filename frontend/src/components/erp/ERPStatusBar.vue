<script setup lang="ts">
import type { SelectOption } from '../../types/erp'
withDefaults(defineProps<{ value: string; steps: SelectOption[]; label?: string }>(), { label: 'Document status' })
</script>
<template><ol class="erp-status-bar" :aria-label="label"><li v-for="step in steps" :key="step.value" :data-value="step.value" :aria-current="value === step.value ? 'step' : undefined">{{ step.label }}</li></ol></template>
