import assert from 'node:assert/strict'

export async function verifyAccounting({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId, secondCompanyId, seedAccountingHistory, results }) {
  const base = `companies/${companyId}/erp/`
  async function ready() { await until(() => evaluate('!document.querySelector(".loading-state") && Boolean(document.querySelector(".accounting-policy"))'), 'accounting data') }
  async function press(text, selector = 'button') {
    await evaluate(`(() => { const button = [...document.querySelectorAll(${JSON.stringify(selector)})].find(item => item.textContent.trim() === ${JSON.stringify(text)}); if (!button) throw new Error('Missing ' + ${JSON.stringify(text)}); button.click(); })()`)
  }
  async function create(resource, body) {
    const result = await browserAPI(base + resource + '/', 'POST', body)
    assert.equal(result.status, 201, JSON.stringify(result.data)); return result.data
  }
  async function invoice(kind, price) {
    let order = await create('orders', { kind, contact_id: partner.id, lines: [{ product_id: product.id, quantity: '1', unit_price: price, tax_rate: '7' }] })
    let response = await browserAPI(base + `orders/${order.id}/actions/`, 'POST', { action: 'confirm', expected_version: order.version })
    assert.equal(response.status, 200); order = response.data
    response = await browserAPI(base + `orders/${order.id}/actions/`, 'POST', { action: 'invoice', expected_version: order.version })
    assert.equal(response.status, 200); return response.data
  }
  const partner = await create('contacts', { name: 'Accounting phase partner', is_customer: true, is_supplier: true })
  const product = await create('products', { name: 'Accounting phase service', sku: 'ACCOUNTING-SERVICE', kind: 'service' })
  const draft = await invoice('sale', '200')
  await navigate(`/invoicing/${draft.id}`)
  await until(() => evaluate('Boolean(document.querySelector(".invoice-sheet"))'), 'draft accounting invoice')
  await press('Issue invoice', '.document-actions button')
  await until(() => evaluate('document.querySelector(".erp-status-bar [aria-current=step]")?.getAttribute("data-value") === "issued"'), 'invoice posting')
  let issued = (await browserAPI(base + `invoices/${draft.id}/`)).data
  assert.equal(issued.journal_entry_count, 1)
  const first = (await browserAPI(base + `accounting/entries/?invoice_id=${draft.id}`)).data.results[0]
  assert.equal(Number(first.lines.find(line => line.account_code === '1100').debit), 214)
  assert.equal(Number(first.lines.find(line => line.account_code === '4000').credit), 200)
  assert.equal(Number(first.lines.find(line => line.account_code === '2100').credit), 14)
  await click(`.document-actions a[href="/sales/${draft.order_id}"]`)
  await until(() => evaluate('Boolean(document.querySelector(".process-summary"))'), 'order accounting summary')
  assert.equal(await evaluate('document.querySelector(".process-summary").textContent.includes("214.00")'), true)
  await click('.process-summary a[href^="/accounting"]')
  await ready()
  assert.equal(await evaluate('document.querySelectorAll(".journal-entry").length'), 1)
  await click('.journal-entry summary')
  assert.equal(await evaluate('document.querySelector(".journal-entry[open]").textContent.includes("Accounts receivable")'), true)
  assert.equal(await evaluate(`Boolean(document.querySelector('.journal-entry a[href="/invoicing/${draft.id}"]'))`), true)
  results.push('Invoice issue posts balanced receivable, revenue and tax entries; orders, invoices and journals link in both directions.')

  const token = await evaluate('crypto.randomUUID()')
  for (let retry = 0; retry < 2; retry++) {
    assert.equal((await browserAPI(base + `invoices/${draft.id}/payments/`, 'POST', { amount: '50', method: 'cash', request_id: token })).status, 200)
  }
  await navigate(`/accounting?invoice_id=${draft.id}`); await ready()
  assert.equal(await evaluate('document.querySelectorAll(".journal-entry").length'), 2)
  const paymentEntries = (await browserAPI(base + `accounting/entries/?invoice_id=${draft.id}`)).data.results
  assert.equal(paymentEntries.filter(entry => entry.kind === 'payment').length, 1)
  const payment = paymentEntries.find(entry => entry.kind === 'payment')
  assert.equal(Number(payment.lines.find(line => line.account_code === '1010').debit), 50)
  assert.equal(Number(payment.lines.find(line => line.account_code === '1100').credit), 50)
  results.push('Partial cash payment clears receivables in the ledger; retrying the same payment creates one posting.')

  const bill = await invoice('purchase', '80')
  await navigate(`/invoicing/${bill.id}`)
  await until(() => evaluate('Boolean(document.querySelector(".invoice-sheet"))'), 'vendor bill')
  await press('Confirm bill', '.document-actions button')
  await until(() => evaluate('document.querySelector(".erp-status-bar [aria-current=step]")?.getAttribute("data-value") === "issued"'), 'vendor posting')
  await evaluate('window.confirm = () => true')
  await press('Cancel', '.document-actions button')
  await until(() => evaluate('document.querySelector(".erp-status-bar [aria-current=step]")?.getAttribute("data-value") === "cancelled"'), 'bill reversal')
  await click('.document-actions a[href^="/accounting"]'); await ready()
  const reversals = (await browserAPI(base + `accounting/entries/?invoice_id=${bill.id}`)).data.results
  assert.equal(reversals.length, 2)
  assert.equal(reversals.filter(entry => entry.kind === 'reversal').length, 1)
  assert.equal(await evaluate('document.querySelector(".journal-entry").parentElement.textContent.includes("Reversed")'), true)
  results.push('Cancelling an unpaid vendor bill creates a linked reversing entry and retains the original journal.')

  const historical = await invoice('sale', '30')
  seedAccountingHistory(companyId, historical.id)
  await navigate('/accounting'); await ready()
  assert.equal(await evaluate('Boolean(document.querySelector(".accounting-missing"))'), true)
  await press('Import historical postings')
  await until(() => evaluate('!document.querySelector(".loading-state") && !document.querySelector(".accounting-missing") && Boolean(document.querySelector(".trial-balance"))'), 'historical accounting import')
  assert.equal((await browserAPI(base + `invoices/${historical.id}/`)).data.journal_entry_count, 1)
  assert.equal((await browserAPI(base + 'accounting/sync/', 'POST', {})).data.created, 0)
  results.push('Existing issued documents show incomplete-report notice; importing history creates the missing posting and safely retries.')

  await navigate('/accounting'); await ready()
  const report = (await browserAPI(base + 'accounting/reports/')).data
  assert.equal(Number(report.debit), Number(report.credit))
  assert.equal(Number(report.closing_debit), Number(report.closing_credit))
  assert.equal(Number(report.balance_check), 0)
  assert.equal(report.unposted_invoices + report.unposted_payments, 0)
  await send('Browser.setDownloadBehavior', { behavior: 'deny' })
  await evaluate('window.__accountingDownloads = []; window.__accountingCreateURL = URL.createObjectURL; URL.createObjectURL = blob => { window.__accountingDownloads.push(blob); return window.__accountingCreateURL(blob) }')
  await press('Export CSV', '.trial-balance button')
  await until(() => evaluate('window.__accountingDownloads.length === 1'), 'trial balance download')
  const csv = await evaluate('window.__accountingDownloads[0].text()')
  assert.match(csv, /"1100","Accounts receivable"/)
  assert.match(csv, /"5000","Purchases expense"/)
  assert.equal(csv.trim().split('\r\n').length, 10)
  assert.equal(csv.trim().split('\r\n').at(-1).includes(String(report.debit)), true)
  assert.deepEqual(await evaluate('(async () => [...new Uint8Array(await window.__accountingDownloads[0].arrayBuffer()).slice(0, 3)])()'), [239, 187, 191])
  await evaluate('URL.createObjectURL = window.__accountingCreateURL')
  await press('1000 Bank', '.trial-balance button'); await ready()
  assert.equal(await evaluate('document.querySelector("select[name=ledger_account]").value'), '1000')
  await navigate('/accounting'); await ready()
  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 1, mobile: true })
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await screenshot('accounting-mobile.png')
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  await screenshot('accounting-reports.png')
  assert.equal((await browserAPI(`companies/${secondCompanyId}/erp/accounting/entries/?invoice_id=${draft.id}`)).status, 404)
  const second = (await browserAPI(`companies/${secondCompanyId}/erp/accounting/reports/`)).data
  assert.equal(Number(second.debit), 0)
  results.push('Trial balance and balance sheet reconcile; CSV export, account drill-down, source isolation and 375px reports work.')

  const closedDate = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  await press('Close dates')
  await until(() => evaluate('Boolean(document.querySelector("dialog[open] input[name=locked_through]"))'), 'accounting lock dialog')
  await fill('dialog[open] input[name=locked_through]', closedDate)
  await press('Close dates permanently', 'dialog[open] button')
  await until(() => evaluate('!document.querySelector("dialog[open]") && document.querySelector(".accounting-policy")?.textContent.includes("Locked through")'), 'posting lock')
  const backdated = await invoice('sale', '10')
  const changed = await browserAPI(base + `invoices/${backdated.id}/`, 'PATCH', { date: closedDate, expected_version: backdated.version })
  assert.equal(changed.status, 200)
  await navigate(`/invoicing/${backdated.id}`)
  await until(() => evaluate('Boolean(document.querySelector(".invoice-sheet"))'), 'backdated invoice')
  await press('Issue invoice', '.document-actions button')
  await until(() => evaluate('document.querySelector(".notice.error")?.textContent.includes("Accounting is locked")'), 'closed-date rejection')
  const unchanged = (await browserAPI(base + `invoices/${backdated.id}/`)).data
  assert.equal(unchanged.status, 'draft'); assert.equal(unchanged.journal_entry_count, 0)
  results.push('Owner posting-date lock persists; a closed-date issue fails without changing the draft or creating ledger entries.')
}

export async function verifyAccountingReadOnly({ evaluate, navigate, until, browserAPI, companyId, results }) {
  await navigate('/accounting')
  await until(() => evaluate('Boolean(document.querySelector(".trial-balance"))'), 'member accounting reports')
  assert.equal(await evaluate('[...document.querySelectorAll("button")].some(button => button.textContent.trim() === "Close dates")'), false)
  assert.equal((await browserAPI(`companies/${companyId}/erp/accounting/sync/`, 'POST', {})).status, 403)
  assert.equal((await browserAPI(`companies/${companyId}/erp/accounting/settings/`, 'PATCH', {})).status, 403)
  results.push('Members can read financial reports while accounting imports and date locks remain protected.')
}
