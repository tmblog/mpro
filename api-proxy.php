<?php
/**
 * API Proxy - For JS calls to shop APIs
 */

load_api_client();

// Get the API path after /api/
$api_path = str_replace('/api', '', $path);

// Get shop ID from query or body
$shop_id = $_GET['shop_id'] ?? null;

if ($method === 'POST' || $method === 'PATCH' || $method === 'PUT') {
    $body = get_post_data();
    $shop_id = $shop_id ?? ($body['shop_id'] ?? null);
}

if (!$shop_id) {
    json_response(['success' => false, 'error' => 'shop_id required'], 400);
}

$shop_id = (int) $shop_id;

// Verify access
if (!can_access_shop(current_user_id(), $shop_id, is_global_admin())) {
    json_response(['success' => false, 'error' => 'Access denied'], 403);
}

$shop = get_shop($shop_id);
if (!$shop) {
    json_response(['success' => false, 'error' => 'Shop not found'], 404);
}

// Route API calls
$result = match(true) {
    // Products
    $method === 'GET' && preg_match('#^/products/(\d+)$#', $api_path, $m) === 1
        => api_get($shop, '/products/' . $m[1]),
    
    $method === 'PATCH' && preg_match('#^/products/(\d+)$#', $api_path, $m) === 1
        => api_patch($shop, '/products/' . $m[1], $body),

    $method === 'PATCH' && preg_match('#^/products/parent/(.+)$#', $api_path, $pm) === 1
    => api_patch($shop, '/products/parent/' . urldecode($pm[1]), [
        'category' => $_GET['category'] ?? $body['category'] ?? '',
        'set' => $body['set'] ?? []
    ]),
    
    $method === 'POST' && $api_path === '/products/bulk-update'
        => api_post($shop, '/products/bulk/update', ['updates' => $body['updates'] ?? []]),
    
    $method === 'POST' && $api_path === '/products'
    => api_post($shop, '/products', ['category' => $body['category'] ?? '', 'product' => $body['product'] ?? []]),

    $method === 'POST' && $api_path === '/products/category'
    => api_post($shop, '/products/category', $body),

    $method === 'POST' && $api_path === '/products/reorder/categories'
        => api_post($shop, '/products/reorder/categories', ['order' => $body['order'] ?? []]),

    $method === 'POST' && $api_path === '/products/reorder/products'
        => api_post($shop, '/products/reorder/products', [
            'category' => $body['category'] ?? '',
            'order' => $body['order'] ?? []
        ]),
    
    $method === 'POST' && preg_match('#^/products/variation/(.+)$#', $api_path, $vm) === 1
    => api_post($shop, '/products/variation/' . urldecode($vm[1]), [
        'category' => $body['category'] ?? '',
        'variation' => $body['variation'] ?? []
    ]),
    
    // Orders
    $method === 'GET' && preg_match('#^/orders/(\d+)$#', $api_path, $m) === 1
        => api_get($shop, '/orders/' . $m[1]),
    
    $method === 'POST' && preg_match('#^/orders/(\d+)/(\w+)$#', $api_path, $m) === 1
        => api_post($shop, '/orders/' . $m[1] . '/' . $m[2], $body),
    
    // Options
    $method === 'GET' && $api_path === '/options'
        => api_get($shop, '/options'),
    
    // Analytics
    $method === 'GET' && str_starts_with($api_path, '/analytics')
        => api_get($shop, $api_path . '?' . http_build_query($_GET)),
    
    $method === 'DELETE' && preg_match('#^/products/(\d+)$#', $api_path, $m) === 1
        => api_delete($shop, '/products/' . $m[1]),

    $method === 'DELETE' && preg_match('#^/products/parent/(.+)$#', $api_path, $pm) === 1
        => api_delete($shop, '/products/parent/' . urldecode($pm[1]) . '?category=' . urlencode($_GET['category'] ?? '')),

    $method === 'DELETE' && preg_match('#^/products/category/(.+)$#', $api_path, $cm) === 1
        => api_delete($shop, '/products/category/' . urldecode($cm[1]) . (isset($_GET['force']) ? '?force=1' : '')),


    // ========== OPTIONS ==========

    // GET /options - List all
    $method === 'GET' && $api_path === '/options'
        => api_get($shop, '/options'),

    // GET /options/{id} - Single group
    $method === 'GET' && preg_match('#^/options/(\d+)$#', $api_path, $m) === 1
        => api_get($shop, '/options/' . $m[1]),

    // POST /options - Create group
    $method === 'POST' && $api_path === '/options'
        => api_post($shop, '/options', [
            'name' => $body['name'] ?? '',
            'order' => $body['order'] ?? 0,
            'options' => $body['options'] ?? []
        ]),

    // PATCH /options/{id} - Update group
    $method === 'PATCH' && preg_match('#^/options/(\d+)$#', $api_path, $m) === 1
        => api_patch($shop, '/options/' . $m[1], [
            'set' => $body['set'] ?? []
        ]),

    // DELETE /options/{id} - Delete group
    $method === 'DELETE' && preg_match('#^/options/(\d+)$#', $api_path, $m) === 1
        => api_delete($shop, '/options/' . $m[1]),

    // POST /options/{id}/option - Add option
    $method === 'POST' && preg_match('#^/options/(\d+)/option$#', $api_path, $m) === 1
        => api_post($shop, '/options/' . $m[1] . '/option', [
            'name' => $body['name'] ?? '',
            'price' => $body['price'] ?? 0,
            'stock' => $body['stock'] ?? 1
        ]),

    // PATCH /options/{id}/option/{opt_id} - Update option
    $method === 'PATCH' && preg_match('#^/options/(\d+)/option/(\d+)$#', $api_path, $m) === 1
        => api_patch($shop, '/options/' . $m[1] . '/option/' . $m[2], [
            'set' => $body['set'] ?? []
        ]),

    // DELETE /options/{id}/option/{opt_id} - Delete option
    $method === 'DELETE' && preg_match('#^/options/(\d+)/option/(\d+)$#', $api_path, $m) === 1
        => api_delete($shop, '/options/' . $m[1] . '/option/' . $m[2]),

    // POST /options/bulk/update
    $method === 'POST' && $api_path === '/options/bulk/update'
        => api_post($shop, '/options/bulk/update', [
            'updates' => $body['updates'] ?? []
        ]),

    // POST /options/bulk/stock
    $method === 'POST' && $api_path === '/options/bulk/stock'
        => api_post($shop, '/options/bulk/stock', array_filter([
            'options' => $body['options'] ?? null,
            'group_id' => $body['group_id'] ?? null,
            'all' => $body['all'] ?? null,
            'stock' => $body['stock'] ?? 1
        ], fn($v) => $v !== null)),

    $method === 'POST' && $api_path === '/options/reorder'
    => api_post($shop, '/options/reorder', [
        'group_id' => $body['group_id'] ?? 0,
        'order' => $body['order'] ?? []
    ]),
    
    // Default
    default => ['success' => false, 'error' => 'Unknown API endpoint']
};

json_response($result);