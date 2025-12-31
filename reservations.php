<?php
/**
 * Reservations System Functions
 * Handles table bookings, availability checking, and deposit payments
 */

require_once CORE_PATH . 'functions/helpers.php';
require_once CORE_PATH . 'functions/email_functions.php';

/**
 * Get available time slots for reservations on a specific date
 *
 * @param string $date Date in Y-m-d format
 * @return array Available time slots with capacity info
 */
function get_reservation_timeslots($date) {
    $config = load_json_config('reservations.json');
    $hours = load_json_config('hours.json');

    $slots = [];
    $dateObj = new DateTime($date);
    $dayName = $dateObj->format('D');

    // Check if restaurant is closed on this day
    $dayHours = null;
    foreach ($hours['days'] as $day) {
        if ($day['day'] === $dayName) {
            $dayHours = $day;
            break;
        }
    }

    // If closed, return empty slots
    if (!$dayHours || $dayHours['closed']) {
        return [];
    }

    // Check for holidays
    foreach ($hours['holidays'] as $holiday) {
        if ($holiday['date'] === $date) {
            return []; // Closed for holiday
        }
    }

    // Check for special hours
    $specialHours = null;
    foreach ($hours['special_hours'] as $special) {
        if ($special['date'] === $date) {
            $specialHours = $special;
            break;
        }
    }

    // Use shop opening/closing hours directly
    $shopOpen = $specialHours['open'] ?? $dayHours['open'];
    $shopClose = $specialHours['close'] ?? $dayHours['close'];
    $interval = $config['capacity']['slot_interval_minutes'];

    // Convert to DateTime objects
    $current = new DateTime($date . ' ' . $shopOpen);
    $end = new DateTime($date . ' ' . $shopClose);

    // Handle next-day closing times
    // Only apply if NOT using special hours, or if closing time is before 6am (indicating next day)
    $closeHour = (int)explode(':', $shopClose)[0];
    $shouldAddDay = false;

    if ($specialHours) {
        // For special hours, only add day if close time is early morning (before 6am)
        $shouldAddDay = ($closeHour >= 0 && $closeHour < 6);
    } else {
        // For regular hours, use the endsNextDay flag
        $shouldAddDay = (isset($dayHours['endsNextDay']) && $dayHours['endsNextDay']);
    }

    if ($shouldAddDay) {
        $end->modify('+1 day');
    }

    // Stop taking reservations 1 hour before closing
    $end->modify('-1 hour');

    // Generate slots from opening to 1 hour before closing
    while ($current < $end) {
        $timeStr = $current->format('H:i');

        // Check if slot is in the past
        $slotDateTime = new DateTime($date . ' ' . $timeStr);
        $now = new DateTime();
        $minAdvance = new DateInterval('PT' . $config['booking_window']['min_hours_advance'] . 'H');
        $minBookingTime = clone $now;
        $minBookingTime->add($minAdvance);

        if ($slotDateTime >= $minBookingTime) {
            // Get current bookings for this slot
            $booked = get_slot_bookings($date, $timeStr);
            $capacity = $config['capacity']['max_covers_per_slot'];
            $available = $capacity - $booked;
            $warningThreshold = $capacity * $config['capacity']['warning_threshold'];

            // Determine service period based on time
            // Hours 0-5 (midnight to 6am) = Late Night/Dinner
            // Hours 6-15 (6am to 3pm) = Lunch
            // Hours 16-23 (4pm to 11pm) = Dinner
            $hour = (int)$current->format('H');
            $service = ($hour >= 6 && $hour < 16) ? 'Lunch' : 'Dinner';

            $slots[] = [
                'time' => $timeStr,
                'formatted_time' => $current->format('g:i A'),
                'service' => $service,
                'capacity' => $capacity,
                'booked' => $booked,
                'available' => $available,
                'almost_full' => ($booked >= $warningThreshold && $booked < $capacity),
                'full' => ($booked >= $capacity)
            ];
        }

        $current->add(new DateInterval('PT' . $interval . 'M'));
    }

    return $slots;
}

/**
 * Get reservation by ID and token (secure access)
 *
 * @param int $reservation_id Reservation ID
 * @param string $token Security token
 * @return array|null Reservation data or null if not found
 */
