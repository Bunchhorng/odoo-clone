# Use the ERP step by step

KERP now has an Odoo-style application launcher and connected core business
workflows. It is a Django/Vue implementation with its own scope. See
[ODOO-COVERAGE.md](ODOO-COVERAGE.md) for the features still needed for full parity.

## 1. Run and sign in

From the project root with Docker Desktop running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

Open <http://localhost:5173/login>. Use your existing account. If you need the
first administrator, run `docker compose exec backend python manage.py createsuperuser`.
See [SETUP.md](../SETUP.md) for ports and troubleshooting.

After sign-in, the Apps screen shows ten working applications. Search filters
the tiles. The grid menu beside KERP lets you switch apps from any screen.

## 2. Choose a company, or explore the demo

Use **Working in** to select your company. **Companies** creates a new workspace
and gives you its owner role. Each company keeps its own business records.

To create a separate sample workspace for an existing account:

```powershell
docker compose exec backend python manage.py seed_demo --email admin@kerp.local
```

Replace the email with your own account's email. Reload KERP and select **KERP
Demo**. It contains example contacts, products, opportunities, stock, sales,
purchases, invoices, payments, projects, and tasks. The sample companies, people,
and addresses are fictional. The command never creates or resets an account
password. Repeating it leaves the existing demo unchanged.

Use a different company for your real work. The demo does not modify existing
companies. Database deletion of companies with business documents is intentionally
restricted; archive records or disable company access rather than deleting them.

## 3. Set the company's currency

Open **Settings**, choose the currency, and select **Save preferences** before
creating your first sales or purchase document. Supported currencies are USD,
THB, EUR, GBP, SGD, AUD, and CAD, with two-decimal monetary amounts.

Currency locks when the first order is created. Each document retains its currency.
This version uses one currency per company and does not perform currency conversion.

## 4. Add customers and suppliers

Open **Contacts > New**. Enter a name, organization, email, phone, country, address,
and any internal notes. Mark **Customer**, **Supplier**, or both. At least one
must be selected. Save the record.

Use the search field to find names, organizations, emails or phones. Filter by
customer/supplier role, sort records, and switch between cards
and a list using the view controls. Select a card/name to edit. **Archive** hides
the contact from new document choices; use the **Archived** filter and **Restore**
to reactivate it. Existing documents retain their saved contact details.

Select several records on the current page for confirmed bulk archive/restore.
**Import** validates a CSV preview before creating records; **Export CSV** downloads
all matching records. Follow [CONTACTS-PRODUCTS.md](CONTACTS-PRODUCTS.md) for examples.

## 5. Create your product catalog

Open **Inventory > Products > New**. Enter:

- Product name and a company-unique internal reference/SKU.
- **Goods** for tracked stock, or **Service** for work without stock movements.
- Sales price, cost, unit of measure, and low-stock threshold.
- An optional company category and unique barcode, preserving leading zeros.

Use **Categories** to create/rename/archive categories. Product filters combine
type, category, stock availability, search and archive status. Category names and
barcodes are searchable. CSV transfer and bulk selection work as in Contacts.

Prices must be nonnegative. SKU values are normalized to uppercase. Stock quantities
support three decimal places. A product's type cannot change after it has appeared
on an order or had stock movements. Archive it and create another product if its
type needs to change.

## 6. Track opportunities in CRM

Open **CRM > New**. Enter the opportunity, optional customer, expected revenue,
probability, expected closing date, stage, and notes.

Move the card by dragging it to a column, or use its stage selector with a keyboard
or on mobile. The stages are **New**, **Qualified**, **Proposition**, **Won**, and
**Lost**. Won sets probability to 100%; Lost sets it to 0%. Card edits and stage
changes are saved to the database. List view provides search and archiving.

This pipeline tracks opportunities independently. Automatic opportunity-to-quotation
conversion, email integration, lead scoring, and custom stages are future work.

## 7. Record opening stock

Open **Inventory > Stock movements > Adjust stock**. Select an active goods product,
enter a positive quantity change (for example `20`), give a reason such as `Opening
stock count`, then select **Record adjustment**.

