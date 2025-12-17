# Online Ordering System - Development Progress

## 📋 Current Status: Session 25 - Table Reservations MVP

**Last Updated:** 2025-12-13
**Overall Progress:** ~99% Complete
**Current Phase:** Core features complete (Reservations system with deposits, email notifications, dashboard integration)

---

## ⚠️ BREAKING CHANGES

### Session 23: Deprecated Files Removed
**Date:** 2025-12-12

Multiple CSS, JS, and template files have been deleted as they were either unused or only referenced by the deprecated order-online.latte.

**Files DELETED:**

| File | Lines | Reason |
|------|-------|--------|
| `nmenu.css` | 1,122 | Not loaded in any template |
| `panel-styles.css` | 57 | Not loaded in any template |
| `options-toggle-styles.css` | 151 | Only used by deprecated order-online.latte |
| `overlay-styles.css` | 24 | Only used by deprecated order-online.latte |
| `layout-responsive.css` | 339 | Only used by deprecated order-online.latte |
| `product-availability.css` | 36 | Only used by deprecated order-online.latte |
| `options.js` | - | Replaced by product-modal.js |
| `scrollspy.js` | - | Only used by deprecated order-online.latte |
| `order-online.latte` | - | Deprecated - replaced by menu.latte |

**Files CLEANED (selectors removed):**

| File | Before | After | Removed |
|------|--------|-------|---------|
| `custom.css` | 260 | 211 | `.quantity-value`, `.option-item`, `.cart-count-badge`, `.cursor-pointer`, `.user-select-none` |
| `fonts.css` | 65 | 46 | `.font-heading`, `.font-body`, `.font-accent`, `.accordion-*` rules |
| `menu.css` | 1,164 | 1,057 | `.child-options`, `.variation-selector`, `.variation-btn*`, `slide-in-up` animation |

**Total Reduction:** 1,904 lines (52% of original CSS)

---

### Session 20: cart.js Notification System Change
**Date:** 2025-12-12

The `showNotification()` method in cart.js has been removed from some functions.

**Remove Toasts** - `cart.js`
- Delete line 53: `this.showNotification(...)` in `add()`
- Delete line 137: `this.showNotification(...)` in `addBogof()`
- Delete line 381: `this.showNotification(...)` in `enforceOfferRules()` (free_on_spend)
- Delete line 423: `this.showNotification(...)` in `enforceOfferRules()` (buy_x_get_free)
- Existing feedback sufficient: button flash, badge pulse, progress messages


---

### Session 20: delivery.js ProductModal Interception
**Date:** 2025-12-12

delivery.js now intercepts ProductModal methods (used by menu.latte) in addition to ProductOptions (used by order-online.latte).

**Added to delivery.js init():**
```javascript
if (typeof ProductModal !== 'undefined') {
    this.state.originalProductModalOpen = ProductModal.open.bind(ProductModal);
    ProductModal.open = (card) => {
        if (!this.canAddToCart({type: 'product_modal_open', card: card})) return false;
        return this.state.originalProductModalOpen(card);
    };
    this.state.originalProductModalQuickAdd = ProductModal.quickAdd.bind(ProductModal);
    ProductModal.quickAdd = (card) => {
        if (!this.canAddToCart({type: 'product_modal_quickadd', card: card})) return false;
        return this.state.originalProductModalQuickAdd(card);
    };
}
```

**menu.latte HTML additions:**
- Wrap methods column in `<div class="delivery-methods-section">`
- Add `<div id="postcodeDisplay" class="d-none mt-2 small"></div>`

---

### Session 19: delivery.js Rewrite & Script Load Order
**Date:** 2025-12-09

The delivery.js file has been completely rewritten with new initialization flow and pending action system.

**Script Load Order Changed in order-online.latte:**

**Before:**
```html
<script src="{$base_path}/assets/js/delivery.js"></script>
<script src="{$base_path}/assets/js/promo.js"></script>
<script src="{$base_path}/assets/js/options.js"></script>
```

**After:**
```html
<script src="{$base_path}/assets/js/options.js"></script>
<script src="{$base_path}/assets/js/delivery.js"></script>
<script src="{$base_path}/assets/js/promo.js"></script>
```

**Reason:** delivery.js now wraps `ProductOptions.showModal()` and `ProductOptions.showVariationsModal()`, so options.js must load first.

**Files Updated:**
| File | Change |
|------|--------|
| `delivery.js` | Complete rewrite - background validation, pending actions, postcode display |
| `order-online.latte` | Script load order changed (lines 466-468) |
| `checkout.latte` | Address selection logic, time slot fix, UX improvements |

---

### Session 18: products.json Structure Change
**Date:** 2025-12-08

The products.json structure has changed to support category descriptions.

**Before:**
```json
{
    "Pizza": [
        { "id": 1, "name": "Margherita", ... }
    ]
}
```

**After:**
```json
{
    "Pizza": {
        "description": "Hand-stretched dough, baked fresh to order",
        "products": [
            { "id": 1, "name": "Margherita", ... }
        ]
    }
}
```

**Migration:** Run `migrate_products.php` in the same directory as products.json to auto-convert.

**Files Updated:**
| File | Function | Change |
|------|----------|--------|
| products.php | `get_product_by_id()` | Loop variable `$data['products']` |
| products.php | `get_products_by_category()` | Return `['products']` |
| products.php | `get_products_for_display()` | Loop variable `$data['products']` |
| products.php | `get_products_with_availability()` | Loop variable + pass description |
| products.php | `get_featured_products_with_availability()` | Loop variable `$data['products']` |
| helpers.php | `find_product_by_id()` | Loop variable `$data['products']` |
| order-online.latte | Category loop | `$categoryData['products']` + description display |

---

## âœ… Completed Systems

### 1. Cart System âœ… (COMPLETE)
- [x] localStorage-based cart with JSON storage
- [x] Add/update/remove items
- [x] Options with nested parent-child relationships
- [x] Quantity controls (1-99 limit)
- [x] Price calculations with option adjustments
- [x] Desktop + mobile sync via storage events
- [x] Cart persists through refresh
- [x] Clear cart with SweetAlert2 confirmation
- [x] `cpn` field tracking for discountable products
- [x] Batch removal by product IDs (`removeByProductIds`)
- [x] `getPromoSubtotal()` - excludes free items from threshold calculations

### 2. Product Options System âœ… (COMPLETE)
- [x] Options modal with single/multiple selection
- [x] Conditional reveals (revealed_by)
- [x] Price adjustments per product-group
- [x] Quantity selectors for multi-select groups
- [x] Nested child options (view swap)
- [x] Variations support (parent â†’ variation â†’ options)
- [x] Validation with error highlighting
- [x] Smooth animations and transitions
- [x] BOGOF badge display in variations modal

