import { execFileSync } from 'node:child_process'
import { randomBytes, randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { expect, test, type Page } from '@playwright/test'

const root = fileURLToPath(new URL('../../../', import.meta.url))
const run = randomBytes(6).toString('hex')

function required(name: string) {
  const value = process.env[name]
  if (!value) throw new Error(`${name} must be exported from C:/tmp/kerp_check/fixture-users.env`)
  return value
}

const password = required('KERP_FIXTURE_PASSWORD')
const users = {
  alphaOwner: required('KERP_ALPHA_OWNER_EMAIL'),
  alphaAdmin: required('KERP_ALPHA_ADMIN_EMAIL'),
  alphaMemberEmployee: required('KERP_ALPHA_MEMBER_EMPLOYEE_EMAIL'),
  alphaMemberNoEmployee: required('KERP_ALPHA_MEMBER_NOEMPLOYEE_EMAIL'),
  bravoOwner: required('KERP_BRAVO_OWNER_EMAIL'),
  bravoAdmin: required('KERP_BRAVO_ADMIN_EMAIL'),
  bravoMemberEmployee: required('KERP_BRAVO_MEMBER_EMPLOYEE_EMAIL'),
  bravoMemberNoEmployee: required('KERP_BRAVO_MEMBER_NOEMPLOYEE_EMAIL'),
}

type Session = { user: { id: number, email: string }, companies: Array<{ id: number, name: string, role: string }>, active_company_id: number | null }
type Catalog = { id: number, name: string, sku?: string }

let alphaId = 0
let bravoId = 0
let ownerSubmittedTime: { id: number, version: number } | undefined

function django(code: string) {
  return execFileSync('docker', ['exec', '-i', 'kerp-browser-backend', 'python', 'manage.py', 'shell'], {
    cwd: root, input: code, encoding: 'utf8', windowsHide: true, timeout: 120000,
  })
}

async function api(page: Page, path: string, method = 'GET', data?: unknown) {
  const csrf = (await page.context().cookies()).find(cookie => cookie.name === 'csrftoken')?.value || ''
  return page.request.fetch(`/api/v1/${path}`, { method, data, headers: { Accept: 'application/json', 'X-CSRFToken': csrf } })
}

async function body<T>(response: Awaited<ReturnType<typeof api>>, expected = 200): Promise<T> {
  expect(await response.text(), `expected HTTP ${expected}, received ${response.status()}`).toBeTruthy()
  expect(response.status()).toBe(expected)
  return response.json() as Promise<T>
}

async function login(page: Page, email: string) {
  await page.context().clearCookies()
  await page.goto('/login')
  await page.getByRole('textbox', { name: 'Email address' }).fill(email)
  await page.getByLabel('Password', { exact: true }).fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page.getByRole('button', { name: 'User account menu' })).toBeVisible()
}

async function session(page: Page) {
  return body<Session>(await api(page, 'auth/session/'))
}

async function company(page: Page, name: string) {
  const current = await session(page)
  const selected = current.companies.find(item => item.name === name)
  expect(selected, `${name} must be a fixture company`).toBeTruthy()
  if (selected && current.active_company_id !== selected.id) await body(await api(page, `companies/${selected.id}/select/`, 'POST'))
  return selected!.id
}

async function fixtureCatalog(page: Page, companyId: number) {
  const contacts = await body<{ results: Catalog[] }>(await api(page, `companies/${companyId}/erp/contacts/?q=E2E%20Fixture%20Customer`))
  const products = await body<{ results: Catalog[] }>(await api(page, `companies/${companyId}/erp/products/?q=E2E%20Fixture%20Product`))
  const projects = await body<{ results: Catalog[] }>(await api(page, `companies/${companyId}/erp/projects/?q=E2E%20Fixture%20Project`))
  expect(contacts.results).toHaveLength(1)
  expect(products.results).toHaveLength(1)
  expect(projects.results).toHaveLength(1)
  return { contact: contacts.results[0], product: products.results[0], project: projects.results[0] }
}

