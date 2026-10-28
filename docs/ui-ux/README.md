# Login and company workspace

The account and company area includes these screens:

| Route | Purpose | Access |
| --- | --- | --- |
| `/login` | Email/password sign-in, errors, expired-session notice | Public |
| `/` | App launcher, app search, connection health | Signed in |
| `/companies` | Create a company and switch between accessible companies | Signed in |
| `/team` | View team and change access according to role | Signed in with selected company |
| `/setup` | Five-step account/company/team guide | Public |

The header shows the account, active company selector, and sign-out action after
login. A connection badge checks Django and MySQL on page load and every 30
seconds. The overview provides a retry button. Status comes from live APIs.

Owner controls include all roles. Administrator controls appear only for ordinary
members. Ordinary members see team access without editing controls. The server
enforces the same restrictions independently of the interface.

Team data clears immediately on company switching and old responses are ignored.
Forms show loading, validation errors, and success feedback. Account/company
creation and team access changes have explicit submit buttons. There are labeled
fields, keyboard focus styles, a skip link, status announcements, responsive
columns, and wrapping layouts for small screens and long account/company names.

Run `node scripts/verify-browser.mjs` on Windows with Node.js 22+ and Edge to check
the actual workflows. Screenshots and results go to ignored `.local/`.

## ERP application screens

The purple application shell provides a grid menu, company switcher, account
actions, and app navigation. The launcher contains ten working application tiles.
The design follows familiar Odoo patterns while retaining KERP's own name/icons.

| Route | Screen |
| --- | --- |
| `/dashboard` | Live metrics, pipeline bars, stock/tasks, orders, activity |
| `/contacts` | Contact cards/list and record forms |
| `/crm` | Opportunity Kanban/list and record forms |
| `/inventory` | Product cards/list and record forms |
| `/inventory/movements` | Stock ledger and signed adjustments |
| `/sales`, `/sales/new`, `/sales/{id}` | Quotations/orders and editable/read-only forms |
| `/purchase`, `/purchase/new`, `/purchase/{id}` | RFQs/orders and receipt actions |
| `/invoicing`, `/invoicing/{id}` | Invoices/bills, manual payments, print layout |
| `/projects`, `/tasks?project_id={id}` | Projects and task Kanban/list |
| `/settings` | Currency preference and workspace links |

Cards and list buttons open actual records. Kanban supports both drag/drop and a
stage selector. Tables and boards scroll within their containers on small screens.
Modal dialogs use the native dialog element for focus containment and Escape
handling. Business write controls require owner/admin access. Changing the active
company clears loaded data and invalidates previous responses.

## Shared catalog components

Contacts, Products, CRM, Projects and Tasks now use shared buttons, notices, badges,
fields, dialogs, empty states, toolbars, tables and pagination. Shared modal dialogs
label their headings, guard unsaved changes on Escape/close, and explicitly wrap
Tab/Shift+Tab within visible enabled controls. Read
[VUE-COMPONENTS.md](../VUE-COMPONENTS.md) for component contracts and usage.

Contacts/Products add structured filters, stable server sorting, page selection for
confirmed bulk archive/restore, CSV previews/transfers, and product category/barcode
forms. The [catalog walkthrough](../CONTACTS-PRODUCTS.md) explains each workflow.
