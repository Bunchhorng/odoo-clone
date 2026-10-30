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

After sign-in, the Apps screen shows fourteen working applications. Search filters
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

Select **New quotation** on an opportunity to open Sales with its available customer
and notes filled in. Add products and Save to create a linked quotation. The
**Quotations & orders** link lists its related sales documents; Sales links back to
the opportunity. Multiple quotations are supported. Quotation creation/confirmation
does not automatically mark the opportunity Won. Email integration, lead scoring,
and custom stages remain future work. See [CRM-SALES.md](CRM-SALES.md).

## 7. Record opening stock

Open **Inventory > Stock movements > Adjust stock**. Select an active goods product,
enter a positive quantity change (for example `20`), give a reason such as `Opening
stock count`, then select **Record adjustment**.

Use a negative change for a reduction. The system rejects changes that would make
stock negative. Quantities on the Products screen are calculated from the movement
ledger. Services do not have stock movements. There is one stock pool per company;
warehouses, locations, lots, reservations, and valuation are not implemented yet.

Movement history now supports product/type/date filters and reference searches.
Each manual adjustment can be reversed once with a reason, preserving both ledger
entries. The adjustment dialog retains its request ID when retrying a submission.

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

If another session changes the document, a stale save or confirmation is rejected.
Use **Reload document**, review the current values, and try again. Unsaved edits
are retained until you explicitly reload/discard. Archived customers/products stay
visible on existing drafts; notes and retained line edits remain possible.

Delivery is for the full order. Partial deliveries, backorders, returns, discounts,
pricelists, email quotations, and online signatures are future work. Cancelling an
undelivered order with no invoice keeps the cancelled document in history. Orders
that already have stock movements or an invoice cannot be cancelled in this version.

## 9. Complete a purchase

1. Open **Purchase > New**.
2. Select an active supplier.
3. Add products, quantities, costs, and optional tax percentages.
4. Save the request for quotation (RFQ), then select **Confirm purchase**.
5. Select **Receive products**, enter the quantities received now and a delivery
   reference/notes, then select **Record receipt**. Set a line to zero to skip it.
   Received/Remaining quantities and numbered receipt history appear on the order.
   Repeat until all remaining goods arrive.
6. Select **Create bill** to prepare a vendor bill.

Repeated delivery/receipt requests do not create duplicate movements. One invoice
or bill is allowed per order; repeated creation returns the existing document.

For damaged goods awaiting replacement, open **Stock movements** on the purchase
order and select **Return to supplier** on its receipt movement. The return reduces
stock and reopens quantities for a replacement receipt. It cannot exceed the
unreturned receipt quantity or available stock. Vendor bills still cover the full
order; returns do not change bills or payments. See [PURCHASE-INVENTORY.md](PURCHASE-INVENTORY.md).

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
reversals and bank reconciliation are future work. Invoice issue and payment now
post to the general ledger; unpaid cancellation creates a linked reversal.

For an unpaid cancelled invoice or bill, **Return to draft** permits corrections
and reissue while preserving the same number and activity history.

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
actions, adjust stock, and register manual payments. Members have read-only
access to the commercial and accounting records. They can
log and submit their own linked employee time, create support requests, edit their
own New tickets, and add internal notes in Helpdesk. Team access has additional
rules: only owners can change administrator or
owner roles, and the final active owner is protected.

Every API checks the company membership again; hiding a button is not the access
control. See [the account guide](USER-GUIDE.md) for team management. Per-app roles,
audit exports, and production authentication hardening are listed in the coverage
document.

## Accounting and cross-module tracing

Open **Accounting** from Apps for journal entries, trial balance, profit/loss and
balance sheet. Choose an inclusive date range, expand a journal entry to inspect
both sides, or click a trial-balance account to inspect its period entries.
**Export CSV** downloads the trial balance. Reports use posted invoice/bill dates
and exclude unissued drafts. Stock movements have no valuation postings.

Order details show **Billing & accounting**, with total, payments, remaining
balance and links to the invoice and journal. Invoices link back to the source
order and opportunity. Journals identify source payments and cancellation
reversals and link to their invoice/order. Orders link to stock movements.

Existing issued documents/payments need **Import historical postings** when the
incomplete-reports notice appears. Owners/admins can import; members can read.
Owners can **Close dates** permanently through a chosen date. Closed-date issue,
payment and reversal attempts fail without changing the source. An unpaid invoice
can be reversed on a later open date; choose its Cancellation posting date.

See [Accounting & integration](ACCOUNTING-INTEGRATION.md) for posting examples,
permissions, correction behavior, historical import and limits. Bank statement
matching, inventory costing, manual opening balances, credit notes and localized
tax/statutory reporting remain outside this phase.

## Employees, time and support

Open **Employees**, create a department, and add work-directory records. Link an
existing Team account to let that person log time; this changes no account role.
Members can read the directory, while owners/admins manage it.

In **Timesheets**, log whole minutes against a project and optional task/ticket,
save a draft, then Submit. Discard draft retains an accidental entry with a reason
and releases its time allowance. Owners/admins approve or return submitted time with a
reason. Approved entries are locked; Void retains a mistaken entry with a reason
and removes it from totals. Members see/export only their own time. Project, task,
employee and ticket links open filtered time views.

In **Helpdesk**, create a support ticket, associate a customer/project, and add
internal notes. Owners/admins assign tickets, manage statuses and create a linked
project task. Resolve requires a resolution; reopening retains previous resolution
messages. The ticket and task link both ways, and support time uses their project
and task. Notes are internal to the company; no email is sent.

The [service application guide](SERVICE-APPLICATIONS.md) covers permissions,
retry/version rules, approval behavior and the remaining HR/service apps. This
phase does not add payroll, leave, attendance, time billing, knowledge base,
appointments or the other remaining Odoo application families.
