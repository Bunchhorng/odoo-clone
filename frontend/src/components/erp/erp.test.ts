import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { api } from '../../services/api'
import ERPAppLauncher from './ERPAppLauncher.vue'
import ERPDataTable from './ERPDataTable.vue'
import ERPCompanySwitcher from './ERPCompanySwitcher.vue'
import ERPPopover from './ERPPopover.vue'
import ERPListView from './ERPListView.vue'
import ERPStatusBar from './ERPStatusBar.vue'
import type { AppDefinition } from '../../types/erp'

vi.mock('../../services/api', () => ({ api: vi.fn(), getHealth: vi.fn() }))
const wrappers: VueWrapper[] = []
const apps: AppDefinition[] = [
  { name: 'Sales', path: '/sales', description: 'Quotations and orders', icon: 'trend', color: '#714b83', category: 'Sales', requiresCompany: true },
  { name: 'Future', path: '/future', description: 'Planned', icon: 'grid', color: '#714b83', category: 'Sales', status: 'coming-soon' },
  { name: 'Restricted', path: '/restricted', description: 'Owners only', icon: 'grid', color: '#714b83', roles: ['owner'] },
]
function session() {
  const auth = useAuthStore()
  auth.user = { id: 1, name: 'Member', email: 'member@example.test', is_staff: false }
  auth.companies = [{ id: 1, name: 'First company', slug: 'first', role: 'member' }, { id: 2, name: 'Second company', slug: 'second', role: 'member' }]
  auth.$patch({ activeCompanyId: 1 })
  return auth
}
async function render(component: any, options: Record<string, any> = {}) {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }] })
  await router.push('/')
  const wrapper = mount(component, { attachTo: document.body, global: { plugins: [router] }, ...options })
  wrappers.push(wrapper)
  return wrapper
}
beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()); document.body.innerHTML = '' })

