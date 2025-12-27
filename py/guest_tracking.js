// ============================================
// GUEST/COVER TRACKING - COMPLETE JS MODULE
// ============================================
// 
// SETUP:
// 1. Include this file after pos.helpers.js
// 2. Inject config in template (see bottom of file for template snippet)
// 3. Update displayCartData() to call renderGuestButton()
// 4. Update showCartModifiers() to include guest dropdown
// 5. Update handleProductButton() to call checkGuestRequired()
//
// Uses existing: updateModal(), openModal(), closeModal()
// ============================================

// ============================================
// GLOBAL STATE
// ============================================

let lockedGuest = null;          // Currently locked guest (1, 2, 3...) or null
let lastSelectedGuest = null;    // Remember last selection for prompt default
let currentCartCovers = 0;       // Total covers for current cart

// Config injected from template (see bottom for template snippet)
// const COVER_SELECT_CONFIG = { enabled, methods, printGroups, categoryPrintGroups }

// ============================================
// HELPER: Check if feature should be active
// ============================================

function isGuestSelectActive(orderType, totalCovers) {
    if (typeof COVER_SELECT_CONFIG === 'undefined') return false;
    if (!COVER_SELECT_CONFIG.enabled) return false;
    if (!COVER_SELECT_CONFIG.methods.includes(orderType)) return false;
    if (totalCovers <= 1) return false;
    return true;
}

function productNeedsGuest(categoryId) {
    if (typeof COVER_SELECT_CONFIG === 'undefined') return false;
    const printGroup = COVER_SELECT_CONFIG.categoryPrintGroups[categoryId];
    if (printGroup === undefined) return false;
    return COVER_SELECT_CONFIG.printGroups.includes(printGroup);
}

// ============================================
// GUEST SELECTOR BUTTON (compact, near merge/split)
// ============================================

/**
 * Render the small guest selector button
 * Call this from displayCartData() for dine-in orders
 * 
 * @param {number} totalCovers - Total covers for the order
 * @param {string} orderType - Order type (dine, takeaway, etc.)
 * @returns {string} HTML for the guest button (empty if not applicable)
 */
function renderGuestButton(totalCovers, orderType) {
    currentCartCovers = totalCovers;
    
    if (!isGuestSelectActive(orderType, totalCovers)) {
        lockedGuest = null;
        return '';
    }
    
    // Validate locked guest against current covers
    if (lockedGuest && lockedGuest > totalCovers) {
        lockedGuest = null;
    }
    
    if (lockedGuest) {
        return `
            <button class="btn btn-primary" onclick="showGuestSelectorModal()" title="Guest ${lockedGuest} selected">
                <i class="bi bi-person-fill"></i><span class="badge bg-light text-primary ms-1">${lockedGuest}</span>
            </button>
        `;
    } else {
        return `
            <button class="btn btn-outline-secondary" onclick="showGuestSelectorModal()" title="Select guest">
                <i class="bi bi-person"></i>
            </button>
        `;
    }
}
/**
 * Show modal to select/change locked guest
 */
function showGuestSelectorModal() {
    const covers = currentCartCovers;
    
    if (covers < 2) {
        showToast('Need 2+ covers for guest selection', false);
        return;
    }
    
    const body = buildGuestGridHTML(covers, lockedGuest, 'setLockedGuest');
    
    const footer = `
        <button class="btn btn-outline-secondary w-100" onclick="clearLockedGuest(); closeModal();">
            <i class="bi bi-x-circle"></i> Clear Selection (Add as Shared)
        </button>
    `;
    
    updateModal('Select Guest for New Items', body, footer, 'modal-md');
    openModal();
}

/**
 * Set the locked guest
 */
function setLockedGuest(guestNum) {
    lockedGuest = guestNum;
    lastSelectedGuest = guestNum;
    closeModal();
    updateGuestButtonDisplay();
    showToast(`Now adding items to Guest ${guestNum}`, true, 1500);
}

/**
 * Clear the locked guest
 */
function clearLockedGuest() {
    lockedGuest = null;
    
    // Refresh cart display to update button
    const cartId = getCurrentCartId();
    if (cartId) {
        fetchCartData(cartId);
    }
}

/**
 * Reset guest state (call on checkout, cart switch)
 */
function resetGuestState() {
    lockedGuest = null;
    // Don't reset lastSelectedGuest - keep for prompt default
    currentCartCovers = 0;
}

// ============================================
// GUEST PROMPT MODAL (shown when adding items)
// ============================================

/**
 * Check if guest selection is required and handle accordingly
 * Call this from handleProductButton() BEFORE addToCart()
 * 
 * @param {object} productData - Product info to add
 * @param {function} callback - Function to call with guest_number
 * @returns {boolean} true if handled (modal shown), false if proceed normally
 */
