# API v2 Endpoints Reference

**Last Updated:** 2025-12-20  
**Base URL:** `/app/v2/`

---

## Authentication

### POST `/auth`
Authenticate and receive JWT token.

**Request:**
```json
{
    "secret": "your_shared_secret",
    "role": "admin"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "expires_in": 86400,
        "expires_at": 1734567890,
        "shop_id": "shop-name",
        "role": "admin"
    }
}
```

**Roles:** `global_admin`, `admin`, `manager`, `staff`

---

### POST `/auth/refresh`
Refresh token before expiry.

**Headers:** `Authorization: Bearer {token}`

**Response:** Same as `/auth`

---

## Products

All product endpoints require JWT authentication.

### Endpoints Table

| Method | Route | Description | Permission |
|--------|-------|-------------|------------|
| GET | `/products` | List all products | Any |
| GET | `/products/{id}` | Get single product | Any |
| GET | `/products/category/{name}` | Get products by category | Any |
| POST | `/products` | Create product | Write |
| POST | `/products/variation/{parent_name}` | Add variation to parent | Write |
| POST | `/products/category` | Create new category | Write |
| PATCH | `/products/{id}` | Update product | Write |
| PATCH | `/products/parent/{name}` | Update variation parent | Write |
| PATCH | `/products/category/{name}` | Update category | Write |
| DELETE | `/products/{id}` | Delete product/variation | Admin |
| DELETE | `/products/parent/{name}` | Delete variation parent + children | Admin |
| DELETE | `/products/category/{name}` | Delete empty category | Admin |
| POST | `/products/bulk/update` | Bulk update products | Write |
| POST | `/products/bulk/stock` | Bulk stock toggle | Write |
| POST | `/products/bulk/delete` | Bulk delete products | Admin |
| POST | `/products/bulk/upsert` | Bulk upsert products | Write |
| POST | `/products/reorder/categories` | Reorder categories | Write |
| POST | `/products/reorder/products` | Reorder products in category | Write |
| POST | `/products/reorder/options` | Reorder option groups on product | Write |

---

### GET `/products`
List all products grouped by category.

**Response:**
```json
{
    "success": true,
    "data": {
        "Pizza": {
            "description": "Fresh made pizzas",
            "products": [
                {"id": 1, "name": "Margherita", "price": "9.95", "stock": 1}
            ]
        },
        "Sides": {
            "description": "Extras",
            "products": [...]
        }
    }
}
```

---

### GET `/products/{id}`
Get single product by ID. Works for simple products and variation children.

**Response:**
```json
{
    "success": true,
    "data": {
        "category": "Pizza",
        "product": {
            "id": 150,
            "name": "Margherita",
            "price": "9.95",
            "dsc": "Classic tomato and mozzarella",
            "stock": 1
        }
    }
}
```

---

### GET `/products/category/{name}`
Get all products in a category.

**Response:**
```json
{
    "success": true,
    "data": {
        "category": "Pizza",
        "description": "Fresh made pizzas",
        "products": [...]
    }
}
```

---

### POST `/products`
Create new product. Price required for simple products, optional for variation parents.

**Simple product:**
```json
{
    "category": "Pizza",
    "product": {
        "name": "Margherita",
        "price": "9.95",
        "dsc": "Classic tomato and mozzarella",
        "stock": 1,
        "cpn": 1
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Product created",
        "id": 150,
        "product": {...}
    }
}
```

**Simple product with options:**
```json
{
    "category": "Pizza",
    "product": {
        "name": "Build Your Own",
        "price": "12.95",
        "dsc": "Create your perfect pizza",
        "stock": 1,
        "options": [
            {"group_id": 1, "min": 1, "max": 1},
            {"group_id": 2, "min": 0, "max": 5, "revealed_by": ["1:2"]}
        ]
    }
}
```

Note: `revealed_by` format is `"group_id:option_id"`. Example: `["1:2"]` means this option group is revealed when option 2 from group 1 is selected.

