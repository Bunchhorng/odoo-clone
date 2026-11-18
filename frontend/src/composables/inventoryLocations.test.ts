import { describe, expect, it } from 'vitest'
import { locationHierarchy } from './inventoryLocations'

describe('location hierarchy', () => {
  it('orders children under parents without assuming the API row order', () => {
    const rows = [{ id: 3, parent_id: 2 }, { id: 1, parent_id: null }, { id: 2, parent_id: 1 }]
    expect(locationHierarchy(rows).map(entry => [entry.row.id, entry.depth])).toEqual([[1, 0], [2, 1], [3, 2]])
  })
  it('keeps records visible when a parent is outside the filter and avoids imported cycles', () => {
    const rows = [{ id: 1, parent_id: 99 }, { id: 2, parent_id: 3 }, { id: 3, parent_id: 2 }]
    expect(locationHierarchy(rows).map(entry => entry.row.id)).toEqual([1, 2, 3])
  })
})
