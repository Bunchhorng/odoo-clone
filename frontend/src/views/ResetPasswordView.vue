<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../services/api'
import { useAuthStore } from '../stores/auth'
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const values = new URLSearchParams(route.hash.slice(1))
const uid = values.get('uid') || ''
const token = values.get('token') || ''
const password = ref('')
const confirmation = ref('')
const busy = ref(false)
const error = ref('')
const success = ref('')
// Fragments never enter HTTP access logs. Remove the bearer token from history
// once captured, and keep it only in this component's memory.
onMounted(() => { if (route.hash) router.replace('/reset-password') })
async function submit() {
  busy.value = true; error.value = ''
  try {
    await api('auth/session/')
    const result = await api('auth/password/reset/confirm/', { method: 'POST', data: {
      uid, token, new_password1: password.value, new_password2: confirmation.value,
    } })
    password.value = ''; confirmation.value = ''; auth.clear(); success.value = result.message
  } catch (err) { error.value = err.message }
  finally { busy.value = false }
}
</script>
<template>
  <section class="recovery-page">
    <form class="panel reset-form" @submit.prevent="submit">
      <p class="eyebrow">ACCOUNT RECOVERY</p><h1>Choose a new password</h1>
      <p v-if="!uid || !token" class="notice error" role="alert">Open the complete reset link from your email. If it expired, request a new one.</p>
      <p v-if="error" class="notice error" role="alert">{{ error }}</p>
      <p v-if="success" class="notice success" role="status">{{ success }}</p>
      <template v-if="uid && token && !success">
        <fieldset :disabled="busy">
          <label>New password<input v-model="password" name="new_password1" type="password" autocomplete="new-password" minlength="8" maxlength="1024" required /></label>
          <label>Confirm new password<input v-model="confirmation" name="new_password2" type="password" autocomplete="new-password" minlength="8" maxlength="1024" required /></label>
        </fieldset>
        <button type="submit" class="button-primary" :disabled="busy">{{ busy ? 'Resetting…' : 'Reset password' }}</button>
      </template>
      <p class="form-help"><RouterLink v-if="success" to="/login" class="text-link">Sign in</RouterLink><RouterLink v-else to="/forgot-password" class="text-link">Request another reset link</RouterLink></p>
    </form>
  </section>
</template>
