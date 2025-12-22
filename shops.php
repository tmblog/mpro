<?php
/**
 * Shops Management Functions
 */

/**
 * Get all shops (for global admin)
 */
function get_all_shops(): array {
    return db_fetch_all(
        "SELECT * FROM shops WHERE active = 1 ORDER BY name ASC"
    );
}

/**
 * Get shops for a specific user
 */
function get_user_shops(int $user_id, bool $is_global_admin = false): array {
    if ($is_global_admin) {
        return db_fetch_all(
            "SELECT s.*, 'global_admin' as role 
             FROM shops s 
             WHERE s.active = 1 
             ORDER BY s.name ASC"
        );
    }
    
    return db_fetch_all(
        "SELECT s.*, us.role 
         FROM shops s
         JOIN user_shops us ON s.shop_id = us.shop_id
         WHERE us.user_id = ? AND s.active = 1
         ORDER BY s.name ASC",
        [$user_id]
    );
}

/**
 * Get single shop by ID
 */
function get_shop(int $shop_id): ?array {
    return db_fetch_one(
        "SELECT * FROM shops WHERE shop_id = ?",
        [$shop_id]
    );
}

/**
 * Check if user can access a shop
 */
function can_access_shop(int $user_id, int $shop_id, bool $is_global_admin = false): bool {
    if ($is_global_admin) {
        return true;
    }
    
    $access = db_fetch_one(
        "SELECT 1 FROM user_shops WHERE user_id = ? AND shop_id = ?",
        [$user_id, $shop_id]
    );
    
    return $access !== null;
}

/**
 * Get user's role at a specific shop
 */
function get_user_shop_role(int $user_id, int $shop_id, bool $is_global_admin = false): ?string {
    if ($is_global_admin) {
        return 'global_admin';
    }
    
    $row = db_fetch_one(
        "SELECT role FROM user_shops WHERE user_id = ? AND shop_id = ?",
        [$user_id, $shop_id]
    );
    
    return $row['role'] ?? null;
}

/**
 * Create a new shop
 */
function create_shop(array $data): int|false {
    return db_insert('shops', [
        'name' => $data['name'],
        'url' => rtrim($data['url'], '/'),
        'api_secret' => $data['api_secret'] ?? API_SHARED_SECRET,
        'active' => $data['active'] ?? 1,
        'created_at' => time(),
    ]);
}

/**
 * Update a shop
 */
function update_shop(int $shop_id, array $data): bool {
    $update = [];
    
    if (isset($data['name'])) {
        $update['name'] = $data['name'];
    }
    if (isset($data['url'])) {
        $update['url'] = rtrim($data['url'], '/');
    }
    if (isset($data['api_secret'])) {
        $update['api_secret'] = $data['api_secret'];
    }
    if (isset($data['active'])) {
        $update['active'] = (int) $data['active'];
    }
    
    if (empty($update)) {
        return true;
    }
    
    $update['updated_at'] = time();
    
    return db_update('shops', $update, 'shop_id = ?', [$shop_id]) !== false;
}

/**
 * Delete a shop (soft delete - sets active = 0)
 */
function delete_shop(int $shop_id): bool {
    return db_update('shops', ['active' => 0], 'shop_id = ?', [$shop_id]) !== false;
}

/**
 * Assign user to shop
 */
function assign_user_to_shop(int $user_id, int $shop_id, string $role = 'manager'): bool {
    // Check if already assigned
    $existing = db_fetch_one(
        "SELECT 1 FROM user_shops WHERE user_id = ? AND shop_id = ?",
        [$user_id, $shop_id]
    );
    
    if ($existing) {
        // Update role
        return db_update(
            'user_shops',
            ['role' => $role],
            'user_id = ? AND shop_id = ?',
            [$user_id, $shop_id]
        ) !== false;
    }
    
    // New assignment
    return db_insert('user_shops', [
        'user_id' => $user_id,
        'shop_id' => $shop_id,
        'role' => $role,
        'created_at' => time(),
    ]) !== false;
}

/**
 * Remove user from shop
 */
function remove_user_from_shop(int $user_id, int $shop_id): bool {
    return db_delete('user_shops', 'user_id = ? AND shop_id = ?', [$user_id, $shop_id]) !== false;
}

/**
 * Get all users assigned to a shop
 */
function get_shop_users(int $shop_id): array {
    return db_fetch_all(
        "SELECT u.id, u.email, u.username, us.role, us.created_at as assigned_at
         FROM users u
         JOIN user_shops us ON u.id = us.user_id
         WHERE us.shop_id = ?
         ORDER BY u.username ASC",
        [$shop_id]
    );
}

/**
 * Get currently selected shop from session
 */
function get_selected_shop(): ?array {
    $shop_id = $_SESSION['selected_shop_id'] ?? null;
    
    if (!$shop_id) {
        return null;
    }
    
    return get_shop($shop_id);
}

/**
 * Set selected shop in session
 */
function set_selected_shop(int $shop_id): bool {
    // Verify access
    if (!can_access_shop(current_user_id(), $shop_id, is_global_admin())) {
        return false;
    }
    
    $_SESSION['selected_shop_id'] = $shop_id;
    return true;
}

/**
 * Clear selected shop from session
 */
function clear_selected_shop(): void {
    unset($_SESSION['selected_shop_id']);
}

/**
 * Get all users (for admin assignment)
 */
function get_all_users(): array {
    return db_fetch_all(
        "SELECT id, email, username, is_global_admin, status 
         FROM users 
         WHERE status = 0 
         ORDER BY username ASC, email ASC"
    );
}

/**
 * Get user by ID
 */
function get_user_by_id(int $user_id): ?array {
    return db_fetch_one(
        "SELECT id, email, username, is_global_admin, status 
         FROM users 
         WHERE id = ?",
        [$user_id]
    );
}

/**
 * Get shops assigned to a user
 */
function get_shops_for_user(int $user_id): array {
    return db_fetch_all(
        "SELECT s.*, us.role, us.created_at as assigned_at
         FROM shops s
         JOIN user_shops us ON s.shop_id = us.shop_id
         WHERE us.user_id = ? AND s.active = 1
         ORDER BY s.name ASC",
        [$user_id]
    );
}

/**
 * Get shops NOT assigned to a user (for assignment dropdown)
 */
function get_unassigned_shops_for_user(int $user_id): array {
    return db_fetch_all(
        "SELECT s.* 
         FROM shops s
         WHERE s.active = 1 
         AND s.shop_id NOT IN (
             SELECT shop_id FROM user_shops WHERE user_id = ?
         )
         ORDER BY s.name ASC",
        [$user_id]
    );
}
