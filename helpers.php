<?php
/**
 * Core Helper Functions
 * 
 * Utility functions used throughout the application
 */

/**
 * Generate URL with base path
 * 
 * @param string $path - Path relative to base (e.g., '/assets/js/cart.js')
 * @return string - Full URL path
 */
function url($path = '') {
    // Remove leading slash if present
    $path = ltrim($path, '/');
    
    // Return base path + path
    return BASE_PATH . '/' . $path;
}

/**
 * Generate asset URL
 * 
 * @param string $path - Asset path (e.g., 'js/cart.js' or '/assets/js/cart.js')
 * @return string - Full asset URL
 */
function asset($path) {
    // Remove leading slash and 'assets/' if present
    $path = ltrim($path, '/');
    $path = preg_replace('#^assets/#', '', $path);
    
    return BASE_PATH . '/assets/' . $path;
}

/**
 * Load and parse JSON config file
 * 
 * @param string $filename - Config filename (e.g., 'site.json')
 * @return array - Parsed JSON as associative array
 */
function load_json_config($filename) {
    $filepath = CONFIG_PATH . $filename;
    
    if (!file_exists($filepath)) {
        error_log("Config file not found: $filepath");
        return [];
    }
    
    $contents = file_get_contents($filepath);
    $data = json_decode($contents, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        error_log("JSON parse error in $filename: " . json_last_error_msg());
        return [];
    }
    
    return $data;
}

/**
 * Save data to JSON config file
 * 
 * @param string $filename - Config filename
 * @param array $data - Data to save
 * @return bool - Success status
 */
function save_json_config($filename, $data) {
    $filepath = CONFIG_PATH . $filename;
    $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        error_log("JSON encode error: " . json_last_error_msg());
        return false;
    }
    
    $result = file_put_contents($filepath, $json);
    return $result !== false;
}

/**
 * Clean and sanitize user input
 * 
 * @param string $input - Raw input
 * @return string - Cleaned input
 */
function clean_input($input) {
    $input = trim($input);
    $input = stripslashes($input);
    $input = htmlspecialchars($input, ENT_QUOTES, 'UTF-8');
    return $input;
}

/**
 * Validate email address
 * 
 * @param string $email - Email to validate
 * @return bool - Valid or not
 */
function is_valid_email($email) {
    return filter_var($email, FILTER_VALIDATE_EMAIL) !== false;
}

/**
 * Validate UK phone number
 * 
 * @param string $phone - Phone number
 * @return bool - Valid or not
 */
function is_valid_phone($phone) {
    // Remove spaces, dashes, parentheses
    $phone = preg_replace('/[\s\-\(\)]/', '', $phone);
    
    // UK phone: 10-11 digits, optionally starting with +44 or 0
    return preg_match('/^(\+44|0)[0-9]{9,10}$/', $phone);
}

/**
 * Validate UK postcode
 * 
 * @param string $postcode - Postcode to validate
 * @return bool - Valid or not
 */
function is_valid_postcode($postcode) {
    // UK postcode regex
    $pattern = '/^[A-Z]{1,2}[0-9R][0-9A-Z]?\s?[0-9][A-Z]{2}$/i';
    return preg_match($pattern, strtoupper(trim($postcode)));
}

/**
 * Format price with currency symbol
 * 
 * @param float $amount - Amount to format
 * @param string $currency - Currency symbol (default from config)
 * @return string - Formatted price
 */
function format_price($amount, $currency = null) {
    if ($currency === null) {
        $site_config = $GLOBALS['site_config'] ?? [];
        $currency = $site_config['currency_symbol'] ?? '£';
    }
    
    return $currency . number_format($amount, 2);
}

/**
 * Generate CSRF token
 * 
 * @return string - CSRF token
 */
function generate_csrf_token() {
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['csrf_token'];
}

/**
 * Verify CSRF token
 * 
 * @param string $token - Token to verify
 * @return bool - Valid or not
 */
