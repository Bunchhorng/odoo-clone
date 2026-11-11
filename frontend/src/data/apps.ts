import { modules } from './modules'
import type { AppDefinition, CompanyRole, NavigationItem } from '../types/erp'

// The session API grants module read access through active company membership.
// Only add role restrictions here when the backend introduces the same policy.
export const applications: AppDefinition[] = modules.map(app => ({
  ...app,
  status: 'available',
  requiresCompany: !['/settings', '/team'].includes(app.path),
}))

export function authorizedApplications(apps: AppDefinition[], role?: CompanyRole) {
  return apps.filter(app => !app.roles || (role !== undefined && app.roles.includes(role)))
}

export function matchesPath(path: string, base: string) {
  return path === base || path.startsWith(`${base}/`)
}

export function activeApplication(path: string) {
  if (path === '/tasks') return applications.find(app => app.path === '/projects')
  if (path === '/companies') return applications.find(app => app.path === '/settings')
  return [...applications].sort((a, b) => b.path.length - a.path.length).find(app => matchesPath(path, app.path))
}

const links = (...items: [string, string][]): NavigationItem[] => items.map(([label, path]) => ({ label, path, exact: true }))
export const moduleNavigation: Record<string, NavigationItem[]> = {
  '/dashboard': links(['Overview', '/dashboard']),
  '/contacts': links(['Contacts', '/contacts']),
  '/crm': links(['Pipeline', '/crm'], ['Quotations', '/sales']),
  '/sales': links(['Quotations & orders', '/sales'], ['Customers', '/contacts'], ['Products', '/inventory']),
  '/purchase': links(['Requests & orders', '/purchase'], ['Suppliers', '/contacts'], ['Products', '/inventory']),
  '/inventory': links(['Products', '/inventory'], ['Stock movements', '/inventory/movements'], ['Warehouses', '/inventory/warehouses'], ['Locations', '/inventory/locations'], ['Purchase orders', '/purchase']),
  '/invoicing': links(['Invoices & bills', '/invoicing'], ['Sales', '/sales'], ['Purchase', '/purchase']),
  '/accounting': links(['Accounting', '/accounting'], ['Invoices & bills', '/invoicing']),
  '/projects': links(['Projects', '/projects'], ['All tasks', '/tasks'], ['Timesheets', '/timesheets']),
  '/employees': links(['Employees', '/employees'], ['Departments', '/employees/departments'], ['Timesheets', '/timesheets']),
  '/timesheets': links(['Time entries', '/timesheets'], ['Projects', '/projects'], ['Employees', '/employees']),
  '/helpdesk': links(['Tickets', '/helpdesk'], ['Tasks', '/tasks']),
  '/team': links(['Users & access', '/team'], ['Companies', '/companies']),
  '/settings': links(['Preferences', '/settings'], ['Companies', '/companies'], ['Users & access', '/team'], ['Getting started', '/setup']),
}

export function pageLabel(path: string) {
  const known: Record<string, string> = {
    '/': 'Applications', '/account': 'Account & security', '/setup': 'Getting started',
    '/companies': 'Companies', '/tasks': 'All tasks', '/inventory/movements': 'Stock movements',
    '/inventory/warehouses': 'Warehouses', '/inventory/locations': 'Stock locations',
    '/employees/departments': 'Departments',
  }
  return known[path] || activeApplication(path)?.name || 'Workspace'
}
