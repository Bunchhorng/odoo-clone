<script setup lang="ts">
import { computed } from 'vue'
import { money } from '../../composables/erp'
import type { ERPColumn, ERPRecord } from '../../types/erp'
import UiBadge from '../ui/UiBadge.vue'
const props = withDefaults(defineProps<{ rows: ERPRecord[]; columns: ERPColumn[]; title: string; currency?: string; ordering?: string; sortable?: boolean; selectable?: boolean; selected?: number[]; busy?: boolean; groupBy?: string }>(), { selected: () => [], groupBy: '' })
const emit = defineEmits<{ open: [row: ERPRecord]; sort: [ordering: string]; toggle: [id: number]; 'toggle-all': [] }>()
const allSelected = computed(() => props.rows.length > 0 && props.rows.every(row => props.selected.includes(row.id)))
const someSelected = computed(() => props.rows.some(row => props.selected.includes(row.id)))
const groups = computed(() => {
  if (!props.groupBy) return [{ label: '', rows: props.rows }]
  const grouped = new Map<string, ERPRecord[]>()
  for (const row of props.rows) {
    const label = String(row[props.groupBy] || 'Unspecified')
    grouped.set(label, [...(grouped.get(label) || []), row])
  }
  return [...grouped.entries()].map(([label, rows]) => ({ label, rows }))
})
function sort(column: ERPColumn) { if (props.sortable && column.sort !== false) emit('sort', props.ordering === column.key ? `-${column.key}` : column.key) }
</script>
<template>
  <div class="table-wrap" role="region" :aria-label="`${title} table. Scroll horizontally for more columns.`" tabindex="0">
    <table class="data-table">
      <caption class="sr-only">{{ title }}{{ groupBy ? ' — groups reflect records on this page' : '' }}</caption>
      <thead><tr>
        <th v-if="selectable" scope="col" class="selection-cell"><input type="checkbox" aria-label="Select all records on this page" :checked="allSelected" :indeterminate="someSelected && !allSelected" :disabled="busy" @change="emit('toggle-all')" /></th>
        <th v-for="column in columns" :key="column.key" scope="col" :class="{ numeric: column.money }" :aria-sort="ordering?.replace(/^-/, '') === column.key ? (ordering?.startsWith('-') ? 'descending' : 'ascending') : undefined">
          <button v-if="sortable && column.sort !== false" type="button" class="sort-button" :disabled="busy" @click="sort(column)">{{ column.label }} <span aria-hidden="true">{{ ordering === column.key ? '↑' : ordering === `-${column.key}` ? '↓' : '↕' }}</span></button><template v-else>{{ column.label }}</template>
        </th><th scope="col">Status</th><th v-if="$slots.actions" scope="col">Actions</th>
      </tr></thead>
      <tbody v-for="group in groups" :key="group.label">
        <tr v-if="groupBy" class="table-group"><th :colspan="columns.length + (selectable ? 1 : 0) + ($slots.actions ? 2 : 1)" scope="rowgroup">{{ group.label }} <span class="muted">({{ group.rows.length }})</span></th></tr>
        <tr v-for="row in group.rows" :key="row.id" :class="{ selected: selected.includes(row.id) }">
          <td v-if="selectable" class="selection-cell"><input type="checkbox" :aria-label="`Select ${row.name || row.title}`" :checked="selected.includes(row.id)" :disabled="busy" @change="emit('toggle', row.id)" /></td>
          <td v-for="(column, index) in columns" :key="column.key" :class="{ numeric: column.money }"><slot :name="`cell-${column.key}`" :row="row"><button v-if="index === 0" type="button" class="text-link" @click="emit('open', row)">{{ row[column.key] }}</button><span v-else>{{ column.money ? money(row[column.key], currency) : row[column.key] ?? '—' }}</span></slot></td>
          <td><UiBadge :tone="row.is_active ? '' : 'cancelled'">{{ row.is_active ? 'Active' : 'Archived' }}</UiBadge></td><td v-if="$slots.actions"><slot name="actions" :row="row" /></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
