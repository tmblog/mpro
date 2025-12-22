# API v2 Documentation

**Last Updated:** 2025-12-20  
**Status:** Foundation Complete - Products, Options & Bulk Operations Done

---

## Overview

The `/app/v2/` API provides a RESTful interface for the central hub to manage individual restaurant installations. Each restaurant site has its own deployment with this API, allowing the hub to:

- Authenticate with JWT tokens
- CRUD all JSON configuration files
- Manage orders (accept, complete, cancel, refund)
- View analytics and reporting
- Control products and options with proper ID management
- Bulk operations (update, stock toggle, delete)

---

## Installation

### File Structure
```
orders/
├── config/
│   ├── products.json
│   ├── options.json
│   └── ... other configs
└── public/
    └── app/
        └── v2/
            ├── index.php
            ├── api.json          ← Create from example
            ├── api.json.example
            ├── .htaccess
            ├── helpers/
            └── endpoints/
```

### Setup Steps

1. Copy `api.json.example` to `api.json`
2. Generate secrets:
   ```php
   echo bin2hex(random_bytes(32)); // jwt_secret
   echo bin2hex(random_bytes(16)); // shared_secret
   ```
3. Edit `api.json` with your secrets
4. Ensure root `.htaccess` excludes `/app/v2/` from main router:
   ```apache
   RewriteCond %{REQUEST_URI} !^/app/v2/
   ```

### Path Configuration

The API auto-detects paths from `$_SERVER['SCRIPT_NAME']`. Works on any install location.

`CONFIG_PATH` points to `../../config/` relative to `app/v2/`

---

## Architecture

```
app/v2/
├── index.php                 # Main router - entry point
├── api.json                  # Config (secrets, allowed files) - NOT in repo
├── api.json.example          # Template for api.json
├── .htaccess                 # URL rewriting + blocks *.json access
├── helpers/
│   ├── jwt.php               # JWT generation/verification (native PHP, no library)
│   ├── response.php          # Consistent JSON responses
│   └── permissions.php       # Role-based access control
└── endpoints/
    ├── auth.php              # Login → JWT token
    ├── config.php            # Generic CRUD for simple JSON configs
    ├── products.php          # Products with ID management
    ├── options.php           # Option groups with ID management
    ├── orders.php            # Order management + status updates
    └── analytics.php         # Reporting/stats
```

---

## Authentication

### Login Flow

```
POST /app/v2/auth
Content-Type: application/json

{
    "secret": "shared_secret_from_api_json",
    "shop_id": "optional-identifier",
    "user_id": "optional-user-id",
    "role": "global_admin|admin|manager|staff"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "token": "eyJ...",
        "expires_in": 86400,
        "expires_at": 1734567890,
        "shop_id": "shop-123",
        "role": "admin"
    }
}
```

### Using the Token

All endpoints except `/auth` require JWT in header:
```
Authorization: Bearer eyJ...
```

### Token Errors

| Code | HTTP | Meaning |
|------|------|---------|
| `TOKEN_MISSING` | 401 | No Authorization header |
| `TOKEN_EXPIRED` | 401 | Token past expiry - re-authenticate |
| `TOKEN_INVALID` | 401 | Bad signature - something wrong |
| `TOKEN_MALFORMED` | 401 | Not a valid JWT format |

### Refresh Token

```
POST /app/v2/auth/refresh
Authorization: Bearer {current_token}
```

Returns new token with fresh expiry.

---

## Role Permissions

| Role | Config | Orders | Refunds | Delete Orders | Global Admin |
|------|--------|--------|---------|---------------|--------------|
| `global_admin` | ✅ R/W | ✅ All | ✅ Yes | ✅ Yes | ✅ Yes |
| `admin` | ✅ R/W | ✅ All | ✅ Yes | ✅ Yes | ❌ No |
| `manager` | ✅ R/W | ✅ All | ✅ Yes | ❌ No | ❌ No |
| `staff` | 📖 Read | ✅ Basic | ❌ No | ❌ No | ❌ No |

**Role descriptions:**
- `global_admin` - Hub super admin (you) - reserved for future site-admin functions
- `admin` - Restaurant owner - full control of their shop
- `manager` - Shop manager - day-to-day operations
- `staff` - Kitchen/KDS - view orders, mark ready

---

## Endpoints Reference

### Auth `/app/v2/auth`

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| POST | `/auth` | No | Login with shared secret |
| POST | `/auth/refresh` | JWT | Refresh token |

