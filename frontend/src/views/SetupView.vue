<script setup>
import { backendOrigin } from '../services/api'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore()
</script>

<template>
  <section class="guide-page">
    <p class="eyebrow">GETTING STARTED</p><h1>Your next steps.</h1><p class="intro">From your first sign-in to a company your team can use.</p>
    <ol class="steps">
      <li><span class="step-number">01</span><div><h2>Create your account</h2><p>Your project administrator runs <code>docker compose exec backend python manage.py createsuperuser</code> once, then signs in with the email and password. For teammates, create ordinary users in Django Admin.</p><a :href="`${backendOrigin}/admin/`" class="text-link">Open Django Admin ↗</a></div></li>
      <li><span class="step-number">02</span><div><h2>Sign in and create a company</h2><p>Sign in to KERP, open Companies, and enter the company name. You become its owner. The new company is selected automatically.</p><RouterLink :to="auth.user ? '/companies' : '/login'" class="text-link">{{ auth.user ? 'Open companies' : 'Sign in' }} →</RouterLink></div></li>
      <li><span class="step-number">03</span><div><h2>Bring your team together</h2><p>Open Team and add an existing account’s email. Owners can choose any role; administrators can add members. Tell your teammate to sign in. Access is immediate and no invitation email is sent.</p></div></li>
      <li><span class="step-number">04</span><div><h2>Work in the right company</h2><p>Use the company selector at the top of the page. It remembers your choice in your session. Each company has its own team and your role may differ between companies.</p></div></li>
      <li><span class="step-number">05</span><div><h2>Manage access as the team changes</h2><p>On Team, change a role or clear Active access, then select Save. Keep at least one active owner. Ask your Django administrator for password resets or account reactivation.</p></div></li>
    </ol>
    <section class="panel"><h2>Try the business workflow</h2><p class="muted">Create a customer in Contacts, add products in Inventory, then save and confirm a quotation in Sales. Validate its delivery, create an invoice, and register its payment. Purchase orders add stock when received; projects organize your team’s tasks.</p><RouterLink to="/" class="text-link">Open your applications →</RouterLink></section>
    <p class="notice">The repository’s SETUP.md explains running the code. docs/ERP-GUIDE.md walks through the business apps, docs/USER-GUIDE.md covers company access, and docs/DEVELOPMENT.md explains the code.</p>
  </section>
</template>
