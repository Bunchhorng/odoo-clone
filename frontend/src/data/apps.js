import { backendOrigin } from '../services/api'

export const apps = [
  {
    title: 'Administration',
    description: 'Manage users, companies, and company memberships in Django Admin.',
    label: 'Open admin',
    icon: 'A',
    tone: 'green',
    href: `${backendOrigin}/admin/`,
  },
  {
    title: 'Connection health',
    description: 'Check the live API response and its connection to your database.',
    label: 'View API response',
    icon: '↗',
    tone: 'blue',
    href: '/api/v1/health/',
  },
  {
    title: 'Getting started',
    description: 'Find your workspace links and the next steps for your team.',
    label: 'Read the guide',
    icon: '01',
    tone: 'sand',
    route: '/setup',
  },
]
