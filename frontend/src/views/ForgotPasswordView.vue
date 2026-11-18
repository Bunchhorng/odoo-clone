<script setup>
import { ref } from 'vue'
import { api } from '../services/api'
const email = ref('')
const busy = ref(false)
const error = ref('')
const success = ref('')
async function submit() {
  busy.value = true; error.value = ''; success.value = ''
  try {
    await api('auth/session/')
    const result = await api('auth/password/reset/', { method: 'POST', data: { email: email.value } })
    success.value = result.message
  } catch (err) { error.value = err.message }
  finally { busy.value = false }
}
</script>
<template>
  <section class="recovery-page">
    <form class="panel recovery-form" @submit.prevent="submit">
      <p class="eyebrow">ACCOUNT RECOVERY</p><h1>Forgot your password?</h1>
      <p class="muted">Enter your account email to request a password reset link.</p>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <p v-if="success" class="notice success" role="status">{{ success }}</p>
      <label>Email address<input v-model="email" name="reset_email" type="email" autocomplete="username" maxlength="254" required :disabled="busy" /></label>
      <button type="submit" class="button-primary" :disabled="busy">{{ busy ? 'Requesting…' : 'Request reset link' }}</button>
      <p class="form-help"><RouterLink to="/login" class="text-link">Back to sign in</RouterLink></p>
    </form>
  </section>
</template>
