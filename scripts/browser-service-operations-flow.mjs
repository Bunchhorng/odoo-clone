import assert from 'node:assert/strict'

export async function verifyServiceOperations({ send, evaluate, fill, click, screenshot, navigate, until, browserAPI, companyId, secondCompanyId, owner, teammate, results }) {
  const base = `companies/${companyId}/erp/`
  async function ready() { await until(() => evaluate('!document.querySelector(".loading-state") && Boolean(document.querySelector(".control-panel"))'), 'service app data') }
  async function press(text, selector = 'button') {
    await evaluate(`(() => { const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find(item => item.textContent.trim() === ${JSON.stringify(text)}); if (!el) throw new Error('Missing ' + ${JSON.stringify(text)}); el.click(); })()`)
  }
  async function create(resource, body) {
    const result = await browserAPI(base + resource + '/', 'POST', body)
    assert.equal(result.status, 201, JSON.stringify(result.data)); return result.data
  }
  async function saveDialog(text = 'Save') {
    await press(text, 'dialog[open] .dialog-footer button')
    await until(() => evaluate('!document.querySelector("dialog[open]") && !document.querySelector(".loading-state")'), 'service form saved')
  }
  async function rowAction(description, action) {
    await evaluate(`(() => { const row = [...document.querySelectorAll('.timesheet-table tbody tr')].find(row => row.textContent.includes(${JSON.stringify(description)})); const button = [...(row?.querySelectorAll('button') || [])].find(button => button.textContent.trim() === ${JSON.stringify(action)}); if (!button) throw new Error('Missing time action ' + ${JSON.stringify(action)}); button.click(); })()`)
  }
  async function timeStatus(description, status) { await until(() => evaluate(`(() => { const row = [...document.querySelectorAll('.timesheet-table tbody tr')].find(row => row.textContent.includes(${JSON.stringify(description)})); return row?.querySelector('.badge')?.textContent === ${JSON.stringify(status)} })()`), 'time status ' + status) }
  const members = (await browserAPI(`companies/${companyId}/members/`)).data.members
  const ownerUser = members.find(item => item.email === owner), memberUser = members.find(item => item.email === teammate)
  await navigate('/employees/departments'); await ready(); await press('New', '.control-actions button')
  await until(() => evaluate('Boolean(document.querySelector("dialog[open] input[name=name]"))'), 'department form')
  await fill('dialog[open] input[name=name]', 'Service operations'); await saveDialog()
  const department = (await browserAPI(base + 'departments/?q=Service%20operations')).data.results[0]
  await navigate('/employees'); await ready(); await press('New', '.control-actions button')
  await until(() => evaluate('Boolean(document.querySelector("dialog[open] fieldset:not(:disabled) select[name=user_id] option[value]"))'), 'employee options')
  await fill('dialog[open] input[name=name]', 'Service phase lead')
  await fill('dialog[open] input[name=employee_code]', 'service-lead')
  await fill('dialog[open] input[name=job_title]', 'Service lead')
  await fill('dialog[open] input[name=work_email]', owner)
  await fill('dialog[open] select[name=department_id]', String(department.id))
  await fill('dialog[open] select[name=user_id]', String(ownerUser.user_id)); await saveDialog()
  const employee = (await browserAPI(base + 'employees/?q=SERVICE-LEAD')).data.results[0]
  assert.equal(employee.department_id, department.id); assert.equal(employee.user_id, ownerUser.user_id)
  assert.equal(employee.employee_code, 'SERVICE-LEAD')
  const memberEmployee = await create('employees', { name: 'Service phase member', employee_code: 'SERVICE-MEMBER', department_id: department.id, user_id: memberUser.user_id })
  results.push('Employees and Departments forms save work-directory records and link existing Team accounts without changing account permissions.')

  const project = await create('projects', { name: 'Service phase project' })
  const contact = await create('contacts', { name: 'Service phase customer' })
  await navigate('/helpdesk'); await ready(); await press('New ticket')
  await fill('dialog[open] input[name=ticket_title]', 'Service phase workstation')
  await fill('dialog[open] textarea[name=ticket_description]', 'Diagnose connectivity and restore access.')
  await fill('dialog[open] select[name=ticket_contact]', String(contact.id))
  await fill('dialog[open] select[name=ticket_project]', String(project.id))
  await fill('dialog[open] select[name=ticket_assignee]', String(ownerUser.user_id))
  await fill('dialog[open] select[name=ticket_priority]', 'high'); await saveDialog('Save ticket')
  await until(() => evaluate('Boolean(document.querySelector(".ticket-details"))'), 'new ticket detail')
  const ticketId = Number(await evaluate('location.pathname.split("/").at(-1)'))
  let ticket = (await browserAPI(base + `helpdesk/${ticketId}/`)).data
  const originalVersion = ticket.version
  await press('Create project task', '.ticket-actions button')
  await until(() => evaluate('Boolean(document.querySelector(".ticket-details")?.textContent.includes("Task:"))'), 'ticket task link')
  ticket = (await browserAPI(base + `helpdesk/${ticketId}/`)).data
  const retry = await browserAPI(base + `helpdesk/${ticketId}/actions/`, 'POST', { action: 'create_task', expected_version: originalVersion })
  assert.equal(retry.status, 200); assert.equal(retry.data.task_id, ticket.task_id)
  await press('Add note'); await fill('dialog[open] textarea[name=ticket_note]', 'Service phase diagnosis'); await saveDialog('Save note')
  const note = (await browserAPI(base + `helpdesk/${ticketId}/messages/`)).data.results[0]
  assert.equal((await browserAPI(base + `helpdesk/${ticketId}/messages/`, 'POST', { request_id: note.request_id, body: note.body })).status, 200)
  assert.equal((await browserAPI(base + `helpdesk/${ticketId}/messages/`)).data.count, 1)
  results.push('Helpdesk tickets link Contacts and Projects; task conversion and internal-note retries preserve one task and one note.')

  await click('.ticket-details a[href^="/timesheets"]'); await ready(); await press('Log time')
  assert.equal(await evaluate('Number(document.querySelector("select[name=time_project]").value)'), project.id)
  assert.equal(await evaluate('Number(document.querySelector("select[name=time_task]").value)'), ticket.task_id)
  await fill('dialog[open] input[name=time_minutes]', '90')
  await fill('dialog[open] textarea[name=time_description]', 'Service phase diagnosis time'); await saveDialog('Save draft')
  await rowAction('Service phase diagnosis time', 'Submit'); await timeStatus('Service phase diagnosis time', 'submitted')
  await rowAction('Service phase diagnosis time', 'Approve'); await timeStatus('Service phase diagnosis time', 'approved')
  const ownerTime = (await browserAPI(base + `timesheets/?ticket_id=${ticketId}`)).data.results[0]
  assert.equal(ownerTime.minutes, 90)
  await press('Log time'); await fill('dialog[open] input[name=time_minutes]', '15')
  await fill('dialog[open] textarea[name=time_description]', 'Service phase duplicate time'); await saveDialog('Save draft')
  await rowAction('Service phase duplicate time', 'Submit'); await timeStatus('Service phase duplicate time', 'submitted')
  await rowAction('Service phase duplicate time', 'Approve'); await timeStatus('Service phase duplicate time', 'approved')
  await rowAction('Service phase duplicate time', 'Void')
  await fill('dialog[open] textarea[name=time_reason]', 'Duplicate work record'); await saveDialog('Confirm')
  await timeStatus('Service phase duplicate time', 'voided')
  assert.equal((await browserAPI(base + `timesheets/?ticket_id=${ticketId}`)).data.summary.approved_minutes, 90)
  results.push('Ticket links prefill project/task time; submission, approval and reasoned voiding retain history and reconcile approved minutes.')

  await press('Log time'); await fill('dialog[open] input[name=time_minutes]', '20')
  await fill('dialog[open] textarea[name=time_description]', 'Service phase conflict time'); await saveDialog('Save draft')
  const draft = (await browserAPI(base + 'timesheets/?q=Service%20phase%20conflict')).data.results[0]
  await rowAction('Service phase conflict time', 'Edit')
  assert.equal((await browserAPI(base + `timesheets/${draft.id}/`, 'PATCH', { minutes: 25, expected_version: draft.version })).status, 200)
  await fill('dialog[open] input[name=time_minutes]', '30'); await press('Save draft', 'dialog[open] button')
  await until(() => evaluate('document.querySelector("dialog[open] .notice.error")?.textContent.includes("changed in another session")'), 'stale time conflict')
  assert.equal(await evaluate('document.querySelector("dialog[open] input[name=time_minutes]").value'), '30')
  await evaluate('window.confirm = () => true'); await press('Reload latest', 'dialog[open] button')
  await until(() => evaluate('!document.querySelector("dialog[open]") && !document.querySelector(".loading-state")'), 'latest time data')
  assert.equal((await browserAPI(base + `timesheets/${draft.id}/`)).data.minutes, 25)
  results.push('Stale time edits preserve the unsaved form and require an explicit reload before continuing.')

  await navigate(`/helpdesk/${ticketId}`); await ready()
  assert.equal(await evaluate('document.querySelector(".ticket-details").textContent.includes("90 approved minutes")'), true)
  await press('Resolve', '.ticket-actions button'); await fill('dialog[open] textarea[name=ticket_resolution]', 'Service phase access restored'); await saveDialog('Resolve ticket')
  await until(() => evaluate('document.querySelector(".ticket-state")?.textContent === "resolved"'), 'resolved ticket')
  await press('Reopen', '.ticket-actions button'); await until(() => evaluate('document.querySelector(".ticket-state")?.textContent === "in progress"'), 'reopened ticket')
  await press('Resolve', '.ticket-actions button'); await fill('dialog[open] textarea[name=ticket_resolution]', 'Service phase final verification'); await saveDialog('Resolve ticket')
  const history = (await browserAPI(base + `helpdesk/${ticketId}/messages/`)).data
  assert.equal(history.results.filter(item => item.kind === 'resolution').length, 2)
  assert.equal(history.count, 3)
  results.push('Resolving and reopening a support ticket preserves both full resolutions and internal-note history.')

  await send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 1, mobile: true })
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await screenshot('helpdesk-mobile.png')
  await navigate(`/timesheets?ticket_id=${ticketId}`); await ready()
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await screenshot('timesheets-mobile.png')
  await navigate('/employees'); await ready()
  assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true)
  await screenshot('employees-mobile.png')
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false })
  await navigate(`/helpdesk/${ticketId}`); await ready(); await screenshot('helpdesk-desktop.png')
  assert.equal((await browserAPI(`companies/${secondCompanyId}/erp/helpdesk/${ticketId}/`)).status, 404)
  assert.equal((await browserAPI(`companies/${secondCompanyId}/erp/timesheets/?ticket_id=${ticketId}`)).status, 404)
  results.push('Employees, Timesheets and Helpdesk fit 375px; foreign-company ticket and timesheet links remain inaccessible.')
  return { employee, memberEmployee, project, ticketId, ownerTime }
}

