# Contacts and Products: step by step

This phase adds a shared Vue component system and expands the existing Contacts
and Products applications. Read [VUE-COMPONENTS.md](VUE-COMPONENTS.md) for the code
structure and [ERP-API.md](ERP-API.md) for API details.

## 1. Start and sign in

Start Docker Desktop, open PowerShell in the project folder, and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1
```

Startup applies the additive migration for categories, optional barcodes and import
receipts. Existing accounts, companies, products and stock are preserved. Open
<http://localhost:5173/login>, sign in, and select your company.

Owners and administrators can create/edit/import/archive records. Members can view
records and export CSV. All API requests check company access independently.

## 2. Manage contacts

1. Open **Contacts**, then **New**.
2. Enter the name, optional organization, email, phone, address and notes.
3. Select **Customer**, **Supplier**, or both. At least one role is required.
4. Select **Save**. Select a card or list name to open the record again.

Search matches name, organization, email and phone. **Contact role** narrows results
to customers, suppliers or contacts with both roles. **Sort by** changes their
order. List column buttons also sort; selecting the same column again reverses it.
Card and list views use the same filters and server results.

Unsaved forms ask before closing with **Discard**, the close button, or Escape.
They also protect route changes, company switches, sign-out and browser reload/close.
Selecting **Save** retains your edits. Read-only users see disabled form controls.

## 3. Manage products and categories

1. Open **Inventory > Products**.
2. Select **Categories**. Enter a new category name and select **Add category**.
   You can rename, archive or restore categories from this dialog.
3. Close the dialog and select **New**.
4. Enter the name, SKU, type, unit, prices and optional category/barcode.
5. Select **Save**.

SKU values are normalized to uppercase and unique within the company. An optional
barcode is also company-unique; empty barcodes are allowed on many products.
Barcodes are stored as text, preserving leading zeros such as `00001122`.
Categories are company-specific and names are unique under the database collation.

Archiving a category preserves it on existing products. The form shows that retained
choice as inactive; it cannot be newly selected on another product. Ordinary edits
to an existing product do not require reactivating its historical category.

Search matches product name, SKU, barcode and category name. Combine **Product type**,
**Category**, **Availability**, active/archive and search filters. **Uncategorized**
finds products without a category, including older products.

Availability filters apply only to goods:

| Filter | Meaning |
| --- | --- |
| Any stock | Goods and services; no stock restriction |
| At or below threshold | Goods whose ledger balance is at or below their low-stock threshold |
| Out of stock | Goods whose balance is zero or less |

Stock remains calculated from movements. Editing a product or importing CSV does not
set opening stock; use **Stock movements**. Prices are nonnegative decimal amounts.
Product type cannot change after stock movements/order lines exist.

## 4. Archive or restore several records

1. Narrow the results with search and filters.
2. Select checkboxes on cards or rows, or **Select all records on this page**.
3. Select **Archive selected** or **Restore selected**, then confirm.

Selection covers the visible page only, up to 24 records in these screens. Changing
the company, page, filters or view clears the selection. Archive hides records from
active results/new document choices and preserves existing business documents.
Use **Archived** or **All records** to find and restore them. There is no permanent
delete action. A missing/foreign-company ID rejects the entire bulk request.

## 5. Import a CSV file

1. Select **Import**, then **Download CSV template**.
2. Fill the template and save it as **UTF-8 CSV with commas**.
3. Choose the file, or paste CSV text into **CSV contents**.
4. Select **Preview CSV**. Review each cell, error and warning in the preview table.
5. Fix errors and preview again. When every row is valid, select **Import records**.

Files may contain up to **200 records** and **512 KiB**. Column names must be unique
and supported; `name` is required, and Products also requires `sku`. Other template
columns are optional. Empty optional cells use create defaults where appropriate.
Boolean values accept `true/false`, `yes/no`, or `1/0`. Quoted commas, quoted double
quotes and multiline notes are supported. Row numbers identify logical CSV records,
with the first data record numbered 2; multiline values can span physical lines.

Example contacts:

```csv
name,organization,email,phone,is_customer,is_supplier
Alice Example,Example Co,alice@example.com,012345678,true,false
Office Supplier,Example Supply,supply@example.com,,false,true
```

Example products (create the **Office** category first):

```csv
name,sku,kind,category,barcode,sale_price,cost_price,unit,reorder_level
Desk,DESK-01,goods,Office,00001234,125.00,70.00,Units,2.000
Consulting,CONSULT,service,,,50.00,0.00,Hours,0
```

Use category **names** in CSV, rather than numeric IDs. Categories must already
exist and be active in this company. Duplicate SKU/barcode values are errors.
Existing contact emails produce a warning; import explicitly creates another
contact and does not merge them.

A preview writes no records. Its confirmation expires after ten minutes and is
bound to the file, account, company and resource. Changing the file invalidates
the displayed preview. Saving revalidates current database state under the company
lock, then creates all rows in one transaction. A failure creates no partial batch.
Retrying the same confirmed request returns its receipt and does not create the
records/activity again. A new preview is a separate, intentional import.

Import creates new records only. Use forms to update existing records. It does not
import stock balances, IDs, company IDs, images, variants or spreadsheets in XLSX
format. Import receipts retain a token digest and count, not the source file/cells.

## 6. Export a CSV file

Apply filters and sorting, then select **Export CSV**. The download contains **all
matching records**, including pages you have not opened, up to **10,000 records**.
Narrow the filters if that limit is exceeded. Selection checkboxes do not limit an
export. To include archived records, choose **All records** before exporting.

Exports contain editable template columns; calculated stock and database IDs are
excluded. Files use UTF-8 with a BOM and quoted CSV cells. Values that can start a
spreadsheet formula are prefixed with an apostrophe. This changes the exported
representation only; it does not change stored records. If that file is imported,
the apostrophe remains literal. Spreadsheet applications can reinterpret cells
after saving/reopening, so this is not a universal spreadsheet-safety guarantee.
Import phone, SKU and barcode columns as **Text** in your spreadsheet editor to
retain leading zeros.

## 7. Verify the code

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check.ps1
node scripts/verify-browser.mjs
```

The optional browser check needs host Node.js 22+ and Edge on Windows. It uses
temporary companies/accounts and checks shared dialogs, filters, CSV validation,
bulk actions, category retention, exports and member access along with existing ERP
workflows. See [VERIFICATION.md](VERIFICATION.md) for the current results.

On 2026-10-28 (Asia/Bangkok), the combined suite passed **101 backend tests** and
**22 browser workflow groups**, plus Django/migration/dependency checks and the
Vue build. Browser checks found no uncaught JavaScript errors or Vue warnings.

## Remaining product work

Contact hierarchy, multiple delivery/invoice addresses, deduplication/merge and
linked-record history remain. Product variants, images, packaging, barcode scanning,
unit conversions, discounts and pricelists also remain. Categories and barcode
storage do not imply those additional capabilities. See the
[parity matrix](ODOO-PARITY-MATRIX.md).
