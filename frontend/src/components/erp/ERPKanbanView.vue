<script setup lang="ts">
import { computed } from 'vue'
import type { ERPRecord } from '../../types/erp'
const props = withDefaults(defineProps<{ stages: string[][]; rows: ERPRecord[]; title: string; canCreate?: boolean; busy?: boolean; stageKey?: string }>(), { stageKey: 'stage' })
const emit = defineEmits<{ create: [stage: string]; drop: [event: DragEvent, stage: string] }>()
const columns = computed(() => props.stages.map(([value = '', label = '']) => ({ value, label, rows: props.rows.filter(row => row[props.stageKey] === value) })))
</script>
<template>
  <div class="kanban-board" role="region" :aria-label="`${title} board. Scroll horizontally for more stages.`" tabindex="0">
    <section v-for="column in columns" :key="column.value" class="kanban-column" :aria-label="column.label" @dragover.prevent @drop.prevent="emit('drop', $event, column.value)">
      <header><h2>{{ column.label }} <span>{{ column.rows.length }}</span></h2><button v-if="canCreate" type="button" :disabled="busy" :aria-label="`New record in ${column.label}`" @click="emit('create', column.value)">+</button></header>
      <slot name="column-header" :stage="column.value" :rows="column.rows" />
      <slot v-for="row in column.rows" :key="row.id" name="card" :row="row" :stage="column.value" />
      <p v-if="!column.rows.length" class="column-empty">No records here</p>
    </section>
  </div>
</template>