function checkGuestRequired(productData, callback) {
    const { categoryId } = productData;
    
    // Get current cart info
    const cartId = getCurrentCartId();
    if (!cartId) return false;
    
    // Check if feature is active (need to get order type and covers)
    // This relies on currentCartCovers being set from displayCartData
    if (currentCartCovers <= 1) return false;
    
    // Check if this product needs guest assignment
    if (!productNeedsGuest(categoryId)) {
        callback(null); // Shared item
        return true;
    }
    
    // If guest is locked, use it
    if (lockedGuest !== null) {
        callback(lockedGuest);
        return true;
    }
    
    // Show prompt modal
    showGuestPromptModal(productData, callback);
    return true;
}

/**
 * Show prompt modal to select guest for this item
 */
function showGuestPromptModal(productData, callback) {
    const covers = currentCartCovers;
    const defaultGuest = lastSelectedGuest;
    
    // Store callback for use by selection
    window._guestPromptCallback = callback;
    window._guestPromptProductData = productData;
    
    const body = `
        <div class="text-center mb-3">
            <span class="badge bg-info fs-6">${productData.productName}</span>
        </div>
        ${buildGuestGridHTML(covers, defaultGuest, 'selectGuestAndAdd')}
    `;
    
    const footer = `
        <button class="btn btn-outline-secondary w-100" onclick="selectGuestAndAdd(null)">
            <i class="bi bi-share"></i> Skip - Add as Shared
        </button>
    `;
    
    updateModal('Assign to Guest', body, footer, 'modal-md');
    openModal();
}

/**
 * Handle guest selection from prompt modal
 */
function selectGuestAndAdd(guestNum) {
    if (guestNum !== null) {
        lastSelectedGuest = guestNum;
        lockedGuest = guestNum;
    }
    
    const callback = window._guestPromptCallback;
    closeModal();
    
    if (callback) {
        callback(guestNum);
    }
    
    // Just update the button display, don't reload cart
    updateGuestButtonDisplay();
    
    // Cleanup
    window._guestPromptCallback = null;
    window._guestPromptProductData = null;
}

// ============================================
// GUEST GRID BUILDER (supports large groups)
// ============================================

/**
 * Build HTML grid of guest buttons
 * Handles small (2-6) and large (7+) groups differently
 * 
 * @param {number} totalCovers - Total guests
 * @param {number|null} highlightGuest - Guest to highlight as default
 * @param {string} onClickFn - Function name to call on click
 * @returns {string} HTML
 */
function buildGuestGridHTML(totalCovers, highlightGuest, onClickFn) {
    let html = '<div class="guest-grid-container">';
    
    // Determine columns based on count
    let colClass = 'col-3'; // 4 per row default
    if (totalCovers <= 4) {
        colClass = 'col-3';
    } else if (totalCovers <= 6) {
        colClass = 'col-4'; // 3 per row
    } else if (totalCovers <= 12) {
        colClass = 'col-3'; // 4 per row
    } else {
        colClass = 'col-2'; // 6 per row for large groups
    }
    
    // Add scrollable wrapper for very large groups
    const needsScroll = totalCovers > 16;
    if (needsScroll) {
        html += '<div class="guest-grid-scroll" style="max-height: 300px; overflow-y: auto;">';
    }
    
    html += '<div class="row g-2 justify-content-center">';
    
    for (let i = 1; i <= totalCovers; i++) {
        const isHighlighted = (highlightGuest === i);
        const btnClass = isHighlighted ? 'btn-primary' : 'btn-outline-primary';
        const checkMark = isHighlighted ? ' <i class="bi bi-check-circle-fill"></i>' : '';
        
        html += `
            <div class="${colClass} p-1">
                <button class="btn ${btnClass} w-100 py-3 guest-select-btn" 
                        onclick="${onClickFn}(${i})"
                        data-guest="${i}">
                    <i class="bi bi-person-fill"></i><br>
                    <span class="fw-bold">Guest ${i}</span>${checkMark}
                </button>
            </div>
        `;
    }
    
    html += '</div>';
    
    if (needsScroll) {
        html += '</div>';
    }
    
    html += '</div>';
    
    return html;
}

// ============================================
// CART MODIFIER MODAL - GUEST DROPDOWN
// ============================================

/**
 * Build HTML for guest reassignment dropdown
 * Add this to showCartModifiers() modal body
 * 
 * @param {number|null} currentGuest - Current guest_number of item
 * @param {number} totalCovers - Total covers (0 if not applicable)
 * @returns {string} HTML for dropdown section
 */
function buildGuestReassignDropdown(currentGuest, totalCovers) {
    // Don't show if feature not active
    if (totalCovers <= 1) {
        return '';
    }
    
    let options = `<option value="">Shared (No Guest)</option>`;
    
    for (let i = 1; i <= totalCovers; i++) {
        const selected = (currentGuest === i) ? 'selected' : '';
        options += `<option value="${i}" ${selected}>Guest ${i}</option>`;
    }
    
    return `
        <div class="mb-3">
            <label class="form-label fw-bold">
                <i class="bi bi-person-fill"></i> Assigned to Guest
            </label>
            <select class="form-select" id="cartItemGuestSelect">
                ${options}
            </select>
        </div>
        <hr>
    `;
}

