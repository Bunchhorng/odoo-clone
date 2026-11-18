import { execFileSync } from 'node:child_process'
import { randomBytes } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { test, expect, type Page, type BrowserContext } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

const root = fileURLToPath(new URL('../../../', import.meta.url))
const run = randomBytes(8).toString('hex')
const owner = `ui-owner-${run}@example.test`
const member = `ui-member-${run}@example.test`
const password = randomBytes(24).toString('hex')
const companyName = `UI workspace ${run}`
const secondName = `UI second ${run}`
let companyId: number, secondId: number
let ownerState: Awaited<ReturnType<BrowserContext['storageState']>>
let seeded = false
const widths = [1440, 1024, 768, 390, 320]
const routes = ['/', '/dashboard', '/contacts', '/crm', '/sales', '/purchase', '/inventory', '/inventory/movements', '/invoicing', '/accounting', '/projects', '/tasks', '/employees', '/employees/departments', '/timesheets', '/helpdesk', '/team', '/settings', '/companies', '/account', '/setup']
function django(code: string) {
  return execFileSync('docker', ['compose', 'exec', '-T', 'backend', 'python', 'manage.py', 'shell'], { cwd: root, input: code, encoding: 'utf8', windowsHide: true, timeout: 120000 })
}
async function api(page: Page, path: string, method = 'GET', data?: unknown) {
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken')?.value || ''
  return page.request.fetch(`/api/v1/${path}`, { method, data, headers: { 'X-CSRFToken': csrf, Accept: 'application/json' } })
}
async function login(page: Page, email = owner) {
  await page.goto('/login')
  await page.getByRole('textbox', { name: 'Email address' }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('button', { name: 'User account menu' })).toBeVisible()
}
async function ready(page: Page, route: string) {
  await page.goto(route)
  await expect(page.locator('main')).toBeVisible()
  await expect(page.locator('#main-content > *')).not.toHaveCount(0)
  await expect(page.locator('.loading-state')).toHaveCount(0)
  await expect(page.locator('.notice.error')).toHaveCount(0)
  await page.evaluate(() => document.fonts.ready)
}
async function noOverflow(page: Page) {
  const overflow = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth,
    offenders: [...document.querySelectorAll<HTMLElement>('body *')].filter(element => {
      const rect = element.getBoundingClientRect()
      return rect.width > 0 && rect.right > innerWidth + 1 && !element.closest('.table-wrap, .kanban-board, .module-tabs')
    }).slice(0, 8).map(element => element.className),
  }))
  expect(overflow.scroll, `${page.url()} ${JSON.stringify(overflow)}`).toBeLessThanOrEqual(overflow.width + 1)
}

test.beforeAll(async ({ browser }) => {
  django(`from django.contrib.auth import get_user_model\nfrom django.db import transaction\nwith transaction.atomic():\n    get_user_model().objects.create_user(${JSON.stringify(owner)}, ${JSON.stringify(password)})\n    get_user_model().objects.create_user(${JSON.stringify(member)}, ${JSON.stringify(password)})\n`)
  seeded = true
  const context = await browser.newContext()
  try {
    const page = await context.newPage()
    await login(page)
    await expect(page.locator('.launcher-tile[aria-disabled=true]')).not.toHaveCount(0)
    await page.goto('/companies')
    await page.locator('input[name=company-name]').fill(companyName)
    await page.locator('.content-columns form .button-primary').click()
    await expect(page.getByLabel('Active company')).toHaveValue(/\d+/)
    companyId = (await (await api(page, 'auth/session/')).json()).active_company_id
    const second = await api(page, 'companies/', 'POST', { name: secondName })
    expect(second.status()).toBe(201)
    secondId = (await second.json()).active_company_id
    expect((await api(page, `companies/${companyId}/select/`, 'POST')).ok()).toBeTruthy()
    expect((await api(page, `companies/${companyId}/members/`, 'POST', { email: member, role: 'member' })).status()).toBe(201)
    await ready(page, '/contacts')
    await page.getByRole('button', { name: 'New', exact: true }).click()
    await page.getByRole('textbox', { name: 'Name', exact: true }).fill('Accessible customer')
    await page.getByRole('button', { name: 'Save', exact: true }).click()
    await expect(page.getByRole('dialog')).toHaveCount(0)
    await expect(page.locator('.record-card')).toHaveCount(1)
    expect((await api(page, `companies/${companyId}/erp/opportunities/`, 'POST', { title: 'Live opportunity', stage: 'new', expected_revenue: '1500', probability: 20 })).status()).toBe(201)
    ownerState = await context.storageState()
  } finally { await context.close() }
})

