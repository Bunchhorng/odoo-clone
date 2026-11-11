// Filtered-out ancestors become labeled roots. Never drop records on page/filter changes.
export function locationHierarchy(rows) {
  const ids = new Set(rows.map(row => row.id))
  const children = new Map()
  for (const row of rows) {
    const parent = ids.has(row.parent_id) ? row.parent_id : null
    if (!children.has(parent)) children.set(parent, [])
    children.get(parent).push(row)
  }
  const result = [], seen = new Set()
  function walk(row, depth) {
    if (seen.has(row.id)) return
    seen.add(row.id); result.push({ row, depth })
    for (const child of children.get(row.id) || []) walk(child, depth + 1)
  }
  for (const root of children.get(null) || []) walk(root, 0)
  // Defensive rendering for malformed imported hierarchies; writes are validated by Django.
  for (const row of rows) if (!seen.has(row.id)) walk(row, 0)
  return result
}