test.describe.configure({ mode: 'serial' })

test.beforeAll(() => {
  django(`
from django.contrib.auth import get_user_model
from apps.business.locations import ensure_defaults
from apps.business.models import Contact, Employee, Product, Project, StockLocation, Task, WorkspaceSettings
from apps.companies.models import Company, CompanyAccessGroup, CompanyAccessGroupMembership, CompanyMembership, UserAppAccessOverride
from apps.companies.seeding import seed_company

User = get_user_model()
alpha = Company.objects.get(slug="browser-test-alpha")
bravo = Company.objects.get(slug="browser-test-bravo")
seed_company(alpha); seed_company(bravo)
emails = ${JSON.stringify(users)}
alpha_owner = User.objects.get(email=emails["alphaOwner"])
alpha_admin = User.objects.get(email=emails["alphaAdmin"])
alpha_member = User.objects.get(email=emails["alphaMemberEmployee"])
alpha_purchase = User.objects.get(email=emails["alphaMemberNoEmployee"])
bravo_member = User.objects.get(email=emails["bravoMemberEmployee"])
Employee.objects.get_or_create(company=alpha, user=alpha_owner, defaults={"name": "Alpha Owner", "employee_code": "E2E-ALPHA-OWNER"})
Employee.objects.get_or_create(company=alpha, user=alpha_member, defaults={"name": "Alpha Member", "employee_code": "E2E-ALPHA-MEMBER"})
Employee.objects.get_or_create(company=bravo, user=bravo_member, defaults={"name": "Bravo Member", "employee_code": "E2E-BRAVO-MEMBER"})
purchase = CompanyAccessGroup.objects.get(company=alpha, system_key="purchase-user")
CompanyAccessGroupMembership.objects.filter(user=alpha_purchase, group__company=alpha, group__is_system=True).exclude(group=purchase).delete()
CompanyAccessGroupMembership.objects.get_or_create(user=alpha_purchase, group=purchase)
UserAppAccessOverride.objects.update_or_create(company=alpha, user=alpha_admin, app_key="sales", defaults={"can_read": False})
contact, _ = Contact.objects.get_or_create(company=alpha, name="E2E Fixture Customer", defaults={"is_customer": True, "is_supplier": True})
if not contact.is_supplier:
    contact.is_supplier = True; contact.save(update_fields=["is_supplier"])
Product.objects.get_or_create(company=alpha, sku="E2E-FIXTURE-001", defaults={"name": "E2E Fixture Product", "kind": "goods", "sale_price": "20.00", "cost_price": "10.00"})
project, _ = Project.objects.get_or_create(company=alpha, name="E2E Fixture Project")
Task.objects.update_or_create(company=alpha, title="E2E assigned task", defaults={"project": project, "assignee": alpha_member, "is_active": True})
Task.objects.update_or_create(company=alpha, title="E2E unassigned task", defaults={"project": project, "assignee": alpha_admin, "is_active": True})
WorkspaceSettings.objects.get_or_create(company=alpha)
stock, _ = ensure_defaults(alpha.pk)
StockLocation.objects.get_or_create(company=alpha, code="E2E-BIN", defaults={"name": "E2E Browser Bin", "usage": "internal"})
`)
})

test('all eight fixture users can sign in only to their own fixture company', async ({ browser }) => {
  const entries = [
    [users.alphaOwner, 'Browser Test Alpha'], [users.alphaAdmin, 'Browser Test Alpha'],
    [users.alphaMemberEmployee, 'Browser Test Alpha'], [users.alphaMemberNoEmployee, 'Browser Test Alpha'],
    [users.bravoOwner, 'Browser Test Bravo'], [users.bravoAdmin, 'Browser Test Bravo'],
    [users.bravoMemberEmployee, 'Browser Test Bravo'], [users.bravoMemberNoEmployee, 'Browser Test Bravo'],
  ] as const
  for (const [email, expectedCompany] of entries) {
    const context = await browser.newContext()
    try {
      const page = await context.newPage()
      await login(page, email)
      const current = await session(page)
      expect(current.user.email).toBe(email)
      expect(current.companies.map(item => item.name)).toEqual([expectedCompany])
      await expect(page.getByRole('button', { name: 'User account menu' })).toBeVisible()
    } finally { await context.close() }
  }
})