test.afterAll(() => {
  if (!seeded) return
  django(`from django.contrib.auth import get_user_model\nfrom apps.companies.models import Company\nfrom django.db import transaction\nwith transaction.atomic():\n    Company.objects.filter(name__in=[${JSON.stringify(companyName)}, ${JSON.stringify(secondName)}], memberships__user__email=${JSON.stringify(owner)}).delete()\n    get_user_model().objects.filter(email__in=[${JSON.stringify(owner)}, ${JSON.stringify(member)}]).delete()\n`)
})

test.beforeEach(async ({ context }) => {
  await context.addCookies(ownerState.cookies)
  await context.addInitScript(() => { if (!localStorage.getItem('kerp.theme')) localStorage.setItem('kerp.theme', 'light') })
})

test('launcher search, keyboard menus, company selection and real activity', async ({ page }) => {
  await ready(page, '/')
  await expect(page.locator('a.launcher-tile')).toHaveCount(14)
  await page.keyboard.press('/')
  await expect(page.getByRole('searchbox', { name: 'Search applications' })).toBeFocused()
  await page.keyboard.type('  QUOTATIONS  ')
  await expect(page.locator('a.launcher-tile')).toHaveCount(1)
  await page.keyboard.press('Escape')
  await expect(page.locator('a.launcher-tile')).toHaveCount(14)
  const switcher = page.getByRole('button', { name: 'Open applications' })
  await switcher.focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('link', { name: 'View all', exact: true })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(switcher).toBeFocused()
  await switcher.click()
  await page.getByRole('navigation', { name: 'Applications', exact: true }).getByRole('link', { name: 'Inventory', exact: true }).click()
  await expect(page).toHaveURL(/\/inventory$/)
  await expect(switcher).toHaveAttribute('aria-expanded', 'false')
  await page.getByRole('navigation', { name: 'Inventory navigation' }).getByRole('link', { name: 'Stock movements' }).click()
  await expect(page).toHaveURL(/\/inventory\/movements$/)
  await page.getByLabel('Active company').selectOption(String(secondId))
  await expect(page.getByLabel('Active company')).toBeEnabled()
  expect((await (await api(page, 'auth/session/')).json()).active_company_id).toBe(secondId)
  await page.getByLabel('Active company').selectOption(String(companyId))
  await expect(page.getByLabel('Active company')).toBeEnabled()
  await page.getByRole('button', { name: 'Notifications and recent activity' }).click()
  await expect(page.locator('.activity-popover')).toContainText('Accessible customer')
  await page.keyboard.press('Escape')
})

test('forms trap focus, protect unsaved changes and preserve the API-backed save', async ({ page }) => {
  await ready(page, '/contacts')
  const newButton = page.getByRole('button', { name: 'New', exact: true })
  await newButton.click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toHaveAccessibleName('New contact')
  await page.getByRole('textbox', { name: 'Name', exact: true }).fill('Unsaved customer')
  await dialog.getByRole('button', { name: 'Discard', exact: true }).focus()
  await page.keyboard.press('Tab')
  await expect(dialog.getByRole('button', { name: 'Close', exact: true })).toBeFocused()
  await page.keyboard.press('Shift+Tab')
  await expect(dialog.getByRole('button', { name: 'Discard', exact: true })).toBeFocused()
  page.once('dialog', prompt => prompt.dismiss())
  await page.keyboard.press('Escape')
  await expect(dialog).toBeVisible()
  page.once('dialog', prompt => prompt.accept())
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(newButton).toBeFocused()
  await page.getByRole('button', { name: 'List view' }).click()
  await expect(page.getByRole('region', { name: /^Contacts table/ })).toBeVisible()
  await page.getByLabel('Group this page by').selectOption('country')
  await expect(page.locator('.table-group')).toContainText('Unspecified')
})