---

### Config `/app/v2/config` (Generic JSON CRUD)

For simple config files (site.json, theme.json, hours.json, etc.)

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/config` | JWT | List allowed config files |
| GET | `/config/{file}` | JWT | Read config file |
| PUT | `/config/{file}` | JWT | Replace entire file |
| PATCH | `/config/{file}` | JWT | Partial update |
| DELETE | `/config/{file}/{id}` | JWT | Delete item by ID |

**Allowed files configured in `api.json` → `allowed_configs[]`**

---

### Products `/app/v2/products`

Dedicated endpoint with proper ID management for products.json.

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/products` | JWT | List all products |
| GET | `/products/{id}` | JWT | Get single product (simple or variation) |
| GET | `/products/category/{name}` | JWT | Get products by category |
| POST | `/products` | JWT | Create product (auto-assigns ID) |
| POST | `/products/variation/{parent_name}` | JWT | Add variation to parent |
| POST | `/products/category` | JWT | Create new category |
| PATCH | `/products/{id}` | JWT | Partial update product |
| PATCH | `/products/parent/{name}` | JWT | Update variation parent name/dsc |
| PATCH | `/products/category/{name}` | JWT | Update category |
| DELETE | `/products/{id}` | JWT | Delete product or variation child |
| DELETE | `/products/parent/{name}` | JWT | Delete variation parent + all children (admin+) |
| DELETE | `/products/category/{name}` | JWT | Delete empty category |
| POST | `/products/bulk/update` | JWT | Bulk update multiple products |
| POST | `/products/bulk/stock` | JWT | Bulk stock toggle |
| POST | `/products/bulk/delete` | JWT | Bulk delete (admin+) |
| POST | `/products/reorder/categories` | JWT | Reorder categories |
| POST | `/products/reorder/products` | JWT | Reorder products within category |

**Create product (simple):**
```json
POST /products
{
    "category": "Pizza",
    "product": {
        "name": "Margherita",
        "price": "9.95",
        "dsc": "Classic tomato and mozzarella"
    }
}
```
Note: `price` is required for simple products, optional for variation parents (which have `vari` array instead).

**Partial update operations:**
```json
PATCH /products/150
{
    "set": {"price": "9.99", "stock": 0},
    "unset": ["featured"],
    "push": {"allergens": "nuts"},
    "pull": {"allergens": "gluten"},
    "options_add": {"group_id": 3, "min": 0, "max": 2},
    "options_remove": 5,
    "options_update": {"group_id": 3, "max": 4}
}
```

**ID Management:**
- IDs auto-assigned as `max_existing_id + 1`
- Scans ALL simple products AND variations (shared pool)
- IDs cannot be modified via API
- Backups created before every save
- Variation parents have NO id - each child variation has its own id
- ID is placed first in JSON for consistency

**Bulk Update:**
```json
POST /products/bulk/update
{
    "updates": [
        {"id": 150, "set": {"price": "9.99", "stock": 1}},
        {"id": 151, "set": {"price": "8.99"}},
        {"id": 152, "set": {"featured": true}}
    ]
}
```

**Bulk Stock (by IDs):**
```json
POST /products/bulk/stock
{
    "ids": [150, 151, 152],
    "stock": 0
}
```

**Bulk Stock (by category):**
```json
POST /products/bulk/stock
{
    "category": "Pizza",
    "stock": 0
}
```

**Bulk Stock (all products):**
```json
POST /products/bulk/stock
{
    "all": true,
    "stock": 1
}
```

**Bulk Delete:**
```json
POST /products/bulk/delete
{
    "ids": [150, 151, 152]
}
```

**Create variation parent (no price):**
```json
POST /products
{
    "category": "Sides",
    "product": {
        "name": "Chicken",
        "dsc": "Choose your style",
        "vari": [
            {"name": "3 Pieces", "price": "4.99"},
            {"name": "6 Pieces", "price": "8.99"}
        ]
    }
}
```
Response:
```json
{
    "success": true,
    "data": {
        "message": "Product created",
        "variation_ids": [1184, 1185],
        "product": {
            "name": "Chicken",
            "dsc": "Choose your style",
            "vari": [
                {"id": 1184, "name": "3 Pieces", "price": "4.99"},
                {"id": 1185, "name": "6 Pieces", "price": "8.99"}
            ]
        }
    }
}
```