### 3. Delivery System âœ… (COMPLETE - Enhanced Session 19)
- [x] Shop hours from JSON config
- [x] Holiday and special hours support
- [x] Overnight hours (endsNextDay)
- [x] Delivery windows by day/time
- [x] Collection vs delivery methods
- [x] Postcode validation with zones
- [x] Delivery fee calculation (base + per mile)
- [x] Free delivery threshold support
- [x] Minimum order enforcement (client + server)
- [x] Smart address handling for logged-in users
- [x] sessionStorage as source of truth for delivery data
- [x] Google Maps Distance Matrix API integration
- [x] Real distance/duration calculation for delivery validation
- [x] Postcode-to-coordinates lookup via Google Geocoding API
- [x] **Background validation on page load** (NEW - Session 19)
- [x] **Pending action system for add-to-cart during validation** (NEW - Session 19)
- [x] **Change postcode UI with "Change" link** (NEW - Session 19)
- [x] **Greyed-out buttons during validation** (NEW - Session 19)
- [x] **Auto-select method after validation** (NEW - Session 19)

### 4. Promo System âœ… (COMPLETE)
- [x] Auto-apply promos on page load
- [x] Manual code entry with validation
- [x] Percentage and fixed discounts
- [x] Free delivery (delivery_fee type)
- [x] Stackable vs non-stackable logic
- [x] Min order requirements
- [x] Max discount caps
- [x] Date range validation
- [x] Usage limits (global and per-customer)
- [x] First order only validation
- [x] One-time per customer validation
- [x] Tier requirements validation
- [x] Guest user validation (optimistic + server revalidation)
- [x] Method-specific promos (delivery-only, collection-only)
- [x] `cpn` field for discountable products
- [x] Discountable subtotal calculation
- [x] Live promo preview on order-online page
- [x] "Spend Â£X more" progress messages
- [x] Post-discount minimum order check
- [x] `stackableWithPoints` per-promo flag

### 5. Checkout System âœ… (COMPLETE - Enhanced Session 19)
- [x] Full checkout form with validation
- [x] Guest checkout
- [x] Registered user checkout
- [x] Existing email detection with login prompt
- [x] Order time selection (ASAP / scheduled)
- [x] Time slot generation (real, from delivery.json)
- [x] Dynamic ASAP ready time (method-dependent)
- [x] Scheduled time validation (past/insufficient prep time)
- [x] Tips (predefined + custom amounts)
- [x] Order notes
- [x] Server-side cart validation
- [x] Server-side price recalculation (anti-tampering)
- [x] Offer validation with specific error messages
- [x] enforceOfferRules() on checkout page load
- [x] **Prefilled customer details for logged-in users** (NEW - Session 19)
- [x] **"Hi [name], we've prefilled your details" greeting** (NEW - Session 19)
- [x] **Email field readonly for logged-in users** (NEW - Session 19)
- [x] **Address selection respects sessionStorage addressId** (NEW - Session 19)
- [x] **Custom postcode opens add address modal** (NEW - Session 19)
- [x] **Collapsible address list with "Show more"** (NEW - Session 19)
- [x] **Modal cancel reverts radio selection** (NEW - Session 19)

### 6. Payment Integration âœ… (COMPLETE)
- [x] Ryft payment integration
- [x] Card payments with secure form
- [x] Cash on delivery/collection
- [x] Payment page with order summary
- [x] Payment webhooks
- [x] Order confirmation page
- [x] Saved payment methods display/delete
- [x] Time correction on payment completion (handles delays)
- [x] Order time updated to payment time (not checkout time)

### 7. Email Notifications âœ… (COMPLETE)
- [x] PHPMailer with Amazon SES
- [x] Order confirmation email (customer)
- [x] New order alert (restaurant)
- [x] Password reset email
- [x] HTML templates with order details
- [x] BOGOF/FREE badges in email templates

### 8. Order System âœ… (COMPLETE)
- [x] Order creation with access tokens
- [x] Order products with structured options data
- [x] Order status tracking
- [x] Payment status separate from order status
- [x] Thank-you page with order details
- [x] Order linking for guest â†’ registered users
- [x] BOGOF/free item grouping in displays
- [x] `is_free`, `offer_id`, `linked_to_id` columns in order_products

### 9. Authentication System âœ… (COMPLETE)
- [x] Login with email/password
- [x] Registration with customer record creation
- [x] Logout with session destruction
- [x] Remember me tokens (30 days)
- [x] Auto-login from remember me cookie
- [x] Forgot password flow
- [x] Password reset with secure tokens (1hr expiry)
- [x] Profile update (name, phone)
- [x] Password change
- [x] CSRF protection on all forms
- [x] Session management with redirect after login
- [x] Link guest orders to account
- [x] Quick registration from thank-you page

### 10. Shop Availability âœ… (COMPLETE)
- [x] Check on checkout page load
- [x] Check before checkout submit
- [x] Payment page blocks if shop closed
- [x] Thank-you page shows warning if shop closed
- [x] `get_available_methods()` returns empty if closed
- [x] Consistent alert styling across pages

### 11. Customer Dashboard âœ… (COMPLETE)
- [x] Dashboard index (welcome, quick stats, recent orders)
- [x] Order history page (list with status badges)
- [x] Order details view (single order, reorder button)
- [x] Profile page (edit name, phone, password)
- [x] Address management (list, add, edit, delete, set default)
- [x] Saved payment methods display and delete
- [x] Loyalty points overview
- [x] Tier progress display
- [x] BOGOF/FREE badges on order details

### 12. Loyalty System âœ… (COMPLETE)
- [x] Points earning on order completion (cash + card)
- [x] Point calculation with tier multipliers
- [x] Bonus multiplier support (e.g. double points week)
- [x] Tier upgrades based on total_spent
- [x] Auto-check tier on dashboard visit
- [x] Display points balance in dashboard
- [x] Points transaction history
- [x] Redeem points at checkout (slider UI)
- [x] Swal choice when points conflict with promos
- [x] Per-promo `stackableWithPoints` flag
- [x] Global `stackableWithPromos` fallback
- [x] Restore promos option after using points
- [x] Customer totals tracking (regardless of loyalty on/off)
- [x] Backend validation for redemption

### 13. Timed Products âœ… (COMPLETE)
- [x] Product availability windows (days, times, dayTimes)
- [x] Days-only restriction (e.g., weekends only)
- [x] Times-only restriction (e.g., 11am-2pm daily)
- [x] Days + times combined (e.g., Mon-Fri 8am-11am)
- [x] DayTimes overrides (e.g., different hours Sat vs Sun)
- [x] Greyed-out UI for unavailable products
- [x] "Available [time/days]" badge display
- [x] Server-side availability check in cart validation
- [x] Auto-remove unavailable items at checkout
- [x] Filtered from free offers carousel

