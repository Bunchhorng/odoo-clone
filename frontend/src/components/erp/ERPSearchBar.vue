<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '../AppIcon.vue'
withDefaults(defineProps<{ modelValue: string; label: string; placeholder?: string; disabled?: boolean }>(), { placeholder: 'Search…' })
const emit = defineEmits<{ 'update:modelValue': [value: string]; search: [] }>()
const input = ref<HTMLInputElement>()
function clear() { emit('update:modelValue', ''); emit('search'); input.value?.focus() }
defineExpose({ focus: () => input.value?.focus() })
</script>
<template>
  <form class="search-field erp-search" role="search" :aria-label="label" @submit.prevent="emit('search')">
    <AppIcon name="search" />
    <input ref="input" :value="modelValue" type="search" :aria-label="label" :placeholder="placeholder" :disabled="disabled" autocomplete="off" @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)" @keydown.esc="clear" />
    <button v-if="modelValue" type="button" aria-label="Clear search" :disabled="disabled" @click="clear"><AppIcon name="close" /></button>
  </form>
</template>
