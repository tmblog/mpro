<?php
/**
 * Router Functions
 * 
 * Handles all URL routing for the application
 */

/**
 * Main routing function
 * 
 * @param string $uri - Request URI (already processed by index.php - base_path removed, store detected)
 * @param string $method - HTTP method (GET, POST, etc.)
 */
function route($uri, $method = 'GET') {
    // Remove trailing slash and ensure leading slash
    $uri = '/' . trim($uri, '/');
    if ($uri !== '/') {
        $uri = rtrim($uri, '/');
    }
    
    // Empty URI = homepage
    if ($uri === '' || $uri === '/') {
        $homepage_config = load_json_config('homepage.json');
        $featured_products = get_featured_products_with_availability();
        return render('pages/home', [
            'homepage' => $homepage_config,
            'page_title' => $homepage_config['title'] ?? null,
            'meta_description' => $homepage_config['meta_description'] ?? null,
            'featured_products' => $featured_products,
            'order_link' => is_multi_store() ? '/stores' : '/order-online'
        ]);
    }

    // Reservations page
    if ($uri === '/reservations' && $method === 'GET') {
        $site_config = $GLOBALS['site_config'] ?? [];

        // Check if reservations feature is enabled
        if (empty($site_config['features']['reservations'])) {
            http_response_code(404);
            return render('pages/404');
        }

        $reservation_config = load_json_config('reservations.json');

        // Get customer data if logged in
        $customer = null;
        if (is_logged_in()) {
            $customer = get_customer_by_id($_SESSION['user_id']);
        }

        return render('pages/reservations', [
            'reservation_config' => $reservation_config,
            'customer' => $customer
        ]);
    }

    // Reservation payment page
    if (preg_match('#^/reservations/payment/(\d+)$#', $uri, $matches) && $method === 'GET') {
        $site_config = $GLOBALS['site_config'] ?? [];

        if (empty($site_config['features']['reservations'])) {
            http_response_code(404);
            return render('pages/404');
        }

        require_once CORE_PATH . 'functions/reservations.php';
        $reservation_id = $matches[1];
        $reservation = get_reservation($reservation_id);

        if (!$reservation) {
            http_response_code(404);
            return render('pages/404');
        }

        // Check if deposit is required and not paid
        if (!$reservation['deposit_required'] || $reservation['deposit_paid']) {
            // Redirect to confirmation if no payment needed
            header('Location: ' . store_url('/reservations/confirmation/' . $reservation_id . '/' . $reservation['token']));
            exit;
        }

        $config = load_json_config('reservations.json');

        // Get Ryft config
        require_once CORE_PATH . 'functions/ryft_functions.php';
        $ryft_config = get_ryft_config();

        // Get customer info for saved cards
        $customer = null;
        $saved_payment_methods_raw_json = null;

        if ($reservation['customer_id'] && $reservation['customer_type'] === 'R') {
            $customer = get_order_customer($reservation['customer_id'], $reservation['customer_type']);
            if ($customer && $customer['card_customer']) {
                $saved_payment_methods = get_customer_payment_methods($reservation['customer_id']);
                if (count($saved_payment_methods) > 0) {
                    $saved_payment_methods_raw_json = json_encode(['items' => $saved_payment_methods]);
                }
            }
        }

        return render('pages/reservation-payment', [
            'reservation' => $reservation,
            'config' => $config,
            'ryft_config' => $ryft_config,
            'saved_payment_methods_raw_json' => $saved_payment_methods_raw_json,
            'customer' => $customer
        ]);
    }

    // Reservation confirmation page
    if (preg_match('#^/reservations/confirmation/(\d+)/([a-f0-9]{32})$#', $uri, $matches) && $method === 'GET') {
        $site_config = $GLOBALS['site_config'] ?? [];

        if (empty($site_config['features']['reservations'])) {
            http_response_code(404);
            return render('pages/404');
        }

        require_once CORE_PATH . 'functions/reservations.php';
        $reservation_id = $matches[1];
        $token = $matches[2];
        $reservation = get_reservation_by_token($reservation_id, $token);

        if (!$reservation) {
            http_response_code(404);
            return render('pages/404');
        }

        $config = load_json_config('reservations.json');

        return render('pages/reservation-confirmation', [
            'reservation' => $reservation,
            'config' => $config
        ]);
    }

    // ========================================
    // PUBLIC ROUTES
    // ========================================
    
    // Order Online (all products)
    if ($uri === '/menu' && $method === 'GET') {
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
if ($uri === '/order-online' && $method === 'GET') {
    // In multi-store mode, must access via store slug
    if (is_multi_store() && !get_current_store()) {
        return redirect(BASE_PATH . '/');
    }
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

    // Load allergens config
    $allergens_config = load_json_config('allergens.json') ?: [];
    
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
        'upsell_products' => $upsell_products,
        'allergens_config' => $allergens_config
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
                $store = get_current_store();
                $store_id = $store ? $store['slug'] : null;
                $loyalty_redemption = get_redemption_limits($_SESSION['user_id'], 100, $store_id);
                $loyalty_redemption['bonus_multiplier'] = get_active_bonus_multiplier();
                $loyalty_redemption['tier_multiplier'] = get_tier_config(get_customer_tier($_SESSION['user_id']))['multiplier'] ?? 1;
                $loyalty_redemption['tier_name'] = get_tier_config(get_customer_tier($_SESSION['user_id']))['name'] ?? 'Bronze';
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

    // Stores listing (multi-store mode)
    if ($uri === '/stores' && $method === 'GET') {
        if (!is_multi_store()) {
            header('Location: ' . BASE_PATH . '/order-online');
            exit;
        }
        
        $stores_config = load_stores_config();
        $homepage_config = load_json_config('homepage.json');
        $active_stores = array_filter($stores_config['stores'], fn($s) => $s['active'] ?? false);
        
        // Load site.json and hours.json for each store
        $stores_with_details = [];
        foreach ($active_stores as $store) {
            $site = load_store_config($store['slug'], 'site.json');
            $hours = load_store_config($store['slug'], 'hours.json');
            
            // Get today's hours
            $today_date = date('Y-m-d');
            $day_abbrev = date('D'); // Mon, Tue, Wed, etc.
            $today_hours = null;

            // Check holidays first
            foreach ($hours['holidays'] ?? [] as $holiday) {
                if ($holiday['date'] === $today_date) {
                    $today_hours = ['closed' => true, 'message' => $holiday['message'] ?? 'Closed'];
                    break;
                }
            }

            // Check special hours
            if (!$today_hours) {
                foreach ($hours['special_hours'] ?? [] as $special) {
                    if ($special['date'] === $today_date) {
                        $today_hours = $special;
                        break;
                    }
                }
            }

            // Fall back to regular hours
            if (!$today_hours) {
                foreach ($hours['days'] ?? [] as $day) {
                    if ($day['day'] === $day_abbrev) {
                        $today_hours = $day;
                        break;
                    }
                }
            }
            
            $stores_with_details[] = [
                'slug' => $store['slug'],
                'name' => $store['name'],
                'address' => $site['address'] ?? null,
                'phone' => $site['contact']['phone'] ?? null,
                'today_hours' => $today_hours
            ];
        }
        
        return render('pages/stores', [
            'stores' => $stores_with_details,
            'page_title' => $homepage_config['title'] ?? 'Restaurant',
            'meta_description' => 'Find your nearest ' . ($homepage_config['title'] ?? 'restaurant') . ' location'
        ]);
    }

    // Store info page
    if ($uri === '/info' && $method === 'GET') {
        $store = get_current_store();
        if (!$store && is_multi_store()) {
            http_response_code(404);
            return render('pages/error', ['message' => 'Store not found']);
        }
        
        $hours = load_json_config('hours.json');
        $delivery = load_json_config('delivery.json');
        $site = load_json_config('site.json');
        
        // Get auto promos (not requiring a code, valid, hide code)
        $all_promos = load_json_config('promotions.json')['codes'] ?? [];
        $now = date('Y-m-d H:i:s');
        $auto_promos = array_filter($all_promos, function($p) use ($now) {
            if (!$p['active'] || !$p['autoApply']) return false;
            if ($now < $p['validFrom'] || $now > $p['validUntil']) return false;
            return true;
        });
        $auto_promos = array_values($auto_promos);
        
        // Loyalty config (if enabled)
        $loyalty_config = null;
        if (!empty($site['features']['loyalty'])) {
            $loyalty_config = load_json_config('loyalty.json');
        }
        
        // Active offers
        $active_offers = [];
        if (!empty($site['features']['offers'])) {
            $active_offers = get_active_offers();
        }
        
        // Today for highlighting
        $today_abbrev = date('D');
        
        return render('pages/store-info', [
            'store' => $store,
            'site' => $site,
            'hours' => $hours,
            'delivery' => $delivery,
            'auto_promos' => $auto_promos,
            'loyalty_config' => $loyalty_config,
            'active_offers' => $active_offers,
            'today' => $today_abbrev
        ]);
    }

    // =========================================================================
    // UBER DIRECT ROUTES
    // =========================================================================

    // Get Uber quote for delivery
    if ($uri === '/uber/quote' && $method === 'POST') {
        require_once CORE_PATH . 'functions/uber.php';

        if (!is_uber_enabled()) {
            return json_response(['error' => true, 'message' => 'Uber Direct is not enabled'], 400);
        }

        $json = file_get_contents('php://input');
        $data = json_decode($json, true) ?? [];

        $address = null;
        $postcode = null;
        $lat = $data['lat'] ?? null;
        $lng = $data['lng'] ?? null;

        // Option 1: address_id provided - look up stored address
        if (!empty($data['address_id'])) {
            $stored = db_fetch_assoc(
                "SELECT address_1, address_2, postcode, latitude, longitude
                 FROM address WHERE address_id = " . (int)$data['address_id']
            );

            if (!$stored) {
                return json_response(['error' => true, 'message' => 'Address not found'], 400);
            }

            $address = trim($stored['address_1'] . ' ' . ($stored['address_2'] ?? ''));
            $postcode = $stored['postcode'];

            // Use stored coordinates if available
            if (!empty($stored['latitude']) && !empty($stored['longitude'])) {
                $lat = (float) $stored['latitude'];
                $lng = (float) $stored['longitude'];
            }
        }
        // Option 2: address and postcode provided directly
        else {
            if (empty($data['address']) || empty($data['postcode'])) {
                return json_response(['error' => true, 'message' => 'Address and postcode are required'], 400);
            }
            $address = $data['address'];
            $postcode = $data['postcode'];
        }

        // Geocode if we don't have coordinates
        if (empty($lat) || empty($lng)) {
            $coords = geocode_address($address, $postcode, $data['city'] ?? 'London');
            if ($coords) {
                $lat = $coords['lat'];
                $lng = $coords['lng'];

                // Save coordinates to address record if address_id was provided
                if (!empty($data['address_id'])) {
                    db_update('address', [
                        'latitude' => $lat,
                        'longitude' => $lng
                    ], ['address_id' => (int)$data['address_id']]);
                }
            }
        }

        // Create quote
        $dropoff = [
            'address' => $address,
            'postcode' => $postcode,
            'phone' => $data['phone'] ?? '',
            'lat' => $lat,
            'lng' => $lng
        ];

        $quote = create_uber_quote($dropoff);

        if (isset($quote['error'])) {
            return json_response([
                'error' => true,
                'message' => $quote['message'],
                'code' => $quote['code'] ?? 'quote_failed'
            ], 400);
        }

        return json_response([
            'success' => true,
            'quote_id' => $quote['id'],
            'expires' => $quote['expires'],
            'fee' => $quote['fee'],
            'currency' => $quote['currency_type'] ?? 'GBP',
            'duration' => $quote['duration'] ?? null,
            'dropoff_eta' => $quote['dropoff_eta'] ?? null,
            'lat' => $lat,
            'lng' => $lng,
            'address' => $address,
            'postcode' => $postcode
        ]);
    }

    // Validate/refresh Uber quote
    if ($uri === '/uber/validate-quote' && $method === 'POST') {
        require_once CORE_PATH . 'functions/uber.php';

        if (!is_uber_enabled()) {
            return json_response(['error' => true, 'message' => 'Uber Direct is not enabled'], 400);
        }

        $json = file_get_contents('php://input');
        $data = json_decode($json, true);

        if (empty($data['quote_id']) || empty($data['expires'])) {
            return json_response(['error' => true, 'message' => 'Quote ID and expiry required'], 400);
        }

        $dropoff = [
            'address' => $data['address'] ?? '',
            'postcode' => $data['postcode'] ?? '',
            'phone' => $data['phone'] ?? '',
            'lat' => $data['lat'] ?? null,
            'lng' => $data['lng'] ?? null
        ];

        $result = validate_or_refresh_quote(
            $data['quote_id'],
            $data['expires'],
            $dropoff
        );

        if (!$result['valid']) {
            return json_response([
                'error' => true,
                'message' => $result['error'] ?? 'Quote validation failed'
            ], 400);
        }

        // If quote was refreshed and order_id provided, update the order's quote_id
        if ($result['refreshed'] && !empty($data['order_id'])) {
            db_update('orders', [
                'uber_quote_id' => $result['quote_id']
            ], ['order_id' => (int)$data['order_id']]);
        }

        return json_response([
            'success' => true,
            'valid' => true,
            'refreshed' => $result['refreshed'],
            'quote_id' => $result['quote_id'],
            'expires' => $result['expires'],
            'fee' => $result['fee'] ?? null
        ]);
    }

    // Uber webhook update (forwarded from central server)
    if ($uri === '/uber/update' && $method === 'POST') {
        require_once CORE_PATH . 'functions/uber.php';

        $json = file_get_contents('php://input');
        $data = json_decode($json, true);

        if (empty($data['delivery_id'])) {
            return json_response(['success' => false, 'error' => 'Missing delivery_id'], 400);
        }

        $result = update_order_from_uber_webhook($data);

        return json_response($result, $result['success'] ? 200 : 400);
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
            // Table is always available if shop is open
            if ($selected_method === 'table') {
                return json_response(['available' => true]);
            }
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

    // Reservation API: Get available time slots
    if ($uri === '/api/reservations/timeslots' && $method === 'POST') {
        require_once CORE_PATH . 'functions/reservations.php';

        $data = json_decode(file_get_contents('php://input'), true);
        $date = $data['date'] ?? null;

        if (!$date) {
            return json_response(['success' => false, 'error' => 'Date required'], 400);
        }

        $slots = get_reservation_timeslots($date);

        return json_response([
            'success' => true,
            'slots' => $slots
        ]);
    }

    // Reservation API: Create reservation
    if ($uri === '/api/reservations/create' && $method === 'POST') {
        require_once CORE_PATH . 'functions/reservations.php';

        $data = json_decode(file_get_contents('php://input'), true);
        $result = create_reservation($data);

        return json_response($result);
    }

    // Reservation API: Create payment intent for deposit
    if ($uri === '/api/reservations/payment-intent' && $method === 'POST') {
        require_once CORE_PATH . 'functions/reservations.php';

        $data = json_decode(file_get_contents('php://input'), true);
        $reservation_id = $data['reservation_id'] ?? null;

        if (!$reservation_id) {
            return json_response(['success' => false, 'message' => 'Missing reservation ID'], 400);
        }

        $result = create_reservation_payment_intent($reservation_id);
        return json_response($result);
    }

    // Reservation API: Confirm payment after successful deposit
    if ($uri === '/api/reservations/confirm-payment' && $method === 'POST') {
        require_once CORE_PATH . 'functions/reservations.php';

        $data = json_decode(file_get_contents('php://input'), true);
        $reservation_id = $data['reservation_id'] ?? null;
        $payment_intent_id = $data['payment_intent_id'] ?? null;

        if (!$reservation_id || !$payment_intent_id) {
            return json_response(['success' => false, 'message' => 'Missing required data'], 400);
        }

        $success = mark_deposit_paid($reservation_id, $payment_intent_id);

        if ($success) {
            $reservation = get_reservation($reservation_id);
            return json_response(['success' => true, 'message' => 'Reservation confirmed', 'token' => $reservation['token']]);
        } else {
            return json_response(['success' => false, 'message' => 'Failed to confirm reservation'], 500);
        }
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
        $table_mode = !empty($order['table_number']);
        $table_number = $order['table_number'];

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
            'table_mode' => $table_mode,
            'table_number' => $table_number,
            'available_methods' => $table_mode ? ['methods' => ['table'], 'preOrderOnly' => false, 'message' => ''] : get_available_methods()
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
            $potential_points = floor(($order['order_subtotal'] * $earn_rate));
            
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

        $table_mode = !empty($order['table_number']);
        $table_number = $order['table_number'];
        
        return render('pages/thank-you', [
            'order' => $order,
            'order_products' => $order_products,
            'customer' => $customer,
            'address' => $address,
            'show_link_prompt' => $show_link_prompt,
            'shop_status' => $shop_status,
            'available_methods' => $available_methods,
            'is_logged_in' => is_logged_in(),
            'loyalty_data' => $loyalty_data,
            'table_mode' => $table_mode,
            'table_number' => $table_number,
            'available_methods' => $table_mode 
                ? ['methods' => ['table'], 'preOrderOnly' => false, 'message' => ''] 
                : get_available_methods()
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
        
        // Set default store context for dashboard in multi-store mode
        if (is_multi_store() && !get_current_store()) {
            $stores_config = load_stores_config();
            $default_slug = $stores_config['default_store'] ?? null;
            if ($default_slug) {
                $GLOBALS['current_store'] = get_store_by_slug($default_slug);
                $GLOBALS['site_config'] = load_json_config('site.json');
            }
        }
        
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
        $orphaned_warning = get_orphaned_points_warning($user_id);
        $transactions = get_loyalty_transactions($user_id, 20);
        $tiers = get_loyalty_config()['tiers'];
        $loyalty_config = get_loyalty_config();
        $points_by_store = get_customer_points_by_store($user_id);
        
        // Check for tier upgrade
        check_tier_upgrade($user_id);
        
        return render('dashboard/loyalty', [
            'profile' => $profile,
            'loyalty_status' => $loyalty_status,
            'transactions' => $transactions,
            'tiers' => $tiers,
            'loyalty_config' => $loyalty_config,
            'points_by_store' => $points_by_store,
            'redemption_scope' => is_multi_store() ? ($loyalty_config['redemptionScope'] ?? 'global') : 'global',
            'orphaned_warning' => $orphaned_warning,
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

    // Reservations
    if ($uri === '/account/reservations' && $method === 'GET') {
        require_auth();
        require_once CORE_PATH . 'functions/dashboard.php';

        $user_id = $_SESSION['user_id'];
        $profile = get_customer_profile($user_id);
        $reservations = get_customer_reservations($user_id);

        return render('dashboard/reservations', [
            'profile' => $profile,
            'upcoming' => $reservations['upcoming'],
            'past' => $reservations['past'],
            'active_page' => 'reservations'
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

    // Reorder API - validate and build cart from previous order
    if ($uri === '/api/reorder' && $method === 'POST') {
        if (!is_logged_in()) {
            return json_response(['success' => false, 'error' => 'Not logged in'], 401);
        }
        
        $data = json_decode(file_get_contents('php://input'), true);
        $order_id = (int)($data['order_id'] ?? 0);
        
        if (!$order_id) {
            return json_response(['success' => false, 'error' => 'Invalid order ID'], 400);
        }
        
        // Get order first to check store_id
        $db = get_db();
        $stmt = mysqli_prepare($db, 
            "SELECT store_id FROM orders 
            WHERE order_id = ? AND customer_id = ? AND customer_type = 'R'"
        );
        mysqli_stmt_bind_param($stmt, "ii", $order_id, $_SESSION['user_id']);
        mysqli_stmt_execute($stmt);
        $result = mysqli_stmt_get_result($stmt);
        $order = mysqli_fetch_assoc($result);
        
        if (!$order) {
            return json_response(['success' => false, 'error' => 'Order not found'], 404);
        }
        
        // Set store context for product loading
        $order_store_id = $order['store_id'];
        if ($order_store_id && is_multi_store()) {
            $store = get_store_by_slug($order_store_id);
            if ($store) {
                $GLOBALS['current_store'] = $store;
            }
        }
        
        // Get order products
        $stmt = mysqli_prepare($db, 
            "SELECT * FROM order_products WHERE order_id = ?"
        );
        mysqli_stmt_bind_param($stmt, "i", $order_id);
        mysqli_stmt_execute($stmt);
        $result = mysqli_stmt_get_result($stmt);
        
        $products = [];
        while ($row = mysqli_fetch_assoc($result)) {
            $products[] = $row;
        }
        
        if (empty($products)) {
            return json_response(['success' => false, 'error' => 'No products in order'], 404);
        }
        
        // Validate and build cart
        $cart = [];
        $warnings = [];
        $all_products = get_all_products();
        $all_options = get_product_options();
        
        foreach ($products as $item) {
            // Skip free items (BOGOF pairs, free-on-spend)
            if (($item['is_free'] ?? false) || ($item['is_bogof_free'] ?? false)) {
                continue;
            }
            
            $product_id = (int)$item['product_id'];
            $product = get_product_by_id($product_id);
            
            // Check product exists
            if (!$product) {
                $warnings[] = "'" . explode('<br>', $item['product_name'])[0] . "' is no longer available";
                continue;
            }
            
            // Check stock
            if (isset($product['stock']) && $product['stock'] === 0) {
                $warnings[] = "'{$product['name']}' is currently out of stock";
                continue;
            }
            
            // Parse original options
            $original_options = [];
            if (!empty($item['options_data'])) {
                $original_options = json_decode($item['options_data'], true) ?? [];
            }

            // Validate options still exist and get current prices
            $validated_options = [];
            $options_total = 0;

            foreach ($original_options as $opt) {
                $group_id = $opt['group_id'] ?? null;
                $choice_name = $opt['option_name'] ?? null;
                
                if (!$group_id || !$choice_name) continue;
                
                // Find option group by group_id
                $option_group = null;
                foreach ($all_options as $group) {
                    if (($group['id'] ?? null) == $group_id) {
                        $option_group = $group;
                        break;
                    }
                }
                
                if (!$option_group) {
                    $warnings[] = "Option group no longer available for '{$product['name']}'";
                    continue;
                }
                
                // Find choice by name
                $choice_found = false;
                foreach ($option_group['options'] ?? [] as $choice) {
                    if ($choice['name'] === $choice_name) {
                        $choice_found = true;
                        $current_price = (float)($choice['price'] ?? 0);
                        $validated_options[] = [
                            'group_id' => $group_id,
                            'option_id' => $opt['option_id'] ?? null,
                            'option_name' => $choice_name,
                            'option_price' => $current_price,
                            'quantity' => $opt['quantity'] ?? 1,
                            'parent_option_id' => $opt['parent_option_id'] ?? null,
                            'parent_group_id' => $opt['parent_group_id'] ?? null
                        ];
                        $options_total += $current_price;
                        break;
                    }
                }
                
                if (!$choice_found) {
                    $warnings[] = "'{$choice_name}' option no longer available for '{$product['name']}'";
                }
            }
            
            // Build cart item with current prices
            $base_price = (float)$product['price'];
            $total_price = $base_price + $options_total;
            
            $cart[] = [
                'product_id' => $product_id,
                'product_name' => $product['name'],
                'base_price' => $base_price,
                'options' => $validated_options,
                'quantity' => (int)$item['product_quantity'],
                'total_price' => $total_price,
                'cpn' => $product['cpn'] ?? 1,
                'added_at' => time() * 1000
            ];
        }
        
        if (empty($cart)) {
            return json_response([
                'success' => false, 
                'error' => 'No items could be added to cart',
                'warnings' => $warnings
            ], 400);
        }
        
        return json_response([
            'success' => true,
            'cart' => $cart,
            'warnings' => $warnings,
            'store_id' => $order_store_id
        ]);
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
    // TABLE ORDERING ROUTES
    // ========================================
    
    // Table landing - /table or /table?token=xxx
    if ($uri === '/table' && $method === 'GET') {
        $site_config = $GLOBALS['site_config'] ?? [];
        
        if (empty($site_config['features']['table_ordering'])) {
            http_response_code(404);
            return render('pages/404');
        }
        
        require_once CORE_PATH . 'functions/table.php';
        
        $token = $_GET['token'] ?? null;
        $token_validation = validate_table_token($token);
        
        if (!$token_validation['valid'] && !empty(get_table_config()['require_token'])) {
            return render('pages/table-error', [
                'error' => $token_validation['error']
            ]);
        }
        
        return render('pages/table-landing', [
            'tables' => get_table_numbers(),
            'token' => $token,
            'token_valid' => $token_validation['valid'],
            'table_mode' => true,
            'table_number' => null
        ]);
    }
    
    // Table with number - /table/5 or /table/5?token=xxx
    if (preg_match('#^/table/(\d+)$#', $uri, $matches) && $method === 'GET') {
        $site_config = $GLOBALS['site_config'] ?? [];
        
        if (empty($site_config['features']['table_ordering'])) {
            http_response_code(404);
            return render('pages/404');
        }
        
        require_once CORE_PATH . 'functions/table.php';
        
        $table_number = (int) $matches[1];
        $token = $_GET['token'] ?? null;
        
        // Validate token if required
        $token_validation = validate_table_token($token);
        if (!$token_validation['valid'] && !empty(get_table_config()['require_token'])) {
            return render('pages/table-error', [
                'error' => $token_validation['error']
            ]);
        }
        
        // Validate table number
        $table_validation = validate_table_number($table_number);
        if (!$table_validation['valid']) {
            return render('pages/table-error', [
                'error' => $table_validation['error']
            ]);
        }
        
        // Redirect to table menu with table number in query
        $redirect_url = store_url('/table/menu?t=' . $table_number);
        if ($token) {
            $redirect_url .= '&token=' . urlencode($token);
        }
        header('Location: ' . $redirect_url);
        exit;
    }
    
    // Table menu - /table/menu?t=5
    if ($uri === '/table/menu' && $method === 'GET') {
        $site_config = $GLOBALS['site_config'] ?? [];
        
        if (empty($site_config['features']['table_ordering'])) {
            http_response_code(404);
            return render('pages/404');
        }
        
        require_once CORE_PATH . 'functions/table.php';
        
        $table_number = (int) ($_GET['t'] ?? 0);
        $token = $_GET['token'] ?? null;
        
        // Validate table
        $table_validation = validate_table_number($table_number);
        if (!$table_validation['valid']) {
            // Redirect to table landing to select table
            header('Location: ' . store_url('/table') . ($token ? '?token=' . urlencode($token) : ''));
            exit;
        }
        
        // Get products with table pricing
        $products_by_category = get_products_with_availability(true); // true = table mode
        $featured_products = get_featured_products_with_availability(true);
        
        $categories = [];
        if (!empty($featured_products)) {
            $categories[] = 'Featured';
        }
        $categories = array_merge($categories, array_keys($products_by_category));
        
        $shop_status = get_shop_status();
        $table_config = get_table_config();
        
        // Get auto-apply promos (filter for table method)
        $all_promos = load_json_config('promotions.json')['codes'] ?? [];
        $auto_promos = array_filter($all_promos, function($p) {
            if (!$p['active'] || !$p['autoApply']) return false;
            $now = date('Y-m-d H:i:s');
            if ($now < $p['validFrom'] || $now > $p['validUntil']) return false;
            // Filter by method - null means all, otherwise must include 'table'
            if ($p['methods'] !== null && !in_array('table', $p['methods'])) return false;
            return true;
        });
        $auto_promos = array_values($auto_promos);
        
        // Get active offers (if feature enabled)
        $active_offers = [];
        $carousel_products = [];
        if (!empty($site_config['features']['offers'])) {
            $active_offers = get_active_offers();
            $all_products = load_json_config('products.json');
            $carousel_products = get_free_carousel_products($all_products);
        }
        
        // Upsells
        $upsell_products = [];
        $upsells_config = ['enabled' => false];
        if ($site_config['features']['upsells'] ?? false) {
            $upsells_config = load_json_config('upsells.json');
            $upsells_config['enabled'] = true;
            
            foreach ($upsells_config['products'] ?? [] as $product_id) {
                $product = get_product_by_id($product_id, true); // true = table mode
                if ($product && empty($product['options']) && empty($product['vari'])) {
                    $upsell_products[] = $product;
                }
            }
        }
        
        $allergens_config = load_json_config('allergens.json') ?: [];
        
        return render('pages/table-menu', [
            'products_by_category' => $products_by_category,
            'featured_products' => $featured_products,
            'categories' => $categories,
            'shop_status' => $shop_status,
            'table_number' => $table_number,
            'table_methods' => $table_config['methods'] ?? ['table'],
            'auto_promos' => $auto_promos,
            'active_offers' => $active_offers,
            'carousel_products' => $carousel_products,
            'upsells' => $upsells_config,
            'upsell_products' => $upsell_products,
            'allergens_config' => $allergens_config,
            'table_mode' => true,
            'table_number' => $table_number
        ]);
    }
    
    // Table checkout - /table/checkout
    if ($uri === '/table/checkout' && $method === 'GET') {
        $site_config = $GLOBALS['site_config'] ?? [];
        
        if (empty($site_config['features']['table_ordering'])) {
            http_response_code(404);
            return render('pages/404');
        }
        
        require_once CORE_PATH . 'functions/table.php';
        $table_number = (int) ($_GET['t'] ?? 0);

        // Validate table number
        $table_validation = validate_table_number($table_number);
        if (!$table_validation['valid']) {
            header('Location: ' . store_url('/table'));
            exit;
        }
        
        $customer = null;
        if (is_logged_in()) {
            $customer = get_customer_by_id($_SESSION['user_id']);
        }
        
        $table_config = get_table_config();
        $guest_fields = get_table_guest_fields();
        
        // Get auto-apply promos for table
        $all_promos = load_json_config('promotions.json')['codes'] ?? [];
        $auto_promos = array_filter($all_promos, function($p) {
            if (!$p['active'] || !$p['autoApply']) return false;
            $now = date('Y-m-d H:i:s');
            if ($now < $p['validFrom'] || $now > $p['validUntil']) return false;
            if ($p['methods'] !== null && !in_array('table', $p['methods'])) return false;
            return true;
        });
        $auto_promos = array_values($auto_promos);
        
        // Loyalty
        $loyalty_config = null;
        $loyalty_redemption = null;
        if (!empty($site_config['features']['loyalty'])) {
            $loyalty_config = load_json_config('loyalty.json');
            
            if (is_logged_in()) {
                require_once CORE_PATH . 'functions/loyalty.php';
                $store = get_current_store();
                $store_id = $store ? $store['slug'] : null;
                $loyalty_redemption = get_redemption_limits($_SESSION['user_id'], 100, $store_id);
                $loyalty_redemption['bonus_multiplier'] = get_active_bonus_multiplier();
                $loyalty_redemption['tier_multiplier'] = get_tier_config(get_customer_tier($_SESSION['user_id']))['multiplier'] ?? 1;
                $loyalty_redemption['tier_name'] = get_tier_config(get_customer_tier($_SESSION['user_id']))['name'] ?? 'Bronze';
            }
        }
        
        // Active offers
        $active_offers = [];
        if (!empty($site_config['features']['offers'])) {
            $active_offers = get_active_offers();
        }
        
        return render('pages/checkout', [
            'site' => $site_config,
            'customer' => $customer,
            'shop_status' => get_shop_status(),
            'tables' => get_table_numbers(),
            'guest_fields' => $guest_fields,
            'prompt_signup' => should_prompt_table_signup(),
            'auto_promos' => $auto_promos,
            'loyalty_config' => $loyalty_config,
            'loyalty_redemption' => $loyalty_redemption,
            'active_offers' => $active_offers,
            'table_mode' => true,
            'table_number' => $table_number,
            'table_methods' => get_table_methods(),
            'addresses' => $addresses ?? [],
            'available_methods' => [
            'methods' => [],
            'preOrderOnly' => false,
            'message' => ''
            ],
            'ready_times' => [
                'delivery' => 0,
                'collection' => get_ready_minutes('collection'),
                'table' => get_ready_minutes('collection')
            ]
        ]);
    }

    // Table checkout process - POST
    if ($uri === '/table/checkout/process' && $method === 'POST') {
        $site_config = $GLOBALS['site_config'] ?? [];
        
        if (empty($site_config['features']['table_ordering'])) {
            return json_response(['success' => false, 'error' => 'Table ordering not available'], 400);
        }
        
        require_once CORE_PATH . 'functions/table.php';
        
        // Validate table number
        $table_number = (int) ($_POST['table_number'] ?? 0);
        $table_validation = validate_table_number($table_number);
        if (!$table_validation['valid']) {
            return json_response(['success' => false, 'error' => $table_validation['error']], 400);
        }
        
        // Add table info to POST data
        $_POST['table_number'] = $table_number;
        $_POST['table_mode'] = true;
        
        // Use existing checkout process (it will detect table_mode)
        return process_checkout($_POST);
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

    $latte->addFilter('firstWord', function ($value) {
        return explode(' ', trim($value ?? ''))[0];
    });

    // Add store_url function for templates
    $latte->addFunction('store_url', function ($path = '') {
        return store_url($path);
    });

    // Add menu_url function for templates
    $latte->addFunction('menu_url', function () {
        return get_menu_url();
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

    // Add store context
    $data['store'] = get_current_store();
    $data['is_multi_store'] = is_multi_store();

    // Add page identifier for CSS scoping
    $page_parts = explode('/', $template);
    $data['page_id'] = end($page_parts); // e.g., 'home', 'order-online', 'checkout'
    
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
