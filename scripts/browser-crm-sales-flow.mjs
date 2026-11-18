import assert from 'node:assert/strict'

export async function verifyCRMSales({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId, results }) {
  const base = `companies/${companyId}/erp/`
  async function ready() { await until(() => evaluate('!document.querySelector(".loading-state") && Boolean(document.querySelector(".control-panel"))'), 'CRM/Sales page') }
  async function press(text, selector = '.document-actions button') {
    await evaluate(`(() => { const button = [...document.querySelectorAll(${JSON.stringify(selector)})].find(item => item.textContent.trim() === ${JSON.stringify(text)}); if (!button) throw new Error('Missing action: ' + ${JSON.stringify(text)}); button.click(); })()`)
  }
  async function create(resource, body) {
    const response = await browserAPI(base + resource + '/', 'POST', body)
    assert.equal(response.status, 201, JSON.stringify(response.data))
    return response.data
  }
  const contact = await create('contacts', { name: 'CRM linked customer', email: 'linked@example.test' })
  const product = await create('products', { name: 'CRM consultation', sku: 'CRM-LINKED', kind: 'service', sale_price: '10' })
  const opportunity = await create('opportunities', { title: 'Connected CRM deal', contact_id: contact.id, stage: 'qualified', notes: 'Scope agreed with the customer' })
  const quoteList = `orders/?kind=sale&opportunity_id=${opportunity.id}`

  await navigate(`/crm?opportunity_id=${opportunity.id}`); await ready()
  await until(() => evaluate('document.querySelectorAll(".kanban-card").length === 1'), 'linked opportunity')
  await click(`.crm-links a[href="/sales/new?opportunity_id=${opportunity.id}"]`)
  await until(() => evaluate('Boolean(document.querySelector("select[name=product_0]"))'), 'quotation from CRM')
  assert.equal(await evaluate('document.querySelector("select[name=contact_id]").value'), String(contact.id))
  assert.equal(await evaluate('document.querySelector("textarea[name=notes]").value'), opportunity.notes)
  assert.equal((await browserAPI(base + quoteList)).data.count, 0)
  await fill('select[name=product_0]', String(product.id))
  await click('button[form=order-form]')
  await until(() => evaluate('Boolean(document.querySelector(".document-actions")) && !location.pathname.endsWith("new")'), 'linked quotation saved')
  const order = (await browserAPI(base + quoteList)).data.results[0]
  assert.equal(order.opportunity_id, opportunity.id)
  assert.equal((await browserAPI(base + `opportunities/${opportunity.id}/`)).data.stage, 'qualified')
  await click('.opportunity-context a')
  await ready()
  await until(() => evaluate('document.querySelector(".crm-links")?.textContent.includes("(1)")'), 'CRM quotation count')
  await click(`.crm-links a[href="/sales?opportunity_id=${opportunity.id}"]`)
  await ready()
  assert.equal(await evaluate('document.querySelectorAll(".data-table tbody tr").length'), 1)
  assert.equal(await evaluate('document.querySelector(".control-actions a.button-primary").getAttribute("href")'), `/sales/new?opportunity_id=${opportunity.id}`)
  await click(`a[href="/sales/${order.id}"]`); await ready()
  results.push('CRM opens a prefilled quotation without creating an empty order; saved quotations have company-scoped links and counts in both apps.')

  const detail = (await browserAPI(base + `orders/${order.id}/`)).data
  const concurrent = await browserAPI(base + `orders/${order.id}/`, 'PATCH', {
    expected_version: detail.version, lines: [{ id: detail.lines[0].id, product_id: product.id, quantity: '1', unit_price: '100' }],
  })
  assert.equal(concurrent.status, 200)
  await press('Confirm sale')
  await until(() => evaluate('document.querySelector(".notice.error")?.textContent.includes("another session")'), 'stale confirmation rejected')
  assert.equal((await browserAPI(base + `orders/${order.id}/`)).data.status, 'draft')
  await press('Reload document', '.notice.error button'); await ready()
  await until(() => evaluate('document.querySelector("input[name=price_0]")?.value === "100.00"'), 'latest quotation values')
  await press('Confirm sale')
  await until(() => evaluate('document.querySelector(".erp-status-bar [aria-current=step]")?.getAttribute("data-value") === "confirmed"'), 'reviewed quotation confirmed')
  results.push('A stale quotation cannot confirm unseen totals; Reload document displays the latest values before confirmation.')

  await press('Create invoice')
  await until(() => evaluate('Boolean(document.querySelector(".invoice-sheet"))'), 'CRM sales invoice')
  const invoice = (await browserAPI(base + `orders/${order.id}/`)).data.invoice_id
  await press('Issue invoice')
  await until(() => evaluate('document.querySelector(".erp-status-bar [aria-current=step]")?.getAttribute("data-value") === "issued"'), 'invoice issued')
  await evaluate('window.__crmOriginalConfirm = window.confirm; window.confirm = () => true')
  try {
    await press('Cancel')
    await until(() => evaluate('document.querySelector(".erp-status-bar [aria-current=step]")?.getAttribute("data-value") === "cancelled"'), 'invoice cancelled')
    await press('Return to draft')
    await until(() => evaluate('document.querySelector(".erp-status-bar [aria-current=step]")?.getAttribute("data-value") === "draft"'), 'cancelled invoice restored')
  } finally { await evaluate('window.confirm = window.__crmOriginalConfirm; delete window.__crmOriginalConfirm') }
  await fill('textarea', 'Corrected invoice terms')
  await press('Save', '.control-actions button')
  await until(async () => (await browserAPI(base + `invoices/${invoice}/`)).data.notes === 'Corrected invoice terms', 'corrected invoice saved')
  await until(() => evaluate('!document.querySelector(".loading-state") && Boolean(document.querySelector(".invoice-sheet"))'), 'invoice ready')
  await press('Issue invoice')
  await until(() => evaluate('document.querySelector(".erp-status-bar [aria-current=step]")?.getAttribute("data-value") === "issued"'), 'corrected invoice reissued')
  assert.equal((await browserAPI(base + `invoices/${invoice}/`)).data.id, invoice)
  results.push('An unpaid cancelled invoice returns to Draft, retains its number/history, and accepts corrections and reissue.')

  const archivedOrder = await create('orders', { kind: 'sale', contact_id: contact.id,
    lines: [{ product_id: product.id, quantity: '1' }] })
  assert.equal((await browserAPI(base + `contacts/${contact.id}/`, 'PATCH', { is_active: false })).status, 200)
  assert.equal((await browserAPI(base + `products/${product.id}/`, 'PATCH', { is_active: false })).status, 200)
  await navigate(`/sales/${archivedOrder.id}`); await ready()
  assert.ok((await evaluate('document.querySelector("select[name=contact_id] option:checked").textContent')).includes('(archived)'))
  assert.ok((await evaluate('document.querySelector("select[name=product_0] option:checked").textContent')).includes('(archived)'))
  await fill('textarea[name=notes]', 'Updated after archiving')
  await click('button[form=order-form]')
  await until(async () => (await browserAPI(base + `orders/${archivedOrder.id}/`)).data.notes === 'Updated after archiving', 'quotation notes with archived relations')
  await until(() => evaluate('!document.querySelector(".loading-state") && Boolean(document.querySelector("input[name=price_0]"))'), 'archived quotation ready')
  await fill('input[name=price_0]', '15')
  await click('button[form=order-form]')
  await until(async () => Number((await browserAPI(base + `orders/${archivedOrder.id}/`)).data.total) === 15, 'retained archived line edited')
  results.push('Archived customers/products remain visible on draft quotations; notes and retained line edits save successfully.')

  await navigate('/crm?stage=qualified'); await ready()
  await fill('select[aria-label="Opportunity stage"]', '')
  await until(() => evaluate('!location.search.includes("stage=") && !document.querySelector(".loading-state")'), 'CRM stage filter cleared')
  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 1, mobile: true })
  await navigate(`/crm?opportunity_id=${opportunity.id}`); await ready()
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await screenshot('crm-linked-quotations-mobile.png')
  results.push('CRM stage filters can be cleared and linked quotation actions fit the mobile viewport.')
  await send('Emulation.setDeviceMetricsOverride', { width: 1365, height: 900, deviceScaleFactor: 1, mobile: false })
  await navigate('/')
}
