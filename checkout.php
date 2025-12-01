<?php
/**
 * Checkout Functions
 * 
 * Handles checkout validation, order creation, promo codes, tips, time slots
 */

/**
 * Process checkout form submission
 * 
 * @param array $data - POST data
 * @return array - Response with success/error
 */
function process_checkout($data) {
    $db = get_db();
    
    // Validate CSRF
    if (!verify_csrf_token($data['csrf_token'] ?? '')) {
        return json_response(['success' => false, 'error' => 'Invalid request'], 400);
    }
    
    // 1. Re-validate shop hours and method availability
    $availability_check = check_shop_availability();
    if (!$availability_check['available']) {
        return json_response([
            'success' => false,
            'error' => $availability_check['message']
        ], 400);
    }
    
    // 2. Validate form data
    $validation = validate_checkout_form($data);
    if (!$validation['valid']) {
        return json_response([
            'success' => false,
            'errors' => $validation['errors']
        ], 400);
    }
    
    // 3. Validate cart from server side
    $cart_validation = validate_cart_server_side($data['cart'] ?? '[]');
    if (!$cart_validation['valid']) {
        return json_response([
            'success' => false,
            'error' => $cart_validation['message']
        ], 400);
    }
    
    // 4. Re-validate postcode if delivery
    $delivery_data = null;
    if ($data['delivery_method'] === 'delivery') {
        $postcode_check = validate_postcode($data['postcode']);
        if (!$postcode_check['valid']) {
            return json_response([
                'success' => false,
                'error' => 'Postcode validation failed: ' . $postcode_check['message']
            ], 400);
        }
        $delivery_data = $postcode_check;
    }
    
    // 5. Check if email exists (for registered guest flow)
    $existing_user = check_existing_user($data['email']);
    if ($existing_user && !is_logged_in()) {
        return json_response([
            'success' => false,
            'error' => 'account_exists',
            'email' => $data['email'],
            'message' => 'We found an account with this email. Please login to continue.',
            'benefits' => get_login_benefits($cart_validation['totals']['final'])
        ], 409);
    }
    
    // 6. Calculate final totals with promos
    // Decode promo codes from JSON string
    $promo_codes = json_decode($data['promo_codes'] ?? '[]', true);

    $totals = calculate_order_totals(
        $cart_validation['cart'],
        $delivery_data,
        $promo_codes,
        $data['tip_amount'] ?? 0,
        $existing_user ? $existing_user['id'] : null,
        $data['email'] ?? null
    );
    
    // 7. Create customer record (guest or registered)
    $customer_id = create_or_get_customer($data, $existing_user);
    
    // 8. Create order
    $order_result = create_order($data, $customer_id, $totals, $delivery_data);
    
    if (!$order_result) {
        return json_response([
            'success' => false,
            'error' => 'Failed to create order'
        ], 500);
    }
    
    // 9. Create order products
    $order_id = $order_result['id'];
    $access_token = $order_result['access_token'];
    create_order_products($order_id, $cart_validation['cart']);
    
    // 10. Record promo usage
    if (!empty($totals['promos_applied'])) {
        foreach ($totals['promos_applied'] as $promo) {
            record_promo_usage($promo['code'], $order_id, $customer_id, $promo['discount']);
        }
    }
    
    // 11. Store order in session for payment page
    $_SESSION['pending_order_id'] = $order_id;
    $_SESSION['order_total'] = $totals['final'];
    $_SESSION['order_access_token'] = $access_token;
    
    // 12a. Send confirmation email for cash orders only (already in processing status)
    if ($data['payment_method'] === 'cash') {
        require_once CORE_PATH . 'functions/email_functions.php';
        send_order_confirmation($order_id, $access_token);
    }

    // 12b. Return success with payment redirect
    return json_response([
        'success' => true,
        'order_id' => $order_id,
        'payment_method' => $data['payment_method'],
        'redirect' => $data['payment_method'] === 'cash' 
            ? '/thank-you?order=' . $order_id . '&token=' . $access_token
            : '/payment/' . $order_id . '?token=' . $access_token
    ]);
}

/**
 * Check if shop is open and method is available
 */
function check_shop_availability() {
    $shop_status = get_shop_status();
    
    if (!$shop_status['isOpen']) {
        return [
            'available' => false,
            'message' => 'Sorry, we are currently closed. ' . $shop_status['message']
        ];
    }
    
    $available_methods = get_available_methods();
    
    if (empty($available_methods['methods'])) {
        return [
            'available' => false,
            'message' => 'Sorry, ordering is not available at this time.'
        ];
    }
    
    return ['available' => true];
}

