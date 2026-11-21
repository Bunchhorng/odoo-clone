<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useHealthStore } from '../stores/health'

const auth = useAuthStore()
const health = useHealthStore()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  if (busy.value || !health.isAvailable) return
  busy.value = true
  error.value = ''
  try {
    await auth.signIn(email.value, password.value)
    password.value = ''
    const next = route.query.next
    await router.replace(typeof next === 'string' && next.startsWith('/') && !next.startsWith('//') && !next.startsWith('/login') ? next : '/')
  } catch (err) { error.value = err.message }
  finally { busy.value = false }
}
</script>

<template>
  <section class="login-page">
    <div><p class="eyebrow">YOUR BUSINESS STARTS HERE</p><h1>Welcome back.<br />Let's get to work.</h1><p class="intro">One account for your companies and your team.</p></div>
    <form class="panel login-form" @submit.prevent="submit">
      <h2>Sign in to Odoo</h2><p class="muted">Use the account created by your administrator.</p>
      <p v-if="!health.isAvailable" class="notice" role="status">Waiting for the Odoo server to finish starting.</p>
      <p v-if="route.query.expired" class="notice" role="status">Your session ended. Please sign in again.</p>
      <p v-if="error || auth.error" class="notice error" role="alert">{{ error || auth.error }}</p>
      <label>Email address<input v-model="email" name="email" type="email" autocomplete="username" maxlength="254" required :disabled="busy || !health.isAvailable" /></label>
      <label>Password<input v-model="password" name="password" type="password" autocomplete="current-password" maxlength="1024" required :disabled="busy || !health.isAvailable" /></label>
      <button class="button-primary" type="submit" :disabled="busy || !health.isAvailable">{{ busy ? 'Signing in...' : 'Sign in' }} <span aria-hidden="true">&rarr;</span></button>
      <p class="form-help"><RouterLink to="/forgot-password" class="text-link">Forgot your password?</RouterLink></p>
      <p class="form-help">Need an account? <RouterLink to="/register" class="text-link">Create one</RouterLink>.</p>
    </form>
  </section>
</template>
