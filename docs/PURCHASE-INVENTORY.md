# Purchase and Inventory workflows

Purchase orders support partial receipts, receipt history and supplier returns
awaiting replacement. Inventory adds searchable movement history, adjustment retry
IDs and reversals that preserve the original ledger entries.

## Receive a purchase in parts

1. Create an RFQ in **Purchase**, select an active supplier, and add goods/services.
   Product prices default to cost. Save, review and confirm the purchase.
2. Select **Receive products**. Enter the quantity received now for each goods
   line. The form starts with the remaining quantities; use zero to skip a line.
3. Add a supplier delivery reference or notes and select **Record receipt**.
4. Review **Received**, **Remaining**, **Partially received**, and **Recent receipts**
   on the order. Each receipt gets a `REC` number and retains its date/actor/notes.
5. Repeat for the remaining goods. The order is marked Received only when every
   goods line has its full net quantity. Services create no stock movements;
   service-only purchases can be marked received directly.

Duplicate product lines are tracked separately by their order-line IDs. Confirmed
lines stay immutable. Archived goods can still be received against an existing
confirmed order. Over-receipts and stale order versions are rejected. Once any
stock movement exists, the order cannot be cancelled, including after all goods
have been returned.

## Return damaged goods for replacement

1. Open the order's **Stock movements**, or open **Inventory > Stock movements**.
2. On the original receipt movement, select **Return to supplier**.
3. Enter the quantity and reason, then select **Record return**.

The return cannot exceed that movement's unreturned quantity or available stock.
It creates a negative movement linked to the original receipt, reduces net
received quantities and reopens the order's remaining quantity. Receive replacement
goods through a new receipt. Historical receipts/returns stay in the ledger, even
when the product is archived. Returns cannot target adjustments, deliveries or
another return. This workflow represents returns awaiting replacement.

Vendor bills still cover the full order independently of receipts. Returns do
not change bill totals, create credit notes or reverse payments. Partial billing,
three-way matching/variance rules and permanent-return credits remain future work.
Sales deliveries also remain full-order operations.

## Adjust stock and correct a mistaken count

Open **Stock movements > Adjust stock**, choose an active goods product, enter a
signed change and a reason, then record it. Retrying in the same dialog keeps its
request ID and cannot add the same movement twice.

For an incorrect manual adjustment, select **Reverse adjustment**, provide a
reason and record the reversal. The original is labelled with its reversal ID;
the opposite movement links back to it. Each adjustment can be reversed once,
and a reversal cannot make stock negative. Receipt corrections use supplier
returns instead. Ledger rows are never edited or deleted through these APIs.

## Trace stock

Search product names/SKUs, order/receipt numbers, receipt notes and movement reasons.
Combine movement type, product and From/To dates. Dates use the company application's
Asia/Bangkok timezone. Product cards/lists link to that product's movements;
purchase orders link to their movements. **Clear filters** restores the full ledger.

Owners/admins can receive, return, adjust and reverse. Members can inspect order
progress, receipt history and stock movements. Every endpoint checks company scope;
request IDs do not grant access. Stock checks and writes share the company lock.

## API and upgrade notes

- `GET/POST orders/<id>/receipts/` is purchase-only. POST requires `request_id`
  (UUID), `expected_version` and optional `notes`. Optional `lines` contains
  `{"line_id": <order-line ID>, "quantity": "2.000"}` entries. Omit `lines` to
  receive all remaining goods; an explicit list must be nonempty. Quantities are
  positive with at most three decimal places.
- New receipts return 201 with `receipt`, refreshed `order`, and `replayed=false`.
  The same request/details returns 200/replayed=true even with its original
  version. Changed details with a used UUID return 409. Retain UUIDs during retries.
- Purchase order responses add `receipt_status` (pending/partial/received),
  `has_stock_movements`, and line `received_quantity`/`remaining_quantity`.
- Existing `actions/` with `action=fulfill` remains supported: purchases receive
  only the remaining quantity; already completed requests have no additional effect.
- `POST stock/` accepts an optional UUID `request_id` for compatibility. New UI
  requests always send one. Without it, each submission is a distinct adjustment.
- `POST stock/<movement_id>/return/` requires positive `quantity`, `reason` and
  `request_id`; `POST .../reverse/` requires `reason` and `request_id`.
  Creation returns 201; matching retries return 200 with `replayed=true`.
- `GET stock/` accepts `q`, `kind=all|adjustment|receipt|delivery|return|reversal`,
  `product_id`, `order_id`, `date_from`, `date_to`, `page` and `page_size`.
  Movement responses include source/reversal/return IDs, receipt details,
  `returnable_quantity`, `can_reverse`, and order links. POST responses also
  include the current `stock_quantity`.

Migration `0004_purchase_inventory_ledgers` adds nullable movement links and
receipt history. It matches existing movements to their original order lines and
labels previous purchase receipts `REC-LEGACY-<order ID>`. Quantities and original
movement timestamps are unchanged. An unmatched legacy movement stops the upgrade
for inspection rather than inventing a receipt allocation. Apply migrations during
the normal local startup or with `python manage.py migrate`.

See [ERP-API.md](ERP-API.md) and [VERIFICATION.md](VERIFICATION.md). Warehouses,
locations, reservations, lots/serials, valuation and automated replenishment remain
outside this phase.

The subsequent [Inventory V2 INV-01 milestone](INVENTORY-V2-INV-01.md) adds warehouse
and location configuration plus protected movement endpoints, preserving the
receipt/return behavior described here. Existing posting APIs use the default
warehouse; transfers and reservations remain outside that milestone.