/**
 * Validate checkout form data
 */
function validate_checkout_form($data) {
    $errors = [];
    
    // Name
    if (empty($data['name']) || strlen($data['name']) < 2) {
        $errors['name'] = 'Name is required (min 2 characters)';
    }
    
    // Email
    if (empty($data['email'])) {
        $errors['email'] = 'Email is required';
    } elseif (!is_valid_email($data['email'])) {
        $errors['email'] = 'Invalid email address';
    }
    
    // Phone
    if (empty($data['phone'])) {
        $errors['phone'] = 'Phone number is required';
    } elseif (!is_valid_phone($data['phone'])) {
        $errors['phone'] = 'Invalid UK phone number';
    }
    
    // Delivery method
    if (empty($data['delivery_method']) || !in_array($data['delivery_method'], ['delivery', 'collection'])) {
        $errors['delivery_method'] = 'Please select delivery or collection';
    }
    
    // Address (only if delivery)
    if ($data['delivery_method'] === 'delivery') {
        if (empty($data['address_1'])) {
            $errors['address_1'] = 'Address is required for delivery';
        }
        if (empty($data['postcode'])) {
            $errors['postcode'] = 'Postcode is required for delivery';
        }
    }
    
    // Time selection
    if (empty($data['order_time_type'])) {
        $errors['order_time'] = 'Please select ASAP or scheduled time';
    }
    
    if ($data['order_time_type'] === 'scheduled' && empty($data['scheduled_time'])) {
        $errors['scheduled_time'] = 'Please select a time slot';
    }
    
    // Payment method
    if (empty($data['payment_method']) || !in_array($data['payment_method'], ['card', 'cash'])) {
        $errors['payment_method'] = 'Please select payment method';
    }
    
    // Terms acceptance
    if (empty($data['terms_accepted'])) {
        $errors['terms'] = 'Please accept terms and conditions';
    }
    
    return [
        'valid' => empty($errors),
        'errors' => $errors
    ];
}

/**
 * Validate cart data from server side
 */
function validate_cart_server_side($cart_json) {
    $cart = json_decode($cart_json, true);
    
    if (empty($cart)) {
        return [
            'valid' => false,
            'message' => 'Cart is empty'
        ];
    }
    
    $validated_cart = [];
    $subtotal = 0;
    
    foreach ($cart as $item) {
        $product = get_product_by_id($item['product_id']);
        
        if (!$product) {
            return [
                'valid' => false,
                'message' => 'Product not found: ' . $item['product_name']
            ];
        }
        
        // Check stock
        if (!is_product_in_stock($item['product_id'])) {
            return [
                'valid' => false,
                'message' => 'Product out of stock: ' . $product['name']
            ];
        }
        
        // Convert cart options format to what calculate_product_price expects
        // Cart has: option_id (actual option), group_id (option group)
        // Function expects: option_id (group), selected_id (option)
        // Convert cart options format
        $converted_options = [];
        if (!empty($item['options'])) {
            foreach ($item['options'] as $opt) {
                // Validate required fields exist
                if (!isset($opt['group_id']) || !isset($opt['option_id'])) {
                    continue;
                }
                
                $converted_options[] = [
                    'option_id' => (int)$opt['group_id'],
                    'selected_id' => (int)$opt['option_id'],
                    'child_id' => isset($opt['child_id']) ? (int)$opt['child_id'] : null
                ];
            }
        }
        
        // Recalculate price server-side
        $server_price = calculate_product_price($item['product_id'], $converted_options);
        
        // Use server price, not client price
        $item['total_price'] = $server_price;
        $item['line_total'] = round($server_price * $item['quantity'], 2);

        // Get cpn from product (server-side, don't trust client)
        $item['cpn'] = isset($product['cpn']) ? (int)$product['cpn'] : 1;

        $subtotal += $item['line_total'];
        $validated_cart[] = $item;
    }
    
    return [
        'valid' => true,
        'cart' => $validated_cart,
        'totals' => [
            'subtotal' => $subtotal
        ]
    ];
}

/**
 * Check if user exists with email
 */
function check_existing_user($email) {
    $db = get_db();
    
    $stmt = mysqli_prepare($db, "SELECT id, email FROM users WHERE email = ? LIMIT 1");
    mysqli_stmt_bind_param($stmt, "s", $email);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    
    return mysqli_fetch_assoc($result);
}

