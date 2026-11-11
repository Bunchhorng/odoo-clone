// Optional Windows smoke check. Requires host Node.js 22+, Edge, and running Compose services.
import { spawn, spawnSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { randomBytes } from 'node:crypto'
import { createServer } from 'node:net'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import assert from 'node:assert/strict'
import { verifyServiceOperations, verifyServiceMember } from './browser-service-operations-flow.mjs'
import { verifyERP } from './browser-erp-flow.mjs'
import { verifyAuthentication } from './browser-foundation-flow.mjs'
import { verifyCatalog, verifyCatalogReadOnly } from './browser-catalog-flow.mjs'
import { verifyAccounting, verifyAccountingReadOnly } from './browser-accounting-flow.mjs'
import { verifyCRMSales } from './browser-crm-sales-flow.mjs'
import { verifyPurchaseInventory, verifyInventoryReadOnly } from './browser-purchase-inventory-flow.mjs'

if (process.platform !== 'win32') throw new Error('This optional browser check currently supports Windows with Microsoft Edge.')
const root = fileURLToPath(new URL('../', import.meta.url))
const local = path.join(root, '.local')
await mkdir(local, { recursive: true })
const configuration = await readFile(path.join(root, '.env'), 'utf8')
const frontend = `http://localhost:${configuration.match(/^FRONTEND_PORT=(\d+)/m)?.[1] || 5173}`
const runId = randomBytes(8).toString('hex')
const owner = `browser-owner-${runId}@example.test`
const teammate = `browser-member-${runId}@example.test`
const password = randomBytes(24).toString('hex')
const companyName = `Browser check ${runId}`
const secondName = `Second company ${runId}`
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))
const results = []
const catalogOnly = process.argv.includes('--catalog-only')
const startedAt = new Date()
const resultPath = path.join(local, catalogOnly ? 'catalog-browser-results.json' : 'auth-browser-results.json')
const jsErrors = []
const vueWarnings = []
let edge, socket, browserSocket, version
let failure
let seeded = false
let sequence = 0
const pending = new Map()
await writeFile(resultPath, JSON.stringify({ status: 'running', runId, scope: catalogOnly ? 'catalog' : 'full', startedAt: startedAt.toISOString(), results }, null, 2) + '\n')

