<?php
/**
 * Product Functions
 * 
 * Load and manage products from products.json and options.json
 */

/**
 * Load all products from JSON
 * 
 * @return array - Products grouped by category
 */
function get_all_products() {
    static $products = null;
    
    if ($products === null) {
        $products = load_json_config('products.json');
    }
    
    return $products;
}

/**
 * Load product options from JSON
 * 
 * @return array - All product options
 */
function get_product_options() {
    static $options = null;
    
    if ($options === null) {
        $options = load_json_config('options.json');
    }
    
    return $options;
}

/**
 * Get single product by ID
 * 
 * @param int $product_id - Product ID
 * @param bool $table_mode - If true, use table_price where available
 * @return array|null - Product data or null if not found
 */
function get_product_by_id($product_id, $table_mode = false) {
    $all_products = get_all_products();
    
    foreach ($all_products as $category => $data) {
        foreach ($data['products'] as $product) {
            // Handle products with variations
            if (isset($product['vari'])) {
                foreach ($product['vari'] as $variation) {
                    if ($variation['id'] == $product_id) {
                        // Merge variation with parent data
                        $variation['category'] = $category;
                        $variation['parent_name'] = $product['name'];
                        $variation['img'] = $product['img'] ?? null;
                        $variation['dsc'] = $variation['dsc'] ?? $product['dsc'] ?? '';
                        
                        // Swap price for table mode
                        if ($table_mode && isset($variation['table_price'])) {
                            $variation['original_price'] = $variation['price'];
                            $variation['price'] = $variation['table_price'];
                        }
                        
                        return $variation;
                    }
                }
            } else {
                // Regular product
                if ($product['id'] == $product_id) {
                    $product['category'] = $category;
                    
                    // Swap price for table mode
                    if ($table_mode && isset($product['table_price'])) {
                        $product['original_price'] = $product['price'];
                        $product['price'] = $product['table_price'];
                    }
                    
                    return $product;
                }
            }
        }
    }
    
    return null;
}

/**
 * Get option configuration by ID
 * 
 * @param int $option_id - Option ID
 * @return array|null - Option data or null if not found
 */
function get_option_by_id($option_id) {
    $all_options = get_product_options();
    
    foreach ($all_options as $option) {
        if ($option['id'] == $option_id) {
            return $option;
        }
    }
    
    return null;
}

/**
 * Check if product is in stock
 * 
 * @param int $product_id - Product ID
 * @return bool - In stock or not
 */
function is_product_in_stock($product_id) {
    $product = get_product_by_id($product_id);
    
    if (!$product) {
        return false;
    }
    
    return isset($product['stock']) && $product['stock'] == 1;
}

/**
 * Calculate product price with selected options
 * 
 * @param int $product_id - Product ID
 * @param array $selected_options - Array of selected options
 * @return float - Total price
 */
function calculate_product_price($product_id, $selected_options = [], $use_table_price = false) {
    $product = get_product_by_id($product_id);
    
    if (!$product) {
        return 0;
    }

    // Use table_price if available and requested
    $base_price = $use_table_price && isset($product['table_price']) 
        ? (float)$product['table_price'] 
        : (float)$product['price'];
    
    $total = $base_price;
    
    // Add option prices
    foreach ($selected_options as $option_data) {
        $option_id = $option_data['option_id'];
        $selected_item_id = $option_data['selected_id'];
        
        $option_config = get_option_by_id($option_id);
        
        if (!$option_config) {
            continue;
        }
        
        // Find selected option item
        foreach ($option_config['options'] as $item) {
            if ($item['id'] == $selected_item_id) {
                $total += (float)$item['price'];
                
                // Check for child options (nested)
                if (isset($option_data['child_id']) && isset($item['childOptions'])) {
                    foreach ($item['childOptions']['options'] as $child) {
                        if ($child['id'] == $option_data['child_id']) {
                            $total += (float)$child['price'];
                            break;
                        }
                    }
                }
                break;
            }
        }
    }
    
    return $total;
}

