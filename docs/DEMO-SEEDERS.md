# Demo seeders

`seed_demo` creates a separate, per-user company named `Odoo Demo`. It is intended
for local development and test environments only; it refuses to run when Django
`DEBUG` is false. It never creates, changes, or prints account passwords.

## Dependency map

```text
active existing user
  -> isolated company + owner membership + workspace settings
  -> contacts and products
  -> opening stock and CRM opportunities
  -> purchase/sales orders
  -> receipts/deliveries -> invoice postings -> payments
  -> projects -> tasks -> activity record
```

The command uses existing order, fulfillment, invoicing, payment, and accounting
services. It does not manufacture unsupported credit notes, refunds, attendance,
payroll, recruitment, POS, manufacturing, or ecommerce records.

## Commands

```sh
docker compose exec backend python manage.py seed_demo --email admin@kerp.local
docker compose exec backend python manage.py seed_demo --email admin@kerp.local --verify
docker compose exec backend python manage.py seed_demo --email admin@kerp.local --dry-run
docker compose exec backend python manage.py seed_demo --email admin@kerp.local --reset-demo --confirm-reset
```

The command is idempotent: a second normal invocation leaves its existing isolated
demo company unchanged. `--dry-run` validates the complete creation path inside a
database transaction and rolls it back. Reset requires both flags and deletes only
the matching `kerp-demo-<user id>` company after checking its demo name; no broad
database truncation is used.

## Verification

```sh
docker compose exec backend python manage.py test apps.business.test_demo
```

The current SEED-01 dataset is intentionally small and coherent. Profile sizing,
multiple demo companies/users, historical volume, HR, Helpdesk, and other expanded
scenarios remain later milestones because the corresponding stable identifiers and
workflow coverage have not yet been implemented.