/**
 * Get benefits message for login prompt
 */
function get_login_benefits($order_total) {
    $site_config = $GLOBALS['site_config'] ?? [];
    $benefits = [];
    
    // Check if loyalty enabled
    if (!empty($site_config['features']['loyalty'])) {
        $loyalty_config = load_json_config('loyalty.json');
        $points_earned = ($order_total * $loyalty_config['earnRate']) / 100;
        
        $benefits[] = "Earn {$points_earned} loyalty points";
    }
    
    // Check if stamps enabled
    if (!empty($site_config['features']['stamp_cards'])) {
        $benefits[] = "Collect stamps towards free items";
    }
    
    $benefits[] = "View order in history";
    $benefits[] = "Faster checkout next time";
    
    return $benefits;
}

/**
 * Calculate order totals with promos and tips
 */
function calculate_order_totals($cart, $delivery_data, $promo_codes, $tip_amount, $customer_id = null, $email = null) {
    $subtotal = 0;
    $discountable_subtotal = 0;
    
    foreach ($cart as $item) {
        $line_total = round($item['line_total'], 2);
        $subtotal += $line_total;
        
        // Only add to discountable if cpn is not 0 (default to discountable)
        $cpn = isset($item['cpn']) ? (int)$item['cpn'] : 1;
        if ($cpn !== 0) {
            $discountable_subtotal += $line_total;
        }
    }
    $subtotal = round($subtotal, 2);
    $discountable_subtotal = round($discountable_subtotal, 2);
    
    $delivery_fee = $delivery_data ? $delivery_data['deliveryFee'] : 0;
    $delivery_method = $delivery_data ? ($delivery_data['method'] ?? null) : null;
    $tip = (float)$tip_amount;
    
    // Apply promo codes (using discountable subtotal for discount calculation)
    $promo_result = apply_promo_codes($promo_codes, $discountable_subtotal, $delivery_fee, $customer_id, $email, $delivery_method);
    
    $discount = $promo_result['total_discount'];
    $promos_applied = $promo_result['applied'];
    $promos_removed = $promo_result['removed'];
    
    $final = $subtotal + $delivery_fee + $tip - $discount;
    
    return [
        'subtotal' => $subtotal,
        'discountable_subtotal' => $discountable_subtotal,
        'delivery_fee' => $delivery_fee,
        'tip' => $tip,
        'discount' => $discount,
        'final' => max(0, $final),
        'promos_applied' => $promos_applied,
        'promos_removed' => $promos_removed
    ];
}

/**
 * Apply multiple promo codes with stacking logic
 */
function apply_promo_codes($codes, $discountable_subtotal, $delivery_fee, $customer_id = null, $email = null, $delivery_method = null) {
    $all_promos = load_json_config('promotions.json')['codes'] ?? [];
    
    // FIX: Ensure codes is an array (frontend might send empty string)
    if (!is_array($codes)) {
        $codes = empty($codes) ? [] : [$codes];
    }
    
    // Trust the frontend - use only the codes they sent
    // Frontend already handled auto-apply logic and stacking rules
    $all_codes = is_array($codes) ? $codes : [];
    
    $stackable_promos = [];
    $non_stackable_promos = [];
    
    // Validate and categorize each promo
    foreach ($all_codes as $code) {
        $promo = find_promo_by_code($code, $all_promos);
        
        if (!$promo) continue;
        
        // Validate promo
        $validation = validate_promo($promo, $discountable_subtotal, $customer_id, $email, $delivery_method);
        
        if (!$validation['valid']) continue;
        
        // Calculate discount
        $discount = calculate_promo_discount($promo, $discountable_subtotal, $delivery_fee);
        
        if ($discount <= 0) continue;
        
        $promo['discount_amount'] = $discount;
        
        if ($promo['stackable']) {
            $stackable_promos[] = $promo;
        } else {
            $non_stackable_promos[] = $promo;
        }
    }
    
    // Sort non-stackable by discount (highest first)
    usort($non_stackable_promos, function($a, $b) {
        return $b['discount_amount'] <=> $a['discount_amount'];
    });

    $applied = [];
    $removed = [];
    $total_discount = 0;

    // If there's a non-stackable promo, it takes priority and NO other promos apply
    if (!empty($non_stackable_promos)) {
        $best_promo = $non_stackable_promos[0];
        $applied[] = [
            'code' => $best_promo['code'],
            'description' => $best_promo['description'],
            'discount' => $best_promo['discount_amount'],
            'type' => $best_promo['type']
        ];
        $total_discount += $best_promo['discount_amount'];
        
        // Mark other non-stackable as removed
        for ($i = 1; $i < count($non_stackable_promos); $i++) {
            $removed[] = [
                'code' => $non_stackable_promos[$i]['code'],
                'reason' => 'Higher discount applied (' . $best_promo['code'] . ')'
            ];
        }
        
        // Mark ALL stackable promos as removed (non-stackable means alone)
        foreach ($stackable_promos as $promo) {
            $removed[] = [
                'code' => $promo['code'],
                'reason' => 'Cannot combine with ' . $best_promo['code']
            ];
        }
        
    } else {
        // No non-stackable promos, apply all stackable
        foreach ($stackable_promos as $promo) {
            $applied[] = [
                'code' => $promo['code'],
                'description' => $promo['description'],
                'discount' => $promo['discount_amount'],
                'type' => $promo['type']
            ];
            $total_discount += $promo['discount_amount'];
        }
    }
    
    return [
        'total_discount' => $total_discount,
        'applied' => $applied,
        'removed' => $removed
    ];
}