function verify_csrf_token($token) {
    return isset($_SESSION['csrf_token']) && hash_equals($_SESSION['csrf_token'], $token);
}

/**
 * Redirect to URL
 * 
 * @param string $url - URL to redirect to
 * @param int $code - HTTP status code (default 302)
 */
function redirect($url, $code = 302) {
    header("Location: $url", true, $code);
    exit;
}

/**
 * Return JSON response
 * 
 * @param array $data - Data to return
 * @param int $code - HTTP status code (default 200)
 */
function json_response($data, $code = 200) {
    http_response_code($code);
    header('Content-Type: application/json');
    echo json_encode($data);
    exit;
}

/**
 * Check if shop is currently open
 * 
 * @param int $timestamp - Time to check (default: now)
 * @return bool - Open or closed
 */
function is_shop_open($timestamp = null) {
    if ($timestamp === null) {
        $timestamp = time();
    }
    
    $hours = load_json_config('hours.json');
    if (empty($hours['days'])) {
        return false;
    }
    
    // Get current day (1 = Mon, 7 = Sun)
    $day_of_week = (int)date('N', $timestamp);
    $current_time = date('H:i', $timestamp);
    $current_date = date('Y-m-d', $timestamp);
    
    // Check holidays
    if (isset($hours['holidays'])) {
        foreach ($hours['holidays'] as $holiday) {
            if ($holiday['date'] === $current_date) {
                return false;
            }
        }
    }
    
    // Check special hours
    if (isset($hours['special_hours'])) {
        foreach ($hours['special_hours'] as $special) {
            if ($special['date'] === $current_date) {
                return time_in_range($current_time, $special['open'], $special['close'], false);
            }
        }
    }
    
    // Check regular hours
    $day_config = $hours['days'][$day_of_week - 1] ?? null;
    
    if (!$day_config || isset($day_config['closed']) && $day_config['closed']) {
        return false;
    }
    
    $ends_next_day = $day_config['endsNextDay'] ?? false;
    return time_in_range($current_time, $day_config['open'], $day_config['close'], $ends_next_day);
}

/**
 * Check if time falls within range
 * 
 * @param string $time - Time to check (HH:MM)
 * @param string $start - Start time (HH:MM)
 * @param string $end - End time (HH:MM)
 * @param bool $ends_next_day - Whether range crosses midnight
 * @return bool - In range or not
 */
function time_in_range($time, $start, $end, $ends_next_day = false) {
    // Convert HH:MM to minutes since midnight for accurate comparison
    $time_mins = time_to_minutes($time);
    $start_mins = time_to_minutes($start);
    $end_mins = time_to_minutes($end);
    
    if (!$ends_next_day) {
        // Simple case: same day (e.g., 12:00 to 23:00)
        return $time_mins >= $start_mins && $time_mins <= $end_mins;
    }
    
    // Overnight case: spans midnight (e.g., 12:00 to 01:30 next day)
    // If end is 00:00, treat as end of day (1440 minutes)
    if ($end_mins == 0) {
        $end_mins = 1440; // 24:00 = end of day
    }
    
    // Current time is either:
    // - After start time today (e.g., 23:00 >= 12:00)
    // - Before end time tomorrow (e.g., 00:30 <= 01:30, which is really 1440+30 <= 1440+90)
    if ($time_mins >= $start_mins) {
        // We're in the first part (today after opening)
        return true;
    } else {
        // We're in the second part (tomorrow before closing)
        return $time_mins <= $end_mins;
    }
}

/**
 * Convert HH:MM time to minutes since midnight
 * 
 * @param string $time - Time in HH:MM format
 * @return int - Minutes since midnight (0-1439)
 */
function time_to_minutes($time) {
    list($hours, $minutes) = explode(':', $time);
    return ((int)$hours * 60) + (int)$minutes;
}

/**
 * Get current day name
 * 
 * @return string - Day name (Mon, Tue, etc.)
 */
