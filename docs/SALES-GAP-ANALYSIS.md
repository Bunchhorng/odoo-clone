# Sales gap analysis and commercial-workflow dependency plan

Audit date: **2026-11-11, Asia/Bangkok**. This audit covers the current working
tree, including uncommitted INV-01 warehouse/location work and the unverified
start of INV-02A reservation work. It does not claim that either new inventory
capability is production-ready.

## 1. Existing sales architecture and functionality

KERP uses one `Order` model for sales quotations/orders and purchase RFQs/orders.
It has `draft`, `confirmed` and `cancelled` states, Decimal totals, an optimistic
`version`, contact snapshots, and immutable product/description/price/tax snapshots
on `OrderLine` when confirmed. CRM can open a prefilled sale quotation and keeps
company-scoped opportunity links/counts. `OrdersView.vue` provides list, form,
confirmation, full delivery and order-based invoice actions.

`fulfill_order()` is a full-order Inventory-domain operation: it writes one
negative `StockMovement` per goods line after the existing no-negative-stock check.
`invoice_order()` produces a draft `Invoice` from the entire order. `Invoice.order`
is currently one-to-one; invoice detail renders current order lines rather than
independent invoice-line allocations. Accounting issues invoice-level balanced
journal entries and payment/reversal records. Those posting responsibilities
remain in the Accounting domain.

Existing verified scope includes quotation creation/editing, server Decimal
calculations, manual percentage line tax, document-version conflict rejection,
confirmation, protected full delivery, one full-order customer invoice, partial
and full manual payments, invoice cancellation/reissue boundaries, and CRM links.

## 2. Gap analysis against selected Odoo 19 behaviour

| Capability | Current KERP state | Status |
| --- | --- | --- |
| Draft quotation, contact and line snapshots | Present. | Implemented within current scope |
| Sent/accepted/rejected/expired quote states | No distinct state/audit workflow. | Missing |
| Customer invoice/delivery addresses | Only one contact-address snapshot. | Missing |
| Quantity tracking | Ordered quantity only. | Missing |
| Partial delivery/backorders/reservations | Inventory dependency is not verified or complete. | Missing |
| Delivery/invoice progress statuses | `fulfilled_at` and one `invoice_id` only. | Missing |
| Multiple/partial invoices | Prevented by `Invoice.order` one-to-one relation. | Missing |
| Discounts/pricelists | No models or policy; prices are directly entered. | Missing |
| Tax/fiscal rules | Manual line percentage only. | Partial |
| Customer returns/credit notes/refunds | No customer return; supplier return only. | Missing |
| PDF/send/signature/customer portal | Browser print only; no secure sharing or generated PDF. | Missing |
| Sales roles/discount approval | Company owner/admin/member roles, no sales-specific policy. | Partial |
| Sales reporting | Dashboard is all-time operational summary, not sales reporting. | Partial |

Odoo documents ordered- and delivered-quantity invoicing policies, including
multiple invoices after partial deliveries; it also documents a draft invoice as
having no accounting impact until confirmation. KERP should reproduce selected
business outcomes in its own Django/Vue implementation rather than copy Odoo
code/assets. The documentation does not establish a granular Community/Enterprise
entitlement for every proposed extension, so no such claim is made here.