Use a negative change for a reduction. The system rejects changes that would make
stock negative. Quantities on the Products screen are calculated from the movement
ledger. Services do not have stock movements. There is one stock pool per company;
warehouses, locations, lots, reservations, and valuation are not implemented yet.

## 8. Complete a sale

1. Open **Sales > New**.
2. Select an active customer and order date.
3. Add products, quantities, unit prices, and a tax percentage for each line.
4. Add terms or notes and select **Save**.
5. Review the saved quotation number and totals.
6. Select **Confirm sale**. The document becomes a confirmed sales order.
7. Select **Validate delivery** to deduct goods from stock. Services do not affect
   stock. There must be enough stock for every goods line.
8. Select **Create invoice**, then follow the invoice steps below.

You may edit a draft quotation. Confirmation freezes the lines, prices, and customer
details. Line amounts are rounded to two decimals with half-up rounding; tax is
calculated on the rounded line subtotal. Totals come from the backend, regardless
of what a client sends. The tax percentage is a manual calculation field, not a
country-specific tax engine.

Delivery is for the full order. Partial deliveries, backorders, returns, discounts,
pricelists, email quotations, and online signatures are future work. Cancelling an
undelivered order with no invoice keeps the cancelled document in history. Orders
that already have stock movements or an invoice cannot be cancelled in this version.

## 9. Complete a purchase

1. Open **Purchase > New**.
2. Select an active supplier.
3. Add products, quantities, costs, and optional tax percentages.
4. Save the request for quotation (RFQ), then select **Confirm purchase**.
5. Select **Receive products** to add goods to stock.
6. Select **Create bill** to prepare a vendor bill.

Repeated delivery/receipt requests do not create duplicate movements. One invoice
or bill is allowed per order; repeated creation returns the existing document.

## 10. Issue an invoice and register payment

Open the invoice created from a confirmed sale, or find it under **Invoicing**.

1. While in Draft, set its date, optional due date, and notes. Select **Save** if
   you change those fields.
2. Select **Issue invoice** (or **Confirm bill** for a vendor bill).
3. Select **Register payment**.
4. Enter an amount, date, Bank/Cash method, and optional reference.
5. Select **Record payment**.

Partial payment reduces the remaining balance. Recording the full balance changes
status to Paid. Overpayments and payments dated before the invoice are rejected.
The payment dialog retains a request ID during retries so a retry cannot record
the same submission twice. These are manual payment records; no bank transfer or
online payment is executed.

**Print / PDF** opens your browser's print dialog. Choose Save as PDF to save a
document. Payments are listed beneath the invoice. An unpaid invoice may be
cancelled; one with recorded payments cannot be cancelled. Credit notes, payment
reversals, reconciliation, and a general ledger are future work.

## 11. Organize projects and tasks

Open **Project > New**, name the project, optionally select a customer, and save.
On its card, select **Open tasks**. Create a task with a title, project, optional
active teammate, priority, due date, and notes.

Move tasks between **To do**, **In progress**, and **Done** by dragging or selecting
a stage. **All tasks** shows tasks across the company. List view offers search,
archive, and restore. Timesheets, dependencies, recurring tasks, and project billing
are future work.

## 12. Review your dashboard

**Dashboard** uses live company records for confirmed sales, pipeline value,
receivables, payables, contacts, products, low stock, open/overdue tasks, recent
orders, and activity. Pipeline bars open CRM with a stage filter. Sales totals
are confirmed order amounts, not accounting revenue. Cancelled invoices are
excluded from balances. The dashboard currently covers all recorded dates.

## Permissions

Owners and administrators can create/update business records, perform document
actions, adjust stock, and register manual payments. Members have read-only business
access. Team access has additional rules: only owners can change administrator or
owner roles, and the final active owner is protected.

Every API checks the company membership again; hiding a button is not the access
control. See [the account guide](USER-GUIDE.md) for team management. Per-app roles,
audit exports, and production authentication hardening are listed in the coverage
document.