export async function verifyServiceMember({ evaluate, fill, click, navigate, until, browserAPI, companyId, fixtures, results }) {
  const base = `companies/${companyId}/erp/`
  async function press(text, selector = 'button') {
    await evaluate(`(() => { const button = [...document.querySelectorAll(${JSON.stringify(selector)})].find(item => item.textContent.trim() === ${JSON.stringify(text)}); if (!button) throw new Error('Missing ' + ${JSON.stringify(text)}); button.click(); })()`)
  }
  await navigate('/employees')
  await until(() => evaluate('Boolean(document.querySelector(".record-card")) && !document.querySelector(".loading-state")'), 'member work directory')
  assert.equal(await evaluate('Boolean(document.querySelector(".control-actions .button-primary"))'), false)
  assert.equal((await browserAPI(base + `employees/${fixtures.memberEmployee.id}/`, 'PATCH', { job_title: 'Unauthorized' })).status, 403)
  await navigate(`/timesheets?ticket_id=${fixtures.ticketId}`)
  await until(() => evaluate('Boolean(document.querySelector(".time-summary")) && !document.querySelector(".loading-state")'), 'member timesheets')
  assert.equal((await browserAPI(base + 'timesheets/')).data.count, 0)
  assert.equal((await browserAPI(base + `timesheets/${fixtures.ownerTime.id}/`)).status, 404)
  await press('Log time')
  assert.equal(await evaluate('document.querySelectorAll("select[name=time_employee] option").length'), 2)
  await fill('dialog[open] input[name=time_minutes]', '45'); await fill('dialog[open] textarea[name=time_description]', 'Service phase member follow-up')
  await press('Save draft', 'dialog[open] button')
  await until(() => evaluate('!document.querySelector("dialog[open]") && Boolean(document.querySelector(".timesheet-table")) && !document.querySelector(".loading-state")'), 'member own time')
  await press('Submit', '.timesheet-table button')
  await until(() => evaluate('document.querySelector(".timesheet-table .badge")?.textContent === "submitted"'), 'member submits time')
  assert.equal(await evaluate('[...document.querySelectorAll(".timesheet-table button")].some(button => button.textContent.trim() === "Approve")'), false)
  const own = (await browserAPI(base + 'timesheets/')).data.results[0]
  assert.equal(own.employee_id, fixtures.memberEmployee.id)
  assert.equal((await browserAPI(base + `timesheets/${own.id}/actions/`, 'POST', { action: 'approve', expected_version: own.version })).status, 403)
  const csv = await evaluate(`(async () => (await fetch('/api/v1/${base}timesheets/export/')).text())()`)
  assert.match(csv, /Service phase member follow-up/); assert.doesNotMatch(csv, /Service phase diagnosis time/)
  await press('Withdraw', '.timesheet-table button')
  await until(() => evaluate('document.querySelector(".timesheet-table .badge")?.textContent === "draft"'), 'member withdraws time')
  await press('Discard draft', '.timesheet-table button')
  await fill('dialog[open] textarea[name=time_reason]', 'Accidental draft entry')
  await press('Confirm', 'dialog[open] button')
  await until(() => evaluate('!document.querySelector("dialog[open]") && document.querySelector(".timesheet-table .badge")?.textContent === "voided"'), 'member discards draft with history')
  assert.equal((await browserAPI(base + 'timesheets/')).data.summary.total_minutes, 0)
  results.push('Members log and submit only their own time; reads and CSV exports hide other employees, and approval controls are protected.')

  await navigate('/helpdesk')
  await until(() => evaluate('!document.querySelector(".loading-state") && Boolean(document.querySelector(".helpdesk-page"))'), 'member helpdesk')
  await press('New ticket'); await fill('dialog[open] input[name=ticket_title]', 'Service phase member request')
  assert.equal(await evaluate('document.querySelector("select[name=ticket_assignee]").disabled'), true)
  await press('Save ticket', 'dialog[open] button')
  await until(() => evaluate('Boolean(document.querySelector(".ticket-details"))'), 'member ticket saved')
  assert.equal(await evaluate('[...document.querySelectorAll(".ticket-actions button")].some(button => button.textContent.trim() === "Resolve")'), false)
  await press('Add note'); await fill('dialog[open] textarea[name=ticket_note]', 'Service phase additional details')
  await press('Save note', 'dialog[open] button')
  await until(() => evaluate('!document.querySelector("dialog[open]") && document.querySelector(".service-history")?.textContent.includes("Service phase additional details")'), 'member internal note')
  results.push('Members can create support requests and add internal notes while ticket assignment and status management stay protected.')
}