**Update variation parent:**
```json
PATCH /products/parent/Chicken
{
    "category": "Sides",
    "set": {
        "name": "Grilled Chicken",
        "dsc": "Succulent flame-grilled chicken"
    }
}
```

**Delete variation parent (and all children):**
```
DELETE /products/parent/Chicken?category=Sides
```
Response:
```json
{
    "success": true,
    "data": {
        "message": "Variation parent deleted",
        "name": "Chicken",
        "deleted_variation_ids": [1184, 1185]
    }
}
```

**Reorder categories:**
```json
POST /products/reorder/categories
{
    "order": ["Burgers", "Pizza", "Sides", "Drinks", "Desserts"]
}
```

**Reorder products within category:**
```json
POST /products/reorder/products
{
    "category": "Sides",
    "order": [100, "Chicken", 1005, 1006, 1007]
}
```
Note: Use product ID (integer) for simple products, or name (string) for variation parents.

---

### Options `/app/v2/options`

Dedicated endpoint for options.json (option groups and their options).

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/options` | JWT | List all option groups |
| GET | `/options/{group_id}` | JWT | Get single group |
| POST | `/options` | JWT | Create group (auto ID) |
| POST | `/options/{group_id}/option` | JWT | Add option to group |
| PATCH | `/options/{group_id}` | JWT | Update group |
| PATCH | `/options/{group_id}/option/{id}` | JWT | Update option |
| DELETE | `/options/{group_id}` | JWT | Delete group |
| DELETE | `/options/{group_id}/option/{id}` | JWT | Delete option |
| POST | `/options/bulk/update` | JWT | Bulk update options |
| POST | `/options/bulk/stock` | JWT | Bulk stock toggle |

**Create option group:**
```json
POST /options
{
    "name": "Sauces",
    "order": 5,
    "options": [
        {"name": "Ketchup", "price": 0},
        {"name": "Mayo", "price": 0.50}
    ]
}
```

**ID Management:**
- Group IDs: separate pool, auto-increment
- Option IDs: per-group (1, 2, 3... within each group)
- IDs cannot be modified

**Bulk Update Options:**
```json
POST /options/bulk/update
{
    "updates": [
        {"group_id": 1, "option_id": 2, "set": {"price": 0.99}},
        {"group_id": 1, "option_id": 3, "set": {"stock": 0}}
    ]
}
```

**Bulk Stock (by specific options):**
```json
POST /options/bulk/stock
{
    "options": [
        {"group_id": 1, "option_id": 2},
        {"group_id": 1, "option_id": 3}
    ],
    "stock": 0
}
```

**Bulk Stock (by group):**
```json
POST /options/bulk/stock
{
    "group_id": 1,
    "stock": 0
}
```

**Bulk Stock (all options):**
```json
POST /options/bulk/stock
{
    "all": true,
    "stock": 1
}
```

---

### Orders `/app/v2/orders`

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/orders` | JWT | List orders (with filters) |
| GET | `/orders/{id}` | JWT | Get single order with items |
| POST | `/orders/{id}/accept` | JWT | Accept order → awards loyalty points |
| POST | `/orders/{id}/time` | JWT | Update estimated time |
| POST | `/orders/{id}/ready` | JWT | Mark as ready/out for delivery |
| POST | `/orders/{id}/complete` | JWT | Complete order |
| POST | `/orders/{id}/cancel` | JWT | Cancel order → refunds loyalty points |
| POST | `/orders/{id}/refund` | JWT | Refund (full/partial) - manager+ |
| DELETE | `/orders/{id}` | JWT | Delete order - admin+ |

**List orders query params:**
- `status` - pending, processing, accepted, ready, out_for_delivery, completed, cancelled
- `date` - YYYY-MM-DD (default: today)
- `from` / `to` - date range
- `method` - delivery, collection, table
- `limit` - max 200 (default 50)
- `offset` - pagination

**Refund request:**
```json
POST /orders/123/refund
{
    "amount": 15.50,
    "reason": "Customer complaint"
}
```

---

### Analytics `/app/v2/analytics`

| Method | Route | Auth | Description |
|--------|-------|------|-------------|
| GET | `/analytics/daily` | JWT | Daily totals |
| GET | `/analytics/historical` | JWT | Date range data |
| GET | `/analytics/bestsellers` | JWT | Top selling products |
| GET | `/analytics/products` | JWT | Product performance |
| GET | `/analytics/customers` | JWT | Customer analytics |
| GET | `/analytics/summary` | JWT | Quick dashboard stats |

