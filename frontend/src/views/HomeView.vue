<script setup>
import ERPAppLauncher from '../components/erp/ERPAppLauncher.vue'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>
<template><ERPAppLauncher :loading="auth.loading" :error="auth.error" @retry="auth.refresh().catch(() => {})" /></template>
