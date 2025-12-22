<?php
/**
 * Dashboard
 */

load_api_client();

$user = get_hub_user();
$shops = get_user_shops($user['id'], (bool) $user['is_global_admin']);

// Get summaries from each shop (could be slow - consider AJAX later)
$summaries = [];
foreach ($shops as $shop) {
    $result = api_get($shop, '/analytics/summary');
    $summaries[$shop['shop_id']] = [
        'shop' => $shop,
        'success' => $result['success'],
        'data' => $result['data'] ?? null,
        'error' => $result['error'] ?? null,
    ];
}

render('dashboard.latte', [
    'user' => $user,
    'shops' => $shops,
    'summaries' => $summaries,
]);