test('member with an employee logs and submits time using only an assigned task', async ({ page }) => {
  await login(page, users.alphaMemberEmployee)
  alphaId = await company(page, 'Browser Test Alpha')
  const data = await body<{ employees: Array<{ id: number, user_id: number }>, projects: Catalog[], tasks: Array<{ id: number, title: string, project_id: number }> }>(
    await api(page, `companies/${alphaId}/erp/timesheets/`),
  )
  expect(data.employees).toHaveLength(1)
  expect(data.tasks.map(item => item.title)).toContain('E2E assigned task')
  expect(data.tasks.map(item => item.title)).not.toContain('E2E unassigned task')
  const assigned = data.tasks.find(item => item.title === 'E2E assigned task')!
  const project = data.projects.find(item => item.id === assigned.project_id)!

  await page.goto('/timesheets')
  await page.getByRole('button', { name: 'Log time', exact: true }).click()
  await expect(page.locator('select[name=time_employee] option')).toHaveCount(2)
  await page.locator('select[name=time_employee]').selectOption(String(data.employees[0].id))
  await page.locator('select[name=time_project]').selectOption(String(project.id))
  await expect(page.locator('select[name=time_task] option')).toHaveText(['No task', 'E2E assigned task'])
  await page.locator('select[name=time_task]').selectOption(String(assigned.id))
  await page.locator('input[name=time_minutes]').fill('30')
  await page.locator('textarea[name=time_description]').fill(`Assigned task time ${run}`)
  await page.getByRole('button', { name: 'Save draft', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Draft time entry saved.')
  await page.getByRole('button', { name: 'Submit', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Time entry updated.')
  await expect(page.locator('.badge.submitted')).toHaveCount(1)
})

test('member without an employee is told why they cannot create a timesheet', async ({ page }) => {
  await login(page, users.alphaMemberNoEmployee)
  const companyId = await company(page, 'Browser Test Alpha')
  const data = await body<{ can_log: boolean, employees: unknown[] }>(await api(page, `companies/${companyId}/erp/timesheets/`))
  expect(data.can_log).toBe(false)
  expect(data.employees).toHaveLength(0)
  await page.goto('/timesheets')
  await expect(page.getByText('Ask an owner or administrator to link your Team account to an active Employee record before logging time.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Log time', exact: true })).toHaveCount(0)
})

test('member creates a helpdesk ticket with a contact and is recorded as creator', async ({ page }) => {
  await login(page, users.alphaMemberEmployee)
  const companyId = await company(page, 'Browser Test Alpha')
  const { contact } = await fixtureCatalog(page, companyId)
  await page.goto('/helpdesk')
  await page.getByRole('button', { name: 'New ticket', exact: true }).click()
  await page.locator('input[name=ticket_title]').fill(`Member contact ticket ${run}`)
  await page.locator('select[name=ticket_contact]').selectOption(String(contact.id))
  await expect(page.locator('select[name=ticket_contact]')).toHaveValue(String(contact.id))
  await page.getByRole('button', { name: 'Save ticket', exact: true }).click()
  await expect(page).toHaveURL(/\/helpdesk\/\d+$/)
  await expect(page.locator('.ticket-facts')).toContainText(users.alphaMemberEmployee)
  await expect(page.locator('.ticket-facts')).toContainText(contact.name)
})

test('admin and member dashboards omit data from applications they cannot read', async ({ page }) => {
  await login(page, users.alphaMemberEmployee)
  const companyId = await company(page, 'Browser Test Alpha')
  const memberDashboard = await body<{ recent_orders: unknown[], sales_total: string | number, quotations: number }>(await api(page, `companies/${companyId}/erp/dashboard/`))
  expect(memberDashboard.recent_orders).toEqual([])
  expect(Number(memberDashboard.sales_total)).toBe(0)
  expect(memberDashboard.quotations).toBe(0)

  await login(page, users.alphaAdmin)
  const adminId = await company(page, 'Browser Test Alpha')
  const adminDashboard = await body<{ recent_orders: unknown[], sales_total: string | number, quotations: number }>(await api(page, `companies/${adminId}/erp/dashboard/`))
  expect(adminDashboard.recent_orders).toEqual([])
  expect(Number(adminDashboard.sales_total)).toBe(0)
  expect(adminDashboard.quotations).toBe(0)
})

test('purchase-only user sees no sale orders from an unqualified order list', async ({ page }) => {
  await login(page, users.alphaMemberNoEmployee)
  const companyId = await company(page, 'Browser Test Alpha')
  const { contact, product } = await fixtureCatalog(page, companyId)
  const created = await body<{ id: number, kind: string }>(await api(page, `companies/${companyId}/erp/orders/`, 'POST', {
    kind: 'purchase', contact_id: contact.id, lines: [{ product_id: product.id, quantity: '1', unit_price: '10.00' }],
  }), 201)
  expect(created.kind).toBe('purchase')
  const listed = await body<{ count: number, results: Array<{ kind: string }> }>(await api(page, `companies/${companyId}/erp/orders/`))
  expect(listed.count).toBeGreaterThan(0)
  expect(listed.results.every(item => item.kind === 'purchase')).toBe(true)
})

test('owner completes contacts, products, sale-to-payment, purchase receipt, transfer, and own-time workflow', async ({ page }) => {
  await login(page, users.alphaOwner)
  const companyId = await company(page, 'Browser Test Alpha')
  alphaId = companyId
  const customer = await body<Catalog>(await api(page, `companies/${companyId}/erp/contacts/`, 'POST', {
    name: `E2E Workflow Contact ${run}`, is_customer: true, is_supplier: true,
  }), 201)
  const product = await body<Catalog>(await api(page, `companies/${companyId}/erp/products/`, 'POST', {
    name: `E2E Workflow Product ${run}`, sku: `E2E-${run.toUpperCase()}`, kind: 'goods', sale_price: '20.00', cost_price: '10.00',
  }), 201)
  expect(product.sku).toContain('E2E-')
  const sale = await body<{ id: number, version: number, status: string }>(await api(page, `companies/${companyId}/erp/orders/`, 'POST', {
    kind: 'sale', contact_id: customer.id, lines: [{ product_id: product.id, quantity: '1', unit_price: '20.00' }],
  }), 201)
  const confirmedSale = await body<{ id: number, version: number, status: string }>(await api(page, `companies/${companyId}/erp/orders/${sale.id}/actions/`, 'POST', { action: 'confirm', expected_version: sale.version }))
  expect(confirmedSale.status).toBe('confirmed')
  const invoice = await body<{ id: number, version: number, status: string }>(await api(page, `companies/${companyId}/erp/orders/${sale.id}/actions/`, 'POST', { action: 'invoice', expected_version: confirmedSale.version }))
  const issued = await body<{ id: number, version: number, status: string }>(await api(page, `companies/${companyId}/erp/invoices/${invoice.id}/actions/`, 'POST', { action: 'issue', expected_version: invoice.version }))
  expect(issued.status).toBe('issued')
  const paid = await body<{ status: string }>(await api(page, `companies/${companyId}/erp/invoices/${invoice.id}/payments/`, 'POST', { amount: '20.00', date: new Date().toISOString().slice(0, 10), method: 'bank', reference: `e2e-${run}`, request_id: randomUUID() }))
  expect(paid.status).toBe('paid')

  const purchase = await body<{ id: number, version: number }>(await api(page, `companies/${companyId}/erp/orders/`, 'POST', {
    kind: 'purchase', contact_id: customer.id, lines: [{ product_id: product.id, quantity: '3', unit_price: '10.00' }],
  }), 201)
  const confirmedPurchase = await body<{ id: number, version: number, lines: Array<{ id: number }> }>(await api(page, `companies/${companyId}/erp/orders/${purchase.id}/actions/`, 'POST', { action: 'confirm', expected_version: purchase.version }))
  const receipt = await body<{ receipt: { movements: unknown[] } }>(await api(page, `companies/${companyId}/erp/orders/${purchase.id}/receipts/`, 'POST', {
    request_id: randomUUID(), expected_version: confirmedPurchase.version, lines: [{ line_id: confirmedPurchase.lines[0].id, quantity: '3' }],
  }), 201)
  expect(receipt.receipt.movements).toHaveLength(1)

  const locations = await body<{ results: Array<{ id: number, code: string }> }>(await api(page, `companies/${companyId}/erp/locations/?usage=internal`))
  const source = locations.results.find(item => item.code !== 'E2E-BIN')!
  const destination = locations.results.find(item => item.code === 'E2E-BIN')!
  expect(source).toBeTruthy(); expect(destination).toBeTruthy()
  const transfer = await body<{ transfer: { id: number, lines: Array<{ id: number }> } }>(await api(page, `companies/${companyId}/erp/transfers/`, 'POST', {
    source_location_id: source.id, destination_location_id: destination.id, lines: [{ product_id: product.id, quantity: '1' }], request_id: randomUUID(),
  }), 201)
  const validated = await body<{ transfer: { status: string } }>(await api(page, `companies/${companyId}/erp/transfers/${transfer.transfer.id}/actions/`, 'POST', {
    action: 'validate', lines: [{ line_id: transfer.transfer.lines[0].id, quantity: '1' }],
  }))
  expect(validated.transfer.status).toBe('done')

  const { project } = await fixtureCatalog(page, companyId)
  const ownerSession = await session(page)
  const timeChoices = await body<{ employees: Array<{ id: number, user_id: number }> }>(await api(page, `companies/${companyId}/erp/timesheets/`))
  const ownerEmployee = timeChoices.employees.find(item => item.user_id === ownerSession.user.id)
  expect(ownerEmployee).toBeTruthy()
  const draft = await body<{ id: number, version: number, status: string }>(await api(page, `companies/${companyId}/erp/timesheets/`, 'POST', {
    employee_id: ownerEmployee!.id, project_id: project.id, task_id: null, ticket_id: null,
    date: new Date().toISOString().slice(0, 10), minutes: 15, description: `Owner time ${run}`, request_id: randomUUID(),
  }), 201)
  ownerSubmittedTime = await body<{ id: number, version: number }>(await api(page, `companies/${companyId}/erp/timesheets/${draft.id}/actions/`, 'POST', { action: 'submit', expected_version: draft.version }))
  await expect(page.getByRole('button', { name: 'User account menu' })).toBeVisible()
})

test('owner self-approval keeps the legacy success response in log mode', async ({ page }) => {
  await login(page, users.alphaOwner)
  const companyId = await company(page, 'Browser Test Alpha')
  const { project } = await fixtureCatalog(page, companyId)
  const ownerSession = await session(page)
  const choices = await body<{ employees: Array<{ id: number, user_id: number }> }>(await api(page, `companies/${companyId}/erp/timesheets/`))
  const ownerEmployee = choices.employees.find(item => item.user_id === ownerSession.user.id)
  expect(ownerEmployee).toBeTruthy()
  const draft = await body<{ id: number, version: number }>(await api(page, `companies/${companyId}/erp/timesheets/`, 'POST', {
    employee_id: ownerEmployee!.id, project_id: project.id, task_id: null, ticket_id: null,
    date: new Date().toISOString().slice(0, 10), minutes: 15, description: `Owner self approval ${run}`, request_id: randomUUID(),
  }), 201)
  const submitted = await body<{ id: number, version: number }>(await api(page, `companies/${companyId}/erp/timesheets/${draft.id}/actions/`, 'POST', {
    action: 'submit', expected_version: draft.version,
  }))
  const approved = await body<{ status: string }>(await api(page, `companies/${companyId}/erp/timesheets/${submitted.id}/actions/`, 'POST', {
    action: 'approve', expected_version: submitted.version,
  }))
  expect(approved.status).toBe('approved')
})

test('admin creates a ticket task, approves another user’s time, and can use settings and team', async ({ page }) => {
  await login(page, users.alphaAdmin)
  const companyId = await company(page, 'Browser Test Alpha')
  const { contact, project } = await fixtureCatalog(page, companyId)
  const ticket = await body<{ id: number, version: number }>(await api(page, `companies/${companyId}/erp/helpdesk/`, 'POST', {
    title: `Admin ticket ${run}`, contact_id: contact.id, project_id: project.id, priority: 'normal', request_id: randomUUID(),
  }), 201)
  const tasked = await body<{ task_id: number | null }>(await api(page, `companies/${companyId}/erp/helpdesk/${ticket.id}/actions/`, 'POST', { action: 'create_task', expected_version: ticket.version }))
  expect(tasked.task_id).toBeTruthy()
  expect(ownerSubmittedTime, 'owner workflow must create submitted time').toBeTruthy()
  const approved = await body<{ status: string }>(await api(page, `companies/${companyId}/erp/timesheets/${ownerSubmittedTime!.id}/actions/`, 'POST', { action: 'approve', expected_version: ownerSubmittedTime!.version }))
  expect(approved.status).toBe('approved')
  const settings = await body<{ currency: string }>(await api(page, `companies/${companyId}/erp/settings/`))
  expect(settings.currency).toMatch(/^[A-Z]{3}$/)
  const team = await body<{ members: Array<{ email: string }> }>(await api(page, `companies/${companyId}/members/`))
  expect(team.members.map(item => item.email)).toContain(users.alphaOwner)
  await page.goto('/team')
  await expect(page.getByRole('heading', { name: 'Your team.' })).toBeVisible()
})

test('admin cannot create or edit privileged roles and has no access-rights endpoint', async ({ page }) => {
  await login(page, users.alphaAdmin)
  const companyId = await company(page, 'Browser Test Alpha')
  const members = await body<{ members: Array<{ id: number, email: string }> }>(await api(page, `companies/${companyId}/members/`))
  const owner = members.members.find(item => item.email === users.alphaOwner)!
  const createOwner = await api(page, `companies/${companyId}/members/`, 'POST', { email: users.bravoOwner, role: 'owner' })
  expect(createOwner.status()).toBe(403)
  const createAdmin = await api(page, `companies/${companyId}/members/`, 'POST', { email: users.bravoOwner, role: 'admin' })
  expect(createAdmin.status()).toBe(403)
  const editOwner = await api(page, `companies/${companyId}/members/${owner.id}/`, 'PATCH', { role: 'member', is_active: true })
  expect(editOwner.status()).toBe(403)
  const accessRights = await api(page, `companies/${companyId}/access-rights/`)
  expect(accessRights.status()).toBe(404)
})

test('alpha and bravo users cannot read one another’s company records', async ({ page }) => {
  await login(page, users.alphaOwner)
  const alpha = await company(page, 'Browser Test Alpha')
  await login(page, users.bravoOwner)
  const bravo = await company(page, 'Browser Test Bravo')
  bravoId = bravo
  const bravoToAlpha = await api(page, `companies/${alpha}/erp/contacts/`)
  expect(bravoToAlpha.status()).toBe(404)
  await login(page, users.alphaOwner)
  const alphaToBravo = await api(page, `companies/${bravoId}/erp/contacts/`)
  expect(alphaToBravo.status()).toBe(404)
})