**Variation parent:**
```json
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

**Response:**
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

---

### POST `/products/variation/{parent_name}`
Add variation to existing parent.

**Request:**
```json
{
    "category": "Sides",
    "variation": {
        "name": "12 Pieces",
        "price": "14.99"
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Variation added",
        "id": 1186,
        "variation": {...}
    }
}
```

---

### POST `/products/category`
Create new category.

**Request:**
```json
{
    "name": "Desserts",
    "description": "Sweet treats"
}
```

---

### PATCH `/products/{id}`
Partial update product. Only touches specified fields.

**Request:**
```json
{
    "set": {
        "price": "10.99",
        "featured": true,
        "table_price": 8.99
    },
    "unset": ["old_field"],
    "push": {
        "allergens": "nuts"
    },
    "pull": {
        "allergens": "gluten"
    },
    "options_add": {
        "group_id": 3,
        "min": 0,
        "max": 2,
        "revealed_by": ["1:5"]
    },
    "options_remove": 5,
    "options_update": {
        "group_id": 3,
        "max": 4,
        "revealed_by": ["1:5", "1:6"]
    }
}
```

**Operations:**
- `set` - Add or update fields
- `unset` - Remove fields (array of field names)
- `push` - Add item to array field
- `pull` - Remove item from array field
- `options_add` - Add option group config
- `options_remove` - Remove option group by group_id
- `options_update` - Update option group config

**Options config fields:**
```json
{
    "group_id": 3,
    "min": 0,
    "max": 2,
    "price_adjustment": 0,
    "initially_visible": true,
    "revealed_by": ["2:5", "2:6"]
}
```

Note: `revealed_by` format is `"group_id:option_id"`. Example: `["2:5"]` means revealed when option 5 from group 2 is selected.

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Product updated",
        "id": 150,
        "product": {...}
    }
}
```

---

### PATCH `/products/parent/{name}`
Update variation parent name and description.

**Request:**
```json
{
    "category": "Sides",
    "set": {
        "name": "Grilled Chicken",
        "dsc": "Flame-grilled chicken pieces"
    }
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Variation parent updated",
        "parent": {...}
    }
}
```

---

### PATCH `/products/category/{name}`
Update category name or description.

**Request:**
```json
{
    "set": {
        "name": "New Name",
        "description": "New description"
    }
}
```

---

