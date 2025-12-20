# Hub Developer Documentation

A central management hub for multiple restaurant ordering sites. Built with PHP (procedural), Latte templating, and Tabler UI.

---

## Architecture Overview

```
┌─────────────────────┐
│        HUB          │
│  (This Application) │
│                     │
│  - User login       │
│  - Shop management  │
│  - Products CRUD    │
│  - Orders           │
└──────────┬──────────┘
           │
           │ API calls via proxy
           │
    ┌──────┴──────┐
    ▼             ▼
┌─────────┐  ┌─────────┐
│ Shop 1  │  │ Shop 2  │  ... (each has /app/v2/ API)
└─────────┘  └─────────┘
```

Each restaurant site is independent with its own database and API. The Hub connects to each site via the `/app/v2/` API endpoints.

---

## Directory Structure

```
hub/
├── index.php              # Router - all requests start here
├── bootstrap.php          # Session, Latte init, helpers
├── .htaccess              # URL rewriting
├── composer.json          # Dependencies (Latte only)
│
├── includes/
│   ├── config.php         # DB credentials, APP_BASE, API_SHARED_SECRET
│   ├── db.php             # Database helpers
│   ├── auth.php           # Authentication functions
│   ├── shops.php          # Shop & user-shop functions
│   └── api-client.php     # Remote API client (lazy loaded)
│
├── pages/                 # Controllers (one per route)
│   ├── login.php
│   ├── logout.php
│   ├── dashboard.php
│   ├── shops.php
│   ├── shop-edit.php
│   ├── products.php
│   ├── product-new.php
│   ├── product-edit.php
│   ├── orders.php
│   ├── user-shops.php
│   ├── select-shop.php
│   ├── api-proxy.php      # Proxies JS calls to shop APIs
│   └── 404.php
│
├── templates/             # Latte templates
│   ├── layout.latte       # Base layout with nav, scripts
│   ├── login.latte
│   ├── dashboard.latte
│   ├── shops.latte
│   ├── shop-edit.latte
│   ├── products.latte
│   ├── product-new.latte
│   ├── product-edit.latte
│   ├── orders.latte
│   ├── user-shops.latte
│   └── 404.latte
│
├── sql/
│   └── hub_tables.sql     # Database schema
│
└── temp/                  # Latte cache (clear after template changes)
```

---

## Global Variables

The following variables are available in ALL templates (set in `bootstrap.php`):

| Variable | Description |
|----------|-------------|
| `$app_base` | Base URL path (e.g., `/hub`) |
| `$current_path` | Current request path |
| `$is_logged_in` | Boolean - user logged in |
| `$is_global_admin` | Boolean - user is global admin |
| `$current_user` | Current user data array |
| `$selected_shop` | Currently selected shop (or null) |
| `$flash_messages` | Flash messages array |

**No need to pass these in `render()` calls** - they're automatically available.

---

## Key Concepts

### 1. Router (index.php)

All requests go through `index.php` which uses PHP 8 match expression:

```php
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$path = str_replace(APP_BASE, '', $path);

match(true) {
    $path === '/' => require BASE_PATH . '/pages/dashboard.php',
    $path === '/products' => require BASE_PATH . '/pages/products.php',
    $path === '/products/new' => require BASE_PATH . '/pages/product-new.php',
    preg_match('#^/products/(\d+)$#', $path, $m) === 1 => require BASE_PATH . '/pages/product-edit.php',
    // ... more routes
    default => require BASE_PATH . '/pages/404.php',
};
```

**To add a new route:**
1. Add the match condition in `index.php`
2. Create the page handler in `pages/`
3. Create the template in `templates/`

### 2. Page Handlers (pages/*.php)

Each page handler:
1. Checks authentication
2. Fetches data (from DB or API)
3. Handles POST actions
4. Renders template

```php
<?php
// pages/example.php

$shop = get_selected_shop();
if (!$shop) {
    flash('error', 'Please select a shop first');
    redirect('/');
}

load_api_client();

// Fetch data from remote API
$result = api_get($shop, '/some-endpoint');

// Handle POST
if ($method === 'POST') {
    // process form...
    redirect('/example');
}

// Render - $app_base, $current_user etc are already available
render('example.latte', [
    'shop' => $shop,
    'data' => $result['data'] ?? [],
    'csrf_token' => csrf_token(),
]);
```