/**
 * Get product display name with options
 * 
 * @param int $product_id - Product ID
 * @param array $selected_options - Selected options
 * @return string - Formatted product name
 */
function get_product_display_name($product_id, $selected_options = []) {
    $product = get_product_by_id($product_id);
    
    if (!$product) {
        return 'Unknown Product';
    }
    
    $name = $product['name'];
    
    // Add parent name for variations
    if (isset($product['parent_name'])) {
        $name = $product['parent_name'] . ' - ' . $name;
    }
    
    // Add selected options
    if (!empty($selected_options)) {
        $option_names = [];
        
        foreach ($selected_options as $option_data) {
            $option_id = $option_data['option_id'];
            $selected_item_id = $option_data['selected_id'];
            
            $option_config = get_option_by_id($option_id);
            
            if (!$option_config) {
                continue;
            }
            
            foreach ($option_config['options'] as $item) {
                if ($item['id'] == $selected_item_id) {
                    $option_text = $item['name'];
                    
                    // Add child option if exists
                    if (isset($option_data['child_id']) && isset($item['childOptions'])) {
                        foreach ($item['childOptions']['options'] as $child) {
                            if ($child['id'] == $option_data['child_id']) {
                                $option_text .= ' (' . $child['name'] . ')';
                                break;
                            }
                        }
                    }
                    
                    $option_names[] = $option_text;
                    break;
                }
            }
        }
        
        if (!empty($option_names)) {
            $name .= '<br>' . implode('<br>', $option_names);
        }
    }
    
    return $name;
}

/**
 * Get all products by category
 * 
 * @param string $category - Category name
 * @return array - Products in that category
 */
function get_products_by_category($category) {
    $all_products = get_all_products();
    
    return $all_products[$category]['products'] ?? [];
}

/**
 * Get all category names
 * 
 * @return array - Array of category names
 */
function get_all_categories() {
    $all_products = get_all_products();
    return array_keys($all_products);
}

/**
 * Format products for display (flatten variations)
 * 
 * @return array - Flattened product list
 */
function get_products_for_display() {
    $all_products = get_all_products();
    $display_products = [];
    
    foreach ($all_products as $category => $products) {
        foreach ($data['products'] as $product) {
            // Check if product has variations
            if (isset($product['vari'])) {
                // Add each variation as separate product
                foreach ($product['vari'] as $variation) {
                    $display_item = $variation;
                    $display_item['category'] = $category;
                    $display_item['parent_name'] = $product['name'];
                    $display_item['full_name'] = $product['name'] . ' - ' . $variation['name'];
                    $display_item['img'] = $product['img'] ?? null;
                    $display_item['dsc'] = $variation['dsc'] ?? $product['dsc'] ?? '';
                    
                    $display_products[] = $display_item;
                }
            } else {
                // Regular product
                $display_item = $product;
                $display_item['category'] = $category;
                $display_item['full_name'] = $product['name'];
                
                $display_products[] = $display_item;
            }
        }
    }
    
    return $display_products;
}

/**
 * Get featured products
 * 
 * @param int $limit - Maximum number of products
 * @return array - Featured products
 */
function get_featured_products($limit = 6) {
    $all_products = get_products_for_display();
    $featured = [];
    
    foreach ($all_products as $product) {
        if (isset($product['featured']) && $product['featured']) {
            $featured[] = $product;
            
            if (count($featured) >= $limit) {
                break;
            }
        }
    }
    
    return $featured;
}

/**
 * Search products by name or description
 * 
 * @param string $search_term - Search term
 * @return array - Matching products
 */
function search_products($search_term) {
    $all_products = get_products_for_display();
    $results = [];
    
    $search_term = strtolower($search_term);
    
    foreach ($all_products as $product) {
        $name = strtolower($product['name']);
        $dsc = strtolower($product['dsc'] ?? '');
        
        if (strpos($name, $search_term) !== false || strpos($dsc, $search_term) !== false) {
            $results[] = $product;
        }
    }
    
    return $results;
}

