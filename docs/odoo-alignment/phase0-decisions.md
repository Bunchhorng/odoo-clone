# Phase 0 — decisions for the Phase 1–2 blockers

**Status:** decision document only. No application code, model, migration, setting, or API change has been made.

**Evidence date:** 2026-11-18. Live `kerp` was queried read-only through the isolated backend. API paths below are relative to `/api/v1/companies/{company_id}/erp/`. Odoo concepts are a behavioural reference only; no Odoo source code is proposed or copied.

## Roadmap corrections accepted

| Decision | Recommendation | Reason |
|---|---|---|
| Partner defaults before redesign | **Move a small but real Partner/Contact redesign to the beginning of Phase 3**, then add payment terms, fiscal positions, and pricelists to it. Do not add the three nullable defaults to today's flat `Contact` first. | A temporary default on current `Contact` would later need copying through person/company/address redesign, creating ambiguous ownership and inheritance. Partner core gives commercial documents one canonical partner and adds each property once. |
| Phase 3 partner scope | First establish partner identity, company/person type, parent/address relationships, active state, and stable API compatibility. Then add nullable, company-scoped `property_payment_term_id`, `property_supplier_payment_term_id`, `property_account_position_id`, and `property_product_pricelist_id`, with explicit inheritance rules. | This matches the purpose of Odoo partner defaults without pretending the current contact row models them safely. [Odoo accounting setup](https://www.odoo.com/documentation/19.0/applications/finance/accounting/get_started/initial_configuration/setup.html) identifies payment terms and fiscal position as contact-related configuration. |
| Extension/localization facilities | Put custom fields, automated/server actions, scheduled jobs, and languages/translations in the final extension/localization phase. | They magnify an unstable model and security surface; the business models, registry, and audit boundary must stabilize first. |

## Baseline rules for a later build

* All new business records are company-scoped unless explicitly global (the currency catalogue).
* Never invent a financial rate, tax rule, or packaging conversion from a display string. Preserve historical facts and report ambiguous data.
* Use additive, dual-read/dual-write cutovers. Removing a legacy field is a later approved release after reconciliation and rollback windows.
* New routes enter the endpoint registry and pass the unmapped-route test. Parent access is resolved afresh on every request; role/group/override changes may not be served from a stale permission decision.

## 1. Legacy Activity → generic thread, message, follower, and scheduled activity

### Current state and live `kerp` inventory

| Item | Current models and fields | Existing endpoint surface | Live count |
|---|---|---|---:|
| Legacy activity | `business.Activity(CompanyRecord)`: `company`, `actor_email`, free-text `resource`, integer `record_id`, `summary`, inherited timestamps | No direct activity API; service code writes it and `GET /dashboard/` serializes it | **10**: contacts 3, employees 3, orders 2, products 1, projects 1 |
| Helpdesk-only message | `business.TicketMessage`: `ticket`, `request_id`, `body`, `kind`, `actor_email`, timestamps | `GET`/`POST /helpdesk/{id}/messages/` | **0** |
| Generic collaboration | No thread, generic message, follower, scheduled activity, activity type, or attachment model | None | **0** of each absent model |

The current live database has five companies (IDs 3, 4, 85, 94, and 95). `Activity.resource` has no foreign key or constrained vocabulary, so every legacy link must be validated before conversion.

### Options and recommendation

| Option | Trade-offs | Decision |
|---|---|---|
| Extend `Activity(resource, record_id)` | Small up front, but keeps an unvalidated parent and requires each app to rebuild messages/files/followers and access checks. | Reject. |
| One chatter table family per business model | Gives ordinary database foreign keys and simple local cascades, but duplicates APIs, rights, migrations, UI, and test matrices for every app. | Reject. |
| Common thread tables with a whitelisted generic parent | Gives one Chatter-like foundation and one parent-access contract. It needs explicit whitelist and deletion lifecycle because the generic parent is not a database FK. | **Recommend.** Use Django `ContentType` plus object ID and a project-owned parent registry. |

Odoo's Chatter combines notes/messages, files, followers, and planned activities on a record. [Odoo Chatter](https://www.odoo.com/documentation/19.0/applications/productivity/discuss/chatter.html) and [Odoo Activities](https://www.odoo.com/documentation/19.0/applications/essentials/activities.html) are the behavioural reference.

### Target models and fields

| Target model (Odoo concept) | Proposed fields and invariants |
|---|---|
| `BusinessThread` (`mail.thread`) | `company`, `content_type`, `object_id`, `created_at`; unique `(company, content_type, object_id)`. Lazy-created only for a registered parent. |
| `BusinessMessage` (`mail.message`) | `thread`, nullable `author_user`, immutable `author_email` snapshot, `message_type` (`comment`, `note`, `system`), `subtype`, `body`, `created_at`, optional reply/reference metadata. Converted legacy activity becomes `system`. |
| `BusinessFollower` (`mail.followers`) | `thread`, internal `user` or partner/contact, subscription/subtype choices, `is_active`; one active subscriber per thread. External delivery is not in the first feature unless separately approved. |
| `ActivityType` | `company`, `name`, `icon`, default delay/summary, `active`; configuration rather than a scheduled record. |
| `ScheduledActivity` (`mail.activity`) | `thread`, `activity_type`, `assigned_to`, `summary`, `note`, `date_deadline`, `state` (`planned`, `done`, `cancelled`), `completed_at`, `completed_by`. Completion writes a system message. |
| `Attachment` (`ir.attachment`) | `thread`, optional `message`, `name`, `mimetype`, `size`, private content-store key/checksum, `uploaded_by`, `created_at`. Never expose an unguarded public object-store URL. |

`content_type` is limited by `THREADABLE_RESOURCES`: one central mapping from ContentType to canonical resource name, model, parent loader, owning app key, deletion policy, and access resolver. Clients cannot submit arbitrary model names.

### Data migration and company defaults

1. Add new tables without destructively changing `Activity` or `TicketMessage`.
2. For every `Activity`, verify `(company, resource, record_id)` resolves through `THREADABLE_RESOURCES` and belongs to that company. Create/find its thread, then create a `BusinessMessage(message_type="system")` with the same timestamp, summary, and actor-email snapshot. Fill `author_user` only if the email resolves, without replacing the snapshot.
3. For an unknown resource, missing parent, or cross-company parent, keep the legacy activity and create a migration exception report. Do not attach it to a guessed record.
4. Convert every `TicketMessage` to a message on its HelpdeskTicket and retain `request_id` as an idempotency reference. Keep the old table readable until samples, counts, and API parity reconcile.
5. Create no followers, planned activities, or attachments by default. Threads remain lazy. After product approval, seed a small per-company activity-type set (for example To-do, Call, Email, Meeting), not notification preferences.

### Compatibility, rollback, registry, rights, tests

| Area | Decision |
|---|---|
| Existing API and Vue | Keep dashboard legacy-activity serialization and the helpdesk messages endpoint during dual-read. Add parent-scoped thread routes; move Vue record pages one at a time. Retain legacy payload keys until that page is proven equivalent. |
| Rollback | Reversible while legacy tables remain and writes are mirrored. New messages/files/followers/activities cannot be losslessly flattened to `Activity`; after creation, rollback means preserve the new tables read-only or restore a backup, never delete data. |
| Endpoint registry | Register only parent-scoped routes such as `/orders/{id}/thread/`, `/thread/messages/`, `/thread/attachments/`, `/thread/followers/`, `/thread/activities/`. There is no raw-child-ID-only route. Each registry entry delegates to the parent resolver. |
| Seeded rights | Parent `read` is required to list/read thread data or download a file. Parent write, plus a narrowly named chatter action if later needed, is required to post/upload. Activity scheduling/completion also checks parent and assignee. Activity-type configuration is Admin/Owner; normal Members receive only capabilities granted by the parent. |
| Required tests | Parent inheritance on every operation; cross-company IDs; registry completeness; no attachment metadata/signed-URL leak; permission changes visible next request; legacy conversion/reconciliation; parent deletion policy; Vue payload compatibility. |

### Risks and questions

* Approve the initial `THREADABLE_RESOURCES` list (contacts, products, orders, invoices, projects, tasks, tickets, employees, and timesheets are candidates).
* Decide whether external followers/mail are in the first release; they add consent, templating, delivery, and audit decisions.
* Decide attachment retention, storage/encryption, file-size/type policy, and whether deletion is soft/audited.

## Generic relation and inherited-permission decision

| Criterion | Django `ContentType` + `object_id` | `(model_name, id)` string pair | Decision |
|---|---|---|---|
| Model identity | Normalized Django identity and controlled rename migration path. | Free text drifts (`orders`, `sale.order`, `Order`) and needs application-wide cleanup. | Prefer **ContentType**. |
| Referential integrity | No actual heterogeneous-parent database FK; validation/deletion still belong to the application. | Also no actual FK, with no normalized model identity. | Neither is sufficient without a whitelist. |
| API clarity | API exposes the canonical resource name from the registry, not internal ContentType IDs. | Leaks a loose implementation string to clients. | ContentType wins. |
| Record rules/registry | One mapping chooses the parent loader and existing company/record-rule resolver. | Requires a second model-name mapping and risks accepting an unregistered model. | ContentType plus mandatory `THREADABLE_RESOURCES`. |
| Parent deletion | A service locates threads for a registered type and applies the declared archive/cascade policy. | Similar work, with fragile strings. | ContentType wins, but lifecycle remains explicit. |

**Required parent access algorithm:** first resolve the parent through its canonical resource and existing company/record-rule resolver; only then load the thread or child. Collection/search queries start from parents visible to the requester, then join children. File metadata and download repeat the parent check on every request. The endpoint registry stores the parent rule, not an independent “attachment read” grant.

Thus a user unable to read a sale order cannot see its chatter, followers, activities, attachment metadata, or file bytes. For writes, parent write is the baseline. A future finer `comment`/`schedule` action may narrow that capability but never bypasses parent access. A short-lived storage URL may be issued only after that request-time check.

## 2. Currency strings → currency and rate records

### Current state and live `kerp` inventory

| Item | Current models and fields | Existing endpoint surface | Live count |
|---|---|---|---:|
| Company setting | `WorkspaceSettings.currency`: three-character choice string (`USD`, `THB`, `EUR`, `GBP`, `SGD`, `AUD`, `CAD`) | `GET`/`PATCH /settings/` | **1** setting, USD |
| Commercial documents | `Order.currency`, `Invoice.currency`: three-character strings with numeric totals | `GET`/`POST /orders/`, `PATCH /orders/{id}/`, `GET /invoices/`, `GET`/`PATCH /invoices/{id}/` | **7** orders USD; **3** invoices USD |
| Accounting | `JournalEntry.currency`: string | `/accounting/entries/`, invoice/payment actions | **0** journal entries |
| Master/rates | No currency master or rate model | No currency/rate route | **0** |

### Options and recommendation

| Option | Trade-offs | Decision |
|---|---|---|
| Extend the fixed string choices | Lowest code cost, but cannot carry symbols, rounding, dates, company-specific rates, or a credible multi-currency path. | Reject. |
| Duplicate a Currency master for each company | Straightforward isolation, but duplicates code/symbol metadata and makes corrections/reporting needlessly difficult. | Reject. |
| Global Currency, company activation/defaults, and dated company rate rows | Clean master data and matches Odoo's global catalogue with dated/company-specific rates. It needs explicit historical-rate semantics. | **Recommend.** |

Odoo documents a global currency catalogue and rates dated and optionally tied to a company. [Foreign currencies](https://www.odoo.com/documentation/19.0/applications/sales/sales/products_prices/prices/currencies.html) and [multi-currency](https://www.odoo.com/documentation/19.0/applications/finance/accounting/get_started/multi_currency.html) are the behavioural reference.

### Target models and fields

| Target model (Odoo concept) | Proposed fields and invariants |
|---|---|
| `Currency` (`res.currency`) | Global `code` (unique, uppercase ISO where applicable), `name`, `symbol`, `position`, `decimal_places`, `rounding`, `active`. |
| `CompanyCurrency` | `company`, `currency`, `active`, `is_company_currency`; unique `(company, currency)`, exactly one active company currency. |
| `CurrencyRate` (`res.currency.rate`) | `currency`, `company`, `name` (effective date), `rate`, `inverse_rate`, timestamps; unique `(company, currency, name)`. Define and test the rate direction once. |
| Settings/documents | `WorkspaceSettings.currency_id`, `Order.currency_id`, `Invoice.currency_id`, `JournalEntry.currency_id`. A posted accounting document also stores its applied rate and company-currency amount/snapshot; draft orders do not fabricate an accounting conversion. |

### Data migration and company defaults

1. Seed the global catalogue only for observed/supported codes, with metadata from an approved maintained reference. Normalize legacy strings by trim/uppercase; unknown values go to an exception report, not a guess.
2. For every company with a settings row, create/activate its selected currency and mark it company currency. The measured data creates one USD setting. A company without settings does not receive an invented foreign rate; any default remains a separately approved product choice.
3. Map all measured document values (`USD`: 7 orders and 3 invoices) to the USD row. Retain the legacy string during compatibility and reconcile code equality.
4. Create a `1.0` rate only for each company currency. Do not manufacture historical foreign rates. A foreign-currency legacy document with no verified rate gets `legacy_rate_missing` and remains in its original currency until corrected.

### Compatibility, rollback, registry, rights, tests

| Area | Decision |
|---|---|
| Existing API and Vue | Continue accepting/returning `currency: "USD"`; add `currency_id`, `currency_code`, symbol/rounding display data, and applicable rate metadata. Change selectors only after fields reconcile. |
| Rollback | Reversible while strings remain and no posted document depends on a new rate snapshot. Do not delete a rate used by a posted entry; later legacy-string removal needs backup plus an approved irreversible-release plan. |
| Endpoint registry | Add `/currencies/` and company-scoped `/currency-rates/` only when built, with explicit registry entries. Existing settings/orders/invoices validate a reference rather than authorize a raw ID. |
| Seeded rights | Users who can make/read a document may read its active currencies/rates. Currency/rate configuration is Accounting Admin/Owner; Members are read-only. |
| Required tests | Normalization/unknown-code report; exactly one company currency; dated-rate selection/direction; no invented historical rate; rounding; cross-company isolation; posted snapshot immutability; registry/role and old/new payload tests. |

### Risks and questions

* Choose the reference data owner, launch currencies, symbols, precision, and activation policy.
* Decide whether company currency becomes immutable once entries are posted. Recommended: restrict it and use a controlled migration, not ordinary edit.
* Decide who enters rates, the date/time-zone rule, and whether an automatic provider is deferred to the final scheduled-jobs phase.
* Gains/losses and accounting postings are later Accounting decisions; Phase 2 must preserve facts without creating fictitious journal entries.

## 3. `Product.unit` text → UoM category and UoM records

### Current state and live `kerp` inventory

| Item | Current models and fields | Existing endpoint surface | Live count |
|---|---|---|---:|
| Product unit | `Product.unit`: free `CharField(max_length=30)`, default `"Units"` | Generic `GET`/`POST /products/`, `GET`/`PATCH /products/{id}/`; catalogue import/export | **9** products: `Units` 6, `Hours` 2, `Doloremque iusto nesciunt inc` 1 |
| Line quantities | `OrderLine.quantity`, `InvoiceLine.quantity`; neither has a UoM snapshot | Orders/invoices routes | **7** order lines; **3** invoice lines |
| Conversion/category | No UoM model, category, factor, rounding, purchase UoM, or validation | None | **0** |

### Options and recommendation

| Option | Trade-offs | Decision |
|---|---|---|
| Canonicalize the text field only | Improves spelling but supplies no category, rounding, or conversion safety. | Reject. |
| Per-company free-form UoM records without categories | Establishes references but allows invalid conversions between hours, pieces, and kilograms. | Reject. |
| Company UoM categories and UoMs with a reference unit/factor | Safely supports same-category conversion and Odoo-like product/inventory/sales behaviour. Ambiguous legacy labels need review. | **Recommend.** |

Odoo permits conversion through a UoM category/reference unit and requires a product's purchase and default UoMs to share a category. [Odoo Units of Measure](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/product_management/configure/uom.html) is the behavioural reference.

### Target models and fields

| Target model (Odoo concept) | Proposed fields and invariants |
|---|---|
| `UoMCategory` (`uom.category`) | `company`, `name`, `active`; unique name per company. |
| `UoM` (`uom.uom`) | `company`, `category`, `name`, `uom_type` (`reference`, `bigger`, `smaller`), `factor`, `factor_inv`, `rounding`, `active`. Exactly one reference UoM per category; conversion only inside a category. |
| Product fields | `uom_id` for inventory/sales; a future purchase UoM must be same-category. Temporary `legacy_unit_label` exists only for reconciliation. |
| Line fields | `uom_id`, immutable `uom_name` snapshot, quantity. A document retains the UoM selected at entry even if the product changes later. |

### Data migration and company defaults

1. Create per-company **Units** category and reference **Unit(s)** UoM (`factor=1`, approved rounding). Do not create a universal conversion catalogue without agreed factors.
2. Case-fold unambiguous `pcs`, `Pcs`, `pc`, `piece`, `pieces`, and `units` to **Unit(s)** while preserving the original in `legacy_unit_label`.
3. Map `Hours` to a separate **Time** category and reference **Hour(s)** UoM, factor 1. The measured `Doloremque iusto nesciunt inc` is not a unit: make no conversion; report it and require operator selection before new operations.
4. Treat `box` as ambiguous until its base-unit ratio is supplied. Do not assume 6, 12, or another ratio. If the business only counts boxes, it may be a reference **Box** in a temporary separate category; merge only after a verified factor exists.
5. Backfill each line from its product's mapping and snapshot its name. For ambiguous history, preserve quantities/totals and flag remediation; never alter a quantity to force conversion.

### Compatibility, rollback, registry, rights, tests

| Area | Decision |
|---|---|
| Existing API and Vue | Keep `unit` as existing display name while adding `uom_id` and `uom`. Temporarily accept a string only if it resolves uniquely inside the company; otherwise return a remediation validation error. Keep imports/exports working and add explicit UoM columns. |
| Rollback | Reversible while `Product.unit`, temporary labels, and snapshots remain. Later merging/retiring ambiguous UoMs is not losslessly reversible without the mapping audit. |
| Endpoint registry | Register `/uom-categories/` and `/uoms/` when introduced; product/order/invoice routes validate same-company, same-category references. |
| Seeded rights | UoM configuration is Admin/Owner. Members who may edit products/documents may read active UoMs but cannot create arbitrary ones in a product payload. |
| Required tests | Case normalization; ambiguity report; one reference per category; same-category conversion/rounding; product/line snapshots; import/export compatibility; cross-company, registry, and role matrix tests. |

### Risks and questions

* Provide approved categories, precision/rounding, and conversion factors for stock, time, weight, volume, and packaging.
* Decide whether `box` is a UoM, a packaging concept, or both. Odoo distinguishes them; packaging must not silently become a conversion.
* Decide whether service products default to hours, days, or units; product `kind` alone is not enough evidence.

## 4. `OrderLine.tax_rate` and `InvoiceLine.tax_rate` → tax records

### Current state and live `kerp` inventory

| Item | Current models and fields | Existing endpoint surface | Live count |
|---|---|---|---:|
| Order tax | `OrderLine.tax_rate`: `Decimal(5,2)`, range 0–100; `subtotal`, `tax_total`, and `total` stored on line | `POST /orders/`, `GET`/`PATCH /orders/{id}/`, order actions | **7** lines: 7.00% 6; 0.00% 1 |
| Invoice tax | `InvoiceLine.tax_rate`: `Decimal(5,2)` plus stored totals | Invoice generation; `GET /invoices/`, `GET`/`PATCH /invoices/{id}/`, invoice actions | **3** lines: 7.00% 3 |
| Tax configuration | No tax, tax group, product default tax, fiscal-position mapping, tax account, or report model | None | **0** |

### Options and recommendation

| Option | Trade-offs | Decision |
|---|---|---|
| Retain decimal rate and add labels | Minimal, but lacks sale/purchase applicability, tax identity, group, fiscal mapping, or credible accounting evolution. | Reject. |
| Minimal `Tax(name, rate)` with one line FK | Improves naming but cannot express multiple taxes, price inclusion, fixed amounts, sequence, or fiscal positions. | Reject. |
| Company Tax/TaxGroup records with line tax relations and frozen line facts | Supports multiple taxes and future fiscal mapping using Odoo concepts. Phase 2 deliberately enables only tested percentage/excluded tax. | **Recommend.** |

Odoo applies configured taxes on individual sales, purchase, and accounting lines, then computes the tax from the configuration; fiscal positions can map those taxes. [Odoo Taxes](https://www.odoo.com/documentation/19.0/applications/finance/accounting/taxes.html) and [tax computation](https://www.odoo.com/documentation/19.0/applications/finance/accounting/taxes/tax_computation.html) are the behavioural references. Repartition, localization, returns, and accounting posting remain later Accounting work.

### Target models and fields

| Target model (Odoo concept) | Proposed fields and invariants |
|---|---|
| `TaxGroup` (`account.tax.group`) | `company`, `name`, `sequence`, `active`; display/report grouping. |
| `Tax` (`account.tax`) | `company`, `name`, `tax_group`, `type_tax_use` (`sale`, `purchase`, `none`), `amount_type` (`percent`, later `fixed`, `division`, `group`), `amount`, `price_include`, `include_base_amount`, `sequence`, `active`. Phase 2 enables only tested percentage/excluded behaviour. |
| Line tax relation | `OrderLine.tax_ids` and `InvoiceLine.tax_ids` through explicit relation tables. Calculation saves selected tax identity/rate/name facts for historical display; posted Accounting later owns immutable tax-entry facts. |
| Deferred defaults | Product sales/purchase taxes and fiscal positions wait for Partner core and Accounting. This migration invents no default rate. |

### Data migration and company defaults

1. Create a **Taxes** group per company only where needed. Do not seed a legal rate or claim a localization without a jurisdiction decision.
2. For every distinct non-zero legacy rate per company, create separate active `Legacy Sales {rate}%` and `Legacy Purchase {rate}%` percentage/excluded taxes as required by order/invoice kind. Map `7.00` exactly; map `7.5` exactly to `7.50%`, never 7% or 8%.
3. Map zero-rate rows to **no selected tax**, retaining `tax_rate=0` as the compatibility/historical aggregate. Do not mislabel absence of tax as a configured legal 0% exemption.
4. Attach tax relations without recalculating legacy `subtotal`, `tax_total`, or `total`. A recomputation mismatch is a migration exception, never a rounding overwrite.
5. New products/documents default to no tax until the company chooses a default. No rate is inferred from the measured 7% demo/history values.

### Compatibility, rollback, registry, rights, tests

| Area | Decision |
|---|---|
| Existing API and Vue | Continue returning/accepting `tax_rate`; add `tax_ids` and tax breakdown. A transition request may use either representation, never contradictory values. Keep the current aggregate in Vue until its line editor supports selected tax records. |
| Rollback | Reversible while decimal/totals remain. Once a document uses multiple/complex tax relations, flattening to one decimal loses meaning; rollback must preserve new tables or restore a backup, not overwrite data. |
| Endpoint registry | Register `/tax-groups/` and `/taxes/` when built. Existing order/invoice routes validate same-company ownership and applicability using registered policy. |
| Seeded rights | Users who can draft relevant documents may read active taxes. Tax configuration, activation, and defaults are Accounting Admin/Owner actions; a Member cannot create/change a rate in line input. |
| Required tests | Exact 7.5 mapping; no-tax semantics; sale/purchase applicability; multi-tax relation and sequence; reject price-included until supported; unchanged legacy totals/snapshots; cross-company, registry, and role tests. |

### Risks and questions

* Identify each company's jurisdiction, legal tax identifiers, accounts, and rounding method. A generic 7% is not legal configuration.
* Decide tax-included versus tax-excluded pricing by company/document. Recommendation: tax-excluded only until an explicit inclusive-calculation suite is accepted.
* Decide whether multiple/compounding taxes must be enabled immediately. Recommendation: establish the relation now, but expose it only after calculation tests pass.

## Work order inside Phases 1 and 2

### Phase 1 — secure collaboration foundation

| Order | Feature | Depends on | Completion gate |
|---:|---|---|---|
| 1 | Threadable-parent registry and parent-access resolver | Existing company/record-rule resolver and endpoint registry | Whitelist, deletion policy, cross-company/role-change tests, and unmapped-route test pass before child data is exposed. |
| 2 | `BusinessThread` and migrated read-only system timeline | 1 | Legacy `Activity`/`TicketMessage` reconciliation has no silent orphan/cross-company attachment; dashboard compatibility remains. |
| 3 | Messages and followers | 1–2 | Parent-read/write inheritance, no raw-child-ID authorization, Vue record page parity, and follower audit tests pass. |
| 4 | Private attachments | 1–3 | Private storage/download path, metadata/file inheritance, size/type controls, deletion/audit policy, and leak tests pass. |
| 5 | Activity types and scheduled activities | 1–3 | Assignment/completion lifecycle, parent/assignee access, system-message trace, and due-date tests pass. |

### Phase 2 — commercial reference data foundation

| Order | Feature | Depends on | Completion gate |
|---:|---|---|---|
| 1 | Currency catalogue, company currency, dated rates | Company isolation and settings compatibility | Current strings reconcile; one-company-currency invariant; rate-date/direction/rounding tests; no invented historical rate. |
| 2 | UoM categories and UoMs | Product/catalogue compatibility | Every product/line maps or is an explicit exception; conversion/rounding and import/export tests pass. |
| 3 | Tax groups and percentage taxes | Currency rounding contract; sale/purchase line calculation | Legacy totals reconcile; exact decimal/no-tax tests pass; unsupported calculation modes rejected. |
| 4 | Vue reference-data editors | 1–3 | New/old API payloads remain compatible during transition; visible calculations and permissions match backend tests. |

## Definition of done for every Phase 1–2 feature

- Plan reviewed and explicitly approved before coding; one feature completes before the next begins.
- Models plus auditable migration/reconciliation report, no guessed values, tested forward and reverse/rollback behaviour.
- Validated API/error contract, with declared compatibility window for existing clients.
- Every route is in the endpoint registry and the unmapped-route guard passes.
- Company isolation, parent/record-rule permissions, seeded Admin/Member rights for every new stable app key, and useful preset groups.
- Unit, migration, permission, integration, regression, and Vue tests; next-request tests prove role/group/override changes do not use stale permission state.
- Complete Vue UI including loading/error/empty states; no hidden raw-ID authorization path.
- Documentation: API/operations note, rollback/data plan, and concise gap note against the relevant Odoo concept.
- Required full verification recorded before the next feature begins.

## Decisions needed before any implementation

1. Approve ContentType-plus-whitelist generic parents and parent-inherited permissions for chatter, activities, and attachments.
2. Identify the first threadable record types and whether external followers/mail are in first release.
3. Provide approved UoM categories, precision, factors, the meaning of `box`, and correction for the invalid legacy label.
4. Identify each company's tax jurisdiction, default-tax policy, price-included rule, and whether 7% is legal configuration or demo data.
5. Approve the Phase 3 Partner-core-first adjustment before payment terms, fiscal positions, and pricelists are planned.