function get_reservation_by_token($reservation_id, $token) {
    $db = get_db();

    $stmt = mysqli_prepare($db, "
        SELECT * FROM reservations
        WHERE reservation_id = ?
        AND token = ?
    ");

    mysqli_stmt_bind_param($stmt, "is", $reservation_id, $token);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);

    return mysqli_fetch_assoc($result);
}

/**
 * Get number of people booked for a specific time slot
 *
 * @param string $date Date in Y-m-d format
 * @param string $time Time in H:i format
 * @return int Total party size booked for this slot
 */
function get_slot_bookings($date, $time) {
    $db = get_db();

    $stmt = mysqli_prepare($db, "
        SELECT COALESCE(SUM(party_size), 0) as total
        FROM reservations
        WHERE reservation_date = ?
        AND reservation_time = ?
        AND status IN ('pending', 'confirmed', 'seated')
    ");

    mysqli_stmt_bind_param($stmt, "ss", $date, $time);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);
    $row = mysqli_fetch_assoc($result);

    return (int)$row['total'];
}

/**
 * Create a new reservation
 *
 * @param array $data Reservation data
 * @return array Result with success status and reservation_id
 */
function create_reservation($data) {
    $db = get_db();

    // Validate required fields
    $required = ['customer_name', 'customer_email', 'customer_phone', 'reservation_date', 'reservation_time', 'party_size'];
    foreach ($required as $field) {
        if (empty($data[$field])) {
            return ['success' => false, 'message' => "Missing required field: $field"];
        }
    }

    // Check availability
    $config = load_json_config('reservations.json');
    $booked = get_slot_bookings($data['reservation_date'], $data['reservation_time']);
    $capacity = $config['capacity']['max_covers_per_slot'];

    if ($booked + $data['party_size'] > $capacity) {
        return ['success' => false, 'message' => 'This time slot is now fully booked. Please choose another time.'];
    }

    // Determine customer type and ID
    $customer_id = $data['customer_id'] ?? null;
    $customer_type = $customer_id ? 'R' : 'G';

    // Check if deposit is required
    $deposit_required = $data['deposit_required'] ?? false;
    $deposit_amount = $data['deposit_amount'] ?? 0;

    // Generate secure token
    $token = bin2hex(random_bytes(16));

    // Insert reservation
    $stmt = mysqli_prepare($db, "
        INSERT INTO reservations (
            customer_id,
            customer_type,
            customer_name,
            customer_email,
            customer_tel,
            reservation_date,
            reservation_time,
            party_size,
            special_requests,
            deposit_required,
            deposit_amount,
            deposit_paid,
            status,
            token,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())
    ");

    $status = $deposit_required ? 'pending' : 'confirmed';
    $deposit_paid = $deposit_required ? 0 : 1;
    $deposit_req_int = $deposit_required ? 1 : 0;
    $special_requests = $data['special_requests'] ?? null;

    mysqli_stmt_bind_param($stmt, "issssssissddss",
        $customer_id,
        $customer_type,
        $data['customer_name'],
        $data['customer_email'],
        $data['customer_phone'],
        $data['reservation_date'],
        $data['reservation_time'],
        $data['party_size'],
        $special_requests,
        $deposit_req_int,
        $deposit_amount,
        $deposit_paid,
        $status,
        $token
    );

    $success = mysqli_stmt_execute($stmt);

    if (!$success) {
        error_log("Reservation creation error: " . mysqli_error($db));
        return ['success' => false, 'message' => 'An error occurred. Please try again.'];
    }

    $reservation_id = mysqli_insert_id($db);

    // If no deposit required, send confirmation email immediately
    if (!$deposit_required) {
        send_reservation_confirmation($reservation_id);
    }

    return [
        'success' => true,
        'reservation_id' => $reservation_id,
        'token' => $token,
        'requires_payment' => $deposit_required,
        'deposit_amount' => $deposit_amount
    ];
}

/**
 * Get reservation by ID
 *
 * @param int $reservation_id
 * @return array|null Reservation data or null if not found
 */
function get_reservation($reservation_id) {
    $db = get_db();

    $stmt = mysqli_prepare($db, "SELECT * FROM reservations WHERE reservation_id = ?");
    mysqli_stmt_bind_param($stmt, "i", $reservation_id);
    mysqli_stmt_execute($stmt);
    $result = mysqli_stmt_get_result($stmt);

    return mysqli_fetch_assoc($result);
}

/**
 * Update reservation status
 *
 * @param int $reservation_id
 * @param string $status New status
 * @return bool Success
 */
function update_reservation_status($reservation_id, $status) {
    $db = get_db();

    $stmt = mysqli_prepare($db, "
        UPDATE reservations
        SET status = ?
            " . ($status === 'confirmed' ? ", confirmed_at = NOW()" : "") . "
            " . ($status === 'cancelled' ? ", cancelled_at = NOW()" : "") . "
        WHERE reservation_id = ?
    ");

    mysqli_stmt_bind_param($stmt, "si", $status, $reservation_id);
    return mysqli_stmt_execute($stmt);
}

/**
 * Mark deposit as paid
 *
 * @param int $reservation_id
 * @param string $payment_intent_id Ryft payment intent ID
 * @return bool Success
 */
function mark_deposit_paid($reservation_id, $payment_intent_id) {
    $db = get_db();

    $stmt = mysqli_prepare($db, "
        UPDATE reservations
        SET deposit_paid = 1,
            payment_intent_id = ?,
            status = 'confirmed',
            confirmed_at = NOW()
        WHERE reservation_id = ?
    ");

    mysqli_stmt_bind_param($stmt, "si", $payment_intent_id, $reservation_id);
    $success = mysqli_stmt_execute($stmt);

    if ($success) {
        send_reservation_confirmation($reservation_id);
    }

    return $success;
}

/**
 * Cancel a reservation
 *
 * @param int $reservation_id
 * @param int $customer_id Customer ID for authorization
 * @return array Result with success status
 */
function cancel_reservation($reservation_id, $customer_id = null) {
    $config = load_json_config('reservations.json');
    $reservation = get_reservation($reservation_id);

    if (!$reservation) {
        return ['success' => false, 'message' => 'Reservation not found'];
    }

    // Check authorization
    if ($customer_id && $reservation['customer_id'] != $customer_id) {
        return ['success' => false, 'message' => 'Unauthorized'];
    }

    // Check cancellation policy
    if ($config['cancellation']['allowed']) {
        $reservationDateTime = new DateTime($reservation['reservation_date'] . ' ' . $reservation['reservation_time']);
        $now = new DateTime();
        $minHours = $config['cancellation']['min_hours_before'];
        $cancelDeadline = clone $reservationDateTime;
        $cancelDeadline->sub(new DateInterval('PT' . $minHours . 'H'));

        if ($now > $cancelDeadline) {
            return ['success' => false, 'message' => "Cancellation not allowed within $minHours hours of reservation"];
        }
    }

    // Update status
    update_reservation_status($reservation_id, 'cancelled');

    // Refund deposit if applicable
    if ($reservation['deposit_paid'] && $config['cancellation']['refund_deposit']) {
        // TODO: Implement Ryft refund
        // refund_deposit($reservation['payment_intent_id']);
    }

    // Send cancellation email
    send_reservation_cancellation($reservation_id);

    return ['success' => true, 'message' => 'Reservation cancelled successfully'];
}

/**
 * Award loyalty points when reservation is completed
 *
 * @param int $reservation_id
 * @return bool Success
 */
function award_reservation_points($reservation_id) {
    $config = load_json_config('reservations.json');

    if (!$config['loyalty_points']['enabled']) {
        return false;
    }

    $reservation = get_reservation($reservation_id);

    if (!$reservation || !$reservation['customer_id'] || $reservation['customer_type'] !== 'R') {
        return false;
    }

    // Calculate points
    $deposit = $reservation['deposit_amount'];
    $percentage = $config['loyalty_points']['percentage'] / 100;
    $minimum = $config['loyalty_points']['minimum_points'];

    // Get customer tier multiplier
    require_once CORE_PATH . 'functions/loyalty.php';
    $customer = get_customer_by_id($reservation['customer_id']);
    $tier_config = load_json_config('loyalty.json');
    $tier_multiplier = $tier_config['tiers'][$customer['loyalty_tier']]['multiplier'] ?? 1;

    // Calculate final points
    $points = max($deposit * $percentage * $tier_multiplier, $minimum);

    // Award points
    award_loyalty_points(
        $reservation['customer_id'],
        $points,
        'earned',
        "Reservation completed - Party of {$reservation['party_size']}"
    );

    return true;
}

/**
 * Create Ryft payment session for reservation deposit
 *
 * @param int $reservation_id
 * @return array Result with client_secret or error
 */
function create_reservation_payment_intent($reservation_id) {
    $db = get_db();

    require_once CORE_PATH . 'functions/ryft_functions.php';
    $ryft_config = get_ryft_config();
    $site_config = load_json_config('site.json');

    $reservation = get_reservation($reservation_id);

    if (!$reservation) {
        return ['success' => false, 'message' => 'Reservation not found'];
    }

    if (!$reservation['deposit_required'] || $reservation['deposit_paid']) {
        return ['success' => false, 'message' => 'Deposit not required'];
    }

    // Check if payment intent already exists
    if (!empty($reservation['payment_intent_id'])) {
        // Return existing client secret from session if available
        $client_secret = $_SESSION['reservation_payment_secret'] ?? null;
        if ($client_secret) {
            return [
                'success' => true,
                'client_secret' => $client_secret,
                'payment_intent_id' => $reservation['payment_intent_id']
            ];
        }
    }

    // Prepare payment session data
    $amount_in_pence = (int)round($reservation['deposit_amount'] * 100);

    // Prepare statement descriptor
    $descriptor = truncate_descriptor($site_config['site_name'], 22);
    $city = truncate_descriptor($site_config['city'] ?? 'UK', 13);

    // Prepare return URL
    $base_url = 'https://' . $_SERVER['HTTP_HOST'] . BASE_PATH;
    $return_url = $base_url . '/reservations/payment-success?reservation=' . $reservation_id;

    // Format reservation date/time for description
    $dateObj = new DateTime($reservation['reservation_date']);
    $dateFormatted = $dateObj->format('M j, Y');

    $payload = [
        'amount' => $amount_in_pence,
        'currency' => 'GBP',
        'customerEmail' => $reservation['customer_email'],
        'returnUrl' => $return_url,
        'metadata' => [
            'reservationId' => (string)$reservation_id,
            'type' => 'reservation_deposit',
            'partySize' => (string)$reservation['party_size'],
            'reservationDate' => $reservation['reservation_date']
        ],
        'statementDescriptor' => [
            'descriptor' => $descriptor,
            'city' => $city
        ]
    ];

    // Add customer details
    if ($reservation['customer_id']) {
        // Get customer Ryft ID if exists
        $customer = get_customer_by_id($reservation['customer_id']);
        if ($customer && !empty($customer['card_customer'])) {
            $payload['customerDetails'] = [
                'id' => $customer['card_customer']
            ];
        } else {
            // Provide name for new customer
            $name_parts = explode(' ', trim($reservation['customer_name']), 2);
            $payload['customerDetails'] = [
                'firstName' => $name_parts[0] ?? '',
                'lastName' => $name_parts[1] ?? ($name_parts[0] ?? '')
            ];
        }
    } else {
        // Guest reservation
        $name_parts = explode(' ', trim($reservation['customer_name']), 2);
        $payload['customerDetails'] = [
            'firstName' => $name_parts[0] ?? '',
            'lastName' => $name_parts[1] ?? ($name_parts[0] ?? '')
        ];
    }

    // Make API request to Ryft
    $api_url = $ryft_config['api_url'] . '/payment-sessions';
    $secret_key = $ryft_config['secret_key'];

    $headers = [
        'Authorization: ' . $secret_key,
        'Content-Type: application/json'
    ];

    if (!empty($ryft_config['account_id'])) {
        $headers[] = 'Account: ' . $ryft_config['account_id'];
    }

    $ch = curl_init($api_url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    if ($http_code !== 200) {
        error_log("Ryft API Error for reservation $reservation_id: HTTP $http_code - $response");
        return ['success' => false, 'message' => 'Payment service error'];
    }

    $result = json_decode($response, true);

    if (!isset($result['id']) || !isset($result['clientSecret'])) {
        error_log("Ryft invalid response for reservation $reservation_id: " . $response);
        return ['success' => false, 'message' => 'Invalid payment response'];
    }

    // Store payment intent ID in database
    $stmt = mysqli_prepare($db, "
        UPDATE reservations
        SET payment_intent_id = ?
        WHERE reservation_id = ?
    ");
    mysqli_stmt_bind_param($stmt, "si", $result['id'], $reservation_id);
    mysqli_stmt_execute($stmt);

    // Store in session
    $_SESSION['reservation_payment_intent'] = $result['id'];
    $_SESSION['reservation_payment_secret'] = $result['clientSecret'];

    return [
        'success' => true,
        'client_secret' => $result['clientSecret'],
        'payment_intent_id' => $result['id']
    ];
}