### 14. Featured Products âœ… (COMPLETE)
- [x] `featured: true` flag on products
- [x] Featured category appears first in navigation
- [x] Featured products show in original category AND Featured section
- [x] Star icon on Featured nav link
- [x] Featured badge on product cards

### 15. Cart Security âœ… (COMPLETE)
- [x] Server-side price recalculation (prevents price manipulation)
- [x] Quantity sanitization (1-99, silently capped)
- [x] Product name from server (not trusted from client)
- [x] Option group validation (must belong to product)
- [x] Invalid options silently skipped
- [x] Stock check on validation
- [x] Timed availability check on validation
- [x] Minimum order server-side enforcement
- [x] Structured error responses for frontend handling
- [x] Free item claims verified server-side

### 16. Free Food Offers System âœ… (COMPLETE)
- [x] Feature flag in site.json (`features.offers`)
- [x] offers.json configuration file
- [x] Helper functions in helpers.php

**Free on Spend Offers:**
- [x] Carousel display at top of order-online page
- [x] Lock/unlock states based on spend threshold
- [x] "Added to cart" state after claiming
- [x] Multiple eligible products support
- [x] Max quantity per offer enforcement
- [x] Auto-remove from cart when below threshold
- [x] Compact free item display in cart (info/blue styling)
- [x] Trash button available for user removal
- [x] Timed/option products filtered from eligibility

**BOGOF (Buy One Get One Free):**
- [x] Badge on product cards
- [x] Badge supports variation products
- [x] Badge in variations modal per variation
- [x] Cart.addBogof() - adds paid + free pair
- [x] Quantity stacking (same item increments both)
- [x] Free qty auto-syncs to paid qty
- [x] Linked removal (remove paid â†’ removes free)
- [x] Compact free item display in cart (success/green styling)
- [x] No trash button on BOGOF free items
- [x] Disabled quantity controls on free items
- [x] Cart.add intercepted to auto-trigger BOGOF

**Progress Messages:**
- [x] "Spend Â£X more for..." progress messages
- [x] "Unlocked! Choose X more" messages
- [x] Auto-generated from offer config (name, maxQuantity)
- [x] Display in cart sidebar

**Info Bar (order-online):**
- [x] Delivery fee info ("Delivery from Â£X" or "Free Delivery")
- [x] Minimum order badge
- [x] Active offer badges (BOGOF, Free on Spend)
- [x] Auto-apply promo badges
- [x] Only shows delivery info if currently available

**Server-Side Validation:**
- [x] validate_cart_offers() wrapper function
- [x] validate_offer_for_checkout() per offer type
- [x] Validates free item claims (not trusted from client)
- [x] Checks offer still active and within date range
- [x] Checks product eligibility for offer
- [x] Checks spend threshold met (free_on_spend)
- [x] Checks paid item exists with cart_key link (BOGOF)
- [x] Checks quantity match - free â‰¤ paid (BOGOF)
- [x] Checks max quantity per offer
- [x] Rejects manipulation attempts with clear error
- [x] enforceOfferRules() corrects cart after rejection
- [x] Free items set to Â£0 in validated cart
- [x] Free items excluded from subtotal calculation

**Checkout Integration:**
- [x] SITE_FEATURES and ACTIVE_OFFERS constants on checkout
- [x] enforceOfferRules() runs on checkout page load
- [x] offer_error type handled in submitCheckout
- [x] Cart corrected and re-rendered after offer error

### 17. BOGOF/Free Item Display âœ… (COMPLETE - Session 17)
- [x] Database columns: `is_free`, `offer_id`, `linked_to_id` on order_products
- [x] Two-pass order insert (paid items first, free items with linked_to_id)
- [x] `group_order_products_for_display()` function in order.php
- [x] BOGOF pairs grouped with combined quantity display
- [x] [BOGOF] badge on payment page
- [x] [BOGOF] badge on checkout sidebar
- [x] [BOGOF] badge on thank-you page
- [x] [BOGOF] badge on order details (dashboard)
- [x] [BOGOF]/[FREE] badges in confirmation emails
- [x] Identical free items grouped (free_on_spend)

### 18. Time Slot System âœ… (COMPLETE - Session 17)
- [x] Real time slots from `get_available_timeslots()` backend
- [x] `/checkout/get-timeslots` API endpoint
- [x] Method-dependent ready times (delivery vs collection)
- [x] Dynamic ASAP text ("Ready in X mins" from config)
- [x] 15-minute slot intervals
- [x] Slots start from now + readyInMinutes, rounded to quarter hour
- [x] Slots end at window close - readyInMinutes
- [x] Overnight window support
- [x] Scheduled time validation on submit (past/insufficient prep)
- [x] `scheduled_time_invalid` error type with slot reload
- [x] Payment page time correction (handles user delays)
- [x] Order time updated to payment completion time

### 19. Category Descriptions âœ… (COMPLETE - Session 18)
- [x] products.json restructured with description field per category
- [x] Migration script (`migrate_products.php`) for existing installations
- [x] Description displayed under category headers on order-online page
- [x] All product functions updated to handle new structure
- [x] Backwards-incompatible change documented

### 20. Google Maps Integration âœ… (COMPLETE - Session 18)
- [x] Google Maps Distance Matrix API for delivery validation
- [x] Google Geocoding API for postcode-to-coordinates
- [x] Real distance calculation (miles) for delivery zones
- [x] Real duration calculation for delivery estimates
- [x] Delivery fee calculation based on actual distance
- [x] Max radius enforcement with accurate distance checking

### 21. Delivery Flow Improvements âœ… (COMPLETE - Session 19)
- [x] Background postcode validation on page load
- [x] Validates sessionStorage postcode OR first saved address
- [x] Auto-selects delivery method after successful validation
- [x] Collection method restored from sessionStorage
- [x] Pending action system queues add-to-cart during validation
- [x] Supports `cart_add`, `show_options`, `show_variations` action types
- [x] Options/variations modal opens AFTER validation (not before)
- [x] "Change" link shows validated postcode with delivery fee
- [x] Buttons greyed out during background validation
- [x] Wraps `Cart.add`, `ProductOptions.showModal`, `ProductOptions.showVariationsModal`

