<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../../stores/auth'
import AppIcon from '../AppIcon.vue'
defineProps<{ disabled?: boolean }>()
const auth = useAuthStore()
const error = ref('')
async function select(event: Event) {
  const select = event.target as HTMLSelectElement
  error.value = ''
  try { await auth.selectCompany(Number(select.value)) }
  catch (failure) { error.value = (failure as Error).message }
  select.value = String(auth.activeCompanyId ?? '')
}
</script>
<template>
  <div class="company-context account-bar">
    <label v-if="auth.companies.length" class="company-picker">
      <AppIcon name="building" /><span class="company-picker-label">Company</span>
      <select :value="auth.activeCompanyId" aria-label="Active company" :disabled="disabled || auth.busy" @change="select">
        <option v-for="company in auth.companies" :key="company.id" :value="company.id">{{ company.name }}</option>
      </select>
      <span class="role-badge">{{ auth.activeCompany?.role }}</span>
    </label>
    <RouterLink v-else to="/companies" class="text-link">Create your first company</RouterLink>
    <p v-if="error" class="notice error" role="alert">{{ error }}</p>
  </div>
</template>
