<script setup>
defineProps({ name: String })
const paths = {
  chart: 'M4 20V12h4v8M10 20V4h4v16M16 20V8h4v12',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  pipeline: 'M3 4h18v4l-7 6v6l-4 2v-8L3 8ZM6 4V2M18 4V2',
  trend: 'M3 17l6-6 4 4 8-10M15 5h6v6M3 22h18',
  cart: 'M2 3h3l3 13h11l3-9H6M10 21h.01M18 21h.01',
  box: 'M21 8l-9-5-9 5v10l9 5 9-5ZM3 8l9 5 9-5M12 13v10M7 5l10 6',
  receipt: 'M5 3h14v19l-3-2-4 2-4-2-3 2ZM8 7h8M8 11h8M8 15h5',
  project: 'M3 3h18v18H3ZM3 8h18M8 8v13M12 12h5M12 16h3',
  team: 'M4 4h16v16H4ZM8 8h.01M12 8h5M8 12h.01M12 12h5M8 16h.01M12 16h5',
  settings: 'M9 3h6l1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1ZM16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  grid: 'M3 3h7v7H3ZM14 3h7v7h-7ZM3 14h7v7H3ZM14 14h7v7h-7Z',
  search: 'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  list: 'M8 5h13M8 12h13M8 19h13M3 5h.01M3 12h.01M3 19h.01',
}
</script>
<template><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] || paths.grid" /></svg></template>