### DELETE `/products/{id}`
Delete product or variation child. Admin+ required.

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Product deleted",
        "id": 150
    }
}
```

---

### DELETE `/products/parent/{name}?category={category}`
Delete variation parent and all children. Admin+ required.

**Request:**
```
DELETE /products/parent/Chicken?category=Sides
```

**Response:**
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

---

### DELETE `/products/category/{name}`
Delete empty category. Admin+ required.

---

### POST `/products/bulk/update`
Update multiple products. Max 100 per request.

**Request:**
```json
{
    "updates": [
        {"id": 150, "set": {"price": "9.99", "stock": 1}},
        {"id": 151, "set": {"price": "8.99"}},
        {"id": 152, "set": {"featured": true}, "unset": ["old_field"]}
    ]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Bulk update complete",
        "success_count": 3,
        "fail_count": 0,
        "results": [
            {"id": 150, "success": true},
            {"id": 151, "success": true},
            {"id": 152, "success": true}
        ]
    }
}
```

---

### POST `/products/bulk/stock`
Bulk stock toggle. Three modes available.

**By IDs:**
```json
{
    "ids": [150, 151, 152],
    "stock": 0
}
```

**By category:**
```json
{
    "category": "Pizza",
    "stock": 0
}
```

**All products:**
```json
{
    "all": true,
    "stock": 1
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

---

### POST `/products/bulk/delete`
Delete multiple products. Admin+ required. Max 100 per request.

**Request:**
```json
{
    "ids": [150, 151, 152]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Bulk delete complete",
        "success_count": 3,
        "fail_count": 0,
        "results": [...]
    }
}
```

---

### POST `/products/bulk/upsert`
Bulk create or update simple products. Max 100 per request.

- Match by `id` if provided → update
- Else match by `name` in category → update
- Else → create new

**Request:**
```json
{
    "category": "Sides",
    "products": [
        {"id": 150, "price": "5.99"},
        {"name": "Fries", "price": "3.50"},
        {"name": "New Item", "price": "4.00", "stock": 1}
    ]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Bulk upsert complete",
        "created": 1,
        "updated": 2,
        "results": [
            {"success": true, "action": "updated", "id": 150},
            {"success": true, "action": "updated", "id": 75},
            {"success": true, "action": "created", "id": 1186}
        ]
    }
}
```

---

### POST `/products/reorder/categories`
Reorder categories. Affects JSON key order.

**Request:**
```json
{
    "order": ["Burgers", "Pizza", "Sides", "Drinks", "Desserts"]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Categories reordered",
        "order": ["Burgers", "Pizza", "Sides", "Drinks", "Desserts"]
    }
}
```

---

### POST `/products/reorder/products`
Reorder products within a category.

Use product ID (integer) for simple products, name (string) for variation parents.

**Request:**
```json
{
    "category": "Sides",
    "order": [100, "Chicken", 1005, 1006, 1007]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Products reordered",
        "category": "Sides",
        "count": 5
    }
}
```

---

### POST `/products/reorder/options`
Reorder option groups assigned to a product.

**Request:**
```json
{
    "product_id": 150,
    "order": [3, 1, 2]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Product options reordered",
        "product_id": 150,
        "count": 3
    }
}
```

---

## Options

All option endpoints require JWT authentication.

### Endpoints Table

| Method | Route | Description | Permission |
|--------|-------|-------------|------------|
| GET | `/options` | List all option groups | Any |
| GET | `/options/{group_id}` | Get single group | Any |
| POST | `/options` | Create group | Write |
| POST | `/options/{group_id}/option` | Add option to group | Write |
| PATCH | `/options/{group_id}` | Update group | Write |
| PATCH | `/options/{group_id}/option/{id}` | Update option | Write |
| DELETE | `/options/{group_id}` | Delete group | Write |
| DELETE | `/options/{group_id}/option/{id}` | Delete option | Write |
| POST | `/options/bulk/update` | Bulk update options | Write |
| POST | `/options/bulk/stock` | Bulk stock toggle | Write |
| POST | `/options/bulk/upsert` | Bulk upsert options | Write |
| POST | `/options/reorder` | Reorder options in group | Write |

---

### GET `/options`
List all option groups.

**Response:**
```json
{
    "success": true,
    "data": [
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
}
```

---

### GET `/options/{group_id}`
Get single option group.

**Response:**
```json
{
    "success": true,
    "data": {
        "id": 1,
        "name": "Pizza Base",
        "order": 1,
        "options": [...]
    }
}
```

---

### POST `/options`
Create new option group. Auto-assigns group ID.

**Request:**
```json
{
    "name": "Sauces",
    "order": 5,
    "options": [
        {"name": "Ketchup", "price": 0},
        {"name": "Mayo", "price": 0.50}
    ]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Option group created",
        "id": 10,
        "group": {
            "id": 10,
            "name": "Sauces",
            "order": 5,
            "options": [
                {"id": 1, "name": "Ketchup", "price": 0, "stock": 1},
                {"id": 2, "name": "Mayo", "price": 0.50, "stock": 1}
            ]
        }
    }
}
```

---

### POST `/options/{group_id}/option`
Add option to existing group.

**Request:**
```json
{
    "name": "BBQ Sauce",
    "price": 0.50,
    "stock": 1
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Option added",
        "option_id": 3,
        "option": {...}
    }
}
```

---

### PATCH `/options/{group_id}`
Update option group.

**Request:**
```json
{
    "set": {
        "name": "Dipping Sauces",
        "order": 10
    }
}
```

---

### PATCH `/options/{group_id}/option/{id}`
Update single option.

**Request:**
```json
{
    "set": {
        "price": 0.75,
        "stock": 0
    }
}
```

---

### DELETE `/options/{group_id}`
Delete entire option group.

---

### DELETE `/options/{group_id}/option/{id}`
Delete single option from group.

---

### POST `/options/bulk/update`
Update multiple options. Max 100 per request.

**Request:**
```json
{
    "updates": [
        {"group_id": 1, "option_id": 2, "set": {"price": 0.99}},
        {"group_id": 1, "option_id": 3, "set": {"stock": 0}}
    ]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Bulk update complete",
        "success_count": 2,
        "fail_count": 0,
        "results": [...]
    }
}
```

---

### POST `/options/bulk/stock`
Bulk stock toggle. Three modes available.

**By specific options:**
```json
{
    "options": [
        {"group_id": 1, "option_id": 2},
        {"group_id": 1, "option_id": 3}
    ],
    "stock": 0
}
```

**By group:**
```json
{
    "group_id": 1,
    "stock": 0
}
```

**All options:**
```json
{
    "all": true,
    "stock": 1
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Stock updated to 0",
        "updated_count": 5
    }
}
```

---

### POST `/options/bulk/upsert`
Bulk create or update options. Max 100 per request.

- Match by `id` if provided → update
- Else match by `name` in group → update
- Else → create new

**Request:**
```json
{
    "group_id": 1,
    "options": [
        {"id": 5, "price": 0.99},
        {"name": "Ketchup", "price": 0},
        {"name": "New Sauce", "price": 0.50}
    ]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Bulk upsert complete",
        "group_id": 1,
        "created": 1,
        "updated": 2,
        "results": [
            {"success": true, "action": "updated", "id": 5},
            {"success": true, "action": "updated", "id": 2},
            {"success": true, "action": "created", "id": 6}
        ]
    }
}
```

---

### POST `/options/reorder`
Reorder options within a group.

**Request:**
```json
{
    "group_id": 1,
    "order": [3, 1, 2]
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Options reordered",
        "group_id": 1,
        "count": 3
    }
}
```

---

## Orders

### Endpoints Table

| Method | Route | Description | Permission |
|--------|-------|-------------|------------|
| GET | `/orders` | List orders with filters | Any |
| GET | `/orders/{id}` | Get single order | Any |
| POST | `/orders/{id}/accept` | Accept order | Write |
| POST | `/orders/{id}/time` | Update estimated time | Write |
| POST | `/orders/{id}/ready` | Mark ready/out for delivery | Write |
| POST | `/orders/{id}/complete` | Complete order | Write |
| POST | `/orders/{id}/cancel` | Cancel order | Write |
| POST | `/orders/{id}/refund` | Full/partial refund | Manager+ |
| DELETE | `/orders/{id}` | Delete order | Admin |

---

### GET `/orders`
List orders with optional filters.

**Query params:**
- `status` - pending, accepted, ready, completed, cancelled
- `date` - YYYY-MM-DD (default: today)
- `from` - Start date
- `to` - End date
- `method` - delivery, collection, table
- `limit` - Per page (default: 50)
- `page` - Page number

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
                "created_at": "2025-12-20 14:30:00"
            }
        ],
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