### 22. Checkout Address UX âœ… (COMPLETE - Session 19)
- [x] Address selection respects `sessionStorage.postcode_data.addressId`
- [x] Falls back to matching postcode if no addressId
- [x] Custom postcode (no matching saved address) opens add address modal
- [x] Collapsible address list - selected address shown first
- [x] "Show X other addresses" toggle for multiple addresses
- [x] "Add new address" always visible at bottom
- [x] Modal cancel reverts radio to previous selection
- [x] Tracks `previousSelectedAddress` state to enable revert
- [x] Logged-in user greeting: "Hi [name], we've prefilled your details"
- [x] Email field readonly with lock icon for logged-in users
- [x] `firstWord` Latte filter for greeting (optional)


### 23. Responsive Notifications ✅ (COMPLETE - Session 20)
- [x] `showNotification()` rewritten for responsive behaviour
- [x] Desktop: Top-right Bootstrap toasts (unchanged)
- [x] Mobile: Bottom snackbar (Material Design style)
- [x] Snackbar slides up from bottom, sits above cart bar
- [x] Cart bar pulse animation on success (green flash)
- [x] Badge bounce animation on cart count
- [x] `options.skipPulse` flag to suppress cart bar animation
- [x] Auto-dismiss after 2.5s (snackbar) / 3s (toast)
- [x] Colour variants: success (green), warning (amber), error (red), info (blue)

### 24. Cart Quantity Selector Redesign ✅ (COMPLETE - Session 20)
- [x] Removed standalone trash button from regular items
- [x] Dynamic minus button: trash icon when qty=1, minus icon when qty>1
- [x] New layout: Name → Options → Price + Quantity selector on same line
- [x] Matches modal quantity selector styling
- [x] Free items keep dedicated trash button (free_on_spend only)
- [x] `.qty-trash` class for red styling when showing trash icon

### 25. Product Modal Child View Animations ✅ (COMPLETE - Session 20)
- [x] Smooth slide/fade animation entering child view
- [x] Smooth slide/fade animation exiting child view
- [x] Auto-scroll to next section within child view
- [x] `autoScrollToNextRequiredChild()` method for child context
- [x] Confirm button scrolls to next unsatisfied section in main view
- [x] Context-aware scroll in `handleSingleSelect` and `handleMultipleSelect`

### 26. Cart Upsells Feature ✅ (COMPLETE - Session 21)
- [x] Feature flag in site.json (`features.upsells`)
- [x] `upsells.json` configuration file
- [x] Simple products only (no options, no variations)
- [x] Server-side filtering via `get_product_by_id()`
- [x] Renders as sibling to `#cart-items` inside scrollable body
- [x] Hides products already in cart
- [x] Hides section when cart empty or all upsells added
- [x] Threshold algorithm checks autoPromos for next minOrder
- [x] Calculates net cost (product price minus discount gained)
- [x] "FREE + save £X" when discount exceeds product price
- [x] Sorting: threshold-unlockers first, then by price
- [x] Quick-add button with check icon feedback

### 27. UX Polish ✅ (COMPLETE - Session 22)
- [x] Removed redundant toast notifications from cart.js
- [x] `scrollToBottom()` method for cart sidebar after add
- [x] Category header sparkle animation on nav click
- [x] `.menu-category-header.sparkle` with title-flash keyframes

### 28. CSS Cleanup ✅ (COMPLETE - Session 23)
- [x] Deleted 6 unused CSS files (1,729 lines)
- [x] Deleted 2 unused JS files (options.js, scrollspy.js)
- [x] Deleted deprecated order-online.latte template
- [x] Cleaned unused selectors from custom.css, fonts.css, menu.css
- [x] Total reduction: 1,904 lines (52% of original CSS)

### 29. Site Builder Light ✅ (COMPLETE - Session 24)
- [x] JSON-based homepage configuration system
- [x] 3 preset layouts (Classic, Minimal, Bold)
- [x] Dynamic rendering engine in home.latte
- [x] 5 component types (hero, columns, cta, featured_products, text_block)
- [x] 4 column types (icon_text, text, image, stat)
- [x] Bootstrap 5 grid system integration
- [x] Row management (add, remove, reorder, toggle)
- [x] Theme CSS variables from theme.json
- [x] Global color customization
- [x] Manual JSON editing (API integration deferred to v2)
- [x] Complete documentation (HOMEPAGE-BUILDER-README.md)

### 30. Table Reservations System ✅ (COMPLETE - Session 25)
- [x] Feature flag in site.json (`features.reservations`)
- [x] reservations.json configuration file (capacity, deposits, cancellation, etc.)
- [x] Database table: reservations (14 columns with secure token)
- [x] 5-step booking flow (Date → Time → Party Size → Details → Confirmation)
- [x] Integration with hours.json for availability
- [x] Conditional deposit system (party size threshold, busy times)
- [x] Ryft payment integration for deposits
- [x] Saved payment methods support for deposits
- [x] Token-based secure URLs (32-char hex tokens)
- [x] Email confirmations with reservation details
- [x] Email reminders (24h before reservation)
- [x] Email cancellation notifications
- [x] Loyalty points integration (10% of deposit on completion)
- [x] Customer dashboard page (/account/reservations)
- [x] Upcoming/past reservation views
- [x] "Add to Calendar" functionality for future reservations
- [x] Special requests field with suggestions
- [x] DD/MM/YYYY date format with Flatpickr
- [x] Smooth auto-scrolling between steps
- [x] Mobile-responsive booking flow
- [x] Navigation link with conditional display

---

## ðŸ”¶ DEFERRED FEATURES

### Buy X Get Free Offers
- [ ] Cart logic exists but untested
- [ ] Auto-add cheapest qualifying item
- [ ] Progress messages
- **Reason:** Two offer types (BOGOF + Free on Spend) sufficient with promo codes and loyalty

### Stamp Cards
- [ ] Buy X get 1 free (product-based)
- [ ] Value-based stamps
- [ ] Dashboard display
- **Reason:** May implement later, loyalty points cover main use case

### Loyalty Refunds
- [ ] `refund_loyalty_points($order_id)` - function exists, needs hook
- [ ] When order cancelled â†’ return redeemed points, remove earned points
- **Reason:** Needs desktop client integration

---

## ðŸ”´ NOT STARTED

### Admin Features
- [ ] Theme editor (colours, logo, images)
- [ ] Product management via web
- [ ] Promo code management via web
- [ ] Order management dashboard
- [ ] Stock toggle via web

### Setup Wizard
- [ ] Multi-step installation
- [ ] Database setup
- [ ] Config generator
- [ ] First admin creation

### Other
- [ ] SMS notifications (Twilio/AWS SNS)
- [ ] Uber Direct integration
- [ ] EngineMailer integration
- [ ] Reservation cancellation via customer (currently phone-only)
- [ ] Reservation modification (currently must cancel + rebook)

---

## ðŸ“ FILES UPDATED - Session 17