**Daily totals query:**
- `date` - YYYY-MM-DD (default: today)

**Historical query:**
- `from` - YYYY-MM-DD (required)
- `to` - YYYY-MM-DD (required)
- `group` - day, week, month

**Bestsellers/Products query:**
- `period` - today, week, month, year, all
- `limit` - number of results (bestsellers only)

---

## Products.json Structure

```json
{
    "Category Name": {
        "description": "Category description",
        "products": [
            {
                "id": 150,
                "name": "Product Name",
                "dsc": "Description",
                "price": "8.95",
                "table_price": 5.99,
                "img": "",
                "stock": 1,
                "cpn": 1,
                "order": 1,
                "featured": true,
                "allergens": ["gluten", "milk"],
                "availability": {"days": ["Sat", "Sun"]},
                "options": [
                    {
                        "group_id": 1,
                        "min": 1,
                        "max": 1,
                        "price_adjustment": 0.5,
                        "initially_visible": true,
                        "revealed_by": ["2:5", "2:6"]
                    }
                ]
            },
            {
                "name": "Variation Parent",
                "dsc": "Has no ID",
                "vari": [
                    {"id": 58, "name": "Small", "price": "5.00"},
                    {"id": 59, "name": "Large", "price": "8.00"}
                ]
            }
        ]
    }
}
```

**Product types:**
- Simple: has `id`, `name`, `price`
- With Options: has `options[]` array linking to option groups
- With Variations: parent has `vari[]`, no `id` on parent, each variation has `id`

**Key fields:**
- `cpn` - 1 = discountable with promo codes
- `stock` - 1 = available, 0 = 86'd
- `table_price` - optional dine-in pricing
- `revealed_by` - array of `"group_id:option_id"` that trigger visibility

---

## Options.json Structure

```json
[
    {
        "id": 1,
        "name": "Pizza Base",
        "order": 1,
        "options": [
            {"id": 1, "name": "Tomato Base", "price": 0, "stock": 1},
            {"id": 2, "name": "Garlic Base", "price": 0, "stock": 1}
        ]
    }
]
```

**Linking:** Products reference `group_id` which matches option group `id`.

**Price calculation:**
```
Final = Base Price + Σ(option.price + product.price_adjustment)
```

---

## api.json Configuration

Located at `app/v2/api.json`:

```json
{
    "shop_id": "your-shop-id",
    "jwt_secret": "64_char_hex_string",
    "shared_secret": "shared_secret_for_auth",
    "token_expiry": 86400,
    "allowed_configs": [
        "site", "theme", "hours", "delivery",
        "payment", "promotions", "loyalty",
        "offers", "table", "reservations", "upsells"
    ]
}
```

**Generate secrets:**
```php
echo bin2hex(random_bytes(32)); // jwt_secret
echo bin2hex(random_bytes(16)); // shared_secret
```

---

## Remaining Work

### Config Files Needing Review

| File | Status | Notes |
|------|--------|-------|
| `site.json` | Pending | Simple - use generic `/config` |
| `theme.json` | Pending | Simple - use generic `/config` |
| `hours.json` | Pending | Medium - day arrays, holidays |
| `delivery.json` | Pending | Medium - zones, fees, windows |
| `payment.json` | Pending | Sensitive - maybe global_admin only |
| `promotions.json` | Pending | Complex - may need dedicated endpoint |
| `loyalty.json` | Pending | Medium |
| `offers.json` | Pending | Complex - BOGOF rules |
| `table.json` | Pending | Simple |
| `reservations.json` | Pending | Medium |
| `upsells.json` | Pending | Medium |

### Features to Add

- [x] Bulk operations (update multiple products) ✓
- [x] Stock toggle shortcut endpoint ✓
- [ ] Image upload handling
- [ ] Webhook for order notifications
- [ ] Rate limiting
- [ ] Request logging/audit trail
- [ ] Global admin special functions

### Completed Features

| Feature | Endpoint | Notes |
|---------|----------|-------|
| Bulk Update (Products) | `POST /products/bulk/update` | Max 100 per request |
| Bulk Stock (Products) | `POST /products/bulk/stock` | By IDs, category, or all |
| Bulk Delete (Products) | `POST /products/bulk/delete` | Admin+ only |
| Bulk Update (Options) | `POST /options/bulk/update` | Max 100 per request |
| Bulk Stock (Options) | `POST /options/bulk/stock` | By options, group, or all |

