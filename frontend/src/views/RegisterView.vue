<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const email = ref('')
const password = ref('')
const passwordConfirmation = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true; error.value = ''
  try {
    await auth.signUp(email.value, password.value, passwordConfirmation.value)
    password.value = ''; passwordConfirmation.value = ''
    await router.replace('/companies')
  } catch (err) { error.value = err.message }
  finally { busy.value = false }
}
</script>

<template>
  <section class="login-page">
    <div><p class="eyebrow">CREATE YOUR WORKSPACE</p><h1>Start with your<br />account.</h1><p class="intro">Create an account, then create or join a company workspace.</p></div>
    <form class="panel login-form" @submit.prevent="submit">
      <h2>Create an account</h2><p class="muted">Use an email address you control and a strong password.</p>
      <p v-if="error || auth.error" class="notice error" role="alert">{{ error || auth.error }}</p>
      <label>Email address<input v-model="email" name="email" type="email" autocomplete="email" maxlength="254" required :disabled="busy" /></label>
      <label>Password<input v-model="password" name="password" type="password" autocomplete="new-password" maxlength="1024" required :disabled="busy" /></label>
      <label>Confirm password<input v-model="passwordConfirmation" name="password_confirmation" type="password" autocomplete="new-password" maxlength="1024" required :disabled="busy" /></label>
      <button class="button-primary" type="submit" :disabled="busy">{{ busy ? 'Creating account…' : 'Create account' }} <span aria-hidden="true">→</span></button>
      <p class="form-help">Already have an account? <RouterLink to="/login" class="text-link">Sign in</RouterLink>.</p>
    </form>
  </section>
</template>
