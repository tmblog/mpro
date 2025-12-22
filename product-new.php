<?php
/**
 * Create New Product
 */

$shop = get_selected_shop();

if (!$shop) {
    flash('error', 'Please select a shop first');
    redirect('/');
}

load_api_client();

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

render('product-new.latte', [
    'shop' => $shop,
    'categories' => $categories,
    'option_groups' => $option_groups,
    'csrf_token' => csrf_token(),
]);