/**
 * Get selected guest from modifier modal dropdown
 * Call this in saveCartItemMods() to include guest_number
 */
function getSelectedGuestFromModal() {
    const select = document.getElementById('cartItemGuestSelect');
    if (!select) return undefined; // Not present, don't update
    
    const value = select.value;
    return value === '' ? null : parseInt(value);
}

// ============================================
// UPDATED: addToCart with guest support
// ============================================

/**
 * Add item to cart with guest_number
 * This is the actual cart addition - call after guest is determined
 */
function addToCartWithGuest(productId, productName, formattedPrice, options, categoryOrder, vatable, guestNumber) {
    const cartId = getCurrentCartId();
    if (!cartId) {
        fetchPosMethods();
        return;
    }
    
    const data = {
        productId,
        cartId,
        productName,
        formattedPrice,
        quantity: 1,
        options: options == "null" ? "" : options,
        productNote: "",
        categoryOrder,
        vatable,
        guest_number: guestNumber
    };
    
    fetch('/add_to_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.error) {
            showToast(result.error, false);
        } else {
            fetchAndDisplayCartItems(cartId);
            
            if (guestNumber !== null) {
                showToast(`Added to Guest ${guestNumber}`, true, 1000);
            }
        }
    })
    .catch(error => {
        console.error("Error:", error);
        showToast("Error adding item to cart", false);
    });
}

// ============================================
// INTEGRATION HELPERS
// ============================================

/**
 * Wrapper for handleProductButton integration
 * Replace your existing addToCart calls with this flow
 * 
 * Usage in handleProductButton:
 *   handleProductWithGuestCheck(productId, productName, formattedPrice, options, categoryOrder, vatable, categoryId);
 */
function handleProductWithGuestCheck(productId, productName, formattedPrice, options, categoryOrder, vatable, categoryId) {
    const cartId = getCurrentCartId();
    if (!cartId) {
        fetchPosMethods();
        return;
    }
    
    // Check if guest selection needed
    if (typeof COVER_SELECT_CONFIG !== 'undefined' && COVER_SELECT_CONFIG.enabled && currentCartCovers > 1) {
        
        // Check if this product needs guest
        if (productNeedsGuest(categoryId)) {
            
            // If guest is locked, use it
            if (lockedGuest !== null) {
                addToCartWithGuest(productId, productName, formattedPrice, options, categoryOrder, vatable, lockedGuest);
                return;
            }
            
            // Show prompt
            const productData = { productId, productName, formattedPrice, options, categoryOrder, vatable, categoryId };
            showGuestPromptModal(productData, (guestNum) => {
                addToCartWithGuest(productId, productName, formattedPrice, options, categoryOrder, vatable, guestNum);
            });
            return;
        }
    }
    
    // No guest needed - add normally (null guest)
    addToCartWithGuest(productId, productName, formattedPrice, options, categoryOrder, vatable, null);
}

/**
 * Handle options flow with guest check
 * Call this instead of fetchOptionsData when product has options
 */
function fetchOptionsWithGuestCheck(optionArray, currentMenu, productId, productName, formattedPrice, categoryOrder, vatable, categoryId) {
    fetch('/get_product_options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            product_id: productId,
            option_ids: optionArray,
            current_menu: currentMenu
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.options) {
            launchCustomisationUI(data.options, { 
                productId, 
                productName, 
                formattedPrice, 
                categoryOrder, 
                vatable,
                categoryId
            });
        } else {
            showToast('No options found for this product', false);
        }
    })
    .catch(err => {
        console.error('Option fetch failed', err);
        showToast('Error fetching options', false);
    });
}

/**
 * Complete customisation with guest check
 * Replace your existing completeCustomisation() with this
 */
function completeCustomisationWithGuest() {
    const optionString = buildOptionString();
    const meta = customData.meta;
    
    handleProductWithGuestCheck(
        meta.productId,
        meta.productName,
        meta.formattedPrice,
        optionString,
        meta.categoryOrder,
        meta.vatable,
        meta.categoryId
    );
    
    closeCustomisation();
}

function updateGuestButtonDisplay() {
    const existingBtn = document.querySelector('[onclick="showGuestSelectorModal()"]');
    if (existingBtn) {
        if (lockedGuest) {
            existingBtn.className = 'btn btn-primary';
            existingBtn.title = `Guest ${lockedGuest} selected`;
            existingBtn.innerHTML = `<i class="bi bi-person-fill"></i><span class="badge bg-light text-primary ms-1">${lockedGuest}</span>`;
        } else {
            existingBtn.className = 'btn btn-outline-secondary';
            existingBtn.title = 'Select guest';
            existingBtn.innerHTML = `<i class="bi bi-person"></i>`;
        }
    }
}