### GET `/orders/{id}`
Get single order with items.

**Response:**
```json
{
    "success": true,
    "data": {
        "order_id": 456,
        "customer_name": "John Smith",
        "customer_email": "john@example.com",
        "customer_phone": "07123456789",
        "order_total": 25.50,
        "order_status": "pending",
        "delivery_collection": "delivery",
        "delivery_address": "123 High Street",
        "items": [
            {
                "product_name": "Margherita",
                "product_quantity": 2,
                "product_price_total": 19.90,
                "options": "Extra Cheese, Garlic Base"
            }
        ]
    }
}
```

---

### POST `/orders/{id}/accept`
Accept order. Awards loyalty points.

**Request (optional):**
```json
{
    "estimated_time": 30
}
```

---

### POST `/orders/{id}/time`
Update estimated time.

**Request:**
```json
{
    "estimated_time": 45
}
```

---

### POST `/orders/{id}/ready`
Mark order ready (collection) or out for delivery.

---

### POST `/orders/{id}/complete`
Mark order completed.

---

### POST `/orders/{id}/cancel`
Cancel order. Refunds loyalty points.

**Request (optional):**
```json
{
    "reason": "Customer requested cancellation"
}
```

---

### POST `/orders/{id}/refund`
Full or partial refund. Manager+ required.

