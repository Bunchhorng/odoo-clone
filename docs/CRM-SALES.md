# CRM and Sales workflows

CRM opportunities can now create and track sales quotations. Company permissions
apply to the link, the quotation and every subsequent document action.

## From an opportunity to a quotation

1. Open CRM and save the opportunity with its customer and requirements.
2. Select **New quotation** on its card, in list view, or in its record dialog.
3. Sales opens a new quotation with the available customer and opportunity notes
   filled in. Choose a customer if the opportunity has none, or its contact is
   archived or unavailable for new sales.
4. Add products, quantities, prices and taxes, then select **Save**. Opening the
   form alone creates no order.
5. Follow the **From opportunity** link to return to CRM. **Quotations & orders**
   shows all quotations/orders linked to that opportunity, including cancelled ones.

An opportunity may have multiple quotations. The link is fixed after a quotation
is created. Purchase orders cannot be linked. Archived opportunities retain their
existing quotations but must be restored before creating another one. Creating or
confirming a quotation does not automatically mark its opportunity Won; the team
controls the CRM stage explicitly. CRM's stage selector and **Clear filters** also
clear dashboard drill-down filters.

## Review and confirm

Save or discard local edits before a document action. If another session changes
the document, a stale save or new transition is rejected and the form retains your
edits. **Reload document** loads the current values; it asks before discarding
unsaved edits. Review those values before confirming again. This applies to sales
quotations, purchase RFQs, invoices and bills.

Archiving a customer or product does not prevent editing an existing draft's
notes or retaining its historical selection. Existing archived product lines stay
visible and can be edited or removed. Adding a new line for an archived product,
or selecting a different archived contact, remains prohibited. Saving unrelated
fields preserves the document's saved contact details.

Confirmation, full delivery and invoice-creation retries do not create duplicate
completion activities, stock movements or invoices. An existing result is returned
without changing its version or timestamp. Payment retries retain their existing
request UUID behavior.

## Correct a cancelled invoice or bill

An owner or administrator can select **Return to draft** on an unpaid cancelled
invoice/bill, confirm, correct its dates or notes, save and issue it again. The
same document number and cancellation/restoration activity remain in history.
This does not create a replacement document, reverse a payment, or issue a credit
note. Documents with recorded payments cannot be cancelled or restored. One
invoice/bill per order remains the current model.

## API and upgrades

Apply the additive migration with `python manage.py migrate` (normal Docker
startup also applies migrations). Existing orders have no opportunity link and
existing orders/invoices start at document version 1. No records are deleted.

- Order responses include `opportunity_id`, `opportunity_title` and `version`.
  Creation accepts an optional company-scoped `opportunity_id` for a sale.
- `GET orders/?opportunity_id=<id>` lists linked orders.
  `GET opportunities/?opportunity_id=<id>&active=all` locates a historical link.
  Opportunity responses include `quotation_count`.
- Order/invoice PATCH requests and new actions must send integer
  `expected_version` from the last response. Missing/invalid versions return 400;
  changed versions return 409. Clients must review fresh data before retrying.
  A replay of an already completed order transition, or invoice cancellation,
  returns its existing result without another activity.
- When replacing draft lines, retain their `id` to edit an existing archived
  product line. IDs must belong to that order and cannot be repeated. New lines
  omit `id` and require active products.
- `POST invoices/<id>/actions/` accepts
  `{"action": "restore", "expected_version": <version>}` for an unpaid cancelled
  document. Other invoice actions remain `issue` and `cancel`.

The version requirement changes the API contract for custom clients. See
[ERP-API.md](ERP-API.md) and [VERIFICATION.md](VERIFICATION.md).

Partial delivery/invoicing, customer portals, email quotations, configurable
stages, automatic winning rules and credit notes remain future work.