### 3. API Client (includes/api-client.php)

Lazy loaded - only include when needed:

```php
load_api_client();
```

**Available functions:**

| Function | Description |
|----------|-------------|
| `api_get($shop, $endpoint)` | GET request |
| `api_post($shop, $endpoint, $data)` | POST request |
| `api_patch($shop, $endpoint, $data)` | PATCH request |
| `api_delete($shop, $endpoint)` | DELETE request |

**Response format:**
```php
[
    'success' => true,
    'data' => [...],
    'http_code' => 200
]
// or
[
    'success' => false,
    'error' => 'Error message',
    'http_code' => 400
]
```

### 4. API Proxy (pages/api-proxy.php)

JavaScript can't call remote APIs directly (CORS, secrets). The proxy:
1. Receives request from browser JS
2. Validates user access to shop
3. Calls remote API with proper auth
4. Returns response to browser

```php
// Route matching in api-proxy.php
$result = match(true) {
    $method === 'GET' && preg_match('#^/products/(\d+)$#', $api_path, $m) === 1
        => api_get($shop, '/products/' . $m[1]),
    
    $method === 'POST' && $api_path === '/products'
        => api_post($shop, '/products', [
            'category' => $body['category'] ?? '',
            'product' => $body['product'] ?? []
        ]),
    
    // ... more routes
    
    default => ['success' => false, 'error' => 'Unknown endpoint']
};
```

**To add a new proxy route:**

```php
// GET request
$method === 'GET' && $api_path === '/your-endpoint'
    => api_get($shop, '/your-endpoint'),

// GET with parameter
$method === 'GET' && preg_match('#^/items/(\d+)$#', $api_path, $m) === 1
    => api_get($shop, '/items/' . $m[1]),

// POST request
$method === 'POST' && $api_path === '/your-endpoint'
    => api_post($shop, '/your-endpoint', $body),

// PATCH request
$method === 'PATCH' && preg_match('#^/items/(\d+)$#', $api_path, $m) === 1
    => api_patch($shop, '/items/' . $m[1], $body),

// DELETE request (use query params, not body)
$method === 'DELETE' && preg_match('#^/items/(\d+)$#', $api_path, $m) === 1
    => api_delete($shop, '/items/' . $m[1]),
```

---

## Latte Templates

### Layout

All pages extend `layout.latte`:

```latte
{layout 'layout.latte'}

{block title}Page Title - Hub{/block}

{block head}
<!-- Extra CSS -->
{/block}

{block content}
<!-- Page content -->
{/block}

{block scripts}
<!-- Extra JS -->
{/block}
```

### Key Latte Syntax

**Variables:**
```latte
{$variable}
{$array['key']}
{$object->property}
```

**Conditionals:**
```latte
{if $condition}
    ...
{elseif $other}
    ...
{else}
    ...
{/if}
```

**Loops:**
```latte
{foreach $items as $item}
    {$item['name']}
{/foreach}

{foreach $items as $key => $value}
    ...
{/foreach}
```

**Local variables:**
```latte
{var $total = 0}
{var $categories = ['Pizza', 'Burgers']}
```

**Filters:**
```latte
{$name|capitalize}
{$date|date:'j M Y'}
{$number|number:2}
{json_encode($data)|noescape}
```

### JavaScript in Latte

**IMPORTANT:** JS variables in braces need a space to avoid Latte parsing:

```latte
{block scripts}
<script>
// Latte variables - no space needed, auto-quoted
const APP_BASE = {$app_base};
const SHOP_ID = {$shop['shop_id']};
const CSRF_TOKEN = {$csrf_token};

// JSON data - use noescape filter
const productsData = {json_encode($products)|noescape};

// JS template literals - ADD SPACE after opening brace
const url = `${ APP_BASE }/products/${ productId }`;
//            ^ space                  ^ space

// Or use concatenation
const url = APP_BASE + '/products/' + productId;
</script>
{/block}
```

**Using data attributes (recommended for dynamic values):**
```latte
<button data-id="{$product['id']}" 
        data-name="{$product['name']}"
        onclick="handleClick(this.dataset.id, this.dataset.name)">
```

Latte auto-escapes based on context - no need for manual escape filters.

---

## JavaScript Patterns

### Global JS Variables

