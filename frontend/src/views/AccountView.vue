<script setup>
import { ref } from 'vue'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
const oldPassword = ref('')
const password = ref('')
const confirmation = ref('')
const busy = ref(false)
const error = ref('')
const success = ref('')
async function submit() {
  busy.value = true; auth.busy = true; error.value = ''; success.value = ''
  try {
    const result = await api('auth/password/change/', { method: 'POST', data: {
      old_password: oldPassword.value, new_password1: password.value, new_password2: confirmation.value,
    } })
    oldPassword.value = ''; password.value = ''; confirmation.value = ''
    success.value = result.message
  } catch (err) { error.value = err.message }
  finally { busy.value = false; auth.busy = false }
}
</script>
<template>
  <section class="page-section account-page">
    <p class="eyebrow">YOUR ACCOUNT</p><h1>Account & security</h1>
    <p class="intro">{{ auth.user?.email }}</p>
    <form class="panel" @submit.prevent="submit">
      <h2>Change your password</h2>
      <p class="muted">Your current browser stays signed in. Your other sessions will need to sign in again.</p>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <p v-if="success" class="notice success" role="status">{{ success }}</p>
      <fieldset :disabled="busy">
        <label>Current password<input v-model="oldPassword" name="old_password" type="password" autocomplete="current-password" maxlength="1024" required /></label>
        <label>New password<input v-model="password" name="new_password1" type="password" autocomplete="new-password" minlength="8" maxlength="1024" required /></label>
        <label>Confirm new password<input v-model="confirmation" name="new_password2" type="password" autocomplete="new-password" minlength="8" maxlength="1024" required /></label>
      </fieldset>
      <p class="form-help">Use at least 8 characters. Avoid common passwords, all-numeric passwords, and passwords similar to your account details.</p>
      <button type="submit" class="button-primary" :disabled="busy">{{ busy ? 'Changing…' : 'Change password' }}</button>
    </form>
  </section>
</template>
