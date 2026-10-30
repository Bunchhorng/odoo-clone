<script setup>
import { ref } from 'vue'
import ERPModal from '../erp/ERPModal.vue'
defineProps({ title: String, busy: Boolean, beforeClose: Function })
const emit = defineEmits(['closed'])
const modal = ref(null)
defineExpose({ showModal: () => modal.value?.showModal(), close: () => modal.value?.close() })
</script>
<template><ERPModal ref="modal" :title="title" :busy="busy" :before-close="beforeClose" @closed="emit('closed')" v-slot="slotProps"><slot v-bind="slotProps" /></ERPModal></template>