---

## Response Format

**Success:**
```json
{
    "success": true,
    "data": { ... }
}
```

**Error:**
```json
{
    "success": false,
    "error": "Error message",
    "details": {"code": "ERROR_CODE"}
}
```

**Paginated:**
```json
{
    "success": true,
    "data": {
        "items": [...],
        "pagination": {
            "total": 150,
            "per_page": 50,
            "current_page": 1,
            "total_pages": 3,
            "has_more": true
        }
    }
}
```

---

## Backup Strategy

All config writes create timestamped backups:
```
config/backups/products_2025-12-18_14-30-00.json
config/backups/options_2025-12-18_14-30-00.json
```

Bulk operations create a single backup before processing all changes (efficient).

---

## Security Notes

1. `api.json` protected by `.htaccess` - never exposed via web
2. JWT uses HMAC-SHA256 (native PHP, no external library)
3. All IDs validated as integers
4. Directory traversal prevented via `basename()`
5. SQL injection prevented via prepared statements
6. Role checks on all write operations
7. Bulk operations limited to 100 items per request
8. Bulk delete requires admin+ role

---

## Hub Implementation Guide

### Architecture Overview

The Hub is a central dashboard that manages multiple restaurant installations. Each restaurant site is completely independent with its own:
- Domain/URL
- Database
- Products, menus, options
- Orders, customers

The Hub connects to each site via this API.

```
                    ┌─────────────────────┐
                    │        HUB          │
                    │  (Central Dashboard) │
                    │                     │
                    │  - User login       │
                    │  - Shop selector    │
                    │  - Manage products  │
                    │  - View orders      │
                    │  - Analytics        │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
   │  Pizza Palace   │ │  Burger Barn    │ │  Curry House    │
   │                 │ │                 │ │                 │
   │ pizzapalace.com │ │ burgerbarn.com  │ │ curryhouse.com  │
   │    /app/v2/     │ │    /app/v2/     │ │    /app/v2/     │
   │                 │ │                 │ │                 │
   │ - products.json │ │ - products.json │ │ - products.json │
   │ - options.json  │ │ - options.json  │ │ - options.json  │
   │ - orders DB     │ │ - orders DB     │ │ - orders DB     │
   └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Hub Database Schema

The Hub has its own database to manage users and shop assignments. Uses existing delight-auth `users` table.

```sql
-- Add to existing users table (delight-auth)
ALTER TABLE users ADD COLUMN is_global_admin TINYINT(1) UNSIGNED DEFAULT 0 AFTER roles_mask;

-- Shops/Sites managed by hub
CREATE TABLE shops (
    shop_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(255) NOT NULL,
    active TINYINT(1) UNSIGNED DEFAULT 1,
    created_at INT(10) UNSIGNED NOT NULL
);

