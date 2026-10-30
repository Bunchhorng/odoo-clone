<script setup lang="ts">
import { dateLabel } from '../../composables/erp'
import type { Activity } from '../../types/erp'
withDefaults(defineProps<{ activities: Activity[]; title?: string; loading?: boolean; error?: string }>(), { title: 'Recent activity', error: '' })
defineEmits<{ retry: [] }>()
</script>
<template>
  <section class="erp-chatter" :aria-label="title" :aria-busy="loading">
    <h2>{{ title }}</h2>
    <p v-if="loading" role="status" class="muted">Loading activity…</p>
    <div v-else-if="error" class="notice error" role="alert">{{ error }} <button type="button" class="inline-button" @click="$emit('retry')">Retry</button></div>
    <template v-else>
      <ol v-if="activities.length" class="activity-list">
        <li v-for="activity in activities" :key="activity.id" class="activity-item">
          <span class="activity-dot" aria-hidden="true"></span>
          <div><span>{{ activity.summary }}</span><small>{{ activity.actor_email }} · <time :datetime="activity.created_at">{{ dateLabel(activity.created_at) }}</time></small></div>
        </li>
      </ol>
      <p v-else class="muted">No recent activity in this company.</p>
      <slot />
    </template>
  </section>
</template>
