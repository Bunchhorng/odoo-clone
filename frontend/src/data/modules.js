export const modules = [
  { name: 'Dashboard', path: '/dashboard', icon: 'chart', color: '#22a5a1', description: 'Your business at a glance' },
  { name: 'Contacts', path: '/contacts', icon: 'users', color: '#e7a651', description: 'Customers and suppliers' },
  { name: 'CRM', path: '/crm', icon: 'pipeline', color: '#e36d74', description: 'Opportunities and pipeline' },
  { name: 'Sales', path: '/sales', icon: 'trend', color: '#8664a2', description: 'Quotations and sales orders' },
  { name: 'Purchase', path: '/purchase', icon: 'cart', color: '#4b9eb8', description: 'RFQs and purchase orders' },
  { name: 'Inventory', path: '/inventory', icon: 'box', color: '#ac795b', description: 'Products and stock movements' },
  { name: 'Invoicing', path: '/invoicing', icon: 'receipt', color: '#4ca496', description: 'Invoices, bills, and payments' },
  { name: 'Project', path: '/projects', icon: 'project', color: '#a177b9', description: 'Projects and task boards' },
  { name: 'Team', path: '/team', icon: 'team', color: '#579ac0', description: 'People and company access' },
  { name: 'Settings', path: '/settings', icon: 'settings', color: '#7c8694', description: 'Companies and preferences' },
]

export const catalogDefinitions = {
  contacts: {
    title: 'Contacts', singular: 'Contact', defaultView: 'cards', icon: 'users',
    fields: [
      { key: 'name', label: 'Name', required: true }, { key: 'organization', label: 'Company / organization' },
      { key: 'email', label: 'Email', type: 'email' }, { key: 'phone', label: 'Phone' },
      { key: 'country', label: 'Country' }, { key: 'address', label: 'Address', type: 'textarea' },
      { key: 'is_customer', label: 'Customer', type: 'checkbox', default: true },
      { key: 'is_supplier', label: 'Supplier', type: 'checkbox', default: false },
      { key: 'notes', label: 'Internal notes', type: 'textarea' },
    ],
    columns: [{ key: 'name', label: 'Name' }, { key: 'organization', label: 'Company' }, { key: 'email', label: 'Email' }, { key: 'phone', label: 'Phone' }],
  },
  products: {
    title: 'Products', singular: 'Product', defaultView: 'cards', icon: 'box',
    fields: [
      { key: 'name', label: 'Product name', required: true }, { key: 'sku', label: 'Internal reference / SKU', required: true, maxlength: 64 },
      { key: 'kind', label: 'Product type', type: 'select', options: [['goods', 'Goods'], ['service', 'Service']], default: 'goods' },
      { key: 'category_id', label: 'Category', type: 'relation', source: 'product-categories' },
      { key: 'barcode', label: 'Barcode', maxlength: 64, help: 'Optional; unique within this company. Keep leading zeros.' },
      { key: 'unit', label: 'Unit of measure', default: 'Units', required: true, maxlength: 30 },
      { key: 'sale_price', label: 'Sales price', type: 'number', step: '.01', default: '0' },
      { key: 'cost_price', label: 'Cost', type: 'number', step: '.01', default: '0' },
      { key: 'reorder_level', label: 'Low stock threshold', type: 'number', step: '.001', default: '0' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
    columns: [{ key: 'name', label: 'Product' }, { key: 'sku', label: 'Reference' }, { key: 'category_name', label: 'Category', sort: false }, { key: 'barcode', label: 'Barcode' }, { key: 'sale_price', label: 'Sales price', money: true }, { key: 'stock_quantity', label: 'On hand' }, { key: 'unit', label: 'Unit', sort: false }],
  },
  opportunities: {
    title: 'Pipeline', singular: 'Opportunity', defaultView: 'kanban', icon: 'pipeline',
    stages: [['new', 'New'], ['qualified', 'Qualified'], ['proposition', 'Proposition'], ['won', 'Won'], ['lost', 'Lost']],
    fields: [
      { key: 'title', label: 'Opportunity', required: true }, { key: 'contact_id', label: 'Customer', type: 'relation', source: 'contacts' },
      { key: 'expected_revenue', label: 'Expected revenue', type: 'number', step: '.01', default: '0' },
      { key: 'probability', label: 'Probability (%)', type: 'number', step: '1', max: 100, default: 10, integer: true },
      { key: 'expected_date', label: 'Expected closing date', type: 'date' },
      { key: 'stage', label: 'Stage', type: 'select', options: [['new', 'New'], ['qualified', 'Qualified'], ['proposition', 'Proposition'], ['won', 'Won'], ['lost', 'Lost']], default: 'new' },
      { key: 'notes', label: 'Notes', type: 'textarea' },
    ],
    columns: [{ key: 'title', label: 'Opportunity' }, { key: 'contact_name', label: 'Customer' }, { key: 'stage', label: 'Stage' }, { key: 'expected_revenue', label: 'Expected revenue', money: true }, { key: 'probability', label: 'Probability (%)' }],
  },
  projects: {
    title: 'Projects', singular: 'Project', defaultView: 'cards', icon: 'project',
    fields: [{ key: 'name', label: 'Project name', required: true }, { key: 'contact_id', label: 'Customer', type: 'relation', source: 'contacts' }, { key: 'notes', label: 'Description', type: 'textarea' }],
    columns: [{ key: 'name', label: 'Project' }, { key: 'contact_name', label: 'Customer' }, { key: 'notes', label: 'Description' }],
  },
  tasks: {
    title: 'Tasks', singular: 'Task', defaultView: 'kanban', icon: 'project',
    stages: [['todo', 'To do'], ['in_progress', 'In progress'], ['done', 'Done']],
    fields: [
      { key: 'title', label: 'Task title', required: true }, { key: 'project_id', label: 'Project', type: 'relation', source: 'projects', required: true },
      { key: 'assignee_id', label: 'Assigned to', type: 'relation', source: 'members' },
      { key: 'priority', label: 'Priority', type: 'select', options: [['low', 'Low'], ['normal', 'Normal'], ['high', 'High']], default: 'normal' },
      { key: 'due_date', label: 'Due date', type: 'date' },
      { key: 'stage', label: 'Stage', type: 'select', options: [['todo', 'To do'], ['in_progress', 'In progress'], ['done', 'Done']], default: 'todo' },
      { key: 'notes', label: 'Description', type: 'textarea' },
    ],
    columns: [{ key: 'title', label: 'Task' }, { key: 'project_name', label: 'Project' }, { key: 'assignee_name', label: 'Assigned to' }, { key: 'stage', label: 'Stage' }, { key: 'due_date', label: 'Due date' }],
  },
}