These are set in `layout.latte` and available on all pages:

```javascript
const APP_BASE = '/hub';  // From {$app_base}
```

Page-specific variables (like `SHOP_ID`) should be set in the page's `{block scripts}`.

### API Calls

```javascript
// GET
const response = await fetch(`${APP_BASE}/api/products/${productId}?shop_id=${SHOP_ID}`);
const result = await response.json();

// POST
const response = await fetch(`${APP_BASE}/api/products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        shop_id: SHOP_ID,
        category: 'Pizza',
        product: { name: 'New Item', price: '9.99' }
    })
});

// PATCH
const response = await fetch(`${APP_BASE}/api/products/${productId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        shop_id: SHOP_ID,
        set: { price: '10.99', stock: 1 }
    })
});

// DELETE (use query params)
const response = await fetch(`${APP_BASE}/api/products/${productId}?shop_id=${SHOP_ID}`, {
    method: 'DELETE'
});
```

### SweetAlert2 (globally available via layout.latte)

```javascript
// Toast notification
Toast.fire({ icon: 'success', title: 'Saved!' });
Toast.fire({ icon: 'error', title: 'Failed' });

// Confirmation dialog
const result = await Swal.fire({
    title: 'Delete item?',
    text: 'This cannot be undone.',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#d63939',
    confirmButtonText: 'Yes, delete'
});

if (result.isConfirmed) {
    // proceed
}

// Loading
Swal.fire({
    title: 'Saving...',
    allowOutsideClick: false,
    didOpen: () => Swal.showLoading()
});
```

### Tabler Modals

```javascript
// Initialize
const myModal = new tabler.Modal(document.getElementById('myModal'));

// Show
myModal.show();

// Hide
myModal.hide();

// Or get existing instance
tabler.Modal.getInstance(document.getElementById('myModal')).hide();
```

### SortableJS (globally available via layout.latte)

```javascript
const sortable = new Sortable(document.getElementById('my-list'), {
    animation: 150,
    handle: '.drag-handle',
    ghostClass: 'sortable-ghost',
    onEnd: function(evt) {
        // Handle reorder
    }
});
```

---

## Database

### Schema (sql/hub_tables.sql)

```sql
-- Extend existing delight-auth users table
ALTER TABLE users ADD COLUMN is_global_admin TINYINT(1) UNSIGNED DEFAULT 0;

-- Shops
CREATE TABLE shops (
    shop_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(255) NOT NULL,
    api_secret VARCHAR(255) DEFAULT NULL,
    active TINYINT(1) UNSIGNED DEFAULT 1,
    created_at INT(10) UNSIGNED NOT NULL
);

-- User <-> Shop assignments
CREATE TABLE user_shops (
    user_id INT(10) UNSIGNED NOT NULL,
    shop_id INT UNSIGNED NOT NULL,
    role ENUM('admin', 'manager', 'staff') DEFAULT 'manager',
    created_at INT(10) UNSIGNED NOT NULL,
    PRIMARY KEY (user_id, shop_id)
);
```

### Database Helpers (includes/db.php)

```php
// Fetch multiple rows
$rows = db_fetch_all("SELECT * FROM shops WHERE active = 1");

// Fetch single row
$shop = db_fetch_one("SELECT * FROM shops WHERE shop_id = ?", [$id]);

// Insert
$id = db_insert('shops', [
    'name' => 'New Shop',
    'url' => 'https://example.com',
    'created_at' => time()
]);

// Update
db_update('shops', ['name' => 'Updated'], 'shop_id = ?', [$id]);

// Delete
db_delete('shops', 'shop_id = ?', [$id]);

// Raw query
db_query("UPDATE shops SET active = 0 WHERE shop_id = ?", [$id]);
```

---

## Adding a New Feature

### Example: Add "Option Groups" Management

**1. Add route to `index.php`:**
```php
$path === '/options' => require BASE_PATH . '/pages/options.php',
$path === '/options/new' => require BASE_PATH . '/pages/option-new.php',
preg_match('#^/options/(\d+)$#', $path, $m) === 1 => require BASE_PATH . '/pages/option-edit.php',
```

**2. Create page handler `pages/options.php`:**
```php
<?php
$shop = get_selected_shop();
if (!$shop) {
    flash('error', 'Please select a shop first');
    redirect('/');
}

load_api_client();

$result = api_get($shop, '/options');
$option_groups = $result['success'] ? $result['data'] : [];

render('options.latte', [
    'shop' => $shop,
    'option_groups' => $option_groups,
    'csrf_token' => csrf_token(),
]);
```

**3. Create template `templates/options.latte`:**
```latte
{layout 'layout.latte'}

{block title}Options - {$shop['name']} - Hub{/block}

{block content}
<div class="page-header mb-4">
    <div class="row align-items-center">
        <div class="col">
            <h2 class="page-title">Option Groups</h2>
        </div>
        <div class="col-auto">
            <a href="{$app_base}/options/new" class="btn btn-primary">
                <i class="ti ti-plus me-1"></i> Add Group
            </a>
        </div>
    </div>
</div>

{foreach $option_groups as $group}
<div class="card mb-3">
    <div class="card-header">
        <h3 class="card-title">{$group['name']}</h3>
    </div>
    <div class="card-body">
        <!-- options list -->
    </div>
</div>
{/foreach}
{/block}

{block scripts}
<script>
// APP_BASE is globally available from layout.latte
const SHOP_ID = {$shop['shop_id']};

// Your JS here
</script>
{/block}
```

**4. Add API proxy routes in `pages/api-proxy.php`:**
```php
// Options
$method === 'GET' && $api_path === '/options'
    => api_get($shop, '/options'),

$method === 'GET' && preg_match('#^/options/(\d+)$#', $api_path, $m) === 1
    => api_get($shop, '/options/' . $m[1]),

$method === 'POST' && $api_path === '/options'
    => api_post($shop, '/options', $body),

$method === 'PATCH' && preg_match('#^/options/(\d+)$#', $api_path, $m) === 1
    => api_patch($shop, '/options/' . $m[1], $body),

$method === 'DELETE' && preg_match('#^/options/(\d+)$#', $api_path, $m) === 1
    => api_delete($shop, '/options/' . $m[1]),
```

**5. Add nav link in `templates/layout.latte`:**
```latte
<li class="nav-item {if str_starts_with($current_path, '/options')}active{/if}">
    <a class="nav-link" href="{$app_base}/options">
        <span class="nav-link-icon"><i class="ti ti-list"></i></span>
        <span class="nav-link-title">Options</span>
    </a>
</li>
```

**6. Clear `temp/` folder and test.**

---

## Remote API Reference

Full API documentation: [API_DOCUMENTATION.md](https://github.com/tmblog/mpro/blob/main/API_DOCUMENTATION.md)

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/products` | List all products |
| GET | `/products/{id}` | Get single product |
| POST | `/products` | Create product |
| PATCH | `/products/{id}` | Update product |
| DELETE | `/products/{id}` | Delete product |
| PATCH | `/products/parent/{name}` | Update variation parent |
| DELETE | `/products/parent/{name}?category=X` | Delete variation parent + children |
| POST | `/products/bulk/stock` | Bulk stock toggle |
| POST | `/products/bulk/update` | Bulk update |
| POST | `/products/reorder/categories` | Reorder categories |
| POST | `/products/reorder/products` | Reorder products in category |
| GET | `/options` | List option groups |
| GET | `/orders` | List orders |
| POST | `/orders/{id}/accept` | Accept order |
| GET | `/analytics/summary` | Dashboard stats |

---

## Troubleshooting

### Template changes not showing
Clear the `temp/` folder - Latte caches compiled templates.

### "Class not found" errors
Run `composer install` to ensure Latte is installed.

### API calls failing
1. Check browser console for errors
2. Check `api-proxy.php` has the route
3. Test API directly: `curl -X GET "http://shop-url/app/v2/products" -H "Authorization: Bearer TOKEN"`

### JS variables undefined
Remember the space rule for JS template literals:
```javascript
// Wrong - Latte tries to parse
`${APP_BASE}/products`

// Right - space prevents Latte parsing
`${ APP_BASE }/products`
```

---

## TODO / Future Work

- [ ] Options management page (CRUD option groups)
- [ ] Order view page (single order details)
- [ ] Analytics page (detailed reporting)
- [ ] Bulk product import
- [ ] Option templates (save & apply to multiple products)
- [ ] API: Cascade cleanup when deleting options referenced in `revealed_by`
