<script setup>
import { backendOrigin } from '../services/api'
</script>

<template>
  <section class="guide-page">
    <p class="eyebrow">GETTING STARTED</p>
    <h1>Your next steps.</h1>
    <p class="intro">A shared foundation for your team and your companies.</p>
    <ol class="steps">
      <li><span class="step-number">01</span><div><h2>Sign in to administration</h2><p>Use the email address and password for your local admin account.</p><a :href="`${backendOrigin}/admin/`" class="text-link">Open Django Admin ↗</a></div></li>
      <li><span class="step-number">02</span><div><h2>Add your company</h2><p>Open Companies in administration, add a company, and choose a unique slug.</p></div></li>
      <li><span class="step-number">03</span><div><h2>Bring your team together</h2><p>Create user accounts, then add company memberships to associate each person with a company and a role.</p></div></li>
      <li><span class="step-number">04</span><div><h2>Keep the foundation healthy</h2><p>The overview checks your API and database automatically. You can also inspect the response directly.</p><a href="/api/v1/health/" class="text-link">View connection health ↗</a></div></li>
    </ol>
  </section>
</template>
