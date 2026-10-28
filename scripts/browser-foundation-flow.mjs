import assert from 'node:assert/strict'

async function press(evaluate, text, selector) {
  await evaluate(`(() => { const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find(item => item.textContent.trim() === ${JSON.stringify(text)}); if (!el) throw new Error('Missing action'); el.click(); })()`)
}

export async function verifyDraftOrder(ctx, orderId, kind) {
  const { evaluate, fill, click, until, browserAPI, companyId, secondCompanyId } = ctx
  const endpoint = `companies/${companyId}/erp/orders/${orderId}/`
  const original = (await browserAPI(endpoint)).data
  const quantity = Number(original.lines[0].quantity) + 1
  const price = Number(original.lines[0].unit_price) + 5
  await fill('input[name=quantity_0]', String(quantity))
  await fill('input[name=price_0]', String(price))
  await press(evaluate, kind === 'sale' ? 'Confirm sale' : 'Confirm purchase', '.document-actions button')
  await until(() => evaluate('document.querySelector(".notice.error")?.textContent.includes("Save or discard")'), 'dirty order transition guard')
  assert.equal((await browserAPI(endpoint)).data.status, 'draft')
  assert.equal(Number((await browserAPI(endpoint)).data.total), Number(original.total))

  if (kind === 'sale') {
    assert.equal(await evaluate("(() => { const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); return event.defaultPrevented })()"), true)
    await evaluate('window.__originalConfirm = window.confirm; window.__discardChecks = 0; window.confirm = () => { window.__discardChecks++; return false }')
    try {
      await click('nav a[href="/"]')
      await until(() => evaluate('window.__discardChecks >= 1'), 'route-leave guard')
      assert.equal(await evaluate('location.pathname'), `/sales/${orderId}`)
      await fill('.company-picker select', String(secondCompanyId))
      await until(() => evaluate('window.__discardChecks >= 2'), 'company-change guard')
      await until(() => evaluate(`document.querySelector('.company-picker select').value === '${companyId}'`), 'cancelled company change')
      await click('.account-actions button')
      await until(() => evaluate('window.__discardChecks >= 3'), 'sign-out guard')
      assert.ok((await browserAPI('auth/session/')).data.user)
    } finally { await evaluate('window.confirm = window.__originalConfirm; delete window.__originalConfirm') }
  }
  await click('button[form=order-form]')
  await until(async () => Number((await browserAPI(endpoint)).data.lines[0].quantity) === quantity, 'explicit draft save')
  await until(() => evaluate('Boolean(document.querySelector("input[name=quantity_0]:not(:disabled)"))'), 'saved draft form')
  assert.equal(Number((await browserAPI(endpoint)).data.lines[0].unit_price), price)
  await fill('input[name=quantity_0]', original.lines[0].quantity)
  await fill('input[name=price_0]', original.lines[0].unit_price)
  await click('button[form=order-form]')
  await until(async () => Number((await browserAPI(endpoint)).data.total) === Number(original.total), 'restored draft save')
  await until(() => evaluate('Boolean(document.querySelector("input[name=quantity_0]:not(:disabled)"))'), 'draft ready for confirmation')
}

export async function verifyDraftInvoice(ctx, invoiceId, kind) {
  const { evaluate, fill, click, until, browserAPI, companyId } = ctx
  const endpoint = `companies/${companyId}/erp/invoices/${invoiceId}/`
  const original = (await browserAPI(endpoint)).data
  const date = new Date(`${original.date}T12:00:00Z`)
  date.setUTCDate(date.getUTCDate() - 1)
  const changedDate = date.toISOString().slice(0, 10)
  date.setUTCDate(date.getUTCDate() + 14)
  const dueDate = date.toISOString().slice(0, 10)
  await fill('input[name=invoice_date]', changedDate)
  await fill('input[name=due_date]', dueDate)
  await press(evaluate, kind === 'customer' ? 'Issue invoice' : 'Confirm bill', '.document-actions button')
  await until(() => evaluate('document.querySelector(".notice.error")?.textContent.includes("Save or discard")'), 'dirty invoice guard')
  assert.equal((await browserAPI(endpoint)).data.status, 'draft')
  await click('.control-actions .button-primary')
  await until(async () => (await browserAPI(endpoint)).data.date === changedDate, 'saved invoice date')
  await until(() => evaluate('Boolean(document.querySelector("input[name=invoice_date]:not(:disabled)"))'), 'invoice form ready')
  assert.equal((await browserAPI(endpoint)).data.due_date, dueDate)
}

