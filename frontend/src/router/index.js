import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import SetupView from '../views/SetupView.vue'
import LoginView from '../views/LoginView.vue'
import CompaniesView from '../views/CompaniesView.vue'
import TeamView from '../views/TeamView.vue'
import { useAuthStore } from '../stores/auth'
import CatalogView from '../views/CatalogView.vue'
import DashboardView from '../views/DashboardView.vue'
import OrdersView from '../views/OrdersView.vue'
import InvoicesView from '../views/InvoicesView.vue'
import AccountingView from '../views/AccountingView.vue'
import TimesheetsView from '../views/TimesheetsView.vue'
import HelpdeskView from '../views/HelpdeskView.vue'
import StockView from '../views/StockView.vue'
import SettingsView from '../views/SettingsView.vue'
import AccountView from '../views/AccountView.vue'
import ForgotPasswordView from '../views/ForgotPasswordView.vue'
import ResetPasswordView from '../views/ResetPasswordView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView, meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/account', name: 'account', component: AccountView, meta: { requiresAuth: true } },
    { path: '/forgot-password', name: 'forgot-password', component: ForgotPasswordView },
    { path: '/reset-password', name: 'reset-password', component: ResetPasswordView },
    { path: '/companies', name: 'companies', component: CompaniesView, meta: { requiresAuth: true } },
    { path: '/team', name: 'team', component: TeamView, meta: { requiresAuth: true } },
    { path: '/dashboard', component: DashboardView, meta: { requiresAuth: true } },
    { path: '/contacts', component: CatalogView, props: { resource: 'contacts' }, meta: { requiresAuth: true } },
    { path: '/crm', component: CatalogView, props: { resource: 'opportunities' }, meta: { requiresAuth: true } },
    { path: '/inventory', component: CatalogView, props: { resource: 'products' }, meta: { requiresAuth: true } },
    { path: '/inventory/movements', component: StockView, meta: { requiresAuth: true } },
    { path: '/projects', component: CatalogView, props: { resource: 'projects' }, meta: { requiresAuth: true } },
    { path: '/tasks', component: CatalogView, props: { resource: 'tasks' }, meta: { requiresAuth: true } },
    { path: '/sales/:recordId?', component: OrdersView, props: { kind: 'sale' }, meta: { requiresAuth: true } },
    { path: '/purchase/:recordId?', component: OrdersView, props: { kind: 'purchase' }, meta: { requiresAuth: true } },
    { path: '/invoicing/:recordId?', component: InvoicesView, meta: { requiresAuth: true } },
    { path: '/employees', component: CatalogView, props: { resource: 'employees' }, meta: { requiresAuth: true } },
    { path: '/employees/departments', component: CatalogView, props: { resource: 'departments' }, meta: { requiresAuth: true } },
    { path: '/timesheets', component: TimesheetsView, meta: { requiresAuth: true } },
    { path: '/helpdesk/:recordId?', component: HelpdeskView, meta: { requiresAuth: true } },
    { path: '/accounting', component: AccountingView, meta: { requiresAuth: true } },
    { path: '/settings', component: SettingsView, meta: { requiresAuth: true } },
    { path: '/setup', name: 'setup', component: SetupView },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async to => {
  const auth = useAuthStore()
  await auth.initialize()
  if (to.meta.requiresAuth && !auth.user) return { name: 'login', query: { next: to.fullPath } }
  if (to.name === 'login' && auth.user) return { name: 'home' }
})

export default router