function django(code) {
  const result = spawnSync('docker', ['compose', 'exec', '-T', 'backend', 'python', 'manage.py', 'shell', '-c', code], {
    cwd: root, encoding: 'utf8', windowsHide: true,
  })
  if (result.status !== 0) throw new Error(`Django browser-test setup/cleanup failed: ${result.stderr || result.error || 'check Docker services'}`)
  return result.stdout
}
function seedAccountingHistory(companyId, invoiceId) {
  // Simulate a pre-ledger issued invoice, scoped to this run's owner and company.
  assert.equal(Number.isSafeInteger(companyId) && Number.isSafeInteger(invoiceId), true)
  django(`from apps.business.models import Invoice\nitem = Invoice.objects.get(pk=${invoiceId}, company_id=${companyId}, company__memberships__user__email=${JSON.stringify(owner)}, status='draft')\nassert not item.journal_entries.exists()\nitem.status = 'issued'\nitem.save(update_fields=['status'])`)
}
function resetLinkFor(email) {
  const output = django(`from django.contrib.auth import get_user_model; from django.contrib.auth.tokens import default_token_generator; from django.utils.encoding import force_bytes; from django.utils.http import urlsafe_base64_encode; import json\nuser = get_user_model().objects.get(email=${JSON.stringify(email)})\nprint('RESET=' + json.dumps({'uid': urlsafe_base64_encode(force_bytes(user.pk)), 'token': default_token_generator.make_token(user)}))`)
  const line = output.split(/\r?\n/).find(item => item.startsWith('RESET='))
  const token = JSON.parse(line.slice(6))
  return `/reset-password#uid=${token.uid}&token=${token.token}`
}
async function until(check, description, timeout = 20000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) { if (await check()) return; await sleep(150) }
  throw new Error(`Timed out waiting for ${description}`)
}
function send(method, params = {}) {
  const id = ++sequence
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`${method} timed out`)) }, 15000)
    pending.set(id, { resolve, reject, timer })
    socket.send(JSON.stringify({ id, method, params }))
  })
}
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text)
  return result.result.value
}
async function fill(selector, value) {
  await until(() => evaluate(`(() => { const element = document.querySelector(${JSON.stringify(selector)}); if (!element || element.matches(':disabled')) return false; return element.tagName !== 'SELECT' || [...element.options].some(option => option.value === ${JSON.stringify(String(value))}) })()`), `available field: ${selector}`)
  await evaluate(`(() => { const el = document.querySelector(${JSON.stringify(selector)}); el.value = ${JSON.stringify(value)}; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); })()`)
}
async function click(selector) {
  await until(() => evaluate(`(() => { const element = document.querySelector(${JSON.stringify(selector)}); return Boolean(element && !element.matches(':disabled') && element.getClientRects().length) })()`), `enabled control: ${selector}`)
  await evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`)
}
async function screenshot(name) {
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true })
  await writeFile(path.join(local, name), Buffer.from(shot.data, 'base64'))
}
async function navigate(route) {
  await send('Page.navigate', { url: `${frontend}${route}` })
  const target = new URL(route, frontend)
  await until(() => evaluate(`document.readyState === 'complete' && (location.pathname === ${JSON.stringify(target.pathname)} || location.pathname === '/login') && Boolean(document.querySelector('#main-content > *'))`), 'Vue page')
}
async function signIn(email, secret = password) {
  await until(() => evaluate('Boolean(document.querySelector(".login-form"))'), 'sign-in form')
  await fill('input[name=email]', email)
  await fill('input[name=password]', secret)
  await click('.login-form button[type=submit]')
}
async function signOut() {
  await until(() => evaluate('Boolean(document.querySelector(".user-avatar"))'), 'account actions ready')
  await click('button[aria-label="User account menu"]'); await click('.sign-out')
  await until(() => evaluate('Boolean(document.querySelector(".login-form"))'), 'sign-out')
}
async function browserAPI(endpoint, method = 'GET', data) {
  return evaluate(`(async () => {
    const token = document.cookie.split('; ').find(item => item.startsWith('csrftoken='))?.slice(10) || '';
    const response = await fetch('/api/v1/' + ${JSON.stringify(endpoint)}, {
      method: ${JSON.stringify(method)}, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(token) },
      ${data !== undefined ? `body: JSON.stringify(${JSON.stringify(data)}),` : ''}
    });
    return { status: response.status, data: await response.json() };
  })()`)
}

try {
  django("from django.conf import settings; assert settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend', 'Browser smoke checks require the local console mail backend.'")
  django(`from django.contrib.auth import get_user_model; from django.db import transaction\nwith transaction.atomic():\n    get_user_model().objects.create_user(${JSON.stringify(owner)}, ${JSON.stringify(password)})\n    get_user_model().objects.create_user(${JSON.stringify(teammate)}, ${JSON.stringify(password)})`)
  seeded = true
  const server = createServer()
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const port = server.address().port
  await new Promise(resolve => server.close(resolve))
  edge = spawn(process.env.EDGE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    `--remote-debugging-port=${port}`, `--user-data-dir=${path.join(local, 'auth-browser-profile')}`, 'about:blank',
  ], { windowsHide: true, stdio: 'ignore' })
  let launchError
  edge.on('error', error => { launchError = error })
  await until(async () => {
    if (launchError) throw launchError
    try { version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); return true }
    catch { return false }
  }, 'headless Edge')
  const page = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json()
  socket = new WebSocket(page.webSocketDebuggerUrl)
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject })
  socket.onmessage = event => {
    const message = JSON.parse(event.data)
    const request = pending.get(message.id)
    if (request) {
      pending.delete(message.id); clearTimeout(request.timer)
      if (message.error) request.reject(new Error(message.error.message))
      else request.resolve(message.result)
    }
    if (message.method === 'Runtime.exceptionThrown') jsErrors.push(message.params.exceptionDetails.text)
    if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'warning') {
      const text = message.params.args.map(arg => arg.value || arg.description || '').join(' ')
      if (text.includes('[Vue warn]')) vueWarnings.push(text)
    }
  }
  await send('Page.enable'); await send('Runtime.enable'); await send('Network.enable')
  await send('Emulation.setDeviceMetricsOverride', { width: 1365, height: 900, deviceScaleFactor: 1, mobile: false })
  await navigate('/team')
  await until(() => evaluate('location.pathname === "/login" && Boolean(document.querySelector(".login-form"))'), 'protected route redirect')
  await screenshot('auth-login-desktop.png')
  results.push('Anonymous access to /team redirects to sign-in.')
  await signIn(owner, 'incorrect-password')
  await until(() => evaluate('document.querySelector(".login-form .error")?.textContent.includes("incorrect")'), 'invalid-password error')
  await until(() => evaluate('!document.querySelector(".login-form button").disabled'), 'login retry')
  await signIn(owner)
  await until(() => evaluate('location.pathname === "/team" && Boolean(document.querySelector(".account-bar"))'), 'successful login and return route')
  assert.equal(await evaluate('Boolean(document.querySelector(".empty-state a"))'), true)
  results.push('Invalid credentials show an error; valid credentials restore the requested route and empty-company state.')

  await navigate('/companies')
  await fill('input[name=company-name]', companyName)
  await click('.content-columns form .button-primary')
  await until(() => evaluate(`document.querySelector('.company-picker select option:checked')?.textContent === ${JSON.stringify(companyName)}`), 'first company creation')
  await until(() => evaluate('!document.querySelector("input[name=company-name]").disabled'), 'company form ready')
  const first = (await browserAPI('auth/session/')).data.active_company_id
  await fill('input[name=company-name]', secondName)
  await click('.content-columns form .button-primary')
  await until(() => evaluate(`document.querySelector('.company-picker select option:checked')?.textContent === ${JSON.stringify(secondName)}`), 'second company creation')
  const second = (await browserAPI('auth/session/')).data.active_company_id
  await until(() => evaluate('!document.querySelector(".company-picker select").disabled'), 'company selector enabled')
  await fill('.company-picker select', String(first))
  await until(() => evaluate(`document.querySelector('.company-picker select option:checked')?.textContent === ${JSON.stringify(companyName)} && !document.querySelector('.company-picker select').disabled`), 'company switch')
  await navigate('/companies')
  await until(() => evaluate(`document.querySelector('.company-picker select')?.value === ${JSON.stringify(String(first))}`), 'persisted company selection')
  results.push('Company creation assigns ownership; switching persists across reloads.')

  await navigate('/team')
  await until(() => evaluate('document.querySelectorAll(".member-row").length === 1'), 'owner team')
  await fill('input[name=teammate-email]', teammate)
  await click('.team-details form .button-primary')
  await until(() => evaluate('document.querySelectorAll(".member-row").length === 2'), 'added teammate')
  await until(() => evaluate('!document.querySelector(".team-details form .button-primary").disabled'), 'team form ready')
  await evaluate(`(() => { const row = [...document.querySelectorAll('.member-row')].find(el => el.textContent.includes(${JSON.stringify(teammate)})); row.querySelector('input[type=checkbox]').click(); row.requestSubmit(); })()`)
  await until(async () => !(await browserAPI(`companies/${first}/members/`)).data.members.find(member => member.email === teammate).is_active, 'membership deactivation')
  await until(() => evaluate('Boolean(document.querySelector(".notice.success"))'), 'deactivation rendered')
  await evaluate(`(() => { const row = [...document.querySelectorAll('.member-row')].find(el => el.textContent.includes(${JSON.stringify(teammate)})); row.querySelector('input[type=checkbox]').click(); row.requestSubmit(); })()`)
  await until(async () => (await browserAPI(`companies/${first}/members/`)).data.members.find(member => member.email === teammate).is_active, 'membership reactivation')
  await until(() => evaluate('Boolean(document.querySelector(".notice.success"))'), 'reactivation rendered')
  await evaluate(`(() => { const row = [...document.querySelectorAll('.member-row')].find(el => el.textContent.includes(${JSON.stringify(owner)})); row.querySelector('input[type=checkbox]').click(); row.requestSubmit(); })()`)
  await until(() => evaluate('document.querySelector(".notice.error")?.textContent.includes("at least one active owner")'), 'last-owner error')
  results.push('Owners can add, deactivate, and reactivate teammates; the final owner is protected.')
  await screenshot('auth-team-desktop.png')

  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 1, mobile: true })
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await screenshot('auth-team-mobile.png')
  await navigate('/companies')
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await click('nav a[href="/"]')
  await until(() => evaluate('Boolean(document.querySelector(".health-panel"))'), 'overview')
  await send('Network.setBlockedURLs', { urls: ['*/api/v1/health/*'] })
  await click('.health-panel button')
  await until(() => evaluate('document.querySelector(".connection-badge")?.classList.contains("disconnected")'), 'disconnected health badge')
  await send('Network.setBlockedURLs', { urls: [] })
  await click('.health-panel button')
  await until(() => evaluate('document.querySelector(".connection-badge")?.classList.contains("connected")'), 'health recovery')
  results.push('Mobile layouts fit 375px; API health failure and retry recovery work.')
  if (!catalogOnly) await verifyERP({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId: first, secondCompanyId: second, results })
  if (!catalogOnly) await verifyCRMSales({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId: first, results })
  if (!catalogOnly) await verifyPurchaseInventory({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId: first, results })
  if (!catalogOnly) await verifyAccounting({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId: first, secondCompanyId: second, seedAccountingHistory, results })
  const serviceFixtures = !catalogOnly ? await verifyServiceOperations({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId: first, secondCompanyId: second, owner, teammate, results }) : null
  await verifyCatalog({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId: first, results })
  if (!catalogOnly) await verifyAuthentication({ evaluate, fill, click, until, navigate, browserAPI, signIn, signOut, resetLinkFor, owner, password, results })
  await signOut()
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await screenshot('auth-login-mobile.png')
  await signIn(teammate)
  await until(() => evaluate('Boolean(document.querySelector(".account-bar"))'), 'member login')
  assert.equal((await browserAPI('companies/')).data.companies.length, 1)
  await verifyCatalogReadOnly({ evaluate, click, navigate, until, results })
  if (!catalogOnly) await verifyInventoryReadOnly({ evaluate, navigate, until, browserAPI, companyId: first, results })
  if (!catalogOnly) await verifyAccountingReadOnly({ evaluate, navigate, until, browserAPI, companyId: first, results })
  if (!catalogOnly) await verifyServiceMember({ evaluate, fill, click, navigate, until, browserAPI, companyId: first, fixtures: serviceFixtures, results })
  if (!catalogOnly) {
    await navigate('/settings')
    await until(() => evaluate('Boolean(document.querySelector("select[name=currency]:disabled"))'), 'member company preferences')
    assert.equal(await evaluate('Boolean(document.querySelector(".settings-content form button"))'), false)
    assert.equal((await browserAPI(`companies/${first}/erp/settings/`, 'PATCH', { currency: 'EUR' })).status, 403)
    results.push('Members can inspect company preferences while currency changes remain protected in the UI and API.')
  }
  await navigate('/team')
  await until(() => evaluate('document.querySelectorAll(".member-row").length === 2'), 'member view')
  assert.equal(await evaluate('document.querySelectorAll(".member-row select, .team-details form").length'), 0)
  assert.equal((await browserAPI(`companies/${first}/members/`, 'POST', { email: owner })).status, 403)
  assert.equal((await browserAPI(`companies/${second}/members/`)).status, 404)
  results.push('Members get a read-only team screen; server rejects role escalation and cross-company access.')

  await click('nav a[href="/"]')
  await until(() => evaluate('Boolean(document.querySelector(".health-panel"))'), 'member overview')
  assert.equal((await browserAPI('auth/logout/', 'POST')).status, 200)
  // Keep the mounted session state to exercise a business API 401 and the
  // session-expired event, rather than reinitializing through a full page load.
  await click('button[aria-label="Open applications"]')
  await click('.app-menu a[href="/team"]')
  await until(() => evaluate('location.pathname === "/login" && location.search.includes("expired=1")'), 'session-expiry redirect')
  await navigate('/setup')
  await until(() => evaluate('document.querySelectorAll(".steps li").length === 5'), 'public guide')
  results.push('Expired sessions return to sign-in; the public guide remains available.')
  assert.deepEqual(jsErrors, [])
  assert.deepEqual(vueWarnings, [])
  results.push('No uncaught JavaScript errors.')
} catch (error) {
  failure = error
  if (socket?.readyState === WebSocket.OPEN) {
    await screenshot('browser-failure.png').catch(() => {})
    const pageState = await evaluate('({ path: location.pathname, text: document.body.innerText })').catch(() => ({}))
    await writeFile(path.join(local, 'browser-failure.json'), JSON.stringify({ runId, error: error.message, ...pageState, jsErrors, vueWarnings, results }, null, 2))
  }
  throw error
} finally {
  const cleanupErrors = []
  try {
    if (version) {
      browserSocket = new WebSocket(version.webSocketDebuggerUrl)
      await new Promise(resolve => { browserSocket.onopen = resolve; browserSocket.onerror = resolve; setTimeout(resolve, 1000) })
      if (browserSocket.readyState === WebSocket.OPEN) browserSocket.send(JSON.stringify({ id: 1, method: 'Browser.close' }))
    }
  } catch (error) { cleanupErrors.push(error.message) }
  socket?.close(); browserSocket?.close(); edge?.kill()
  for (const request of pending.values()) clearTimeout(request.timer)
  try {
    if (seeded) {
      // Delete only records tied to this unpredictable test run's exact identifiers.
      django(`from django.contrib.auth import get_user_model; from apps.companies.models import Company; from apps.business.models import TimesheetEntry, HelpdeskTicket, Employee, Department, JournalEntry, Payment, Invoice, StockMovement, PurchaseReceipt, Order, Task, Project, Opportunity, Product, Contact, Warehouse, StockLocation; from apps.accounts.models import PasswordResetDelivery; from django.db import transaction; from django.db.models import Q\nwith transaction.atomic():\n    companies = Company.objects.filter(name__in=[${JSON.stringify(companyName)}, ${JSON.stringify(secondName)}], memberships__user__email=${JSON.stringify(owner)})\n    ids = list(companies.values_list('id', flat=True))\n    JournalEntry.objects.filter(company_id__in=ids, reversal_of__isnull=False).delete()\n    JournalEntry.objects.filter(company_id__in=ids).delete()\n    StockMovement.objects.filter(company_id__in=ids).filter(Q(return_of__isnull=False) | Q(reversal_of__isnull=False)).delete()\n    for model in (TimesheetEntry, HelpdeskTicket, Employee, Department, Payment, Invoice, StockMovement, PurchaseReceipt, Order, Task, Project, Opportunity, Product, Contact):\n        model.objects.filter(company_id__in=ids).delete()\n    Warehouse.objects.filter(company_id__in=ids).delete()\n    while StockLocation.objects.filter(company_id__in=ids).exists():\n        StockLocation.objects.filter(company_id__in=ids, children__isnull=True).delete()\n    companies.delete()\n    PasswordResetDelivery.objects.filter(email__in=[${JSON.stringify(owner)}, ${JSON.stringify(teammate)}]).delete()\n    get_user_model().objects.filter(email__in=[${JSON.stringify(owner)}, ${JSON.stringify(teammate)}]).delete()`)
    }
  } catch (error) { cleanupErrors.push(error.message) }
  if (cleanupErrors.length) {
    process.exitCode = 1
    console.error('Browser-test cleanup failed:', cleanupErrors.join('; '))
  }
  const report = {
    status: failure || cleanupErrors.length ? 'failed' : 'passed',
    runId, scope: catalogOnly ? 'catalog' : 'full', frontend,
    startedAt: startedAt.toISOString(), completedAt: new Date().toISOString(),
    durationMs: Date.now() - startedAt.getTime(), browser: version?.Browser,
    groupCount: results.length, results, jsErrors, vueWarnings,
    cleanup: { status: cleanupErrors.length ? 'failed' : 'passed', errors: cleanupErrors },
    ...(failure ? { error: failure.message } : {}),
  }
  await writeFile(resultPath, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify(report, null, 2))
}