export async function verifyFoundationLists(ctx) {
  const { evaluate, fill, click, until, navigate, browserAPI, companyId, secondCompanyId, results } = ctx
  async function ready() { await until(() => evaluate('!document.querySelector(".loading-state") && Boolean(document.querySelector(".control-panel"))'), 'list data') }
  const task = (await browserAPI(`companies/${companyId}/erp/tasks/`)).data.results[0]
  const teammate = (await browserAPI(`companies/${companyId}/members/`)).data.members.find(item => item.email.startsWith('browser-member-'))
  assert.equal((await browserAPI(`companies/${companyId}/erp/tasks/${task.id}/`, 'PATCH', { assignee_id: teammate.user_id })).status, 200)
  assert.equal((await browserAPI(`companies/${companyId}/members/${teammate.id}/`, 'PATCH', { is_active: false })).status, 200)
  await navigate('/tasks'); await ready()
  await click('.record-title')
  await until(() => evaluate('Boolean(document.querySelector("dialog[open] fieldset:not(:disabled)"))'), 'task form options')
  assert.ok((await evaluate('document.querySelector("select[name=assignee_id] option:checked").textContent')).includes('(inactive)'))
  await fill('dialog[open] input[name=title]', 'Edited after access was disabled')
  await click('dialog[open] .dialog-footer .button-primary')
  await until(() => evaluate('!document.querySelector("dialog[open]")'), 'task edit with historical inactive relation')
  const changed = (await browserAPI(`companies/${companyId}/erp/tasks/${task.id}/`)).data
  assert.equal(changed.title, 'Edited after access was disabled')
  assert.equal(changed.assignee_id, teammate.user_id)
  assert.equal((await browserAPI(`companies/${companyId}/members/${teammate.id}/`, 'PATCH', { is_active: true })).status, 200)

  for (let i = 0; i < 24; i++) assert.equal((await browserAPI(`companies/${companyId}/erp/contacts/`, 'POST', { name: `Pagination regression ${i}` })).status, 201)
  assert.equal((await browserAPI(`companies/${secondCompanyId}/erp/contacts/`, 'POST', { name: 'Second company contact' })).status, 201)
  await navigate('/contacts'); await ready()
  await until(() => evaluate('Boolean(document.querySelector(".pagination"))'), 'contact pagination')
  await click('.pagination button:last-child')
  await until(() => evaluate('document.querySelectorAll(".record-card").length === 1'), 'second page of contacts')
  await fill('.company-picker select', String(secondCompanyId))
  await until(() => evaluate('!document.querySelector(".loading-state") && !document.querySelector(".company-picker select").disabled && document.querySelectorAll(".record-card").length === 1'), 'company page reset')
  assert.equal(await evaluate('document.querySelector(".record-card h2").textContent'), 'Second company contact')
  await fill('.company-picker select', String(companyId))
  await until(() => evaluate('!document.querySelector(".loading-state") && !document.querySelector(".company-picker select").disabled && document.querySelectorAll(".record-card").length === 24'), 'original company first page')
  results.push('Audit regressions: draft transitions, navigation guards, company pagination, inactive relations, and payment activity retries work.')
  await navigate('/dashboard'); await ready()
}

export async function verifyAuthentication(ctx) {
  const { evaluate, fill, click, until, navigate, browserAPI, signIn, signOut, resetLinkFor, owner, password, results } = ctx
  const changed = `${password}-changed`
  const recovered = `${password}-recovered`
  await navigate('/account')
  await until(() => evaluate('Boolean(document.querySelector("input[name=old_password]"))'), 'account security form')
  await fill('input[name=old_password]', password)
  await fill('input[name=new_password1]', changed)
  await fill('input[name=new_password2]', changed)
  await click('.account-page button[type=submit]')
  await until(() => evaluate('document.querySelector(".notice.success")?.textContent.includes("Password changed")'), 'password change')
  assert.equal((await browserAPI('auth/session/')).data.user.email, owner)
  await signOut()
  await signIn(owner, password)
  await until(() => evaluate('document.querySelector(".login-form .error")?.textContent.includes("incorrect")'), 'old password rejection')
  await until(() => evaluate('!document.querySelector(".login-form button").disabled'), 'sign-in retry ready')
  await signIn(owner, changed)
  await until(() => evaluate('Boolean(document.querySelector(".account-bar"))'), 'new password sign-in')
  await navigate('/forgot-password')
  await until(() => evaluate('Boolean(document.querySelector("input[name=reset_email]"))'), 'recovery form')
  await fill('input[name=reset_email]', owner)
  await click('.recovery-form button[type=submit]')
  await until(() => evaluate('document.querySelector(".notice.success")?.textContent.includes("eligible account")'), 'generic recovery response')
  const link = resetLinkFor(owner)
  await navigate(link)
  await until(() => evaluate('Boolean(document.querySelector(".reset-form input[name=new_password1]")) && !location.hash'), 'reset form and token URL cleanup')
  await fill('input[name=new_password1]', recovered)
  await fill('input[name=new_password2]', recovered)
  await click('.reset-form button[type=submit]')
  await until(() => evaluate('document.querySelector(".notice.success")?.textContent.includes("Password reset")'), 'password reset')
  assert.equal((await browserAPI('auth/session/')).data.user, null)
  await navigate('/login')
  await signIn(owner, recovered)
  await until(() => evaluate('Boolean(document.querySelector(".account-bar"))'), 'recovered account sign-in')
  await navigate(link)
  await until(() => evaluate('Boolean(document.querySelector(".reset-form input[name=new_password1]")) && !location.hash'), 'replayed reset form')
  await fill('input[name=new_password1]', `${password}-invalid-replay`)
  await fill('input[name=new_password2]', `${password}-invalid-replay`)
  await click('.reset-form button[type=submit]')
  await until(() => evaluate('document.querySelector(".notice.error")?.textContent.includes("invalid or expired")'), 'used reset token rejection')
  results.push('Account password change, recovery UI, token URL cleanup, single-use reset, and recovered sign-in work.')
  await navigate('/')
}
