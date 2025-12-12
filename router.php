<?php
/**
 * Router Functions
 * 
 * Handles all URL routing for the application
 */

/**
 * Main routing function
 * 
 * @param string $uri - Request URI
 * @param string $method - HTTP method (GET, POST, etc.)
 */
function route($uri, $method = 'GET') {
    // Remove base path if running in subdirectory (e.g., /orders/)
    $base_path = dirname($_SERVER['SCRIPT_NAME']);
    if ($base_path !== '/') {
        $uri = preg_replace('#^' . preg_quote($base_path) . '#', '', $uri);
    }
    
    // Remove trailing slash
    $uri = rtrim($uri, '/');
    
    // Empty URI = homepage
    if ($uri === '' || $uri === '/') {
        return render('pages/home');
    }
    
    // ========================================
    // PUBLIC ROUTES
    // ========================================
    
    // Order Online (all products)
    if ($uri === '/order-online' && $method === 'GET') {
        $products_by_category = get_products_with_availability();
        $featured_products = get_featured_products_with_availability();
        
        // Build categories array - add Featured first if there are featured products
        $categories = [];
        if (!empty($featured_products)) {
            $categories[] = 'Featured';
        }
        $categories = array_merge($categories, array_keys($products_by_category));
        
        $shop_status = get_shop_status();
        $available_methods = get_available_methods();
        // Get auto-apply promos for display
        $all_promos = load_json_config('promotions.json')['codes'] ?? [];
        $auto_promos = array_filter($all_promos, function($p) {
            if (!$p['active'] || !$p['autoApply']) return false;
            $now = date('Y-m-d H:i:s');
            if ($now < $p['validFrom'] || $now > $p['validUntil']) return false;
            return true;
        });
        $auto_promos = array_values($auto_promos); // Re-index

        // Get addresses for logged-in users
        $addresses = [];
        if (is_logged_in()) {
            $addresses = get_customer_addresses($_SESSION['user_id']);
        }
        
        // Get active offers (if feature enabled)
        $active_offers = [];
        $carousel_products = [];
        $site_config = $GLOBALS['site_config'] ?? [];
        if (!empty($site_config['features']['offers'])) {
            $active_offers = get_active_offers();
            
            // Get products for free carousel (free_on_spend offers)
            $all_products = load_json_config('products.json');
            $carousel_products = get_free_carousel_products($all_products);
        }

        // Get delivery info for info bar
        $delivery_config = load_json_config('delivery.json');
        $delivery_info = [
            'baseFee' => $delivery_config['baseFee'] ?? null,
            'feePerMile' => $delivery_config['feePerMile'] ?? 0,
            'minOrder' => get_minimum_order('delivery'),
            'available' => false
        ];

        // Check if delivery is currently available
        foreach ($available_methods['methods'] ?? [] as $method) {
            if ($method['method'] === 'delivery') {
                $delivery_info['available'] = true;
                break;
            }
        }
        
        return render('pages/order-online', [
            'products_by_category' => $products_by_category,
            'featured_products' => $featured_products,
            'categories' => $categories,
            'shop_status' => $shop_status,
            'available_methods' => $available_methods,
            'auto_promos' => $auto_promos,
            'addresses' => $addresses,
            'active_offers' => $active_offers,
            'carousel_products' => $carousel_products,
            'delivery_info' => $delivery_info
        ]);
    }

    // Menu (Modern Layout)
if ($uri === '/menu' && $method === 'GET') {
    $products_by_category = get_products_with_availability();
    $featured_products = get_featured_products_with_availability();
    
    $categories = [];
    if (!empty($featured_products)) {
        $categories[] = 'Featured';
    }
    $categories = array_merge($categories, array_keys($products_by_category));
    
    $shop_status = get_shop_status();
    $available_methods = get_available_methods();
    
    $all_promos = load_json_config('promotions.json')['codes'] ?? [];
    $auto_promos = array_filter($all_promos, function($p) {
        if (!$p['active'] || !$p['autoApply']) return false;
        $now = date('Y-m-d H:i:s');
        if ($now < $p['validFrom'] || $now > $p['validUntil']) return false;
        return true;
    });
    $auto_promos = array_values($auto_promos);

    $addresses = [];
    if (is_logged_in()) {
        $addresses = get_customer_addresses($_SESSION['user_id']);
    }
    
    $active_offers = [];
    $carousel_products = [];
    $site_config = $GLOBALS['site_config'] ?? [];
    if (!empty($site_config['features']['offers'])) {
        $active_offers = get_active_offers();
        $all_products = load_json_config('products.json');
        $carousel_products = get_free_carousel_products($all_products);
    }

    $delivery_config = load_json_config('delivery.json');
    $delivery_info = [
        'baseFee' => $delivery_config['baseFee'] ?? null,
        'feePerMile' => $delivery_config['feePerMile'] ?? 0,
        'minOrder' => get_minimum_order('delivery'),
        'available' => false
    ];

    foreach ($available_methods['methods'] ?? [] as $method) {
        if ($method['method'] === 'delivery') {
            $delivery_info['available'] = true;
            break;
        }
    }

    // Load upsells config and products
    $upsell_products = [];
    $upsells_config = ['enabled' => false];

    if ($site_config['features']['upsells'] ?? false) {
        $upsells_config = load_json_config('upsells.json');
        $upsells_config['enabled'] = true;
        
        foreach ($upsells_config['products'] ?? [] as $product_id) {
            $product = get_product_by_id($product_id);
            if ($product && empty($product['options']) && empty($product['vari'])) {
                $upsell_products[] = $product;
            }
        }
    }
    
    return render('pages/menu', [
        'products_by_category' => $products_by_category,
        'featured_products' => $featured_products,
        'categories' => $categories,
        'shop_status' => $shop_status,
        'available_methods' => $available_methods,
        'auto_promos' => $auto_promos,
        'addresses' => $addresses,
        'active_offers' => $active_offers,
        'carousel_products' => $carousel_products,
        'delivery_info' => $delivery_info,
        'upsells' => $upsells_config,
        'upsell_products' => $upsell_products
    ]);
}
    
    // Cart (AJAX endpoints)
    if ($uri === '/cart/add' && $method === 'POST') {
        return cart_add($_POST);
    }
    
    if ($uri === '/cart/update' && $method === 'POST') {

        return cart_update($_POST);
    }
    
    if ($uri === '/cart/remove' && $method === 'POST') {
        return cart_remove($_POST);
    }
    
    if ($uri === '/cart/apply-promo' && $method === 'POST') {
        return apply_promo_code($_POST);
    }
    
    // Checkout
    if ($uri === '/checkout' && $method === 'GET') {
        $customer = null;
        $addresses = [];
        
        if (is_logged_in()) {
            $customer = get_customer_by_id($_SESSION['user_id']);
            $addresses = get_customer_addresses($_SESSION['user_id']);
        }
        
        // Get auto-apply promos (same logic as order-online)
        $all_promos = load_json_config('promotions.json')['codes'] ?? [];
        $auto_promos = array_filter($all_promos, function($p) {
            if (!$p['active'] || !$p['autoApply']) return false;
            $now = date('Y-m-d H:i:s');
            if ($now < $p['validFrom'] || $now > $p['validUntil']) return false;
            return true;
        });
        $auto_promos = array_values($auto_promos);
        
        // Load loyalty config and redemption data if enabled
        $loyalty_config = null;
        $loyalty_redemption = null;
        if (!empty($GLOBALS['site_config']['features']['loyalty'])) {
            $loyalty_config = load_json_config('loyalty.json');
            
            // Get redemption limits for logged-in users
            if (is_logged_in()) {
                require_once CORE_PATH . 'functions/loyalty.php';
                $loyalty_redemption = get_redemption_limits($_SESSION['user_id'], 100);
                $loyalty_redemption['bonus_multiplier'] = get_active_bonus_multiplier();
            }
        }

        // Get active offers (if feature enabled)
        $active_offers = [];
        $site_config = $GLOBALS['site_config'] ?? [];
        if (!empty($site_config['features']['offers'])) {
            $active_offers = get_active_offers();
        }

        // Get ready times for each method
        $ready_times = [
            'delivery' => get_ready_minutes('delivery'),
            'collection' => get_ready_minutes('collection')
        ];
        
        return render('pages/checkout', [
            'site' => $GLOBALS['site_config'] ?? [],
            'customer' => $customer,
            'addresses' => $addresses,
            'shop_status' => get_shop_status(),
            'available_methods' => get_available_methods(),
            'ready_times' => $ready_times,
            'auto_promos' => $auto_promos,
            'loyalty_config' => $loyalty_config,
            'loyalty_redemption' => $loyalty_redemption,
            'active_offers' => $active_offers
        ]);
    }

    if ($uri === '/checkout/apply-promo' && $method === 'POST') {
        $json = file_get_contents('php://input');
        $data = json_decode($json, true);
        return handle_apply_promo($data);
    }

    if ($uri === '/checkout/check-auto-promos' && $method === 'POST') {
        $json = file_get_contents('php://input');
        $data = json_decode($json, true);
        return handle_check_auto_promos($data);
    }
    
    if ($uri === '/checkout/validate-postcode' && $method === 'POST') {
        return validate_postcode_ajax($_POST);
    }

    if ($uri === '/checkout/check-availability' && $method === 'POST') {
        $json = file_get_contents('php://input');
        $data = json_decode($json, true);
        $selected_method = $data['method'] ?? null;
        
        $shop_status = get_shop_status();
        $available_methods = get_available_methods();
        
        if (!$shop_status['isOpen']) {
            return json_response([
                'available' => false,
                'message' => 'Sorry, we are currently closed. ' . $shop_status['message']
            ]);
        }
        
        if (empty($available_methods['methods'])) {
            return json_response([
                'available' => false,
                'message' => 'Sorry, ordering is not available at this time.'
            ]);
        }
        
        // Check if selected method is available
        if ($selected_method) {
            $method_available = false;
            foreach ($available_methods['methods'] as $m) {
                if ($m['method'] === $selected_method) {
                    $method_available = true;
                    break;
                }
            }
            if (!$method_available) {
                return json_response([
                    'available' => false,
                    'message' => ucfirst($selected_method) . ' is not available at this time.'
                ]);
            }
        }
        
        return json_response(['available' => true]);
    }

    if ($uri === '/checkout/validate-cart' && $method === 'POST') {
        $json = file_get_contents('php://input');
        $data = json_decode($json, true);
        
        $cart_items = $data['items'] ?? [];
        $delivery_method = $data['method'] ?? null;
        
        // Check availability
        $availability = validate_cart_availability($cart_items);
        
        // Calculate subtotal of valid items only
        $valid_subtotal = 0;
        $unavailable_ids = array_column($availability['unavailable'], 'product_id');
        
        foreach ($cart_items as $item) {
            if (!in_array($item['product_id'], $unavailable_ids)) {
                $valid_subtotal += ($item['total_price'] ?? 0) * ($item['quantity'] ?? 1);
            }
        }
        
        // Check minimum order if method provided
        $min_order = 0;
        $below_minimum = false;
        if ($delivery_method) {
            $min_order = get_minimum_order($delivery_method);
            $below_minimum = $min_order > 0 && $valid_subtotal < $min_order;
        }
        
        return json_response([
            'valid' => $availability['valid'] && !$below_minimum,
            'unavailable' => $availability['unavailable'],
            'messages' => $availability['messages'],
            'valid_subtotal' => $valid_subtotal,
            'min_order' => $min_order,
            'below_minimum' => $below_minimum,
            'minimum_shortfall' => $below_minimum ? ($min_order - $valid_subtotal) : 0
        ]);
    }

    if ($uri === '/api/address/add' && $method === 'POST') {
        if (!is_logged_in()) {
            return json_response(['success' => false, 'error' => 'Not authenticated'], 401);
        }
        
        $data = json_decode(file_get_contents('php://input'), true);
        
        // Validate postcode first
        $postcode_result = validate_postcode($data['postcode'] ?? '');
        if (!$postcode_result['valid']) {
            return json_response([
                'success' => false, 
                'error' => $postcode_result['message']
            ], 400);
        }
        
        // Add address
        $address_id = add_customer_address($_SESSION['user_id'], $data);
        
        return json_response([
            'success' => true,
            'address_id' => $address_id,
            'address' => [
                'address_id' => $address_id,
                'address_1' => $data['address_1'],
                'address_2' => $data['address_2'] ?? '',
                'postcode' => strtoupper($data['postcode'])
            ],
            'delivery' => $postcode_result
        ]);
    }
    
    if ($uri === '/checkout/process' && $method === 'POST') {
        return process_checkout($_POST);
    }

    // Get available time slots for scheduling
    if ($uri === '/checkout/get-timeslots' && $method === 'GET') {
        $method_param = $_GET['method'] ?? 'collection';
        
        if (!in_array($method_param, ['delivery', 'collection'])) {
            return json_response(['success' => false, 'error' => 'Invalid method'], 400);
        }
        
        $slots = get_available_timeslots($method_param);
        
        return json_response([
            'success' => true,
            'slots' => $slots
        ]);
    }

    // Payment with order ID
    if (preg_match('#^/payment/(\d+)$#', $uri, $matches) && $method === 'GET') {
        require_once CORE_PATH . 'functions/order.php';
        require_once CORE_PATH . 'functions/ryft_functions.php';
        
        $order_id = $matches[1];
        $token = $_GET['token'] ?? '';
        
        // Validate order access
        $order = get_order_with_token($order_id, $token);
        
        if (!$order) {
            http_response_code(403);
            return render('pages/error', ['message' => 'Invalid order or access token']);
        }
        
        // Check if payment already completed
        if ($order['payment_status'] === 'completed') {
            redirect('/thank-you?order=' . $order_id . '&token=' . $token);
        }
        
        // Create or retrieve Ryft payment session
        $payment_session = create_ryft_payment_session($order_id);
        
        if (!$payment_session['success']) {
            return render('pages/error', ['message' => $payment_session['message']]);
        }
        
        // Get order products for display (grouped for BOGOF/free items)
        $order_products_raw = get_order_products($order_id);
        $order_products = group_order_products_for_display($order_products_raw);
        
        // Get customer info for saved cards
        $customer = null;
        $saved_payment_methods = [];
        $saved_payment_methods_raw_json = null;
        $has_saved_card = false;
        
        if ($order['customer_id'] && $order['customer_type'] === 'R') {
            $customer = get_order_customer($order['customer_id'], $order['customer_type']);
            if ($customer && $customer['card_customer']) {
                $saved_payment_methods = get_customer_payment_methods($order['customer_id']);
                $has_saved_card = count($saved_payment_methods) > 0;
                
                // Convert to raw JSON string for Ryft
                if ($has_saved_card) {
                    $saved_payment_methods_raw_json = json_encode(['items' => $saved_payment_methods]);
                }
            }
        }
        
        // Get Ryft config
        $ryft_config = get_ryft_config();
        $shop_status = get_shop_status();
        $available_methods = get_available_methods();
        
        return render('pages/payment', [
            'order' => $order,
            'order_products' => $order_products,
            'client_secret' => $payment_session['client_secret'],
            'payment_intent_id' => $payment_session['payment_intent_id'],
            'ryft_config' => $ryft_config,
            'customer' => $customer,
            'saved_payment_methods' => $saved_payment_methods,
            'saved_payment_methods_raw_json' => $saved_payment_methods_raw_json,
            'has_saved_card' => $has_saved_card,
            'branch_name' => $site_config['site_name'] ?? 'Restaurant',
            'is_logged_in' => is_logged_in(),
            'shop_status' => $shop_status,
            'available_methods' => $available_methods,
        ]);
    }

    // Webhook endpoint for payment confirmation
    if ($uri === '/complete' && $method === 'POST') {
        require_once CORE_PATH . 'functions/order.php';
        require_once CORE_PATH . 'functions/ryft_functions.php';
        
        // This will be called by the unified webhook system
        $data = json_decode(file_get_contents('php://input'), true);
        
        $order_id = $data['order_id'] ?? $data['oid'] ?? null;
        $payment_intent_id = $data['payment_intent_id'] ?? null;
        
        if (!$order_id || !$payment_intent_id) {
            return json_response(['success' => false, 'error' => 'Missing data'], 400);
        }
        
        // Update order status and payment info
        $success = complete_ryft_payment($order_id, $payment_intent_id);
        
        // If customer opted to save card and we have the customer ID from Ryft
        if (isset($data['ryft_customer_id']) && $data['save_card']) {
            $db = get_db();
            $stmt = mysqli_prepare($db, "SELECT customer_id FROM orders WHERE order_id = ?");
            mysqli_stmt_bind_param($stmt, "i", $order_id);
            mysqli_stmt_execute($stmt);
            $result = mysqli_stmt_get_result($stmt);
            $order = mysqli_fetch_assoc($result);
            
            if ($order && $order['customer_id']) {
                save_customer_card($order['customer_id'], $data['ryft_customer_id']);
            }
        }
        
        return json_response(['success' => $success]);
    }

    // API endpoint to check payment status (for auto-refresh on thank you page)
    if (preg_match('#^/api/order-status/(\d+)$#', $uri, $matches) && $method === 'GET') {
        require_once CORE_PATH . 'functions/order.php';
        
        $order_id = $matches[1];
        
        $db = get_db();
        $stmt = mysqli_prepare($db, 
            "SELECT order_status, payment_status FROM orders WHERE order_id = ?"
        );
        mysqli_stmt_bind_param($stmt, "i", $order_id);
        mysqli_stmt_execute($stmt);
        $result = mysqli_stmt_get_result($stmt);
        $order = mysqli_fetch_assoc($result);
        
        if (!$order) {
            return json_response(['error' => 'Order not found'], 404);
        }
        
        return json_response([
            'order_status' => $order['order_status'],
            'payment_status' => $order['payment_status']
        ]);
    }

    // Thank you page with token validation
    if ($uri === '/thank-you' && $method === 'GET') {
        require_once CORE_PATH . 'functions/order.php';
        require_once CORE_PATH . 'functions/ryft_functions.php';
        
        $order_id = $_GET['order'] ?? null;
        $token = $_GET['token'] ?? '';

        $shop_status = get_shop_status();
        $available_methods = get_available_methods();
        
        // Validate order ID and token
        if (!$order_id || !$token) {
            return render('pages/thank-you', [
                'error' => 'Invalid order link',
                'branch_name' => $site_config['site_name'] ?? 'Restaurant',
                'is_logged_in' => is_logged_in()
            ]);
        }
        
        // Validate order access
        $order = get_order_with_token($order_id, $token);
        
        if (!$order) {
            return render('pages/thank-you', [
                'error' => 'Order not found',
                'branch_name' => $site_config['site_name'] ?? 'Restaurant',
                'is_logged_in' => is_logged_in()
            ]);
        }
        // CHECK PAYMENT STATUS AND UPDATE IF NEEDED
        if ($order['order_status'] === 'waiting' && strpos($order['payment_method'], 'pi_temp_') === 0) {
            // Extract intent ID from payment_method field
            $payment_intent_id = preg_replace('/^pi_temp_/i', '', $order['payment_method']);

            // Check status with Ryft
            $status_check = check_payment_status($payment_intent_id);
            
            if ($status_check['success'] && 
                ($status_check['status'] === 'Approved' || $status_check['status'] === 'Captured')) {
                // Payment successful - update database
                complete_ryft_payment($order_id, $payment_intent_id);
                
                // Save Ryft customer ID for logged-in registered users
                if (is_logged_in() && $order['customer_type'] === 'R' && $order['customer_id']) {
                    // Check if card was tokenized
                    $card_stored = $status_check['data']['paymentMethod']['tokenizedDetails']['stored'] ?? false;
                    if ($card_stored) {
                        $customer_email = $status_check['data']['customerEmail'] ?? null;
                        if ($customer_email) {
                            $ryft_customer = get_ryft_customer_by_email($customer_email);
                            if ($ryft_customer && !empty($ryft_customer['id'])) {
                                save_customer_card($order['customer_id'], $ryft_customer['id']);
                            }
                        }
                    }
                }
                
                // Refresh order data
                $order = get_order_with_token($order_id, $token);
            }
        }
        
        $order_products = group_order_products_for_display(get_order_products($order_id));

        $customer = get_order_customer($order['customer_id'], $order['customer_type']);
        $address = null;
        
        if ($order['delivery_collection'] === 'delivery') {
            $address = get_customer_address($order['customer_id'], $order['customer_type']);
        }
        
        // Check if guest order has a registered email (for link prompt)
        $show_link_prompt = false;
        if ($order['customer_type'] === 'G' && !is_logged_in()) {
            $db = get_db();
            $stmt = mysqli_prepare($db, "SELECT id FROM users WHERE email = ? LIMIT 1");
            mysqli_stmt_bind_param($stmt, "s", $order['order_email']);
            mysqli_stmt_execute($stmt);
            $result = mysqli_stmt_get_result($stmt);
            $show_link_prompt = mysqli_num_rows($result) > 0;
        }

        // Loyalty data for thank-you page
        $loyalty_data = null;
        $site_config = $GLOBALS['site_config'] ?? [];
        if (!empty($site_config['features']['loyalty'])) {
            require_once CORE_PATH . 'functions/loyalty.php';
            $loyalty_config = get_loyalty_config();
            $earn_rate = $loyalty_config['earnRate'] ?? 5;
            
            // Points earned on this order (from DB)
            $points_earned = $order['loyalty_points_earned'] ?? 0;
            
            // Potential points for guests (what they could have earned)
            $potential_points = floor(($order['order_total'] * $earn_rate) / 100);
            
            // Customer's current balance if logged in
            $customer_balance = 0;
            if (is_logged_in() && $order['customer_type'] === 'R' && $order['customer_id']) {
                $customer_balance = get_customer_points($order['customer_id']);
            }
            
            $loyalty_data = [
                'enabled' => true,
                'earn_rate' => $earn_rate,
                'points_earned' => $points_earned,
                'potential_points' => $potential_points,
                'customer_balance' => $customer_balance
            ];
        }
        
        return render('pages/thank-you', [
            'order' => $order,
            'order_products' => $order_products,
            'customer' => $customer,
            'address' => $address,
            'show_link_prompt' => $show_link_prompt,
            'shop_status' => $shop_status,
            'available_methods' => $available_methods,
            'is_logged_in' => is_logged_in(),
            'loyalty_data' => $loyalty_data
        ]);
    }
    
    // Link guest order to account (POST from thank-you page after login)
    if ($uri === '/account/link-order' && $method === 'POST') {
        if (!is_logged_in()) {
            return json_response(['success' => false, 'error' => 'Not logged in'], 401);
        }
        
        $json = file_get_contents('php://input');
        $data = json_decode($json, true);
        
        $order_id = (int)($data['order_id'] ?? 0);
        $token = $data['token'] ?? '';
        
        if (!$order_id || !$token) {
            return json_response(['success' => false, 'error' => 'Invalid request'], 400);
        }
        
        // Verify order access
        require_once CORE_PATH . 'functions/order.php';
        $order = get_order_with_token($order_id, $token);
        
        if (!$order) {
            return json_response(['success' => false, 'error' => 'Order not found'], 404);
        }
        
        // Verify order email matches logged-in user
        $user = get_mycurrent_user();
        if ($order['order_email'] !== $user['email']) {
            return json_response(['success' => false, 'error' => 'Email mismatch'], 403);
        }
        
        // Verify it's a guest order
        if ($order['customer_type'] !== 'G') {
            return json_response(['success' => false, 'error' => 'Order already linked'], 400);
        }
        
        // Link the order
        $success = link_guest_order_to_user($order_id, $user['id']);
        
        return json_response(['success' => $success]);
    }
    
    // ========================================
    // AUTH ROUTES
    // ========================================
    
    // Login
    if ($uri === '/account/login' && $method === 'GET') {
        // If already logged in, redirect to dashboard
        if (is_logged_in()) {
            redirect('/account');
        }
        return render('pages/login');
    }
    
    if ($uri === '/account/login' && $method === 'POST') {
        return handle_login($_POST);
    }
    
    // Register
    if ($uri === '/account/register' && $method === 'GET') {
        if (is_logged_in()) {
            redirect('/account');
        }
        return render('pages/register');
    }
    
    if ($uri === '/account/register' && $method === 'POST') {
        return handle_register($_POST);
    }
    
    // Logout
    if ($uri === '/account/logout') {
        return handle_logout();
    }
    
    // Forgot password
    if ($uri === '/account/forgot-password' && $method === 'GET') {
        return render('pages/forgot-password');
    }
    
    if ($uri === '/account/forgot-password' && $method === 'POST') {
        return handle_forgot_password($_POST);
    }
    
    // Reset password
    if ($uri === '/account/reset-password' && $method === 'GET') {
        $token = $_GET['token'] ?? '';
        $success = isset($_GET['success']);
        
        // Show success page
        if ($success) {
            return render('pages/reset-password', ['success' => true]);
        }
        
        // Validate token
        $validation = validate_reset_token($token);
        
        if (!$validation['valid']) {
            return render('pages/reset-password', ['error' => $validation['error']]);
        }
        
        return render('pages/reset-password', ['token' => $token]);
    }
    
    if ($uri === '/account/reset-password' && $method === 'POST') {
        return handle_reset_password($_POST);
    }
    
    // ========================================
    // CUSTOMER DASHBOARD ROUTES (AUTH REQUIRED)
    // ========================================

    // Dashboard home
    if ($uri === '/account' && $method === 'GET') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        
        $user_id = $_SESSION['user_id'];
        $profile = get_customer_profile($user_id);
        $recent_orders = get_recent_orders($user_id, 5);
        $next_tier = get_next_tier_info($profile['loyalty_tier'] ?? 'bronze', $profile['total_spent'] ?? 0);
        
        return render('dashboard/index', [
            'profile' => $profile,
            'recent_orders' => $recent_orders,
            'next_tier' => $next_tier,
            'active_page' => 'index'
        ]);
    }

    // Order history
    if ($uri === '/account/orders' && $method === 'GET') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        
        $user_id = $_SESSION['user_id'];
        $profile = get_customer_profile($user_id);
        
        $page = max(1, (int)($_GET['page'] ?? 1));
        $per_page = 10;
        $offset = ($page - 1) * $per_page;
        
        $result = get_customer_orders($user_id, $per_page, $offset);
        $total_pages = ceil($result['total'] / $per_page);
        
        return render('dashboard/orders', [
            'profile' => $profile,
            'orders' => $result['orders'],
            'current_page' => $page,
            'total_pages' => $total_pages,
            'total_orders' => $result['total'],
            'active_page' => 'orders'
        ]);
    }

    // Single order details
    if (preg_match('#^/account/order/(\d+)$#', $uri, $matches)) {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        
        $order_id = $matches[1];
        $user_id = $_SESSION['user_id'];
        $profile = get_customer_profile($user_id);
        
        $order = get_customer_order_details($order_id, $user_id);
        
        if (!$order) {
            http_response_code(404);
            return render('pages/error', ['message' => 'Order not found']);
        }
        
        return render('dashboard/order-details', [
            'profile' => $profile,
            'order' => $order,
            'active_page' => 'orders'
        ]);
    }

    // Loyalty page
    if ($uri === '/account/loyalty' && $method === 'GET') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        require_once CORE_PATH . 'functions/loyalty.php';
        
        $user_id = $_SESSION['user_id'];
        $profile = get_customer_profile($user_id);
        $loyalty_status = get_customer_loyalty_status($user_id);
        $transactions = get_loyalty_transactions($user_id, 20);
        $tiers = get_loyalty_config()['tiers'];
        // Check for tier upgrade (self-corrects if total_spent was updated externally)
        check_tier_upgrade($user_id);
        return render('dashboard/loyalty', [
            'profile' => $profile,
            'loyalty_status' => $loyalty_status,
            'transactions' => $transactions,
            'tiers' => $tiers,
            'active_page' => 'loyalty'
        ]);
    }

    // Favorites
    if ($uri === '/account/favorites' && $method === 'GET') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        
        $user_id = $_SESSION['user_id'];
        $profile = get_customer_profile($user_id);
        
        return render('dashboard/favorites', [
            'profile' => $profile,
            'active_page' => 'favorites'
        ]);
    }

    // Profile page
    if ($uri === '/account/profile' && $method === 'GET') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        require_once CORE_PATH . 'functions/ryft_functions.php';
        
        $user_id = $_SESSION['user_id'];
        $profile = get_customer_profile($user_id);
        $addresses = get_customer_addresses($user_id);
        
        // Get saved payment methods if customer has card_customer
        $payment_methods = [];
        if (!empty($profile['card_customer'])) {
            $payment_methods = get_customer_payment_methods($user_id);
        }
        
        return render('dashboard/profile', [
            'profile' => $profile,
            'addresses' => $addresses,
            'payment_methods' => $payment_methods,
            'active_page' => 'profile'
        ]);
    }

    // Profile update
    if ($uri === '/account/profile/update' && $method === 'POST') {
        require_auth();
        return handle_profile_update($_POST);
    }

    // Password update (NEW)
    if ($uri === '/account/profile/password' && $method === 'POST') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        
        $user_id = $_SESSION['user_id'];
        $result = update_customer_password(
            $user_id,
            $_POST['current_password'] ?? '',
            $_POST['new_password'] ?? ''
        );
        
        return json_response($result);
    }

    // Address management (NEW routes)
    if ($uri === '/account/address/add' && $method === 'POST') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        
        $data = json_decode(file_get_contents('php://input'), true);
        
        if (!verify_csrf_token($data['csrf_token'] ?? '')) {
            return json_response(['success' => false, 'error' => 'Invalid request'], 400);
        }
        
        $address_id = add_customer_address($_SESSION['user_id'], $data);
        
        if ($address_id) {
            return json_response(['success' => true, 'address_id' => $address_id]);
        } else {
            return json_response(['success' => false, 'error' => 'Failed to add address'], 500);
        }
    }

    if ($uri === '/account/address/update' && $method === 'POST') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        
        $data = json_decode(file_get_contents('php://input'), true);
        
        if (!verify_csrf_token($data['csrf_token'] ?? '')) {
            return json_response(['success' => false, 'error' => 'Invalid request'], 400);
        }
        
        $success = update_customer_address(
            (int)$data['address_id'],
            $_SESSION['user_id'],
            $data
        );
        
        return json_response(['success' => $success]);
    }

    if ($uri === '/account/address/delete' && $method === 'POST') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';
        
        $data = json_decode(file_get_contents('php://input'), true);
        
        if (!verify_csrf_token($data['csrf_token'] ?? '')) {
            return json_response(['success' => false, 'error' => 'Invalid request'], 400);
        }
        
        $success = delete_customer_address(
            (int)$data['address_id'],
            $_SESSION['user_id']
        );
        
        return json_response(['success' => $success]);
    }

    // Delete payment method
    if ($uri === '/account/payment-method/delete' && $method === 'POST') {
        require_auth();
        require_once CORE_PATH . 'functions/ryft_functions.php';
        
        $data = json_decode(file_get_contents('php://input'), true);
        
        if (!verify_csrf_token($data['csrf_token'] ?? '')) {
            return json_response(['success' => false, 'error' => 'Invalid request'], 400);
        }
        
        $payment_method_id = $data['payment_method_id'] ?? '';
        if (empty($payment_method_id)) {
            return json_response(['success' => false, 'error' => 'Missing payment method ID'], 400);
        }
        
        $success = delete_customer_payment_method($_SESSION['user_id'], $payment_method_id);
        
        return json_response(['success' => $success]);
    }
    
    // ========================================
    // RESERVATIONS (if enabled)
    // ========================================
    
    if ($uri === '/reservations' && $method === 'GET') {
        $site_config = $GLOBALS['site_config'] ?? [];
        if (!empty($site_config['features']['reservations'])) {
            return render('pages/reservations');
        }
    }
    
    if ($uri === '/reservations/check' && $method === 'POST') {
        return check_reservation_availability($_POST);
    }
    
    if ($uri === '/reservations/create' && $method === 'POST') {
        return create_reservation($_POST);
    }
    
    if ($uri === '/account/reservations' && $method === 'GET') {
        require_auth();
        return render('dashboard/reservations');
    }
    
    if ($uri === '/account/reservations/cancel' && $method === 'POST') {
        require_auth();
        return cancel_reservation($_POST);
    }
    
    // ========================================
    // 404 NOT FOUND
    // ========================================
    
    http_response_code(404);
    return render('pages/404');
}