### Database Changes
```sql
ALTER TABLE `order_products` 
ADD COLUMN `is_free` TINYINT(1) DEFAULT 0,
ADD COLUMN `offer_id` VARCHAR(50) DEFAULT NULL,
ADD COLUMN `linked_to_id` INT(11) DEFAULT NULL;
```

### Modified Files
| File | Changes |
|------|---------|
| `checkout.php` | Two-pass order product insert (paid first, free with linked_to_id), scheduled time validation (past/insufficient prep), error_type in validation response |
| `order.php` | Added `group_order_products_for_display()` function for BOGOF/free grouping |
| `dashboard.php` | Updated order details query with grouping columns, applied grouping wrapper |
| `router.php` | Added `/checkout/get-timeslots` endpoint, added `$ready_times` to checkout route, applied grouping on thank-you page |
| `ryft_functions.php` | Updated `complete_ryft_payment()` - order_time set to payment time, scheduled time recalculated if invalid |
| `email_functions.php` | Applied `group_order_products_for_display()` in 3 email functions |
| `checkout.latte` | Real time slots API call, dynamic ASAP ready time, `updateAsapReadyTime()` method, `scheduled_time_invalid` error handler |
| `payment.latte` | BOGOF/FREE badges in product display |
| `thank-you.latte` | BOGOF/FREE badges in product display |
| `order-details.latte` | BOGOF/FREE badges in product display |
| `order-confirmation.latte` | Inline-styled BOGOF/FREE badges for email |

---

## ðŸ“ FILES UPDATED - Session 18

### Modified Files
| File | Changes |
|------|---------|
| `products.json` | Structure changed: categories now objects with `description` and `products` keys |
| `products.php` | Updated `get_product_by_id()`, `get_products_by_category()`, `get_products_for_display()`, `get_products_with_availability()`, `get_featured_products_with_availability()` |
| `helpers.php` | Updated `find_product_by_id()` |
| `order-online.latte` | Category loop updated, description display added |

### New Files
| File | Purpose |
|------|---------|
| `migrate_products.php` | Migration script to convert products.json to new structure |

---

## ðŸ“ FILES UPDATED - Session 19

### Modified Files
| File | Changes |
|------|---------|
| `delivery.js` | **Complete rewrite:** background validation on page load, pending action system (`cart_add`, `show_options`, `show_variations`), wraps Cart.add and ProductOptions methods, `updatePostcodeDisplay()` with "Change" link, `setButtonsLoading()` for greyed-out state, `initializeMethodSelection()` respects sessionStorage |
| `order-online.latte` | Script load order changed: options.js before delivery.js (lines 466-468) |
| `checkout.latte` | Multiple changes - see detailed list below |

### checkout.latte Changes (Session 19)
| Location | Change |
|----------|--------|
| Line 1022 | Removed auto-check of first address in `renderSavedAddresses()` |
| Lines 916-959 | New `initAddressHandling()` logic: respects `addressId` from sessionStorage, matches postcode, opens modal for custom postcodes |
| Lines 1007-1050 | New `renderSavedAddresses()`: collapsible list, selected address first, "Show X other addresses" toggle |
| After line 1050 | New `renderAddressOption()` helper method |
| After line 1050 | New `toggleOtherAddresses()` method |
| Line 695 (state) | Added `previousSelectedAddress: null` |
| Lines 1052+ | Updated `handleAddressRadioChange()`: stores previous selection before opening modal |
| Lines 983+ | Updated `initAddressModal()`: reverts radio on modal close without save |
| Lines 203-207 | Added logged-in greeting: "Hi [name], we've prefilled your details" |
| Lines 215-220 | Email field readonly with lock icon for logged-in users |
| Line 1727 | Fixed case sensitivity: `timeASAP` â†’ `timeAsap` |

### router.php Changes (Session 19)
| Location | Change |
|----------|--------|
| Around line 958 | Add `firstWord` Latte filter (optional - for greeting) |

### Latte Filter (Optional)
Add to router.php before render call:
```php
$latte->addFilter('firstWord', function ($str) {
    return explode(' ', trim($str ?? ''))[0];
});
```

---

## ðŸ›¡ï¸ SECURITY NOTES

### Offer System Security
- Free items validated server-side, never trusted from client
- `is_free` flag verified against actual offer eligibility
- Manipulated carts rejected with specific error message
- enforceOfferRules() corrects cart after rejection
- Products not in eligibleProducts array charged full price
- BOGOF requires matching paid item with cart_key link
- Quantity manipulation detected (free > paid) and rejected
- Fake offer_id values result in "Offer not found" error

### Time Slot Security (NEW - Session 17)
- Scheduled times validated server-side before order creation
- Past times rejected with "Selected time has passed"
- Times with insufficient prep time rejected
- Payment completion recalculates if scheduled time no longer valid
- Order time reflects actual payment time (prevents false delay claims)