**Full refund:**
```json
{
    "full": true,
    "reason": "Order not delivered"
}
```

**Partial refund:**
```json
{
    "amount": 5.00,
    "reason": "Missing item"
}
```

---

### DELETE `/orders/{id}`
Delete order permanently. Admin+ required.

---

## Analytics

### Endpoints Table

| Method | Route | Description | Permission |
|--------|-------|-------------|------------|
| GET | `/analytics/summary` | Quick dashboard stats | Any |
| GET | `/analytics/daily` | Daily totals | Any |
| GET | `/analytics/historical` | Date range stats | Any |
| GET | `/analytics/bestsellers` | Top products | Any |
| GET | `/analytics/products` | Product performance | Any |
| GET | `/analytics/customers` | Customer analytics | Any |

---

### GET `/analytics/summary`
Quick dashboard stats.

**Response:**
```json
{
    "success": true,
    "data": {
        "today": {
            "orders": 45,
            "sales": 1250.50,
            "average": 27.79
        },
        "week": {
            "orders": 312,
            "sales": 8750.00
        },
        "pending_orders": 3
    }
}
```

---

### GET `/analytics/daily?date=2025-12-20`
Daily totals for specific date.

---

### GET `/analytics/historical?from=2025-12-01&to=2025-12-20&group=day`
Historical stats for date range.

**Query params:**
- `from` - Start date (required)
- `to` - End date (required)
- `group` - day, week, month (default: day)

---

### GET `/analytics/bestsellers?period=week&limit=10`
Top selling products.

**Query params:**
- `period` - day, week, month (default: week)
- `limit` - Number of products (default: 10)

---

### GET `/analytics/products`
Product performance stats.

---

### GET `/analytics/customers`
Customer analytics.

---

## Config (Generic)

For simple config files (site.json, hours.json, etc.)

### Endpoints Table

| Method | Route | Description | Permission |
|--------|-------|-------------|------------|
| GET | `/config` | List allowed configs | Any |
| GET | `/config/{file}` | Read config | Any |
| PUT | `/config/{file}` | Replace entire config | Write |
| PATCH | `/config/{file}` | Partial update | Write |

---

## Error Responses

**Standard error format:**
```json
{
    "success": false,
    "error": "Error message",
    "details": {
        "code": "ERROR_CODE"
    }
}
```

**HTTP Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 500 | Server error |

**Auth Error Codes:**

| Code | Meaning | Action |
|------|---------|--------|
| `TOKEN_MISSING` | No Authorization header | Authenticate |
| `TOKEN_EXPIRED` | Token past expiry | Re-authenticate |
| `TOKEN_INVALID` | Bad signature | Re-authenticate |
| `TOKEN_MALFORMED` | Invalid format | Check token |

---

## Permission Levels

| Role | Read | Write | Refunds | Delete |
|------|------|-------|---------|--------|
| `global_admin` | ✅ | ✅ | ✅ | ✅ |
| `admin` | ✅ | ✅ | ✅ | ✅ |
| `manager` | ✅ | ✅ | ✅ | ❌ |
| `staff` | ✅ | ❌ | ❌ | ❌ |

---

## ID Management

**Products:**
- Simple products have `id` on product
- Variation parents have NO `id`
- Variation children each have `id`
- All IDs from shared pool (auto-increment)
- ID placed first in JSON

**Options:**
- Group IDs: separate pool, auto-increment
- Option IDs: per-group (1, 2, 3... within each group)

---

## Rate Limits

- Bulk operations: max 100 items per request
- Standard requests: no limit (shared hosting optimized)

---

## Backup Strategy

All config writes create timestamped backups:
```
config/backups/products_2025-12-20_14-30-00.json
config/backups/options_2025-12-20_14-30-00.json
```

Bulk operations create single backup before all changes.
