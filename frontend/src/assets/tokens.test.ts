// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
const css = readFileSync(resolve('src/assets/tokens.css'), 'utf8')
const themes = [...css.matchAll(/:root(?:\[data-theme='(dark)'\])?\s*\{([^}]+)\}/g)]
it('defines both themes for the contrast checks', () => { expect(themes).toHaveLength(2) })
function luminance(hex: string) {
  const rgb = hex.replace('#', '').match(/../g)!.map(value => {
    const channel = parseInt(value, 16) / 255
    return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4
  })
  return rgb[0]! * .2126 + rgb[1]! * .7152 + rgb[2]! * .0722
}
for (const theme of themes) {
  const tokens = Object.fromEntries([...theme[2]!.matchAll(/--([\w-]+):\s*(#[\da-f]{6});/g)].map(match => [match[1], match[2]])) as Record<string, string>
  describe(`${theme[1] || 'light'} contrast`, () => {
    const textPairs = [['text', 'surface'], ['text-muted', 'surface'], ['text-soft', 'surface'], ['text-muted', 'background'], ['text-muted', 'surface-subtle'], ['primary', 'selected'], ['link', 'surface'], ['on-primary', 'primary'], ['on-header', 'header'], ['success', 'success-bg'], ['warning', 'warning-bg'], ['danger', 'danger-bg'], ['info', 'info-bg']]
    for (const [foreground, background] of textPairs) {
      it(`${foreground} on ${background} meets AA normal-text contrast`, () => {
        const a = luminance(tokens[foreground!]!), b = luminance(tokens[background!]!)
        expect((Math.max(a, b) + .05) / (Math.min(a, b) + .05)).toBeGreaterThanOrEqual(4.5)
      })
    }
    for (const foreground of ['input-border', 'focus']) {
      it(`${foreground} meets control contrast`, () => {
        const a = luminance(tokens[foreground]!), b = luminance(tokens.surface!)
        expect((Math.max(a, b) + .05) / (Math.min(a, b) + .05)).toBeGreaterThanOrEqual(3)
      })
    }
  })
}
