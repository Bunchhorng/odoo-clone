<!-- Compatibility adapter: existing callers retain events, props and named cells. -->
<script setup>
import ERPDataTable from '../erp/ERPDataTable.vue'
</script>
<template><ERPDataTable v-bind="$attrs"><template v-for="(_, name) in $slots" #[name]="slotProps"><slot :name="name" v-bind="slotProps" /></template></ERPDataTable></template>