-- User <-> Shop assignments
CREATE TABLE user_shops (
    user_id INT(10) UNSIGNED NOT NULL,
    shop_id INT UNSIGNED NOT NULL,
    role ENUM('admin', 'manager', 'staff') DEFAULT 'manager',
    created_at INT(10) UNSIGNED NOT NULL,
    PRIMARY KEY (user_id, shop_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (shop_id) REFERENCES shops(shop_id) ON DELETE CASCADE
);
```

### Access Control Logic

```php
/**
 * Get shops user can access
 */
function get_user_shops($user_id, $is_global_admin) {
    global $db;
    
    // Global admin sees all
    if ($is_global_admin) {
        $sql = "SELECT * FROM shops WHERE active = 1 ORDER BY name";
        $result = mysqli_query($db, $sql);
    } else {
        $sql = "SELECT s.*, us.role 
                FROM shops s
                JOIN user_shops us ON s.shop_id = us.shop_id
                WHERE us.user_id = ? AND s.active = 1
                ORDER BY s.name";
        $stmt = mysqli_prepare($db, $sql);
        mysqli_stmt_bind_param($stmt, 'i', $user_id);
        mysqli_stmt_execute($stmt);
        $result = mysqli_stmt_get_result($stmt);
    }
    
    return mysqli_fetch_all($result, MYSQLI_ASSOC);
}

/**
 * Get user's role at specific shop
 */
function get_user_shop_role($user_id, $shop_id, $is_global_admin) {
    global $db;
    
    if ($is_global_admin) {
        return 'global_admin';
    }
    
    $sql = "SELECT role FROM user_shops WHERE user_id = ? AND shop_id = ?";
    $stmt = mysqli_prepare($db, $sql);
    mysqli_stmt_bind_param($stmt, 'ii', $user_id, $shop_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    $row = mysqli_fetch_assoc($result);
    
    return $row ? $row['role'] : null;
}

/**
 * Check if user can access shop
 */
function can_access_shop($user_id, $shop_id, $is_global_admin) {
    return $is_global_admin || get_user_shop_role($user_id, $shop_id, false) !== null;
}
```

### Shared Secret Strategy

All sites use the same `shared_secret` in their `api.json`. This simplifies management:
- Hub stores one secret
- New sites use same secret
- If compromised, rotate everywhere (you control all sites)

```php
// Hub config
define('API_SHARED_SECRET', 'your_shared_secret_here');
```

---

### JavaScript/Fetch Examples

#### API Client Class

```javascript
class ShopAPI {
    constructor(shopUrl) {
        this.baseUrl = shopUrl.replace(/\/$/, '') + '/app/v2';
        this.token = null;
        this.tokenExpiresAt = null;
    }

    /**
     * Authenticate with shop
     */
    async authenticate(secret, role = 'admin') {
        const response = await fetch(`${this.baseUrl}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ secret, role })
        });

        const data = await response.json();

        if (data.success) {
            this.token = data.data.token;
            this.tokenExpiresAt = data.data.expires_at;
            return data.data;
        }

        throw new Error(data.error || 'Authentication failed');
    }

    /**
     * Make authenticated API request
     */
    async request(method, endpoint, body = null) {
        // Check token expiry
        if (this.isTokenExpired()) {
            throw new Error('TOKEN_EXPIRED');
        }

        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            }
        };

        if (body && ['POST', 'PUT', 'PATCH'].includes(method)) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(`${this.baseUrl}${endpoint}`, options);
        const data = await response.json();

        // Handle token errors
        if (!data.success && data.details?.code === 'TOKEN_EXPIRED') {
            throw new Error('TOKEN_EXPIRED');
        }

        return data;
    }

    /**
     * Check if token is expired or expiring soon
     */
    isTokenExpired(bufferSeconds = 300) {
        if (!this.tokenExpiresAt) return true;
        return Date.now() / 1000 > (this.tokenExpiresAt - bufferSeconds);
    }

    // Convenience methods
    async get(endpoint) { return this.request('GET', endpoint); }
    async post(endpoint, body) { return this.request('POST', endpoint, body); }
    async patch(endpoint, body) { return this.request('PATCH', endpoint, body); }
    async delete(endpoint) { return this.request('DELETE', endpoint); }
}
```

#### Usage Examples

```javascript
// Initialize API for a shop
const shop = new ShopAPI('https://pizzapalace.com');

// Authenticate
await shop.authenticate('shared_secret_here', 'admin');

// Get all products
const products = await shop.get('/products');
console.log(products.data);

// Update a product price
const updated = await shop.patch('/products/150', {
    set: { price: '9.99' }
});

// Bulk stock update
const result = await shop.post('/products/bulk/stock', {
    ids: [150, 151, 152],
    stock: 0
});

// Get today's orders
const orders = await shop.get('/orders');

// Accept an order
await shop.post('/orders/123/accept');

// Get analytics
const stats = await shop.get('/analytics/summary');
```

---

### Full Request/Response Examples

#### Authentication

**Request:**
```http
POST /app/v2/auth HTTP/1.1
Host: pizzapalace.com
Content-Type: application/json

{
    "secret": "your_shared_secret",
    "role": "admin"
}
```

**Response (Success):**
```json
{
    "success": true,
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "expires_in": 86400,
        "expires_at": 1734567890,
        "shop_id": "pizza-palace",
        "role": "admin"
    }
}
```

**Response (Error):**
```json
{
    "success": false,
    "error": "Invalid credentials"
}
```

#### Get Products

**Request:**
```http
GET /app/v2/products HTTP/1.1
Host: pizzapalace.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
    "success": true,
    "data": {
        "Pizza": {
            "description": "Fresh made pizzas",
            "products": [
                {
                    "id": 1,
                    "name": "Margherita",
                    "price": "9.95",
                    "stock": 1
                }
            ]
        }
    }
}
```

#### Update Product

**Request:**
```http
PATCH /app/v2/products/150 HTTP/1.1
Host: pizzapalace.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
    "set": {
        "price": "10.99",
        "featured": true
    },
    "push": {
        "allergens": "nuts"
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Product updated",
        "id": 150,
        "product": {
            "id": 150,
            "name": "Classic Burger",
            "price": "10.99",
            "featured": true,
            "allergens": ["gluten", "nuts"],
            "stock": 1
        }
    }
}
```

#### Bulk Stock Update

**Request:**
```http
POST /app/v2/products/bulk/stock HTTP/1.1
Host: pizzapalace.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
    "category": "Pizza",
    "stock": 0
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Stock updated to 0",
        "updated_count": 12
    }
}
```

#### Get Orders

**Request:**
```http
GET /app/v2/orders?status=pending&limit=20 HTTP/1.1
Host: pizzapalace.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
    "success": true,
    "data": {
        "items": [
            {
                "order_id": 456,
                "customer_name": "John Smith",
                "order_total": 25.50,
                "order_status": "pending",
                "delivery_collection": "delivery",
                "items": [
                    {
                        "product_name": "Margherita",
                        "product_quantity": 2,
                        "product_price_total": 19.90
                    }
                ]
            }
        ],
        "pagination": {
            "total": 45,
            "per_page": 20,
            "current_page": 1,
            "total_pages": 3,
            "has_more": true
        }
    }
}
```

---

### Token Management Strategy

#### Per-Site Token Storage

```javascript
class TokenManager {
    constructor() {
        // Store tokens per shop URL
        this.tokens = new Map();
    }

    /**
     * Get or refresh token for a shop
     */
    async getToken(shopUrl, secret) {
        const stored = this.tokens.get(shopUrl);

        // Return valid token
        if (stored && !this.isExpired(stored)) {
            return stored.token;
        }

        // Authenticate and store new token
        const api = new ShopAPI(shopUrl);
        const auth = await api.authenticate(secret, 'admin');

        this.tokens.set(shopUrl, {
            token: auth.token,
            expiresAt: auth.expires_at
        });

        return auth.token;
    }

    /**
     * Check if token is expired (with 5 min buffer)
     */
    isExpired(stored) {
        return Date.now() / 1000 > (stored.expiresAt - 300);
    }

    /**
     * Clear token (on auth error)
     */
    clearToken(shopUrl) {
        this.tokens.delete(shopUrl);
    }
}

// Usage
const tokenManager = new TokenManager();

async function callShopAPI(shopUrl, endpoint) {
    const token = await tokenManager.getToken(shopUrl, SHARED_SECRET);
    // Use token...
}
```

#### Session Storage (Browser)

```javascript
// Store tokens in sessionStorage per shop
function storeToken(shopUrl, tokenData) {
    const key = `api_token_${btoa(shopUrl)}`;
    sessionStorage.setItem(key, JSON.stringify({
        token: tokenData.token,
        expiresAt: tokenData.expires_at
    }));
}

function getStoredToken(shopUrl) {
    const key = `api_token_${btoa(shopUrl)}`;
    const stored = sessionStorage.getItem(key);
    if (!stored) return null;

    const data = JSON.parse(stored);
    
    // Check expiry
    if (Date.now() / 1000 > data.expiresAt - 300) {
        sessionStorage.removeItem(key);
        return null;
    }

    return data.token;
}
```

---

### Error Handling Patterns

#### Error Codes Reference

| HTTP | Code | Meaning | Action |
|------|------|---------|--------|
| 401 | `TOKEN_MISSING` | No Authorization header | Authenticate |
| 401 | `TOKEN_EXPIRED` | Token past expiry | Re-authenticate |
| 401 | `TOKEN_INVALID` | Bad signature | Clear token, re-authenticate |
| 403 | - | Insufficient permissions | Show error, check user role |
| 404 | - | Resource not found | Show error |
| 400 | - | Bad request | Show validation error |
| 500 | - | Server error | Retry or show error |

#### Error Handler

```javascript
class APIError extends Error {
    constructor(response) {
        super(response.error || 'Unknown error');
        this.code = response.details?.code || null;
        this.status = response.status || 500;
    }
}

async function handleAPIRequest(shopUrl, requestFn) {
    try {
        const result = await requestFn();
        
        if (!result.success) {
            throw new APIError(result);
        }
        
        return result.data;
        
    } catch (error) {
        if (error.code === 'TOKEN_EXPIRED' || error.code === 'TOKEN_INVALID') {
            // Clear stored token
            tokenManager.clearToken(shopUrl);
            
            // Re-authenticate and retry
            await tokenManager.getToken(shopUrl, SHARED_SECRET);
            return handleAPIRequest(shopUrl, requestFn);
        }
        
        if (error.code === 'TOKEN_MISSING') {
            // Need to authenticate first
            await tokenManager.getToken(shopUrl, SHARED_SECRET);
            return handleAPIRequest(shopUrl, requestFn);
        }
        
        // Other errors - show to user
        showErrorNotification(error.message);
        throw error;
    }
}

// Usage
const products = await handleAPIRequest(shopUrl, () => 
    shop.get('/products')
);
```

#### Retry with Exponential Backoff

```javascript
async function retryRequest(fn, maxRetries = 3) {
    let lastError;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            return await fn();
        } catch (error) {
            lastError = error;
            
            // Don't retry auth errors
            if (['TOKEN_EXPIRED', 'TOKEN_INVALID', 'TOKEN_MISSING'].includes(error.code)) {
                throw error;
            }
            
            // Wait before retry (exponential backoff)
            if (attempt < maxRetries - 1) {
                await new Promise(r => setTimeout(r, Math.pow(2, attempt) * 1000));
            }
        }
    }
    
    throw lastError;
}
```

---

### Multi-Site Hub Workflow

#### Complete Flow Example

```javascript
// 1. User logs into Hub (delight-auth handles this)
// 2. Load user's assigned shops

async function loadUserShops(userId, isGlobalAdmin) {
    // This calls Hub's own backend, not site APIs
    const response = await fetch('/hub/api/user-shops');
    return response.json();
}

// 3. User selects a shop
async function selectShop(shop) {
    // Get/refresh token for this shop
    const token = await tokenManager.getToken(shop.url, SHARED_SECRET);
    
    // Now can make API calls
    const api = new ShopAPI(shop.url);
    api.token = token;
    
    // Load shop data
    const [products, orders, stats] = await Promise.all([
        api.get('/products'),
        api.get('/orders'),
        api.get('/analytics/summary')
    ]);
    
    return { products, orders, stats };
}

// 4. User makes changes
async function updateProductPrice(shop, productId, newPrice) {
    const api = new ShopAPI(shop.url);
    api.token = await tokenManager.getToken(shop.url, SHARED_SECRET);
    
    return api.patch(`/products/${productId}`, {
        set: { price: newPrice }
    });
}

// 5. Bulk operations across site
async function turnOffAllStock(shop) {
    const api = new ShopAPI(shop.url);
    api.token = await tokenManager.getToken(shop.url, SHARED_SECRET);
    
    return api.post('/products/bulk/stock', {
        all: true,
        stock: 0
    });
}
```

#### Dashboard Data Aggregation

```javascript
// Load summary from all user's shops
async function loadDashboard(userShops) {
    const summaries = await Promise.all(
        userShops.map(async (shop) => {
            try {
                const api = new ShopAPI(shop.url);
                api.token = await tokenManager.getToken(shop.url, SHARED_SECRET);
                
                const stats = await api.get('/analytics/summary');
                
                return {
                    shop_id: shop.shop_id,
                    name: shop.name,
                    ...stats.data
                };
            } catch (error) {
                return {
                    shop_id: shop.shop_id,
                    name: shop.name,
                    error: error.message
                };
            }
        })
    );
    
    return summaries;
}
```

---

### Hub User Roles Summary

| Hub Role | `is_global_admin` | Shop Access | API Role Passed |
|----------|-------------------|-------------|-----------------|
| Global Admin | 1 | All shops | `global_admin` |
| Regular User | 0 | Assigned only | From `user_shops.role` |

| Shop Role | Config | Orders | Refunds | Delete |
|-----------|--------|--------|---------|--------|
| `global_admin` | ✅ R/W | ✅ All | ✅ Yes | ✅ Yes |
| `admin` | ✅ R/W | ✅ All | ✅ Yes | ✅ Yes |
| `manager` | ✅ R/W | ✅ All | ✅ Yes | ❌ No |
| `staff` | 📖 Read | ✅ Basic | ❌ No | ❌ No |