function get_current_day() {
    $days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    $day_index = (int)date('N') - 1;
    return $days[$day_index];
}

/**
 * Format datetime for display
 * 
 * @param string $datetime - Datetime string
 * @param string $format - Format string (default: d/m/Y H:i)
 * @return string - Formatted datetime
 */
function format_datetime($datetime, $format = 'd/m/Y H:i') {
    if (empty($datetime)) {
        return '';
    }
    
    $timestamp = strtotime($datetime);
    return date($format, $timestamp);
}

/**
 * Get site timezone
 * 
 * @return string - Timezone
 */
function get_site_timezone() {
    $site_config = $GLOBALS['site_config'] ?? [];
    return $site_config['timezone'] ?? 'Europe/London';
}

/**
 * Log error message
 * 
 * @param string $message - Error message
 * @param array $context - Additional context
 */
function log_error($message, $context = []) {
    $log_message = date('[Y-m-d H:i:s] ') . $message;
    
    if (!empty($context)) {
        $log_message .= ' | Context: ' . json_encode($context);
    }
    
    $log_message .= PHP_EOL;
    
    $log_file = ROOT_PATH . 'logs/error.log';
    error_log($log_message, 3, $log_file);
}

/**
 * Debug helper - only logs if debug mode enabled
 * 
 * @param mixed $data - Data to log
 * @param string $label - Optional label
 */
function debug_log($data, $label = '') {
    $site_config = $GLOBALS['site_config'] ?? [];
    
    if (empty($site_config['debug_mode'])) {
        return;
    }
    
    $message = $label ? "$label: " : '';
    $message .= print_r($data, true);
    
    log_error('[DEBUG] ' . $message);
}

// ============================================
// OFFER HELPER FUNCTIONS
// Add these to helpers.php (after line 364)
// ============================================

/**
 * Get active offers (if feature enabled)
 * 
 * @return array - Active offers or empty array
 */
function get_active_offers() {
    $site = load_json_config('site.json');
    
    // Feature disabled = no offers
    if (empty($site['features']['offers'])) {
        return [];
    }
    
    $offers = load_json_config('offers.json')['offers'] ?? [];
    $now = date('Y-m-d H:i:s');
    
    return array_filter($offers, function($offer) use ($now) {
        if (empty($offer['active'])) return false;
        
        // Check date range
        if (!empty($offer['validFrom']) && $now < $offer['validFrom']) return false;
        if (!empty($offer['validUntil']) && $now > $offer['validUntil']) return false;
        
        return true;
    });
}

/**
 * Get offers by type
 * 
 * @param string $type - Offer type (bogof, free_on_spend, buy_x_get_free)
 * @return array - Matching offers
 */
function get_offers_by_type($type) {
    $offers = get_active_offers();
    return array_filter($offers, fn($o) => $o['type'] === $type);
}

/**
 * Get BOGOF offers for a specific product
 * 
 * @param int $product_id - Product ID
 * @return array|null - Matching BOGOF offer or null
 */
function get_bogof_for_product($product_id) {
    $bogof_offers = get_offers_by_type('bogof');
    
    foreach ($bogof_offers as $offer) {
        if (in_array($product_id, $offer['products'] ?? [])) {
            return $offer;
        }
    }
    
    return null;
}

/**
 * Get free-on-spend offers
 * 
 * @return array - Free on spend offers with eligible products
 */
function get_free_on_spend_offers() {
    return array_values(get_offers_by_type('free_on_spend'));
}

/**
 * Get buy-x-get-free offers
 * 
 * @return array - Buy X get free offers
 */
function get_buy_x_get_free_offers() {
    return array_values(get_offers_by_type('buy_x_get_free'));
}

/**
 * Check if a product is part of any active offer
 * 
 * @param int $product_id - Product ID
 * @return array - Array of offer info for this product
 */