### Existing Security
- Server-side price recalculation (can't send fake prices)
- CSRF protection on all forms
- Session-based authentication
- Postcode validation server-side
- Promo code validation server-side
- Access tokens for order viewing (64 char random)

---

## ðŸ“ CONFIGURATION REFERENCE

### site.json features
```json
{
  "features": {
    "offers": true,
    "loyalty": true,
    "stamp_cards": false,
    "favorites": true,
    "scheduling": true,
    "tips": true,
    "upsells": true
  }
}
```

### upsells.json structure
```json
{
  "products": [101, 102, 103],
  "maxDisplay": 3,
  "title": "Add to your order"
}
```

### offers.json structure
```json
{
  "offers": [
    {
      "id": "bogof_burger",
      "type": "bogof",
      "name": "2 for 1 Burgers",
      "description": "Buy one get one free on selected burgers",
      "badge": "2 FOR 1",
      "products": [1, 2, 3],
      "active": true,
      "validFrom": "2025-01-01 00:00:00",
      "validUntil": "2025-12-31 23:59:59"
    },
    {
      "id": "free_side_25",
      "type": "free_on_spend",
      "name": "Free Side",
      "description": "Spend Â£25 and choose a free side",
      "minSpend": 25,
      "eligibleProducts": [100, 101, 102],
      "maxQuantity": 2,
      "active": true,
      "validFrom": "2025-01-01 00:00:00",
      "validUntil": "2025-12-31 23:59:59"
    }
  ]
}
```

### Offer Types
| Type | Trigger | Behaviour |
|------|---------|-----------|
| `bogof` | Add qualifying product | Auto-add free duplicate (paid+free pair) |
| `free_on_spend` | Reach minSpend threshold | Unlock carousel, user chooses free item |
| `buy_x_get_free` | Buy X qualifying items | Auto-add cheapest free (DEFERRED) |

### Eligibility Rules
- Products with `options` array excluded from free_on_spend
- Products with `stock: 0` excluded
- Timed products outside availability excluded
- Variations work for BOGOF (badge shows if any variation qualifies)

---

## ðŸŽ¯ NEXT PRIORITIES

### Priority 1: Testing & Polish
- [x] Full order flow test with BOGOF offer
- [x] Full order flow test with free_on_spend offer
- [x] Checkout cart display for free items (match sidebar styling)
- [x] Order confirmation/receipt showing free items correctly
- [ ] Desktop client compatibility check (Â£0 line items)

### Priority 2: Nice-to-Have
- [ ] Buy X Get Free testing (if needed later)
- [ ] Payment trust signals / card icons on checkout

### Priority 3: Admin Features
- [ ] Order management interface
- [ ] Product stock management
- [ ] Theme editor

---

## ðŸ’¡ Key Architectural Decisions

### Why localStorage for Cart?
- Zero server load during browsing
- Instant updates, survives refresh
- 70 concurrent users = no impact on shared hosting

### Why JSON for Configs?
- Edit without database migrations
- In-memory processing faster than SQL
- Copy to new sites instantly

### Why Token-Based Order Access?
- 64-char tokens prevent URL guessing
- Guest-friendly, no login required
- Shareable email links

### Why Unified Email Sender?
- One SES identity for unlimited restaurants
- Zero per-restaurant config needed
- Shop name shows in email clients

### Why Separate payment_status?
- Order workflow separate from payment state
- Easy to query pending payments
- Track refund lifecycle independently

### Why cpn for Discountable Products?
- Some products excluded from discounts
- Restaurant controls what's discountable
- Server-side authority (not trusted from client)

### Why Points on Processing (not Acceptance)?
- Cash orders go straight to processing
- Card orders hit processing after payment confirmed
- Simpler than waiting for desktop client "accept" action
- Refund function exists for cancellations

### Why Server-Side Cart Validation?
- localStorage is client-controlled (untrusted)
- Prevents price manipulation attacks
- Enforces stock, availability, minimum order
- Single source of truth for order totals

### Why Timed Products at Product Level?
- More flexible than category-level restrictions
- Same product can have different availability (variations)
- Follows Deliveroo/UberEats patterns
- Greyed-out UI better than hiding (shows what's coming)

### Why Order Time = Payment Time? (NEW)
- Checkout time is misleading if user delays payment
- Restaurant needs accurate prep time calculation
- Prevents false complaints about slow service
- Email/receipt shows when order was truly confirmed

### Why Category Descriptions in products.json? (NEW - Session 18)
- Single source of truth for menu structure
- No separate config file to match categories
- Description displays directly on order-online page
- Migration script provided for existing installations

### Why Background Validation on Page Load? (NEW - Session 19)
- No delay on first add-to-cart (validation already done)
- User sees immediately which postcode is active
- "Change" link available from the start
- Catches stale/invalid postcodes early
- Pending action system handles edge cases

### Why Wrap ProductOptions Methods? (NEW - Session 19)
- Validation check happens BEFORE options modal opens
- User doesn't waste time configuring options for invalid delivery
- Consistent flow for simple products and products with options
- Single point of validation for all add-to-cart paths

### Why JSON-Based Homepage Builder? (NEW - Session 24)
- Manual editing now, API integration later (v2 admin dashboard)
- No database needed for layout storage
- Version control friendly (Git tracks changes)
- Easy to backup/restore/duplicate across sites
- Bootstrap 5 grid system = responsive by default
- Component-based architecture = reusable patterns
- Preset layouts = quick start for new sites
- Future-proof for centralized admin API

---

## ðŸ“– Product Availability Reference

### JSON Structure
```json
{
    "id": 1,
    "name": "Breakfast Special",
    "price": "8.95",
    "featured": true,
    "availability": {
        "days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "times": {"start": "08:00", "end": "11:30"},
        "dayTimes": [
            {"day": "Sat", "start": "09:00", "end": "14:00"}
        ]
    }
}
```

### Rules
| Config | Meaning |
|--------|---------|
| No `availability` | Always available |
| `days` only | All day on those days |
| `times` only | Those times every day |
| `days` + `times` | Those times on those days |
| `dayTimes` | Specific day+time overrides (checked first) |

### Day Format
Must use: `Mon`, `Tue`, `Wed`, `Thu`, `Fri`, `Sat`, `Sun` (capitalised)

---

## ðŸ“– NOTES & REMINDERS

- **Promo codes are case-insensitive** (auto-uppercased)
- **Non-stackable means ALONE** (no other promos allowed)
- **stackableWithPoints per-promo** overrides global `stackableWithPromos`
- **Free options always stay free** (price adjustments don't make them paid)
- **Server-side validation is final** (client cart is recalculated)
- **Guest orders link to user after login** (via email matching)
- **Loyalty points awarded on processing status** (cash immediate, card after payment)
- **Loyalty refund needs desktop client hook** (function ready: `refund_loyalty_points()`)
- **Customer totals tracked always** (regardless of loyalty feature on/off)
- **Tier auto-checks on dashboard visit** (self-corrects after migrations)
- **Desktop client API untouched** (backward compatibility)
- **Cart persists until thank-you page** (for order confirmation)
- **Access tokens are 64 chars** (random_bytes(32))
- **Payment intent stored as pi_temp_[id]** (reuses payment_method field)
- **Email reply-to** (restaurant's actual email)
- **cpn:1 means discountable** (default if missing)
- **methods field in promos** (null = all methods)
- **sessionStorage is source of truth** for delivery fee
- **Availability days must be capitalised** (Mon, Tue, Wed, Thu, Fri, Sat, Sun)
- **Empty availability = always available** (no restriction)
- **Timed products honoured after payment started** (don't block mid-payment)
- **Minimum order checked server-side** (can't bypass via direct URL)

### Offers System
- **Simple products only** for free_on_spend (no options/variations)
- **BOGOF works with all products** including variations with options
- **Free items have cpn: 0** (excluded from promo calculations)
- **Quantity sync is automatic** - change paid qty, free follows
- **Linked removal** - remove paid BOGOF item, free auto-removes
- **Progress messages auto-generate** from offer name and maxQuantity
- **Info bar only shows delivery** if delivery method currently available

### Time Slots (NEW - Session 17)
- **Real slots from backend** - not generated client-side
- **Method-dependent ready times** - delivery vs collection from delivery.json
- **Scheduled time validated twice** - on checkout submit AND payment completion
- **Order time = payment time** - not checkout submission time
- **Stale times auto-corrected** - switched to ASAP if scheduled time invalid

### Category Descriptions (NEW - Session 18)
- **products.json structure changed** - categories are now objects not arrays
- **Migration required** - run migrate_products.php for existing sites
- **Description is optional** - empty string if not set
- **Displayed on order-online page** - under category headers

### Delivery Flow (NEW - Session 19)
- **Background validation on page load** - no delay on first add-to-cart
- **sessionStorage.postcode_data.addressId** - tracks which saved address was selected
- **Pending actions queued** - processed after validation completes
- **Options modal opens AFTER validation** - not before
- **Script load order matters** - options.js must load before delivery.js
- **Buttons greyed during validation** - prevents race conditions
- **"Change" link always visible** - when delivery selected with valid postcode

### Checkout Address UX (NEW - Session 19)
- **Address selection from sessionStorage** - respects user's choice from order-online
- **Custom postcode triggers modal** - for addresses not in saved list
- **Collapsible address list** - reduces clutter for users with many addresses
- **Modal cancel reverts selection** - prevents "Add new" staying selected
- **Email readonly for logged-in** - prevents confusion about account email
- **Greeting shows first name only** - using `firstWord` filter

### Responsive Notifications (NEW - Session 20)
- **Mobile snackbar** - Removed from few functions

### Upsells System (NEW - Session 21)
- **Simple products only** - no options/variations in upsells
- **Threshold algorithm** - checks autoPromos for discount opportunities
- **Net cost display** - shows actual cost after discount unlock
- **"FREE + save £X"** - when discount exceeds product price
- **Smart sorting** - threshold-unlockers first, then by price

---

## 📁 FILES UPDATED - Session 20

### Modified Files
| File | Changes |
|------|---------|
| `cart.js` | Notification system rewrite: `showNotification()` → `showSnackbar()`, `showToast()`, `pulseCartBar()` methods; quantity selector redesign (lines 506-578) |
| `delivery.js` | Added ProductModal interception (`product_modal_open`, `product_modal_quickadd` action types); state properties for originalProductModalOpen/QuickAdd |
| `product-modal.js` | Child view animations (openChildView, confirmChildView, cancelChildView); `autoScrollToNextRequiredChild()` method; context-aware scroll in selection handlers |
| `menu.latte` | Added `.delivery-methods-section` wrapper; added `#postcodeDisplay` div |
| `menu.css` | Added snackbar styles, cart-bar-pulse animation, badge-bounce animation, cart-qty-selector styles |

---

## 📁 FILES UPDATED - Session 21

### New Files
| File | Purpose |
|------|---------|
| `upsells.json` | Configuration for upsell products |
| `upsells.js` | Client-side upsell logic, filtering, sorting, threshold calculation |
| `upsells.css` | Upsell section and card styles |
| `upsell-card.latte` | Server-rendered upsell card component |

### Modified Files
| File | Changes |
|------|---------|
| `site.json` | Added `features.upsells` flag |
| `menu.latte` | Integrated upsell section into cart sidebar body |
| `router.php` | Added upsell data loading and passing to template |

---

## 📁 FILES UPDATED - Session 22

### Modified Files
| File | Changes |
|------|---------|
| `cart.js` | Removed 4 `showNotification()` calls (lines 53, 137, 381, 423); added `scrollToBottom()` method |
| `menu.css` | Added `.menu-category-header.sparkle` and `@keyframes title-flash` |
| `menu.latte` | Added sparkle trigger after scroll timeout (~line 460) |

---

## 📁 FILES UPDATED - Session 24

### New Files (Site Builder Light)
| File | Purpose |
|------|---------|
| `config/homepage.json` | Active homepage configuration (JSON-based page builder) |
| `config/homepage-presets/layout-classic.json` | Preset 1: Hero + Features + Products + CTA |
| `config/homepage-presets/layout-minimal.json` | Preset 2: Text-focused, clean design |
| `config/homepage-presets/layout-bold.json` | Preset 3: Full-screen hero + stats |
| `config/HOMEPAGE-BUILDER-README.md` | Complete documentation for homepage builder |

### Modified Files (Site Builder Light)
| File | Changes |
|------|---------|
| `core/functions/router.php` | Load `homepage.json` and `featured_products` for homepage route (lines 26-31) |
| `core/templates/pages/home.latte` | Complete rewrite - dynamic rendering engine with 5 component types |
| `core/templates/layouts/main.latte` | Added theme CSS variables injection (lines 15-49) |

---

## 📁 FILES UPDATED - Session 23

### Deleted Files (CSS)
| File | Lines |
|------|-------|
| `nmenu.css` | 1,122 |
| `panel-styles.css` | 57 |
| `options-toggle-styles.css` | 151 |
| `overlay-styles.css` | 24 |
| `layout-responsive.css` | 339 |
| `product-availability.css` | 36 |

### Deleted Files (JS)
| File | Reason |
|------|--------|
| `options.js` | Replaced by product-modal.js |
| `scrollspy.js` | Only used by deprecated order-online.latte |

### Deleted Templates
| File | Reason |
|------|--------|
| `order-online.latte` | Deprecated - replaced by menu.latte |

### Cleaned Files
| File | Removed Selectors |
|------|-------------------|
| `custom.css` | `.quantity-value`, `.option-item`, `.cart-count-badge`, `.cursor-pointer`, `.user-select-none` |
| `fonts.css` | `.font-heading`, `.font-body`, `.font-accent`, `.accordion-*` |
| `menu.css` | `.child-options`, `.variation-selector`, `.variation-btn*`, `slide-in-up` |

---

**Session 23 Complete:** Major codebase cleanup removing 1,904 lines of deprecated CSS/JS (52% reduction). order-online.latte fully deprecated in favour of menu.latte with ProductModal system.

---

## 📁 FILES UPDATED - Session 25

### New Files (Table Reservations)
| File | Purpose |
|------|---------|
| `config/reservations.json` | Reservation system configuration (capacity, deposits, cancellation rules) |
| `config/RESERVATIONS-README.md` | Complete documentation for reservation system |
| `config/RESERVATIONS-SECURITY-UPDATE.md` | Security update documentation (token-based access) |
| `add_reservation_token.sql` | Database migration script for token column |
| `core/functions/reservations.php` | All reservation backend logic (15 functions) |
| `core/templates/pages/reservations.latte` | Public booking page (5-step flow) |
| `core/templates/pages/reservation-payment.latte` | Deposit payment page (Ryft integration) |
| `core/templates/pages/reservation-confirmation.latte` | Confirmation page with calendar export |
| `core/templates/dashboard/reservations.latte` | Customer dashboard reservations page |
| `core/templates/emails/reservation-confirmation.latte` | Confirmation email template |
| `core/templates/emails/reservation-reminder.latte` | 24h reminder email template |
| `core/templates/emails/reservation-cancellation.latte` | Cancellation email template |
| `public/assets/js/reservations.js` | Main booking flow JavaScript (447 lines) |
| `public/assets/js/reservation-payment.js` | Deposit payment handler (195 lines) |

### Modified Files (Table Reservations)
| File | Changes |
|------|---------|
| `core/functions/router.php` | Added 10 reservation routes (booking, payment, confirmation, calendar, API endpoints, dashboard) |
| `core/functions/dashboard.php` | Added 4 functions: `get_customer_reservations()`, `get_reservation_badge_class()`, `get_reservation_status_text()`, `can_add_to_calendar()` |
| `core/functions/email_functions.php` | Added `firstWord` Latte filter for personalized greetings |
| `core/templates/layouts/main.latte` | Added "Book a Table" navigation link (conditional on feature flag) |
| `core/templates/dashboard/layout.latte` | Added "Reservations" sidebar link (conditional on feature flag) |
| `config/site.json` | Added `features.reservations: true` flag |

### Database Changes (Table Reservations)
```sql
CREATE TABLE `reservations` (
  `reservation_id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_id` int(11) DEFAULT NULL,
  `customer_type` char(1) DEFAULT 'R',
  `customer_name` varchar(100) NOT NULL,
  `customer_email` varchar(100) NOT NULL,
  `customer_phone` varchar(20) NOT NULL,
  `reservation_date` date NOT NULL,
  `reservation_time` time NOT NULL,
  `party_size` int(11) NOT NULL,
  `special_requests` text,
  `deposit_required` tinyint(1) DEFAULT 0,
  `deposit_amount` decimal(10,2) DEFAULT 0.00,
  `deposit_paid` tinyint(1) DEFAULT 0,
  `status` enum('pending','confirmed','completed','cancelled','no_show') DEFAULT 'pending',
  `token` varchar(32) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`reservation_id`),
  KEY `idx_customer` (`customer_id`,`customer_type`),
  KEY `idx_date` (`reservation_date`),
  KEY `idx_token` (`token`)
);
```

---

## 📖 Reservation System Reference

### Configuration (reservations.json)
```json
{
  "capacity": {
    "max_covers_per_slot": 30,
    "slot_interval_minutes": 30,
    "warning_threshold": 0.8
  },
  "booking_window": {
    "min_hours_advance": 2,
    "max_days_advance": 60
  },
  "cancellation": {
    "allowed": true,
    "min_hours_before": 24,
    "refund_deposit": true
  },
  "deposits": {
    "enabled": true,
    "mode": "conditional",
    "amount_per_person": 10.00,
    "conditions": {
      "always_require": false,
      "party_size_threshold": 6,
      "busy_times": [
        {
          "name": "Friday & Saturday Evenings",
          "days": ["Fri", "Sat"],
          "start": "18:00",
          "end": "22:00"
        }
      ]
    }
  },
  "loyalty_points": {
    "enabled": true,
    "award_on": "completed",
    "percentage": 10,
    "minimum_points": 10
  },
  "party_size": {
    "min": 1,
    "max": 20,
    "large_party_threshold": 8
  },
  "reminders": {
    "enabled": true,
    "send_before_hours": 24
  },
  "special_requests": {
    "enabled": true,
    "max_length": 500,
    "suggestions": [
      "Window seat",
      "Quiet area",
      "High chair needed",
      "Birthday celebration",
      "Allergies (please specify)"
    ]
  }
}
```

### Key Features

**5-Step Booking Flow:**
1. **Date Selection** - Flatpickr calendar (DD/MM/YYYY format, readonly input)
2. **Time Selection** - Dynamic slots from hours.json (30min intervals, stops 1h before closing)
3. **Party Size** - Visual selector (1-12 guests quick-select, 13-20 custom input)
4. **Customer Details** - Name, email, phone, special requests (prefilled for logged-in users)
5. **Confirmation** - Summary review with deposit notice if required

**Conditional Deposits:**
- Always required mode (all reservations)
- Party size threshold (e.g., 6+ guests)
- Busy times (specific days/hours like Friday/Saturday evenings)
- £10/person default (configurable)

**Security:**
- 32-character hex tokens (`bin2hex(random_bytes(16))`)
- Secure URLs: `/reservations/confirmation/{id}/{token}`
- Token column indexed for fast lookups
- `get_reservation_by_token()` validates both ID and token

**Email Notifications:**
- Confirmation email sent immediately
- 24h reminder email (configurable timing)
- Cancellation email (manual cancellation only)
- All emails include secure token links
- Proper address formatting from site config

**Ryft Payment Integration:**
- Pre-rendered DOM elements (`#ryft-card-element`, `#ryft-field-collection`)
- Saved payment methods for logged-in users
- `paymentMethodSelectionChanged` event handler
- Auto-hide fields when saved card selected
- Check both 'Approved' AND 'Captured' statuses
- Proper £ symbol encoding in JavaScript

**Customer Dashboard:**
- Highlighted "Next Reservation" card at top
- Upcoming reservations list (today onwards, confirmed only)
- Past reservations (20 most recent)
- Status badges (Confirmed, Completed, Cancelled, No Show)
- "Add to Calendar" button for future confirmed reservations
- Deposit status indicators
- Phone-only cancellation notice

**Integration Points:**
- hours.json for availability (opening/closing times, holidays, special hours)
- Loyalty points awarded on completion (10% of deposit, configurable)
- Navigation links conditional on `$site['features']['reservations']`
- Dashboard sidebar link conditional on feature flag

### Status Workflow
| Status | Description | Visible to Customer |
|--------|-------------|---------------------|
| `pending` | Awaiting deposit payment | No (hidden from dashboard) |
| `confirmed` | Deposit paid, reservation active | Yes (upcoming) |
| `completed` | Customer arrived and seated | Yes (past) |
| `cancelled` | Cancelled by restaurant/customer | Yes (past) |
| `no_show` | Customer didn't arrive | Yes (past) |

### Auto-Scrolling Behavior
- Date selected → auto-scroll to time selection
- Time selected → auto-scroll to party size
- Party size selected → auto-scroll to customer details
- Next/Back buttons → scroll to `.reservation-card` top
- Smooth `scrollIntoView({ behavior: 'smooth', block: 'start' })`

### Date/Time Handling
- Input format: DD/MM/YYYY (readonly, Flatpickr)
- Internal format: YYYY-MM-DD (ISO for database/API)
- Time slots: HH:MM (24-hour format)
- Lunch label: 06:00-15:59
- Dinner label: 16:00-05:59 (handles overnight)

---

**Session 25 Complete:** Full table reservations system with conditional deposits, secure token-based access, Ryft payment integration, email notifications, customer dashboard, and seamless hours.json integration. Ready for production use.