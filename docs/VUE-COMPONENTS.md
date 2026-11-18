# Vue component system

The component system builds on Vue 3, Vue Router, Pinia and the existing ERP CSS.
It adds no UI-library dependency. Contacts, Products, CRM, Projects and Tasks share
`CatalogView.vue` and these components; existing order/invoice screens retain their
specialized document editors.

## File map

```text
frontend/src/components/
  AppIcon.vue
  ui/
    UiButton.vue       Native button with variants and busy/disabled handling
    UiNotice.vue       Status/error announcements with slotted actions
    UiBadge.vue        Compact state labels
    UiEmpty.vue        Icon, title, description and optional action
    UiField.vue        Labeled inputs driven by field definitions
    UiDialog.vue       Native modal dialog with a title and close guard
    UiPagination.vue   Server count/page/page-size controls
  catalog/
    CatalogToolbar.vue   Heading, search, active filter and view switch
    RecordTable.vue      Columns, sorting, selection and row/action slots
    CatalogImport.vue    File reading, validation preview and import confirmation
    ProductCategories.vue Category list and create/edit/archive form
frontend/src/assets/components.css
frontend/src/composables/forms.js
frontend/src/composables/download.js
frontend/src/data/modules.js
```

## Basic components

Import components explicitly into `<script setup>`. Data travels through props;
components emit changes and actions. They do not silently mutate parent records.
Native buttons default to `type="button"`; use `type="submit"` deliberately.

```vue
<script setup>
import { ref } from 'vue'
import UiButton from './components/ui/UiButton.vue'
import UiField from './components/ui/UiField.vue'
import UiNotice from './components/ui/UiNotice.vue'
const name = ref('')
const saving = ref(false)
const nameField = { key: 'name', label: 'Name', required: true, maxlength: 200 }
</script>

<template>
  <UiField v-model="name" :field="nameField" />
  <UiButton variant="primary" :busy="saving">Save</UiButton>
  <UiNotice tone="error">A record could not be saved.</UiNotice>
</template>
```

| Component | Main props / events | Notes |
| --- | --- | --- |
| UiButton | variant: primary/secondary/text; busy; disabled; type | Attributes and click listeners fall through to the native button; busy disables it and exposes aria-busy. |
| UiNotice | tone: success/error | Error uses role=alert; other notices use role=status. Default slot accepts text and actions. |
| UiBadge | tone | Uses the existing badge palette, including cancelled/blue/high. Always include text. |
| UiEmpty | title; description; icon | Default slot is the optional create/retry action. |
| UiField | field; v-model; options | Supports text/email/number/date, checkbox, select, relation and textarea. Put it inside a disabled fieldset for a read-only/busy form. |
| UiPagination | count; v-model:page; pageSize; busy | Visible when multiple pages exist; parent loads the requested page and adopts server clamping. |
| UiDialog | title; busy; beforeClose; closed event | Exposes showModal()/close(); default slot receives requestClose. Programmatic close() bypasses the guard for a successful save or company reset. |

`UiField` definitions use `key`, `label`, `type`, `required`, `maxlength`, `help`,
`min/max/step` where supported, and select `options: [[value, label]]`. Number inputs
emit text so monetary amounts can remain decimal strings. Parents convert IDs and
whole-number fields before calling the API. Relation options are `{id, name}`;
retained historical choices may add `inactive: true` and remain disabled.

## Dialog and dirty-form behavior

`UiDialog` uses native `showModal()` to make the background inert and wraps Tab/
Shift+Tab at the first/last visible enabled control. A unique heading ID labels the
dialog. Escape, close and discard
must pass `beforeClose`; `busy` prevents cancellation while saving. Pass a synchronous
function returning a boolean. Do not call native `dialog.close()` for user-triggered
discard, because that bypasses validation/confirmation.

The route view owns `useDirtyForm(form)`, initializes the draft, then calls
`markClean()`. It calls `markClean()` after successful saves/resets. The composable
protects route updates/leaves, company changes, sign-out and beforeunload. It returns
`dirty`, `markClean()` and `discard()`; dialog-specific confirmations remain in the
parent's `beforeClose`. Import/category forms participate while their drafts exist
and reset on close. Async option/file requests use generation counters so closed
dialogs/company switches do not receive stale results.

## Catalog toolbar and table

`CatalogToolbar` accepts `title`, `count`, `search`, `active`, `view`, `defaultView`,
`canCreate`, `busy` and `disabled`. Use `v-model:search`, `v-model:active` and
`v-model:view`; handle `create` and `search`. Named slots are `actions`, `filters`
and `subtitle`. Search debounce and data loading belong to the view.

`RecordTable` takes `rows`, `columns`, `title`, `currency`, `ordering`, `sortable`,
`selectable`, `selected` ID array and `busy`. It emits `open(row)`, `sort(field)`,
`toggle(id)` and `toggle-all`. A column can set `money: true` or `sort: false`.
Sorting is a request to the server, including an ID tiebreaker; it does not reorder
one page in memory. Column headings expose `aria-sort`. Selection is explicit and
limited to the current page.

Use `#cell-columnKey="{ row }"` to override a cell and `#actions="{ row }"` for row
actions. For example, `#cell-name` can render a link when a module has detail routes.
The table scrolls internally at narrow widths rather than overflowing the page.

## Add or extend a catalog

1. Define the API model, explicit writable fields, access rules and validation.
2. Add the UI title, fields, columns, icon and default view in `data/modules.js`.
3. Add a route whose CatalogView prop selects that resource.
4. Define filter/sort allowlists server-side. Put API calls in the parent view or
   composable, rather than the small presentation components.
5. Test the actual record workflow, permissions and cross-company behavior. Do not
   assume a hidden button enforces access.

CSV and bulk actions are intentionally exposed only for Contacts and Products.
Adding a catalog definition does not automatically authorize those endpoints.

## Style and verification

`erp.css` supplies the purple/teal palette and base ERP layouts.
`components.css` adds focus treatment, shared spacing/radius/selection tokens,
catalog filters, selection rows, import previews and responsive dialog layouts.
Keep component styles here when shared; avoid copying module-specific inline CSS.

```powershell
docker compose exec -T frontend npm run build
node scripts/verify-browser.mjs
```

The browser suite verifies real forms and network responses, keyboard modal behavior,
375px layouts, read-only controls and existing ERP workflows. It also fails on Vue
runtime warnings and uncaught JavaScript errors. It is not a complete WCAG audit.

References: [Vue props](https://vuejs.org/guide/components/props.html),
[component events](https://vuejs.org/guide/components/events.html), and
[OWASP CSV injection](https://community.owasp.org/attacks/CSV_Injection).