function get_product_offers($product_id) {
    $offers = get_active_offers();
    $product_offers = [];
    
    foreach ($offers as $offer) {
        $in_offer = false;
        
        switch ($offer['type']) {
            case 'bogof':
                $in_offer = in_array($product_id, $offer['products'] ?? []);
                break;
            case 'free_on_spend':
                $in_offer = in_array($product_id, $offer['eligibleProducts'] ?? []);
                break;
            case 'buy_x_get_free':
                $in_offer = in_array($product_id, $offer['triggerProducts'] ?? []) ||
                           in_array($product_id, $offer['rewardProducts'] ?? []);
                break;
        }
        
        if ($in_offer) {
            $product_offers[] = $offer;
        }
    }
    
    return $product_offers;
}

/**
 * Get products eligible for free carousel display
 * 
 * @param array $products - All products from products.json
 * @return array - Products with offer info for carousel
 */
function get_free_carousel_products($products) {
    $free_on_spend = get_free_on_spend_offers();
    
    if (empty($free_on_spend)) {
        return [];
    }
    
    $carousel_products = [];
    
    foreach ($free_on_spend as $offer) {
        foreach ($offer['eligibleProducts'] ?? [] as $product_id) {
            $product = find_product_by_id($products, $product_id);
            
            if (!$product) continue;
            if (($product['stock'] ?? 1) != 1) continue;
            
            // Skip products with options
            if (!empty($product['options'])) continue;
            
            // Skip timed products not currently available
            if (!empty($product['availability'])) {
                if (!is_product_available_now($product)) continue;
            }
            
            $carousel_products[] = [
                'product' => $product,
                'offer' => $offer
            ];
        }
    }
    
    return $carousel_products;
}

/**
 * Find product by ID in products array
 * 
 * @param array $products - Products from products.json
 * @param int $product_id - Product ID to find
 * @return array|null - Product or null
 */
function find_product_by_id($products, $product_id) {
    foreach ($products as $category => $data) {
        if (!is_array($data) || !isset($data['products'])) continue;
    
        foreach ($data['products'] as $product) {
            if (($product['id'] ?? 0) == $product_id) {
                return $product;
            }
            // Check variants
            foreach ($product['variants'] ?? [] as $variant) {
                if (($variant['id'] ?? 0) == $product_id) {
                    return $variant;
                }
            }
        }
    }
    return null;
}

/**
 * Validate offer eligibility for checkout
 * 
 * @param array $cart - Cart items
 * @param string $offer_id - Offer ID to validate
 * @return array - Validation result
 */
function validate_offer_for_checkout($cart, $offer_id) {
    $offers = get_active_offers();
    $offer = null;
    
    foreach ($offers as $o) {
        if ($o['id'] === $offer_id) {
            $offer = $o;
            break;
        }
    }
    
    if (!$offer) {
        return ['valid' => false, 'reason' => 'Offer not found or no longer active'];
    }
    
    // Calculate cart subtotal (excluding free items)
    $subtotal = 0;
    foreach ($cart as $item) {
        if (empty($item['is_free'])) {
            $subtotal += ($item['line_total'] ?? ($item['total_price'] * $item['quantity']));
        }
    }
    
    switch ($offer['type']) {
        case 'bogof':
            // Check if paid item still in cart
            $paid_item = null;
            foreach ($cart as $i) {
                if (empty($i['is_free']) && in_array($i['product_id'], $offer['products'] ?? [])) {
                    $paid_item = $i;
                    break;
                }
            }
            if (!$paid_item) {
                return ['valid' => false, 'reason' => 'No qualifying item for BOGOF'];
            }
            
            // Check free qty doesn't exceed paid qty
            $free_qty = 0;
            foreach ($cart as $i) {
                if (!empty($i['is_free']) && ($i['offer_id'] ?? '') === $offer['id']) {
                    $free_qty += $i['quantity'] ?? 1;
                }
            }
            $paid_qty = $paid_item['quantity'] ?? 1;
            
            if ($free_qty > $paid_qty) {
                return [
                    'valid' => false,
                    'reason' => "Free quantity ({$free_qty}) cannot exceed paid quantity ({$paid_qty})"
                ];
            }
            break;
            
        case 'free_on_spend':
            if ($subtotal < $offer['minSpend']) {
                return [
                    'valid' => false, 
                    'reason' => sprintf('Minimum spend £%.2f required (current: £%.2f)', $offer['minSpend'], $subtotal)
                ];
            }
            break;
            
        case 'buy_x_get_free':
            $qualifying_qty = 0;
            foreach ($cart as $item) {
                if (empty($item['is_free']) && in_array($item['product_id'], $offer['triggerProducts'] ?? [])) {
                    $qualifying_qty += $item['quantity'];
                }
            }
            if ($qualifying_qty < $offer['triggerQuantity']) {
                return [
                    'valid' => false, 
                    'reason' => sprintf('Need %d qualifying items (have %d)', $offer['triggerQuantity'], $qualifying_qty)
                ];
            }
            break;
    }
    
    return ['valid' => true];
}