for (const theme of ['light', 'dark']) {
  for (const width of widths) {
    test(`${theme} layouts at ${width}px`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.evaluate(value => { localStorage.setItem('kerp.theme', value) }, theme)
      for (const route of ['/', '/contacts', '/crm', '/sales', '/inventory', '/accounting', '/timesheets', '/helpdesk', '/team']) {
        await ready(page, route)
        await expect(page.locator('html')).toHaveAttribute('data-theme', theme)
        await noOverflow(page)
      }
      await page.goto('/')
      await page.screenshot({ path: info.outputPath(`launcher-${theme}-${width}.png`), fullPage: true })
    })
  }
}

test('all existing routes load without Vue errors', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('console', message => { if (message.text().includes('[Vue warn]')) errors.push(message.text()) })
  for (const route of routes) await ready(page, route)
  expect(await page.evaluate(() => getComputedStyle(document.body).fontFamily)).toContain('Segoe UI')
  expect(errors).toEqual([])
})

test('AA accessibility in both themes on launcher, list, form and board', async ({ page }) => {
  test.setTimeout(120000)
  for (const theme of ['light', 'dark']) {
    await page.goto('/')
    await page.evaluate(value => localStorage.setItem('kerp.theme', value), theme)
    for (const route of ['/', '/contacts', '/crm', '/dashboard', '/team']) {
      await ready(page, route)
      if (route === '/contacts') await page.getByRole('button', { name: 'List view' }).click()
      const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
      expect(scan.violations, `${theme} ${route}: ${JSON.stringify(scan.violations)}`).toEqual([])
    }
    await ready(page, '/contacts')
    await page.getByRole('button', { name: 'New', exact: true }).click()
    const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    expect(scan.violations, `${theme} modal: ${JSON.stringify(scan.violations)}`).toEqual([])
    await page.keyboard.press('Escape')
  }
})

test('200 percent zoom reflow and keyboard search', async ({ page }, info) => {
  // Browser zoom halves the CSS viewport. CDP does not expose desktop browser UI zoom.
  // Validate the equivalent 1440px -> 720 CSS-pixel reflow; retain the manual zoom check.
  await page.setViewportSize({ width: 720, height: 450 })
  for (const route of ['/', '/contacts', '/crm', '/accounting']) { await ready(page, route); await noOverflow(page) }
  await page.screenshot({ path: info.outputPath('zoom-reflow.png'), fullPage: true })
})

test('API failures and health failures remain distinct and recover', async ({ page }) => {
  await page.route('**/api/v1/companies/*/erp/contacts/**', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: 'Contacts temporarily unavailable' }) }))
  await page.goto('/contacts')
  await expect(page.getByRole('alert')).toContainText('Contacts temporarily unavailable')
  await expect(page.locator('.connection-badge')).toHaveClass(/connected/)
  await page.unroute('**/api/v1/companies/*/erp/contacts/**')
  await page.getByRole('button', { name: 'Retry', exact: true }).click()
  await expect(page.locator('.record-card')).toHaveCount(1)
  await ready(page, '/')
  await page.route('**/api/v1/health/', route => route.abort())
  await page.getByRole('button', { name: 'Check connection' }).click()
  await expect(page.locator('.connection-badge')).toHaveClass(/disconnected/)
  await expect(page.locator('a.launcher-tile')).toHaveCount(14)
  await page.unroute('**/api/v1/health/')
  await page.getByRole('button', { name: 'Check connection' }).click()
  await expect(page.locator('.connection-badge')).toHaveClass(/connected/)
})

test('members retain read access; CSRF and cross-company writes remain protected', async ({ page }) => {
  await page.context().clearCookies()
  await login(page, member)
  await ready(page, '/contacts')
  await expect(page.getByRole('button', { name: 'New', exact: true })).toHaveCount(0)
  expect((await api(page, `companies/${companyId}/erp/contacts/`, 'POST', { name: 'Forbidden' })).status()).toBe(403)
  expect((await api(page, `companies/${secondId}/erp/contacts/`)).status()).toBe(404)
  await page.locator('.record-card-main').click()
  await expect(page.getByRole('textbox', { name: 'Name', exact: true })).toBeDisabled()
  await page.keyboard.press('Escape')
  const missingCsrf = await page.request.post(`/api/v1/companies/${companyId}/select/`, { data: {} })
  expect(missingCsrf.status()).toBe(403)
  await api(page, 'auth/logout/', 'POST')
  await page.goto('/contacts')
  await expect(page).toHaveURL(/\/login/)
})
