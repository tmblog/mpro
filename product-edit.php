<?php
/**
 * Edit Product
 */

$shop = get_selected_shop();

if (!$shop) {
    flash('error', 'Please select a shop first');
    redirect('/');
}

// Get product ID from URL
$product_id = $m[1] ?? null;

if (!$product_id) {
    flash('error', 'Product ID required');
    redirect('/products');
}

load_api_client();

// Fetch the product
$product_result = api_get($shop, '/products/' . $product_id);

if (!$product_result['success']) {
    flash('error', $product_result['error'] ?? 'Product not found');
    redirect('/products');
}

$product = $product_result['data']['product'] ?? null;
$product_type = $product_result['data']['type'] ?? 'simple';
$product_category = $product_result['data']['category'] ?? '';

if (!$product) {
    flash('error', 'Product not found');
    redirect('/products');
}

// For variations, fetch parent and all siblings
$parent_product = null;
$all_variations = [];

if ($product_type === 'variation') {
    // Fetch all products to find the parent
    $all_products = api_get($shop, '/products/category/' . urlencode($product_category));
    
    if ($all_products['success']) {
        foreach ($all_products['data']['products'] ?? [] as $p) {
            if (isset($p['vari'])) {
                foreach ($p['vari'] as $v) {
                    if ((int)$v['id'] === (int)$product_id) {
                        $parent_product = $p;
                        $all_variations = $p['vari'];
                        break 2;
                    }
                }
            }
        }
    }
}

// Fetch existing categories from products
$products_result = api_get($shop, '/products');
$categories = [];
if ($products_result['success']) {
    $categories = array_keys($products_result['data'] ?? []);
}

// Fetch option groups
$options_result = api_get($shop, '/options');
$option_groups = [];
if ($options_result['success']) {
    $option_groups = $options_result['data'] ?? [];
}

render('product-edit.latte', [
    'shop' => $shop,
    'product' => $product,
    'product_id' => $product_id,
    'product_type' => $product_type,
    'product_category' => $product_category,
    'categories' => $categories,
    'option_groups' => $option_groups,
    'parent_product' => $parent_product,
    'all_variations' => $all_variations,
    'csrf_token' => csrf_token(),
]);