function validate_cart_offers($cart_items) {
    $errors = [];
    $offers = get_active_offers();
    
    // Calculate subtotal of non-free items
    $subtotal = 0;
    foreach ($cart_items as $item) {
        if (empty($item['is_free'])) {
            $subtotal += $item['line_total'];
        }
    }
    
    foreach ($cart_items as $item) {
        if (empty($item['is_free'])) continue;
        
        $offer_id = $item['offer_id'] ?? null;
        if (!$offer_id) {
            $errors[] = "Invalid free item: " . ($item['product_name'] ?? 'Unknown');
            continue;
        }
        
        // Find the offer
        $offer = null;
        foreach ($offers as $o) {
            if ($o['id'] === $offer_id) {
                $offer = $o;
                break;
            }
        }
        
        if (!$offer) {
            $errors[] = "Offer not found or expired";
            continue;
        }
        
        switch ($offer['type']) {
            case 'free_on_spend':
                if ($subtotal < ($offer['minSpend'] ?? 0)) {
                    $errors[] = "Spend £{$offer['minSpend']} to qualify for free {$item['product_name']}";
                    continue 2;
                }
                if (!in_array($item['product_id'], $offer['eligibleProducts'] ?? [])) {
                    $errors[] = "{$item['product_name']} not eligible for this offer";
                    continue 2;
                }
                // Check max quantity for this offer
                $free_count = 0;
                foreach ($cart_items as $i) {
                    if (!empty($i['is_free']) && ($i['offer_id'] ?? '') === $offer_id) {
                        $free_count += $i['quantity'] ?? 1;
                    }
                }
                if ($free_count > ($offer['maxQuantity'] ?? 1)) {
                    $errors[] = "Maximum " . ($offer['maxQuantity'] ?? 1) . " free items allowed";
                }
                break;
                
            case 'bogof':
                if (!in_array($item['product_id'], $offer['products'] ?? [])) {
                    $errors[] = "{$item['product_name']} not eligible for 2-for-1";
                    continue 2;
                }
                $linked_to = $item['linked_to'] ?? null;
                if (!$linked_to) {
                    $errors[] = "Invalid BOGOF: no linked purchase";
                    continue 2;
                }
                // Find the specific linked paid item
                $paid_item = null;
                foreach ($cart_items as $i) {
                    if (($i['cart_key'] ?? '') === $linked_to) {
                        $paid_item = $i;
                        break;
                    }
                }
                if (!$paid_item) {
                    $errors[] = "BOGOF requires matching paid item";
                    continue 2;
                }
                if (($item['quantity'] ?? 1) > ($paid_item['quantity'] ?? 1)) {
                    $errors[] = "Free quantity ({$item['quantity']}) cannot exceed paid quantity ({$paid_item['quantity']})";
                }
                break;
                
            case 'buy_x_get_free':
                // Add when testing this offer type
                break;
        }
    }
    
    return [
        'valid' => empty($errors),
        'errors' => array_unique($errors)
    ];
}