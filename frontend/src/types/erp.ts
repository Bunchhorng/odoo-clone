export type CompanyRole = 'owner' | 'admin' | 'member'
export interface User { id: number; name: string; email: string; is_staff: boolean }
export interface Company { id: number; name: string; slug: string; role: CompanyRole }
export interface AppDefinition {
  name: string
  path: string
  icon: string
  color: string
  description: string
  status?: 'available' | 'coming-soon'
  roles?: CompanyRole[]
  requiresCompany?: boolean
}
export interface NavigationItem { label: string; path: string; exact?: boolean }
export interface Activity {
  id: number
  summary: string
  actor_email: string
  created_at: string
  resource?: string
  record_id?: number
}
export interface ERPColumn {
  key: string
  label: string
  money?: boolean
  sort?: boolean
}
export interface ERPRecord { id: number; [key: string]: unknown }
export interface SelectOption { value: string; label: string }