/**
 * Render a Latte template
 * 
 * @param string $template - Template path (e.g., 'pages/home')
 * @param array $data - Data to pass to template
 */
function render($template, $data = []) {
    // Initialize Latte
    $latte = new Latte\Engine;
    $latte->setTempDirectory(ROOT_PATH . 'temp/cache');

    $latte->addFilter('json', function ($value) {
        return json_encode($value, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    });

    $latte->addFilter('nlTobr', function ($value) {
        return nl2br($value);
    });

    $latte->addFilter('escapeJs', function ($value) {
        return addslashes($value);
    });
    
    // Create temp directory if it doesn't exist
    if (!is_dir(ROOT_PATH . 'temp/cache')) {
        mkdir(ROOT_PATH . 'temp/cache', 0755, true);
    }
    
    // Add global data
    $data['site'] = $GLOBALS['site_config'] ?? [];
    $data['theme'] = $GLOBALS['theme_config'] ?? [];
    $data['current_user'] = get_mycurrent_user();
    $data['is_logged_in'] = is_logged_in();
    $data['cart'] = get_cart();
    $data['cart_count'] = get_cart_count();
    $data['cart_total'] = get_cart_total();
    $data['csrf_token'] = generate_csrf_token();
    $data['base_path'] = BASE_PATH;
    
    // Template path
    $template_file = CORE_PATH . 'templates/' . $template . '.latte';
    
    if (!file_exists($template_file)) {
        http_response_code(500);
        die("Template not found: $template");
    }
    
    // Render template
    $latte->render($template_file, $data);
    exit;
}

/**
 * Require authentication - redirect to login if not authenticated
 */
function require_auth() {
    if (!is_logged_in()) {
        $_SESSION['redirect_after_login'] = $_SERVER['REQUEST_URI'];
        redirect('/account/login');
    }
}