describe('launcher', () => {
  it('uses company permissions and never links unfinished applications', async () => {
    session()
    const wrapper = await render(ERPAppLauncher, { props: { apps } })
    expect(wrapper.find('a[href="/sales"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Restricted')
    expect(wrapper.find('a[href="/future"]').exists()).toBe(false)
    expect(wrapper.find('[aria-disabled="true"]').text()).toContain('Coming soon')
  })
  it('searches descriptions, trims whitespace, clears and announces empty results', async () => {
    session()
    const wrapper = await render(ERPAppLauncher, { props: { apps } })
    const input = wrapper.get('input[type=search]')
    await input.setValue('  ORDERS  ')
    expect(wrapper.findAll('.launcher-tile')).toHaveLength(1)
    await input.setValue('unmatched')
    expect(wrapper.text()).toContain('No applications found')
    await input.trigger('keydown', { key: 'Escape' })
    expect((input.element as HTMLInputElement).value).toBe('')
    expect(wrapper.findAll('.launcher-tile')).toHaveLength(2)
  })
  it('presents permitted applications in the visual app gallery', async () => {
    session()
    const wrapper = await render(ERPAppLauncher, { props: { apps: [...apps, { name: 'Accounts', path: '/accounts', description: 'Ledger', icon: 'chart', color: '#714b83', category: 'Finance', requiresCompany: true }] } })
    expect(wrapper.findAll('.launcher-grid > li')).toHaveLength(3)
    expect(wrapper.find('a[href="/sales"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/accounts"]').exists()).toBe(true)
    expect(wrapper.find('.launcher-category').exists()).toBe(false)
  })
  it('handles loading, errors, retry and the absence of a company without fake actions', async () => {
    const auth = session()
    auth.$patch({ activeCompanyId: null })
    const wrapper = await render(ERPAppLauncher, { props: { apps, loading: true } })
    expect(wrapper.find('section').attributes('aria-busy')).toBe('true')
    expect(wrapper.findAll('.launcher-tile')).toHaveLength(0)
    await wrapper.setProps({ loading: false, error: 'Session unavailable' })
    await wrapper.get('[role=alert] button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
    await wrapper.setProps({ error: '' })
    expect(wrapper.find('a[href="/sales"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Choose a company')
  })
})

describe('company switching', () => {
  it('posts the real company selection and retains the old context on failure', async () => {
    const auth = session()
    vi.mocked(api).mockRejectedValueOnce(new Error('Company access unavailable'))
    const wrapper = await render(ERPCompanySwitcher)
    await wrapper.get('select').setValue('2')
    await flushPromises()
    expect(api).toHaveBeenCalledWith('companies/2/select/', { method: 'POST' })
    expect(auth.activeCompanyId).toBe(1)
    expect((wrapper.get('select').element as HTMLSelectElement).value).toBe('1')
    expect(wrapper.get('[role=alert]').text()).toContain('Company access unavailable')
  })
  it('honors unsaved form guards without posting', async () => {
    const auth = session()
    auth.registerLeaveGuard(() => false)
    const wrapper = await render(ERPCompanySwitcher)
    await wrapper.get('select').setValue('2')
    await flushPromises()
    expect(api).not.toHaveBeenCalled()
    expect((wrapper.get('select').element as HTMLSelectElement).value).toBe('1')
  })
})

describe('keyboard disclosure', () => {
  it('moves focus with arrows, returns it on Escape and dismisses outside', async () => {
    const wrapper = await render(ERPPopover, { props: { label: 'Options' }, slots: { trigger: 'Options', default: '<a href="/one">First</a><a href="/two">Second</a>' } })
    const trigger = wrapper.get('button')
    await trigger.trigger('keydown', { key: 'ArrowDown' })
    await flushPromises()
    expect(document.activeElement?.textContent).toBe('First')
    await wrapper.get('a').trigger('keydown', { key: 'ArrowDown' })
    expect(document.activeElement?.textContent).toBe('Second')
    await wrapper.get('a').trigger('keydown', { key: 'Escape' })
    expect(trigger.attributes('aria-expanded')).toBe('false')
    expect(document.activeElement).toBe(trigger.element)
    await trigger.trigger('click')
    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await flushPromises()
    expect(wrapper.find('.erp-popover-panel').exists()).toBe(false)
  })
})

describe('data and feedback', () => {
  it('sorts through events, selects only the current page, and groups without mutating data', async () => {
    const wrapper = await render(ERPDataTable, { props: { title: 'Contacts', rows: [{ id: 1, name: 'Acme', country: 'TH', is_active: true }], columns: [{ key: 'name', label: 'Name' }], ordering: 'name', sortable: true, selectable: true, selected: [99], groupBy: 'country' } })
    expect((wrapper.get('thead input').element as HTMLInputElement).indeterminate).toBe(false)
    await wrapper.get('.sort-button').trigger('click')
    expect(wrapper.emitted('sort')?.[0]).toEqual(['-name'])
    expect(wrapper.get('.table-group').text()).toContain('TH')
    expect(wrapper.get('[role=region]').attributes('tabindex')).toBe('0')
    await wrapper.get('tbody .text-link').trigger('click')
    expect(wrapper.emitted('open')?.[0]?.[0]).toMatchObject({ id: 1 })
  })
  it('does not render stale records while loading or after an API error', async () => {
    const wrapper = await render(ERPListView, { props: { loading: true, title: 'Contacts' }, slots: { default: 'Stale data' } })
    expect(wrapper.text()).not.toContain('Stale data')
    await wrapper.setProps({ loading: false, error: 'Permission denied' })
    expect(wrapper.text()).not.toContain('Stale data')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })
  it('presents document status without pretending a status click changes business state', async () => {
    const wrapper = await render(ERPStatusBar, { props: { value: 'draft', steps: [{ value: 'draft', label: 'Draft' }, { value: 'confirmed', label: 'Confirmed' }] } })
    expect(wrapper.get('[aria-current=step]').text()).toBe('Draft')
    expect(wrapper.findAll('button')).toHaveLength(0)
  })
})