/**
 * Find promo by code
 */
function find_promo_by_code($code, $all_promos) {
    $code_upper = strtoupper($code);
    
    foreach ($all_promos as $promo) {
        if (strtoupper($promo['code']) === $code_upper) {
            return $promo;
        }
    }
    
    return null;
}

/**
 * Validate promo code
 */
function validate_promo($promo, $subtotal, $customer_id, $email = null, $delivery_method = null) {
    $db = get_db();
    
    // Check if active
    if (!$promo['active']) {
        return ['valid' => false, 'message' => 'Promo code not active'];
    }
    
    // Check date range
    $now = date('Y-m-d H:i:s');
    if ($now < $promo['validFrom'] || $now > $promo['validUntil']) {
        return ['valid' => false, 'message' => 'Promo code expired'];
    }
    
    // Check min order
    if ($subtotal < $promo['minOrder']) {
        return ['valid' => false, 'message' => 'Minimum order Ãƒâ€šÃ‚Â£' . $promo['minOrder'] . ' required'];
    }

    // Check method restriction
    if (!empty($promo['methods']) && is_array($promo['methods'])) {
        if ($delivery_method && !in_array($delivery_method, $promo['methods'])) {
            $method_names = implode(' or ', array_map('ucfirst', $promo['methods']));
            return ['valid' => false, 'message' => "This code is only valid for {$method_names}"];
        }
    }
    
    // Check usage limit
    if ($promo['usageLimit']) {
        $stmt = mysqli_prepare($db, "SELECT COUNT(*) as count FROM promo_usage WHERE promo_code = ?");
        mysqli_stmt_bind_param($stmt, "s", $promo['code']);
        mysqli_stmt_execute($stmt);
        $result = mysqli_stmt_get_result($stmt);
        $usage = mysqli_fetch_assoc($result);
        
        if ($usage['count'] >= $promo['usageLimit']) {
            return ['valid' => false, 'message' => 'Promo code usage limit reached'];
        }
    }
    
    // Check first order only
    if ($promo['firstOrderOnly']) {
        if ($customer_id) {
            // Registered customer - check by customer_id
            $stmt = mysqli_prepare($db, "SELECT COUNT(*) as count FROM orders WHERE customer_id = ?");
            mysqli_stmt_bind_param($stmt, "i", $customer_id);
            mysqli_stmt_execute($stmt);
            $result = mysqli_stmt_get_result($stmt);
            $orders = mysqli_fetch_assoc($result);
            
            if ($orders['count'] > 0) {
                return ['valid' => false, 'message' => 'Code already used'];
            }
        } elseif ($email) {
            // Guest - check if ANY customer (G or R) with this email has orders
            $stmt = mysqli_prepare($db, "SELECT COUNT(*) as count 
                                        FROM orders o
                                        WHERE (o.customer_id, o.customer_type) IN (
                                            SELECT customer_id, customer_type 
                                            FROM customer 
                                            WHERE customer_email = ?
                                        )");
            mysqli_stmt_bind_param($stmt, "s", $email);
            mysqli_stmt_execute($stmt);
            $result = mysqli_stmt_get_result($stmt);
            $orders = mysqli_fetch_assoc($result);
            
            if ($orders['count'] > 0) {
                return ['valid' => false, 'message' => 'Code already used'];
            }
        }
    }
    
    // Check one time per customer
    if ($promo['oneTimePerCustomer']) {
        if ($customer_id) {
            // Registered customer - check by customer_id
            $stmt = mysqli_prepare($db, "SELECT COUNT(*) as count FROM promo_usage WHERE promo_code = ? AND customer_id = ?");
            mysqli_stmt_bind_param($stmt, "si", $promo['code'], $customer_id);
            mysqli_stmt_execute($stmt);
            $result = mysqli_stmt_get_result($stmt);
            $usage = mysqli_fetch_assoc($result);
            
            if ($usage['count'] > 0) {
                return ['valid' => false, 'message' => 'Code already used'];
            }
        }   elseif ($email) {
            // Guest - check if ANY customer (G or R) with this email used the code
            $stmt = mysqli_prepare($db, "SELECT COUNT(*) as count 
                                        FROM promo_usage pu
                                        WHERE pu.promo_code = ?
                                        AND (pu.customer_id, pu.customer_type) IN (
                                            SELECT customer_id, customer_type 
                                            FROM customer 
                                            WHERE customer_email = ?
                                        )");
            mysqli_stmt_bind_param($stmt, "ss", $promo['code'], $email);
            mysqli_stmt_execute($stmt);
            $result = mysqli_stmt_get_result($stmt);
            $usage = mysqli_fetch_assoc($result);
            
            if ($usage['count'] > 0) {
                return ['valid' => false, 'message' => 'Code already used'];
            }
        }
        // If no customer_id and no email, allow it (will be validated on submit)
    }
    
    // Check tier requirement
    if (!empty($promo['requiresTier'])) {
        if (!$customer_id) {
            // Reject guests immediately if tier required
            return ['valid' => false, 'message' => 'This code requires a loyalty account. Please log in.'];
        }
        
        $customer = get_customer_by_id($customer_id);
        $tier_levels = ['bronze' => 1, 'silver' => 2, 'gold' => 3, 'platinum' => 4];
        
        $required_level = $tier_levels[$promo['requiresTier']] ?? 0;
        $customer_level = $tier_levels[$customer['loyalty_tier'] ?? 'bronze'] ?? 1;
        
        if ($customer_level < $required_level) {
            return ['valid' => false, 'message' => 'Requires ' . ucfirst($promo['requiresTier']) . ' tier or higher'];
        }
    }
    
    return ['valid' => true];
}

/**
 * Calculate promo discount
 */
function calculate_promo_discount($promo, $discountable_subtotal, $delivery_fee) {
    if ($promo['type'] === 'percent') {
        $discount = round(($discountable_subtotal * $promo['value'] / 100), 2);
        if ($promo['maxDiscount']) {
            $discount = min($discount, $promo['maxDiscount']);
        }
    } elseif ($promo['type'] === 'fixed') {
        $discount = round(min($promo['value'], $discountable_subtotal), 2); // Don't exceed discountable amount
    } elseif ($promo['type'] === 'delivery_fee') {
        $discount = round(min($delivery_fee, $delivery_fee * $promo['value'] / 100), 2);
    } else {
        $discount = 0;
    }
    
    return $discount;
}

/**
 * Create or get customer record
 */
function create_or_get_customer($data, $existing_user = null) {
    $db = get_db();
    
    if (is_logged_in()) {
        // Logged in - use their user_id
        return $_SESSION['user_id'];
    }
    
    if ($existing_user) {
        // Email exists but not logged in - create as guest for now
        // (Order will be linked after login)
        $customer_type = 'G';
        
        // Generate unique guest ID
        $stmt = mysqli_prepare($db, "SELECT MAX(customer_id) as max_id FROM customer WHERE customer_type = 'G'");
        mysqli_stmt_execute($stmt);
        $result = mysqli_stmt_get_result($stmt);
        $row = mysqli_fetch_assoc($result);
        $customer_id = ($row['max_id'] ?? 0) + 1;
        
    } else {
        // New guest
        $customer_type = 'G';
        
        $stmt = mysqli_prepare($db, "SELECT MAX(customer_id) as max_id FROM customer WHERE customer_type = 'G'");
        mysqli_stmt_execute($stmt);
        $result = mysqli_stmt_get_result($stmt);
        $row = mysqli_fetch_assoc($result);
        $customer_id = ($row['max_id'] ?? 0) + 1;
    }
    
    // Insert customer record
    $stmt = mysqli_prepare($db, 
        "INSERT INTO customer (customer_type, customer_id, customer_name, customer_email, customer_tel) 
         VALUES (?, ?, ?, ?, ?)"
    );
    mysqli_stmt_bind_param($stmt, "sisss", $customer_type, $customer_id, $data['name'], $data['email'], $data['phone']);
    mysqli_stmt_execute($stmt);
    
    // Insert address if delivery
    if ($data['delivery_method'] === 'delivery') {
        $stmt = mysqli_prepare($db,
            "INSERT INTO address (customer_type, customer_id, address_1, address_2, postcode)
             VALUES (?, ?, ?, ?, ?)"
        );
        $address2 = $data['address_2'] ?? '';
        mysqli_stmt_bind_param($stmt, "sisss", 
            $customer_type, 
            $customer_id, 
            $data['address_1'], 
            $address2, 
            $data['postcode']
        );
        mysqli_stmt_execute($stmt);
    }
    
    return $customer_id;
}

/**
 * Create order record
 */
function create_order($data, $customer_id, $totals, $delivery_data) {
    $db = get_db();
    
    $customer_type = is_logged_in() ? 'R' : 'G';
    $order_time = date('Y-m-d H:i:s');
    
    // Calculate order_for_time based on time selection
    if ($data['order_time_type'] === 'asap') {
        $ready_minutes = get_ready_minutes($data['delivery_method']);
        $order_for_time = date('Y-m-d H:i:s', strtotime("+{$ready_minutes} minutes"));
    } else {
        $order_for_time = date('Y-m-d H:i:s', strtotime($data['scheduled_time']));
    }
    
    $is_scheduled = $data['order_time_type'] === 'scheduled' ? 1 : 0;
    $scheduled_for = $is_scheduled ? $order_for_time : null;
    
    $payment_method = $data['payment_method'];
    $order_status = $payment_method === 'cash' ? 'processing' : 'waiting';
    
    // Generate access token for secure order viewing  
    $access_token = bin2hex(random_bytes(32));
    
    // Set payment status
    $payment_status = $payment_method === 'cash' ? 'completed' : 'pending';
    
    $promo_codes = !empty($totals['promos_applied']) 
        ? implode(',', array_column($totals['promos_applied'], 'code')) 
        : null;
    
    // Store order notes in variable (required for bind_param by reference)
    $order_notes = $data['order_notes'] ?? '';
    
    $stmt = mysqli_prepare($db,
        "INSERT INTO orders (
            customer_id, customer_type, order_email, order_time, order_for_time,
            scheduled_for, is_scheduled, order_request, order_subtotal, payment_method,
            delivery_collection, delivery_value, discount_value, promo_code,
            tip_amount, order_total, order_status, access_token, payment_status, order_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    );
    
    mysqli_stmt_bind_param($stmt, "isssssisdssddsdsssss",
        $customer_id,
        $customer_type,
        $data['email'],
        $order_time,
        $order_for_time,
        $scheduled_for,
        $is_scheduled,
        $data['delivery_method'],
        $totals['subtotal'],
        $payment_method,
        $data['delivery_method'],
        $totals['delivery_fee'],
        $totals['discount'],
        $promo_codes,
        $totals['tip'],
        $totals['final'],
        $order_status,
        $access_token,
        $payment_status,
        $order_notes
    );
    
    mysqli_stmt_execute($stmt);
    $order_id = mysqli_insert_id($db);
    
    // Return both order_id and access_token
    return [
        'id' => $order_id,
        'access_token' => $access_token
    ];
}

/**
 * Create order products
 */
function create_order_products($order_id, $cart) {
    $db = get_db();
    
    $receipt_order = 1;
    
    foreach ($cart as $item) {
        // Store clean product name separately
        $product_name_only = $item['product_name'];
        // Legacy format for backwards compatibility (desktop client)
        $product_name = $item['product_name'];
        if (!empty($item['options'])) {
            $option_lines = [];
            foreach ($item['options'] as $opt) {
                $opt_text = $opt['option_name'];
                if (!empty($opt['child_name'])) {
                    $opt_text .= ' (' . $opt['child_name'] . ')';
                }
                $option_lines[] = $opt_text;
            }
            if (!empty($option_lines)) {
                $product_name .= '<br>' . implode('<br>', $option_lines);
            }
        }
        
        // NEW: Store structured JSON for KDS/reprinting
        $options_data = !empty($item['options']) ? json_encode($item['options']) : null;
        
        // NEW: Pre-formatted with proper indentation for KDS display
        $options_formatted = '';
        if (!empty($item['options'])) {
            $rendered = [];
            foreach ($item['options'] as $optIndex => $opt) {
                if (in_array($optIndex, $rendered)) continue;
                
                $isChild = !empty($opt['parent_option_id']);
                if ($isChild) continue; // Rendered with parent
                
                // Parent option
                $qtyStr = ($opt['quantity'] ?? 1) > 1 ? ' x' . $opt['quantity'] : '';
                $options_formatted .= "+ {$opt['option_name']}{$qtyStr}\n";
                $rendered[] = $optIndex;
                
                // Children immediately after
                foreach ($item['options'] as $childIndex => $childOpt) {
                    if (($childOpt['parent_option_id'] ?? null) === $opt['option_id']) {
                        $childQtyStr = ($childOpt['quantity'] ?? 1) > 1 ? ' x' . $childOpt['quantity'] : '';
                        $options_formatted .= "  + {$childOpt['option_name']}{$childQtyStr}\n";
                        $rendered[] = $childIndex;
                    }
                }
            }
        }
        
        $stmt = mysqli_prepare($db,
            "INSERT INTO order_products 
            (order_id, product_id, product_name, product_name_only, options_data, options_formatted, product_quantity, product_price_total, receipt_order) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        );
        
        mysqli_stmt_bind_param($stmt, "iisssssdi",
            $order_id,
            $item['product_id'],
            $product_name,
            $product_name_only,
            $options_data,
            $options_formatted,
            $item['quantity'],
            $item['line_total'],
            $receipt_order
        );
        
        mysqli_stmt_execute($stmt);
        $receipt_order++;
    }
}

/**
 * Record promo usage
 */
function record_promo_usage($promo_code, $order_id, $customer_id, $discount_amount) {
    $db = get_db();
    $customer_type = is_logged_in() ? 'R' : 'G';
    
    $stmt = mysqli_prepare($db,
        "INSERT INTO promo_usage (promo_code, promo_id, order_id, customer_id, customer_type, discount_amount, used_at)
        VALUES (?, NULL, ?, ?, ?, ?, NOW())"
    );

    mysqli_stmt_bind_param($stmt, "siisd",
        $promo_code,
        $order_id,
        $customer_id,
        $customer_type,
        $discount_amount
    );
    
    mysqli_stmt_execute($stmt);
}

/**
 * Get ready minutes for method
 */
function get_ready_minutes($method) {
    $delivery = load_json_config('delivery.json');
    $day_of_week = (int)date('N');
    
    foreach ($delivery['windows'] as $window) {
        if (in_array($day_of_week, $window['days']) && $window['method'] === $method) {
            return $window['readyInMinutes'] ?? 30;
        }
    }
    
    return 30; // Default
}

/**
 * Get available time slots for scheduling
 */
function get_available_timeslots($method) {
    $delivery = load_json_config('delivery.json');
    $now = time();
    $current_time = date('H:i', $now);
    $day_of_week = (int)date('N');
    
    // Find active window for this method
    $active_window = null;
    foreach ($delivery['windows'] as $window) {
        if (!in_array($day_of_week, $window['days'])) continue;
        if ($window['method'] !== $method && $window['method'] !== 'both') continue;
        
        $ends_next_day = $window['endsNextDay'] ?? false;
        if (time_in_range($current_time, $window['start'], $window['end'], $ends_next_day)) {
            $active_window = $window;
            break;
        }
    }
    
    if (!$active_window) {
        return [];
    }
    
    $slots = [];
    $ready_minutes = $active_window['readyInMinutes'] ?? 30;
    
    // Start from next quarter hour after ready time
    $start_time = strtotime("+{$ready_minutes} minutes");
    $start_quarter = ceil($start_time / 900) * 900; // Round up to nearest 15 min
    
    // End time = window end time minus ready minutes
    $end_time_str = $active_window['end'];
    $end_minutes = time_to_minutes($end_time_str) - $ready_minutes;
    $end_time = strtotime("today") + ($end_minutes * 60);
    
    // Handle overnight
    if ($active_window['endsNextDay']) {
        $end_time = strtotime("tomorrow") + ($end_minutes * 60);
    }
    
    // Generate 15-minute slots
    for ($time = $start_quarter; $time <= $end_time; $time += 900) {
        $slots[] = [
            'value' => date('Y-m-d H:i:s', $time),
            'label' => date('H:i', $time)
        ];
    }
    
    return $slots;
}

/**
 * Get customer by ID
 */
function get_customer_by_id($customer_id) {
    $db = get_db();
    
    $stmt = mysqli_prepare($db, 
        "SELECT * FROM customer WHERE customer_id = ? AND customer_type = 'R' LIMIT 1"
    );
    mysqli_stmt_bind_param($stmt, "i", $customer_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    
    return mysqli_fetch_assoc($result);
}

/**
 * Handle AJAX request to apply manual promo code
 * 
 * @param array $data - POST data with 'code', 'subtotal', 'delivery_fee', 'customer_id'
 * @return array - JSON response
 */
function handle_apply_promo($data) {
    $code = strtoupper(trim($data['code'] ?? ''));
    $subtotal = (float)($data['subtotal'] ?? 0);
    $delivery_fee = (float)($data['delivery_fee'] ?? 0);
    $customer_id = $data['customer_id'] ?? null;
    $email = trim($data['email'] ?? '');
    
    if (empty($code)) {
        return json_response(['success' => false, 'error' => 'Please enter a promo code'], 400);
    }
    
    // Load all promos
    $all_promos = load_json_config('promotions.json')['codes'] ?? [];
    
    // Find the promo
    $promo = find_promo_by_code($code, $all_promos);
    
    if (!$promo) {
        return json_response(['success' => false, 'error' => 'Invalid promo code'], 400);
    }
    
    // Validate the promo
    $delivery_method = $data['method'] ?? null;
    $validation = validate_promo($promo, $subtotal, $customer_id, $email ?: null, $delivery_method);
    
    if (!$validation['valid']) {
        return json_response(['success' => false, 'error' => $validation['message']], 400);
    }
    
    // Get currently applied codes from frontend
    $current_codes = $data['current_codes'] ?? [];
    
    // Check if already applied
    if (in_array($code, $current_codes)) {
        return json_response(['success' => false, 'error' => 'Code already applied'], 400);
    }
    
    // Add new code to the list
    $all_codes = array_merge($current_codes, [$code]);
    
    // Calculate totals with all promos
    $result = apply_promo_codes($all_codes, $subtotal, $delivery_fee, $customer_id, $email ?: null, $delivery_method);
    
    return json_response([
        'success' => true,
        'total_discount' => $result['total_discount'],
        'applied' => $result['applied'],
        'removed' => $result['removed']
    ]);
}

/**
 * Handle AJAX request to check for auto-apply promos
 * 
 * @param array $data - POST data with 'subtotal', 'delivery_fee', 'customer_id'
 * @return array - JSON response
 */
function handle_check_auto_promos($data) {
    $subtotal = (float)($data['subtotal'] ?? 0);
    $delivery_fee = (float)($data['delivery_fee'] ?? 0);
    $customer_id = $data['customer_id'] ?? null;
    $email = trim($data['email'] ?? '');
    
    // Discover auto-apply promos
    $all_promos = load_json_config('promotions.json')['codes'] ?? [];
    $auto_codes = [];
    foreach ($all_promos as $promo) {
        if ($promo['autoApply'] && $promo['active']) {
            $auto_codes[] = $promo['code'];
        }
    }
    
    // Pass discovered auto-promos to validation
    $delivery_method = $data['method'] ?? null;
    $result = apply_promo_codes($auto_codes, $subtotal, $delivery_fee, $customer_id, $email ?: null, $delivery_method);
    
    return json_response([
        'success' => true,
        'total_discount' => $result['total_discount'],
        'applied' => $result['applied']
    ]);
}

/**
 * Get all addresses for a registered customer
 */
function get_customer_addresses($customer_id) {
    $db = get_db();
    
    $stmt = mysqli_prepare($db, 
        "SELECT * FROM address WHERE customer_id = ? AND customer_type = 'R' ORDER BY address_id DESC"
    );
    mysqli_stmt_bind_param($stmt, "i", $customer_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    
    $addresses = [];
    while ($row = mysqli_fetch_assoc($result)) {
        $addresses[] = $row;
    }
    
    return $addresses;
}

/**
 * Add new address for registered customer
 */
function add_customer_address($customer_id, $data) {
    $db = get_db();
    
    $stmt = mysqli_prepare($db,
        "INSERT INTO address (customer_type, customer_id, address_1, address_2, postcode)
         VALUES ('R', ?, ?, ?, ?)"
    );
    $address2 = $data['address_2'] ?? '';
    mysqli_stmt_bind_param($stmt, "isss", 
        $customer_id, 
        $data['address_1'], 
        $address2, 
        $data['postcode']
    );
    mysqli_stmt_execute($stmt);
    
    return mysqli_insert_id($db);
}