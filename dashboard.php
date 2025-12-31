<?php
require_once CORE_PATH . 'functions/order.php';
/**
 * Dashboard Functions
 * 
 * Functions for customer dashboard pages
 */

/**
 * Get customer profile with points and tier info
 * 
 * @param int $user_id - User ID
 * @return array|null - Customer data or null
 */
function get_customer_profile($user_id) {
    $db = get_db();
    
    $stmt = mysqli_prepare($db, "
        SELECT 
            c.customer_id,
            c.customer_name,
            c.customer_email,
            c.customer_tel,
            c.customer_sub,
            c.loyalty_tier,
            c.total_spent,
            c.total_orders,
            c.card_customer,
            COALESCE(SUM(cp.points_available), 0) as points_available,
            COALESCE(SUM(cp.points_used), 0) as points_used
        FROM customer c
        LEFT JOIN customer_points cp ON c.customer_id = cp.customer_id
        WHERE c.customer_id = ? AND c.customer_type = 'R'
        GROUP BY c.customer_id
        LIMIT 1
    ");
    mysqli_stmt_bind_param($stmt, "i", $user_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    
    return mysqli_fetch_assoc($result);
}

/**
 * Get customer's orders with pagination
 * 
 * @param int $user_id - User ID
 * @param int $limit - Orders per page
 * @param int $offset - Offset for pagination
 * @return array - ['orders' => [], 'total' => int]
 */
function get_customer_orders($user_id, $limit = 10, $offset = 0) {
    $db = get_db();
    
    // Get total count
    $stmt = mysqli_prepare($db, "
        SELECT COUNT(*) as total 
        FROM orders 
        WHERE customer_id = ? AND customer_type = 'R'
    ");
    mysqli_stmt_bind_param($stmt, "i", $user_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    $total = mysqli_fetch_assoc($result)['total'];
    
    // Get orders
    $stmt = mysqli_prepare($db, "
        SELECT 
            order_id,
            store_id,
            order_time,
            order_for_time,
            delivery_collection,
            order_subtotal,
            delivery_value,
            discount_value,
            tip_amount,
            order_total,
            order_status,
            payment_status,
            payment_method,
            access_token
        FROM orders 
        WHERE customer_id = ? AND customer_type = 'R'
        ORDER BY order_time DESC
        LIMIT ? OFFSET ?
    ");
    mysqli_stmt_bind_param($stmt, "iii", $user_id, $limit, $offset);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    
    $orders = [];
    while ($row = mysqli_fetch_assoc($result)) {
        // Get item count for this order
        $stmt2 = mysqli_prepare($db, "
            SELECT SUM(product_quantity) as item_count 
            FROM order_products 
            WHERE order_id = ?
        ");
        mysqli_stmt_bind_param($stmt2, "i", $row['order_id']);
        mysqli_stmt_execute($stmt2);
        $count_result = mysqli_stmt_get_result($stmt2);
        $row['item_count'] = mysqli_fetch_assoc($count_result)['item_count'] ?? 0;
        
        // Add store display name
        $row['store_name'] = $row['store_id'] ? get_store_display_name($row['store_id']) : null;
        
        $orders[] = $row;
    }
    
    return [
        'orders' => $orders,
        'total' => $total
    ];
}

/**
 * Get recent orders for dashboard overview
 * 
 * @param int $user_id - User ID
 * @param int $limit - Number of orders
 * @return array - Orders
 */
function get_recent_orders($user_id, $limit = 5) {
    $result = get_customer_orders($user_id, $limit, 0);
    return $result['orders'];
}

/**
 * Get single order details for customer
 * 
 * @param int $order_id - Order ID
 * @param int $user_id - User ID (for authorization)
 * @return array|null - Order with products or null
 */
function get_customer_order_details($order_id, $user_id) {
    $db = get_db();
    
    // Get order (verify ownership)
    $stmt = mysqli_prepare($db, "
        SELECT 
            o.*,
            c.customer_name,
            c.customer_tel
        FROM orders o
        LEFT JOIN customer c ON o.customer_id = c.customer_id AND o.customer_type = c.customer_type
        WHERE o.order_id = ? AND o.customer_id = ? AND o.customer_type = 'R'
        LIMIT 1
    ");
    mysqli_stmt_bind_param($stmt, "ii", $order_id, $user_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    $order = mysqli_fetch_assoc($result);
    
    if (!$order) {
        return null;
    }

    // Get products (include offer fields for grouping)
    $stmt = mysqli_prepare($db, "
        SELECT 
            order_products_id,
            product_id,
            product_name,
            product_name_only,
            options_formatted,
            product_quantity,
            product_price_total,
            is_free,
            offer_id,
            linked_to_id
        FROM order_products 
        WHERE order_id = ?
        ORDER BY receipt_order ASC
    ");
    mysqli_stmt_bind_param($stmt, "i", $order_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    
    $products = [];
    while ($row = mysqli_fetch_assoc($result)) {
        $products[] = $row;
    }
    
    $order['products'] = group_order_products_for_display($products);
    
    // Get address if delivery
    if ($order['delivery_collection'] === 'delivery') {
        $order['address'] = get_order_address($order_id, $user_id, 'R');
    }
    
    return $order;
}

/**
 * Get order address
 * 
 * @param int $order_id - Order ID
 * @param int $customer_id - Customer ID
 * @param string $customer_type - R or G
 * @return array|null - Address or null
 */
function get_order_address($order_id, $customer_id, $customer_type) {
    $db = get_db();
    
    // First try to get from order_address table if it exists
    // Fallback to customer's default address
    $stmt = mysqli_prepare($db, "
        SELECT address_1, address_2, postcode 
        FROM address 
        WHERE customer_id = ? AND customer_type = ?
        ORDER BY address_id DESC
        LIMIT 1
    ");
    mysqli_stmt_bind_param($stmt, "is", $customer_id, $customer_type);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    
    return mysqli_fetch_assoc($result);
}

/**
 * Get order status badge class
 * 
 * @param string $status - Order status
 * @return string - Bootstrap badge class
 */
function get_status_badge_class($status) {
    $classes = [
        'waiting' => 'bg-warning text-dark',
        'processing' => 'bg-info',
        'accepted' => 'bg-primary',
        'ready' => 'bg-success',
        'completed' => 'bg-success',
        'cancelled' => 'bg-danger',
        'refunded' => 'bg-secondary'
    ];
    
    return $classes[$status] ?? 'bg-secondary';
}

/**
 * Get order status display text
 * 
 * @param string $status - Order status
 * @return string - Display text
 */
function get_status_display_text($status) {
    $texts = [
        'waiting' => 'Awaiting Payment',
        'processing' => 'Being Prepared',
        'accepted' => 'Accepted',
        'ready' => 'Ready',
        'completed' => 'Completed',
        'cancelled' => 'Cancelled',
        'refunded' => 'Refunded'
    ];
    
    return $texts[$status] ?? ucfirst($status);
}

/**
 * Get payment status badge class
 * 
 * @param string $status - Payment status
 * @return string - Bootstrap badge class
 */
function get_payment_badge_class($status) {
    $classes = [
        'pending' => 'bg-warning text-dark',
        'processing' => 'bg-info',
        'completed' => 'bg-success',
        'failed' => 'bg-danger',
        'refunded' => 'bg-secondary'
    ];
    
    return $classes[$status] ?? 'bg-secondary';
}

/**
 * Update customer profile
 * 
 * @param int $user_id - User ID
 * @param array $data - Profile data
 * @return bool - Success
 */
function update_customer_profile($user_id, $data) {
    $db = get_db();
    
    $name = clean_input($data['name'] ?? '');
    $phone = clean_input($data['phone'] ?? '');
    
    if (empty($name)) {
        return false;
    }
    
    $stmt = mysqli_prepare($db, "
        UPDATE customer 
        SET customer_name = ?, customer_tel = ?
        WHERE customer_id = ? AND customer_type = 'R'
    ");
    mysqli_stmt_bind_param($stmt, "ssi", $name, $phone, $user_id);
    mysqli_stmt_execute($stmt);
    
    return mysqli_affected_rows($db) >= 0;
}

/**
 * Update customer password
 * 
 * @param int $user_id - User ID
 * @param string $current_password - Current password
 * @param string $new_password - New password
 * @return array - ['success' => bool, 'error' => string|null]
 */
function update_customer_password($user_id, $current_password, $new_password) {
    $db = get_db();
    
    // Get current password hash
    $stmt = mysqli_prepare($db, "SELECT password FROM users WHERE id = ? LIMIT 1");
    mysqli_stmt_bind_param($stmt, "i", $user_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    $user = mysqli_fetch_assoc($result);
    
    if (!$user) {
        return ['success' => false, 'error' => 'User not found'];
    }
    
    // Verify current password
    if (!password_verify($current_password, $user['password'])) {
        return ['success' => false, 'error' => 'Current password is incorrect'];
    }
    
    // Validate new password
    if (strlen($new_password) < 8) {
        return ['success' => false, 'error' => 'New password must be at least 8 characters'];
    }
    
    // Update password
    $new_hash = password_hash($new_password, PASSWORD_DEFAULT);
    $stmt = mysqli_prepare($db, "UPDATE users SET password = ? WHERE id = ?");
    mysqli_stmt_bind_param($stmt, "si", $new_hash, $user_id);
    mysqli_stmt_execute($stmt);
    
    return ['success' => true, 'error' => null];
}

/**
 * Update customer address
 * 
 * @param int $address_id - Address ID
 * @param int $user_id - User ID (for authorization)
 * @param array $data - Address data
 * @return bool - Success
 */
function update_customer_address($address_id, $user_id, $data) {
    $db = get_db();
    
    $stmt = mysqli_prepare($db, "
        UPDATE address 
        SET address_1 = ?, address_2 = ?, postcode = ?
        WHERE address_id = ? AND customer_id = ? AND customer_type = 'R'
    ");
    
    $address_2 = $data['address_2'] ?? '';
    $postcode = strtoupper(trim($data['postcode'] ?? ''));
    
    mysqli_stmt_bind_param($stmt, "sssii", 
        $data['address_1'], 
        $address_2, 
        $postcode,
        $address_id,
        $user_id
    );
    mysqli_stmt_execute($stmt);
    
    return mysqli_affected_rows($db) >= 0;
}

/**
 * Delete customer address
 * 
 * @param int $address_id - Address ID
 * @param int $user_id - User ID (for authorization)
 * @return bool - Success
 */
function delete_customer_address($address_id, $user_id) {
    $db = get_db();
    
    $stmt = mysqli_prepare($db, "
        DELETE FROM address 
        WHERE address_id = ? AND customer_id = ? AND customer_type = 'R'
    ");
    mysqli_stmt_bind_param($stmt, "ii", $address_id, $user_id);
    mysqli_stmt_execute($stmt);
    
    return mysqli_affected_rows($db) > 0;
}

/**
 * Get loyalty tier info
 * 
 * @param string $tier - Tier name
 * @return array - Tier configuration
 */
function get_tier_info($tier = 'bronze') {
    $loyalty_config = load_json_config('loyalty.json');
    return $loyalty_config['tiers'][$tier] ?? $loyalty_config['tiers']['bronze'];
}

/**
 * Get next tier info
 * 
 * @param string $current_tier - Current tier name
 * @param float $total_spent - Total spent
 * @return array|null - Next tier info or null if at max
 */
function get_next_tier_info($current_tier, $total_spent) {
    $loyalty_config = load_json_config('loyalty.json');
    $tiers = $loyalty_config['tiers'];
    $tier_order = ['bronze', 'silver', 'gold', 'platinum'];
    
    $current_index = array_search($current_tier, $tier_order);
    if ($current_index === false || $current_index >= count($tier_order) - 1) {
        return null; // Already at max tier
    }
    
    $next_tier = $tier_order[$current_index + 1];
    $next_threshold = $tiers[$next_tier]['threshold'];
    $current_threshold = $tiers[$current_tier]['threshold'];
    $remaining = $next_threshold - $total_spent;
    
    // Calculate progress within tier range (matches loyalty.php)
    $range = $next_threshold - $current_threshold;
    $progress = $total_spent - $current_threshold;
    $progress_percent = $range > 0 ? min(100, ($progress / $range) * 100) : 100;
    
    return [
        'name' => $tiers[$next_tier]['name'],
        'threshold' => $next_threshold,
        'remaining' => max(0, $remaining),
        'progress' => round($progress_percent, 1)
    ];
}

/**
 * Get customer's reservations
 *
 * @param int $user_id - User ID
 * @return array - ['upcoming' => [], 'past' => []]
 */
function get_customer_reservations($user_id) {
    $db = get_db();

    $now = date('Y-m-d H:i:s');
    $today = date('Y-m-d');

    // Get upcoming reservations (today onwards, not cancelled/no-show)
    $stmt = mysqli_prepare($db, "
        SELECT * FROM reservations
        WHERE customer_id = ?
        AND customer_type = 'R'
        AND reservation_date >= ?
        AND status NOT IN ('pending', 'cancelled', 'no_show')
        ORDER BY reservation_date ASC, reservation_time ASC
    ");
    mysqli_stmt_bind_param($stmt, "is", $user_id, $today);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);

    $upcoming = [];
    while ($row = mysqli_fetch_assoc($result)) {
        $upcoming[] = $row;
    }

    // Get past reservations (before today, or completed/cancelled/no-show)
    $stmt = mysqli_prepare($db, "
        SELECT * FROM reservations
        WHERE customer_id = ?
        AND customer_type = 'R'
        AND (
            reservation_date < ?
            OR status IN ('completed', 'cancelled', 'no_show')
        )
        ORDER BY reservation_date DESC, reservation_time DESC
        LIMIT 20
    ");
    mysqli_stmt_bind_param($stmt, "is", $user_id, $today);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);

    $past = [];
    while ($row = mysqli_fetch_assoc($result)) {
        $past[] = $row;
    }

    return [
        'upcoming' => $upcoming,
        'past' => $past
    ];
}

/**
 * Get reservation status badge class
 *
 * @param string $status - Reservation status
 * @return string - Bootstrap badge class
 */
function get_reservation_badge_class($status) {
    $classes = [
        'pending' => 'bg-warning text-dark',
        'confirmed' => 'bg-success',
        'completed' => 'bg-secondary',
        'cancelled' => 'bg-danger',
        'no_show' => 'bg-danger'
    ];

    return $classes[$status] ?? 'bg-secondary';
}

/**
 * Get reservation status display text
 *
 * @param string $status - Reservation status
 * @return string - Display text
 */
function get_reservation_status_text($status) {
    $texts = [
        'pending' => 'Pending',
        'confirmed' => 'Confirmed',
        'completed' => 'Completed',
        'cancelled' => 'Cancelled',
        'no_show' => 'No Show'
    ];

    return $texts[$status] ?? ucfirst($status);
}

/**
 * Check if reservation can have calendar export
 *
 * @param array $reservation - Reservation data
 * @return bool - True if future reservation
 */
function can_add_to_calendar($reservation) {
    $reservation_datetime = strtotime($reservation['reservation_date'] . ' ' . $reservation['reservation_time']);
    return $reservation_datetime > time() && in_array($reservation['status'], ['confirmed']);
}