/**
 * Check if product is available right now based on time restrictions
 * 
 * @param array $product - Product data with optional 'availability' field
 * @return bool - Available now or not
 */
function is_product_available_now($product) {
    // No availability restrictions = always available
    if (!isset($product['availability']) || empty($product['availability'])) {
        return true;
    }
    
    $avail = $product['availability'];
    $now = time();
    $currentDay = date('D', $now); // Mon, Tue, Wed, etc.
    $currentTime = date('H:i', $now);
    
    // Check dayTimes first (specific day+time overrides)
    if (!empty($avail['dayTimes'])) {
        foreach ($avail['dayTimes'] as $dt) {
            if ($dt['day'] === $currentDay) {
                // This day has specific times
                return time_in_range($currentTime, $dt['start'], $dt['end'], false);
            }
        }
        // If dayTimes exists but current day not in it, check if days/times apply
        // If no days array, dayTimes is the only restriction
        if (empty($avail['days'])) {
            return false;
        }
    }
    
    // Check days restriction
    $dayAllowed = true;
    if (!empty($avail['days'])) {
        $dayAllowed = in_array($currentDay, $avail['days']);
    }
    
    if (!$dayAllowed) {
        return false;
    }
    
    // Check times restriction
    if (!empty($avail['times'])) {
        return time_in_range($currentTime, $avail['times']['start'], $avail['times']['end'], false);
    }
    
    // Day is allowed and no time restriction
    return true;
}

/**
 * Get availability message for display
 * 
 * @param array $product - Product data
 * @return string - Human readable availability message
 */
function get_availability_message($product) {
    if (!isset($product['availability']) || empty($product['availability'])) {
        return '';
    }
    
    $avail = $product['availability'];
    $parts = [];
    
    // Format days
    if (!empty($avail['days'])) {
        $days = $avail['days'];
        if (count($days) === 7) {
            $dayStr = 'daily';
        } elseif (count($days) === 5 && !in_array('Sat', $days) && !in_array('Sun', $days)) {
            $dayStr = 'Mon-Fri';
        } elseif (count($days) === 2 && in_array('Sat', $days) && in_array('Sun', $days)) {
            $dayStr = 'weekends';
        } else {
            $dayStr = implode(', ', $days);
        }
        $parts[] = $dayStr;
    }
    
    // Format times
    if (!empty($avail['times'])) {
        $start = date('g:ia', strtotime($avail['times']['start']));
        $end = date('g:ia', strtotime($avail['times']['end']));
        $parts[] = "{$start}-{$end}";
    }
    
    // Format dayTimes exceptions
    if (!empty($avail['dayTimes'])) {
        $dtParts = [];
        foreach ($avail['dayTimes'] as $dt) {
            $start = date('g:ia', strtotime($dt['start']));
            $end = date('g:ia', strtotime($dt['end']));
            $dtParts[] = "{$dt['day']} {$start}-{$end}";
        }
        if (!empty($parts)) {
            $parts[] = '& ' . implode(', ', $dtParts);
        } else {
            $parts = $dtParts;
        }
    }
    
    return 'Available ' . implode(' ', $parts);
}

/**
 * Get all products with availability status added
 * 
 * @param bool $table_mode - If true, use table_price where available
 * @return array - Products by category with 'available_now' and 'availability_message' added
 */
function get_products_with_availability($table_mode = false) {
    $all_products = get_all_products();
    $result = [];
    
    foreach ($all_products as $category => $data) {
        $result[$category] = ['description' => $data['description'] ?? '', 'products' => []];
        foreach ($data['products'] as $product) {
            // Swap price for table mode
            if ($table_mode && isset($product['table_price'])) {
                $product['original_price'] = $product['price'];
                $product['price'] = $product['table_price'];
            }
            
            // Handle variations
            if (isset($product['vari'])) {
                foreach ($product['vari'] as &$variation) {
                    // Swap variation price for table mode
                    if ($table_mode && isset($variation['table_price'])) {
                        $variation['original_price'] = $variation['price'];
                        $variation['price'] = $variation['table_price'];
                    }
                    
                    $variation['available_now'] = is_product_available_now($variation);
                    $variation['availability_message'] = get_availability_message($variation);
                }
                unset($variation);
            }
            
            $product['available_now'] = is_product_available_now($product);
            $product['availability_message'] = get_availability_message($product);
            $result[$category]['products'][] = $product;
        }
    }
    
    return $result;
}

