<script setup>
import { computed } from 'vue'
import { money } from '../../composables/erp'
import UiBadge from '../ui/UiBadge.vue'
const props = defineProps({ rows: Array, columns: Array, title: String, currency: String, ordering: String, sortable: Boolean, selectable: Boolean, selected: { type: Array, default: () => [] }, busy: Boolean })
const emit = defineEmits(['open', 'sort', 'toggle', 'toggle-all'])
const allSelected = computed(() => props.rows.length > 0 && props.rows.every(row => props.selected.includes(row.id)))
function sort(column) { if (props.sortable && column.sort !== false) emit('sort', props.ordering === column.key ? `-${column.key}` : column.key) }
</script>
<template>
  <div class="table-wrap"><table class="data-table">
    <caption class="sr-only">{{ title }}</caption>
    <thead><tr>
      <th v-if="selectable" class="selection-cell"><input type="checkbox" aria-label="Select all records on this page" :checked="allSelected" :indeterminate="selected.length > 0 && !allSelected" :disabled="busy" @change="emit('toggle-all')" /></th>
      <th v-for="column in columns" :key="column.key" :aria-sort="ordering?.replace(/^-/, '') === column.key ? (ordering.startsWith('-') ? 'descending' : 'ascending') : undefined">
        <button v-if="sortable && column.sort !== false" type="button" class="sort-button" @click="sort(column)">{{ column.label }} <span aria-hidden="true">{{ ordering === column.key ? '↑' : ordering === `-${column.key}` ? '↓' : '↕' }}</span></button><template v-else>{{ column.label }}</template>
      </th><th>Status</th><th v-if="$slots.actions">Actions</th>
    </tr></thead>
    <tbody><tr v-for="row in rows" :key="row.id" :class="{ selected: selected.includes(row.id) }">
      <td v-if="selectable" class="selection-cell"><input type="checkbox" :aria-label="`Select ${row.name || row.title}`" :checked="selected.includes(row.id)" :disabled="busy" @change="emit('toggle', row.id)" /></td>
      <td v-for="(column, index) in columns" :key="column.key" :class="{ numeric: column.money }"><slot :name="`cell-${column.key}`" :row="row"><button v-if="index === 0" type="button" class="text-link" @click="emit('open', row)">{{ row[column.key] }}</button><span v-else>{{ column.money ? money(row[column.key], currency) : row[column.key] ?? '—' }}</span></slot></td>
      <td><UiBadge :tone="row.is_active ? '' : 'cancelled'">{{ row.is_active ? 'Active' : 'Archived' }}</UiBadge></td><td v-if="$slots.actions"><slot name="actions" :row="row" /></td>
    </tr></tbody>
  </table></div>
</template>
