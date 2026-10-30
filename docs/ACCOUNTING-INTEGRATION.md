# Cross-module integration and accounting

This phase connects the existing commercial workflow to a company-scoped,
document-derived accrual ledger. Open **Accounting** from Apps to view journals
and financial reports. It uses the company's existing two-decimal currency.

## Follow a transaction

1. CRM opens a linked sales quotation. Confirm the order and deliver goods through
   the existing stock workflow.
2. Create the order's invoice or vendor bill. A draft creates no accounting entry.
3. Issue the invoice or confirm the bill. This creates one numbered, balanced
   journal entry in the same transaction as the document transition.
4. Register bank/cash payments. Each payment creates its own entry and reduces
   the receivable or payable. Retrying its UUID creates no duplicate payment,
   posting, activity, or document number.
5. Open **Billing & accounting** on the source order to see invoice status, total,
   payments and remaining balance. Follow its invoice or journal links.
6. The invoice links to its order, source opportunity when present, and journals.
   Sales and purchase orders link to their stock movements. Journal entries link
   back to both the invoice and order and identify the payment or reversal.

Source links show every accounting date, including future-dated documents. Normal
Accounting navigation defaults to January 1 through today. Source filters apply
to the journal list; financial reports always cover the selected company's ledger.

## Fixed chart and posting rules

| Code | Account | Type |
| --- | --- | --- |
| 1000 | Bank | Asset |
| 1010 | Cash | Asset |
| 1100 | Accounts receivable | Asset |
| 1200 | Input tax | Asset |
| 2000 | Accounts payable | Liability |
| 2100 | Output tax | Liability |
| 4000 | Sales revenue | Income |
| 5000 | Purchases expense | Expense |

| Event | Debit | Credit |
| --- | --- | --- |
| Customer invoice issue | Receivable: total | Sales: subtotal; output tax: tax |
| Vendor bill issue | Purchases expense: subtotal; input tax: tax | Payable: total |
| Customer payment | Bank or cash: payment amount | Receivable: payment amount |
| Vendor payment | Payable: payment amount | Bank or cash: payment amount |
| Unpaid invoice/bill cancellation | Opposite of original entry | Opposite of original entry |

For example, issuing a 100.00 sale with 7.00 tax posts a 107.00 debit to
receivables, 100.00 credit to sales, and 7.00 credit to output tax. A 20.00 bank
payment debits bank and credits receivables by 20.00, leaving 87.00 receivable.
This is an arithmetic example, not a tax-rate or tax-eligibility determination.

Zero-value invoices have a numbered journal entry without monetary lines.
Accounts initialize on the first posting; reading empty reports creates no data.
Orders, stock receipts, deliveries, adjustments and supplier returns do not post
money. Purchases are expensed at bill issue. There is no inventory valuation or
cost-of-goods-sold calculation. A purchase bill still covers the full order,
independently of partial receipts and returns awaiting replacement.

The design uses double-entry posting as described in [Odoo's accounting
documentation](https://www.odoo.com/documentation/19.0/applications/finance/accounting.html),
consulted 2026-10-28. These fixed accounts and direct bank/cash settlement rules
are KERP's implementation; they do not imply Odoo configuration or feature parity.

## Cancellation and correction

An unpaid issued document can be cancelled. Choose **Cancellation posting date**
before Cancel; the default is today or the invoice date, whichever is later.
The date must not precede the original entry and must be open. Cancelling a draft
has no accounting effect. Paid documents and documents with any payments remain
protected from cancellation.

Cancellation retains the original posting and adds a linked entry with swapped
debits and credits. Retrying cancellation creates no second reversal. Returning
the cancelled document to Draft creates no entry. Correcting and reissuing it
creates a new posting, retaining the original and reversal. Change the invoice
date before reissue if its old date is closed. Reversals in a later period leave
closed-period reports intact.

## Existing documents

Migration `0005_accounting_ledger` adds tables and constraints without rewriting
existing documents or creating historical financial rows. New issues and payments
post automatically. A newly created demo workspace also includes its postings.
Repeating the demo command leaves existing demo workspaces unchanged.

Accounting displays an incomplete-reports notice if issued/paid invoices or
payments lack entries. An owner/admin can select **Import historical postings**.
It posts current issued/paid documents and recorded payments on their original
dates in one company-locked transaction. Repeating it adds nothing. An error
rolls back the complete import. Existing cancelled documents have no reconstructable
issue/cancellation history and are not invented as historical postings. Drafts
are excluded. An older issued document cancelled before import posts its issue
and reversal together through the normal cancellation transaction.

Import existing history before relying on reports. An incomplete notice remains
until all eligible sources have postings. There is no automatic modification of
every existing company's ledger during migration or page reads.

## Posting-date locks and permissions

All active members can read accounting, matching the existing company-wide role
policy. Owners/admins can issue documents, record payments and import history.
Only owners can use **Close dates**. The lock blocks entries dated on or before
the chosen date, including issue, payment, historical import and reversal.
It does not prevent a reversal on a later open date.

The lock can only move forward, cannot be future-dated, and requires the current
settings version. Missing historical postings in the closing range block closure.
Drafts do not block closure; backdated drafts must be redated before issue.
The dialog explains the permanent lock before submission. No unlock endpoint is
provided. Closing dates logs activity; a stale settings request returns 409.
Completed issue/payment/cancellation retries do not create new entries even when
their original dates are now locked.

Posted entries, lines, account definitions and locks have no direct edit/delete
APIs. Django Admin exposes them read-only. The write services validate balanced
amounts, use the company lock and unique source keys, and create entries atomically
with their source changes. Journal lines enforce one positive debit or credit in
the database. This is application-level integrity, not protection against a trusted
database administrator changing rows directly.

## Reports

- **Trial balance:** opening debit-minus-credit before From, period debit/credit,
  and closing debit/credit through the inclusive Through date. Click an account to
  inspect its period entries. Export CSV includes all eight accounts and totals;
  the filename identifies company, currency and dates.
- **Profit & loss:** period sales revenue, purchases expense and their difference.
  Payments affect cash and outstanding balances, not recognized revenue/expense.
- **Balance sheet:** all ledger assets, liabilities and accumulated earnings
  through the end date, including earlier periods. Its balance check is
  assets minus liabilities minus accumulated earnings. There are no opening
  capital balances or year-end equity closing entries in this phase.
- **Journal entries:** paginated, expandable balanced entries with date, account,
  journal, partner/reference search and scoped invoice/order filters. An account
  filter keeps all lines of matching entries so both sides remain visible.

These reports represent transactions posted in KERP. They do not claim complete
real-world bank balances or certified statutory financial statements. Existing
dashboard confirmed sales remain order totals; accounting revenue follows issued
invoices, excludes tax, and respects posting/reversal dates.

## Remaining scope

Custom/manual accounts and journals, opening balances, manual adjustments,
credit notes/refunds, payment reversal, bank feeds and statement reconciliation,
partial/standalone billing, receivable aging, foreign exchange, fixed assets,
analytic dimensions, inventory costing, tax returns/e-invoicing and jurisdiction
localization remain separate work. Manual tax percentages are posted as entered;
this phase does not determine recoverability, exemptions or filing treatment.

See [API reference](ERP-API.md), [user walkthrough](ERP-GUIDE.md), and current
[verification](VERIFICATION.md). Regression coverage is in
[test_accounting.py](../backend/apps/business/test_accounting.py),
[MySQL concurrency tests](../backend/apps/business/test_concurrency.py), and
[browser-accounting-flow.mjs](../scripts/browser-accounting-flow.mjs).