/**
 * Get featured products with availability
 * 
 * @param bool $table_mode - If true, use table_price where available
 * @return array - Featured products
 */
function get_featured_products_with_availability($table_mode = false) {
    $all_products = get_products_with_availability($table_mode);
    $featured = [];
    
    foreach ($all_products as $category => $data) {
        foreach ($data['products'] as $product) {
            if (isset($product['featured']) && $product['featured']) {
                $product['_original_category'] = $category;
                $featured[] = $product;
            }
            // Also check variations
            if (isset($product['vari'])) {
                foreach ($product['vari'] as $variation) {
                    if (isset($variation['featured']) && $variation['featured']) {
                        $featuredVar = $variation;
                        $featuredVar['_original_category'] = $category;
                        $featuredVar['img'] = $product['img'] ?? null;
                        $featured[] = $featuredVar;
                    }
                }
            }
        }
    }
    
    return $featured;
}

/**
 * Validate cart items are currently available (timed products + stock)
 * 
 * @param array $cart_items - Cart items array
 * @return array - ['valid' => bool, 'unavailable' => array, 'messages' => array]
 */
function validate_cart_availability($cart_items) {
    $unavailable = [];
    $messages = [];
    
    foreach ($cart_items as $item) {
        $product = get_product_by_id($item['product_id']);
        
        if (!$product) {
            $unavailable[] = [
                'product_id' => $item['product_id'],
                'product_name' => $item['product_name'] ?? 'Unknown product',
                'reason' => 'not_found'
            ];
            $messages[] = ($item['product_name'] ?? 'Unknown product') . ' is no longer available';
            continue;
        }
        
        // Check stock
        if (isset($product['stock']) && $product['stock'] == 0) {
            $unavailable[] = [
                'product_id' => $item['product_id'],
                'product_name' => $item['product_name'] ?? $product['name'],
                'reason' => 'out_of_stock'
            ];
            $messages[] = $product['name'] . ' is out of stock';
            continue;
        }
        
        // Check timed availability
        if (!is_product_available_now($product)) {
            $unavailable[] = [
                'product_id' => $item['product_id'],
                'product_name' => $item['product_name'] ?? $product['name'],
                'reason' => 'timed',
                'availability_message' => get_availability_message($product)
            ];
            $avail_msg = get_availability_message($product);
            $messages[] = $product['name'] . ' is not available right now' . ($avail_msg ? " ($avail_msg)" : '');
        }
    }
    
    return [
        'valid' => empty($unavailable),
        'unavailable' => $unavailable,
        'messages' => $messages
    ];
}

/**
 * Get minimum order amount for a delivery method
 * 
 * @param string $method - 'delivery' or 'collection'
 * @return float - Minimum order amount
 */
function get_minimum_order($method) {
    $delivery_config = load_json_config('delivery.json');
    $day_of_week = (int)date('N');
    $current_time = date('H:i');
    
    foreach ($delivery_config['windows'] ?? [] as $window) {
        if (!in_array($day_of_week, $window['days'] ?? [])) continue;
        
        $window_method = $window['method'] ?? '';
        if ($window_method !== $method && $window_method !== 'both') continue;
        
        $ends_next_day = $window['endsNextDay'] ?? false;
        if (time_in_range($current_time, $window['start'], $window['end'], $ends_next_day)) {
            return (float)($window['minOrder'] ?? 0);
        }
    }
    
    return 0;
}