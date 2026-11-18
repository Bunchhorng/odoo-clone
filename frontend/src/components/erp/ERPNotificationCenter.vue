<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { erp } from '../../composables/erp'
import { useAuthStore } from '../../stores/auth'
import type { Activity } from '../../types/erp'
import AppIcon from '../AppIcon.vue'
import ERPPopover from './ERPPopover.vue'
import ERPChatter from './ERPChatter.vue'

const auth = useAuthStore()
const activities = ref<Activity[]>([])
const loading = ref(false)
const error = ref('')
let generation = 0
async function refresh() {
  const current = ++generation
  activities.value = []; error.value = ''
  if (!auth.activeCompanyId) { loading.value = false; return }
  loading.value = true
  try {
    const data = await erp(auth.activeCompanyId, 'dashboard/')
    if (generation === current) activities.value = data.activities
  } catch (failure) { if (generation === current) error.value = (failure as Error).message }
  finally { if (generation === current) loading.value = false }
}
watch(() => auth.activeCompanyId, () => { generation++; activities.value = []; error.value = ''; loading.value = false })
onUnmounted(() => { generation++ })
</script>
<template>
  <ERPPopover label="Notifications and recent activity" panel-class="activity-popover" @opened="refresh">
    <template #trigger><AppIcon name="bell" /><span class="sr-only">Recent activity</span></template>
    <template #default>
      <div class="activity-center">
        <p class="popover-eyebrow">{{ auth.activeCompany?.name || 'No company selected' }}</p>
        <ERPChatter :activities="activities" :loading="loading" :error="error" @retry="refresh">
          <p class="muted">Latest company events. This feed has no unread status.</p>
        </ERPChatter>
        <button v-if="auth.activeCompanyId" type="button" class="button-secondary" :disabled="loading" @click="refresh">Refresh activity</button>
      </div>
    </template>
  </ERPPopover>
</template>
