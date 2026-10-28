import assert from 'node:assert/strict'
import { verifyDraftOrder, verifyDraftInvoice, verifyFoundationLists } from './browser-foundation-flow.mjs'

// Shared with the authentication smoke check: all records belong to its temporary company.
export async function verifyERP({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId, secondCompanyId, results }) {
  const foundation = { evaluate, fill, click, navigate, until, browserAPI, companyId, secondCompanyId, results }
  await send('Emulation.setDeviceMetricsOverride', { width: 1365, height: 900, deviceScaleFactor: 1, mobile: false })
  async function ready() { await until(() => evaluate('!document.querySelector(".loading-state") && Boolean(document.querySelector(".control-panel"))'), 'module data') }
  async function openNew() {
    await click('.control-actions .button-primary')
    await until(() => evaluate('Boolean(document.querySelector("dialog[open] fieldset:not(:disabled)"))'), 'record form and its options')
  }
  async function saveDialog() {
    await click('dialog[open] .dialog-footer .button-primary')
    await until(() => evaluate('!document.querySelector("dialog[open]")'), 'saved record')
  }
  async function buttonText(text, selector = '.document-actions button') {
    await evaluate(`(() => { const button = [...document.querySelectorAll(${JSON.stringify(selector)})].find(el => el.textContent.trim() === ${JSON.stringify(text)}); if (!button) throw new Error('Missing button: ' + ${JSON.stringify(text)}); button.click(); })()`)
  }

  await navigate('/')
  await until(() => evaluate('document.querySelectorAll(".launcher-tile").length === 10'), 'ten live applications')
  await fill('input[aria-label="Search applications"]', 'inventory')
  await until(() => evaluate('document.querySelectorAll(".launcher-tile").length === 1'), 'app search')
  await fill('input[aria-label="Search applications"]', '')
  await screenshot('erp-apps-desktop.png')

  await click('.launcher-tile[href="/contacts"]')
  await ready(); await openNew()
  await fill('dialog[open] input[name=name]', 'Browser customer')
  await fill('dialog[open] input[name=email]', 'customer@example.test')
  await click('dialog[open] input[name=is_supplier]')
  await saveDialog()
  await until(() => evaluate('document.querySelectorAll(".record-card").length === 1'), 'customer card')
  const contact = (await browserAPI(`companies/${companyId}/erp/contacts/`)).data.results[0]

  await navigate('/inventory'); await ready(); await openNew()
  await fill('dialog[open] input[name=name]', 'Browser desk')
  await fill('dialog[open] input[name=sku]', 'BROWSER-DESK')
  await fill('dialog[open] input[name=sale_price]', '25')
  await fill('dialog[open] input[name=cost_price]', '10')
  await saveDialog()
  await until(() => evaluate('document.querySelectorAll(".record-card").length === 1'), 'product card')
  const product = (await browserAPI(`companies/${companyId}/erp/products/`)).data.results[0]

  await navigate('/crm'); await ready(); await openNew()
  await fill('dialog[open] input[name=title]', 'Browser office opportunity')
  await fill('dialog[open] select[name=contact_id]', String(contact.id))
  await fill('dialog[open] input[name=expected_revenue]', '500')
  await saveDialog()
  await until(() => evaluate('document.querySelectorAll(".kanban-card").length === 1'), 'pipeline card')
  await fill('.kanban-card select', 'qualified')
  await until(async () => (await browserAPI(`companies/${companyId}/erp/opportunities/`)).data.results[0].stage === 'qualified', 'saved pipeline stage')
  await until(() => evaluate('document.querySelectorAll(".kanban-card").length === 1'), 'reloaded pipeline')
  await screenshot('erp-crm-desktop.png')
  results.push('The launcher filters ten live apps; contacts, products, and CRM records save through their forms.')

  await navigate('/inventory/movements'); await ready()
  await click('.control-panel .button-primary')
  await until(() => evaluate('document.querySelectorAll("select[name=stock_product] option").length === 2'), 'stock product choices')
  await fill('select[name=stock_product]', String(product.id))
  await fill('input[name=stock_quantity]', '10')
  await fill('input[name=stock_reason]', 'Browser opening stock')
  await saveDialog()

  await navigate('/sales/new')
  await until(() => evaluate('document.querySelectorAll("select[name=contact_id] option").length === 2'), 'quotation choices')
  await fill('select[name=contact_id]', String(contact.id))
  await fill('select[name=product_0]', String(product.id))
  await fill('input[name=quantity_0]', '2')
  await fill('input[name=tax_0]', '7')
  await click('button[form=order-form]')
  await until(() => evaluate('location.pathname.startsWith("/sales/") && !location.pathname.endsWith("new") && Boolean(document.querySelector(".document-actions"))'), 'saved quotation')
  const order = (await browserAPI(`companies/${companyId}/erp/orders/?kind=sale`)).data.results[0]
  assert.equal(Number(order.total), 53.5)
  await verifyDraftOrder(foundation, order.id, 'sale')
  await buttonText('Confirm sale')
  await until(() => evaluate('document.querySelector(".state-label")?.textContent === "confirmed"'), 'confirmed order')
  await buttonText('Validate delivery')
  await until(async () => Boolean((await browserAPI(`companies/${companyId}/erp/orders/${order.id}/`)).data.fulfilled_at), 'delivery')
  await until(() => evaluate('document.querySelector(".document-actions")?.textContent.includes("Delivered")'), 'delivery rendered')
  await buttonText('Create invoice')
  await until(() => evaluate('location.pathname.startsWith("/invoicing/") && Boolean(document.querySelector(".invoice-sheet"))'), 'created invoice')
  const invoice = (await browserAPI(`companies/${companyId}/erp/invoices/`)).data.results[0]
  await verifyDraftInvoice(foundation, invoice.id, 'customer')
  await buttonText('Issue invoice')
  await until(() => evaluate('document.querySelector(".state-label")?.textContent === "issued"'), 'issued invoice')
  await buttonText('Register payment')
  await fill('input[name=payment_amount]', '20')
  await saveDialog()
  await until(async () => Number((await browserAPI(`companies/${companyId}/erp/invoices/${invoice.id}/`)).data.paid_amount) === 20, 'partial payment')
  await until(() => evaluate('Boolean(document.querySelector(".payments-history"))'), 'payment rendered')
  const partial = (await browserAPI(`companies/${companyId}/erp/invoices/${invoice.id}/`)).data.payments[0]
  const retry = await browserAPI(`companies/${companyId}/erp/invoices/${invoice.id}/payments/`, 'POST', {
    request_id: partial.request_id, amount: partial.amount, date: partial.date, method: partial.method, reference: partial.reference,
  })
  assert.equal(retry.status, 200)
  assert.equal(retry.data.payments.length, 1)
  assert.equal((await browserAPI(`companies/${companyId}/erp/dashboard/`)).data.activities.filter(item => item.summary.startsWith('Payment ')).length, 1)
  await buttonText('Register payment')
  await saveDialog()
  await until(() => evaluate('document.querySelector(".state-label")?.textContent === "paid"'), 'paid invoice')
  assert.equal(Number((await browserAPI(`companies/${companyId}/erp/products/${product.id}/`)).data.stock_quantity), 8)
  await evaluate('window.print = () => { window.__printInvoked = true }')
  await buttonText('Print / PDF', '.control-actions button')
  assert.equal(await evaluate('window.__printInvoked'), true)
  await screenshot('erp-invoice-desktop.png')
  results.push('A quotation confirms, delivers stock, creates an invoice, accepts partial/full payments, and invokes printing.')

  await navigate('/purchase/new')
  await until(() => evaluate('document.querySelectorAll("select[name=contact_id] option").length === 2'), 'RFQ choices')
  await fill('select[name=contact_id]', String(contact.id))
  await fill('select[name=product_0]', String(product.id))
  await fill('input[name=quantity_0]', '5')
  await click('button[form=order-form]')
  await until(() => evaluate('Boolean(document.querySelector(".document-actions"))'), 'saved RFQ')
  const purchase = (await browserAPI(`companies/${companyId}/erp/orders/?kind=purchase`)).data.results[0]
  await verifyDraftOrder(foundation, purchase.id, 'purchase')
  await buttonText('Confirm purchase')
  await until(() => evaluate('document.querySelector(".state-label")?.textContent === "confirmed"'), 'confirmed purchase')
  await buttonText('Receive products')
  await until(() => evaluate('document.querySelector(".document-actions")?.textContent.includes("Received")'), 'purchase receipt')
  await buttonText('Create bill')
  await until(() => evaluate('location.pathname.startsWith("/invoicing/") && Boolean(document.querySelector(".invoice-sheet"))'), 'vendor bill')
  const bill = (await browserAPI(`companies/${companyId}/erp/invoices/?kind=vendor`)).data.results[0]
  await verifyDraftInvoice(foundation, bill.id, 'vendor')
  await buttonText('Confirm bill')
  await until(() => evaluate('document.querySelector(".state-label")?.textContent === "issued"'), 'issued bill')
  assert.equal(Number((await browserAPI(`companies/${companyId}/erp/products/${product.id}/`)).data.stock_quantity), 13)
  results.push('The purchasing UI confirms RFQs, receives products, and creates vendor bills.')

  await navigate('/projects'); await ready(); await openNew()
  await fill('dialog[open] input[name=name]', 'Browser project')
  await saveDialog()
  await until(() => evaluate('Boolean(document.querySelector(".record-card-footer a"))'), 'project tasks link')
  await click('.record-card-footer a')
  await ready(); await openNew()
  await fill('dialog[open] input[name=title]', 'Browser task')
  await saveDialog()
  await until(() => evaluate('document.querySelectorAll(".kanban-card").length === 1'), 'task card')
  await fill('.kanban-card select', 'in_progress')
  await until(async () => (await browserAPI(`companies/${companyId}/erp/tasks/`)).data.results[0].stage === 'in_progress', 'task stage')
  await navigate('/dashboard')
  await until(() => evaluate('document.querySelectorAll(".metric-card").length === 4'), 'business dashboard')
  const stats = (await browserAPI(`companies/${companyId}/erp/dashboard/`)).data
  assert.equal(Number(stats.sales_total), 53.5)
  assert.equal(Number(stats.receivable), 0)
  assert.equal(Number(stats.payable), 50)
  assert.equal(stats.open_tasks, 1)
  await screenshot('erp-dashboard-desktop.png')
  await verifyFoundationLists(foundation)
  results.push('Projects and task stages persist; dashboard totals reflect the real sales, payments, and vendor bill.')

  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 1, mobile: true })
  for (const endpoint of ['/', '/contacts', '/crm', `/sales/${order.id}`, `/invoicing/${invoice.id}`, '/inventory', '/inventory/movements', '/tasks', '/dashboard']) {
    await navigate(endpoint)
    if (endpoint !== '/') await ready()
    assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true, `Mobile overflow on ${endpoint}`)
  }
  await screenshot('erp-dashboard-mobile.png')
  results.push('All core ERP screens fit a 375px mobile viewport; wide tables and boards scroll internally.')
  await fill('.company-picker select', String(secondCompanyId))
  await until(() => evaluate('Boolean(document.querySelector(".metrics-grid")) && !document.querySelector(".company-picker select").disabled'), 'second company dashboard')
  assert.equal(Number((await browserAPI(`companies/${secondCompanyId}/erp/dashboard/`)).data.sales_total), 0)
  assert.equal(await evaluate('document.querySelectorAll(".activity-item").length'), (await browserAPI(`companies/${secondCompanyId}/erp/dashboard/`)).data.activities.length)
  await fill('.company-picker select', String(companyId))
  await until(() => evaluate('Boolean(document.querySelector(".metrics-grid")) && !document.querySelector(".company-picker select").disabled'), 'restored company dashboard')
  await until(() => evaluate('document.querySelectorAll(".activity-item").length > 0'), 'restored company activities')
  results.push('Switching companies clears business data and restores only the selected company’s records.')
  await navigate('/')
}