References: [Odoo 19 invoicing policies](https://www.odoo.com/documentation/19.0/applications/sales/sales/invoicing/invoicing_policy.html),
[customer invoices](https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices.html),
and [reservation methods](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/reservation_methods.html).

## 3. Required data-model changes

The commercial core needs independent documents and allocation lines, not new
flags overloaded onto `Order` or `StockMovement`.

| Model | Required change | Ownership |
| --- | --- | --- |
| `OrderLine` | Preserve existing `quantity` compatibility; derive/store ordered, reserved, delivered, returned and invoiced progress from authoritative allocations. Snapshot invoicing policy at confirmation. | Sales read model, Inventory/Accounting allocations authoritative |
| `StockOperation` / lines / reservations | Delivery, backorder, transfer and customer-return physical operations with immutable completed lines. | Inventory |
| `Invoice` | Replace one-to-one order link with a source-order foreign key during a safe data migration. | Sales/Accounting boundary |
| `InvoiceLine` | Immutable quantity, price, tax, totals and source-order-line/delivery allocation snapshots. | Sales invoice creation; Accounting uses invoice totals for posting |
| Later pricing models | Pricelist, rule, discount approval and tax/fiscal entities. | Separate Sales pricing milestone |

Confirmed order lines and issued invoices must remain immutable. Posted journals
are not edited to correct quantity; later corrections require explicit physical
return and financial credit-note workflows.

## 4. API plan

Preserve existing company-scoped `/api/v1/companies/{company_id}/erp/` routes and
fields during migration. Do not introduce the prompt’s unscoped `/api/v1/sales/`
names as a parallel API.

1. Inventory owns order reservation and delivery-operation endpoints, including
   operation validation/backorder/release/retry semantics.
2. Sales `GET orders/{id}/` adds derived per-line progress and independent
   delivery/invoice smart-button counts while retaining existing fields.
3. Sales `GET/POST orders/{id}/invoices/` lists related invoices and creates a
   draft invoice from explicit eligible quantities after Inventory verifies
   delivered-quantity availability.
4. Invoice detail returns stored `InvoiceLine` data; it no longer reads mutable
   order lines. Accounting’s existing issue/payment/reversal endpoints remain the
   posting authority.
5. Later quote sending, pricing, return/credit, portal and reporting each need
   separate endpoints and acceptance scopes.

Every mutation uses company-scoped lookups, backend authorization, atomic
transactions, optimistic document versions where edited, and UUID/payload-digest
idempotency for irreversible creation/validation.

## 5. Vue UI plan

`OrdersView.vue` should gain separate quote, delivery, invoice and payment status
indicators; ordered/reserved/delivered/invoiced/returned quantities; and smart
buttons to working delivery and invoice lists. A Create Invoice dialog must query
server-calculated invoiceable quantities and cannot authoritatively calculate them
in Vue. `InvoicesView.vue` must render immutable invoice lines and link to source
delivery allocations. New delivery/operation pages belong to Inventory, not Sales.

Later pricing/discount UI, quotation send/PDF/portal, approval flows and reporting
must not show decorative buttons before their backend policies exist.

## 6. Dependency analysis and implementation order

The requested first Sales milestone is blocked by Inventory’s physical workflow:

```text
Reservations + delivery operations + backorders (Inventory, verified)
    -> delivered/returned quantities (Inventory read model)
    -> invoiceable quantities and invoice allocations (Sales)
    -> immutable invoice lines + accounting posting (Accounting)
    -> returns/credit notes, pricing, approvals, portal and reporting
```

Current gate: `StockReservation` and its endpoint were started but have no focused
tests, release API, automatic confirmation policy, partial-delivery document or
backorder implementation. Existing regression tests are blocked by a corrupted
disposable `test_kerp` test database created by an interrupted runner. This is a
test-environment condition, not proof that the feature works or fails.

Therefore the next code milestone must finish and verify **INV-02A: reservations,
partial delivery and backorders**. Only then should work begin on **SA-02A:
multiple/partial invoice allocations**. Discounts/pricelists, credit notes,
approvals, portal/PDF and reporting are later distinct milestones.

## 7. Test plan and acceptance criteria

INV-02A must prove reservation capacity, release/retry, partial delivery,
backorder reconciliation, no duplicate movement, company isolation, role
permissions and concurrent reservation/delivery safety. Existing sales, purchase,
inventory, accounting and browser tests must remain green.

SA-02A may begin only after that evidence. It must prove that delivery batches of
6 and 4 from an order of 10 create separate draft invoices of 6 and 4 under
delivered-quantity policy; no invoice may exceed `delivered - invoiced`; retried
creation creates one invoice/allocation/journal; issued invoices balance; and
legacy one-invoice records migrate with their totals/journal links unchanged.

No code was changed by this Sales audit. The Sales parity statuses must remain
unchanged until the dependency and all stated tests pass.
