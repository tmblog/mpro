/**
 * Cart Management - LocalStorage Based
 * Generic for all restaurant sites
 */

const Cart = {
    /**
     * Get storage key - separate cart for table ordering
     */
    getKey() {
        return window.TABLE_MODE ? 'tableCart' : 'cart';
    },

    /**
     * Get cart from localStorage
     */
    get() {
        const cart = localStorage.getItem(this.getKey());
        return cart ? JSON.parse(cart) : [];
    },

    /**
     * Save cart to localStorage
     */
    set(cart) {
        localStorage.setItem(this.getKey(), JSON.stringify(cart));
        this.updateUI();
    },

    /**
     * Add item to cart
     */
    add(productId, productName, basePrice, options = [], quantity = 1, cpn = 1) {
        let cart = this.get();
        
        // Calculate total price with options
        let totalPrice = parseFloat(basePrice);
        options.forEach(opt => {
            totalPrice += parseFloat(opt.option_price || 0);
            if (opt.child_price) {
                totalPrice += parseFloat(opt.child_price);
            }
        });

        // Check if exact item already exists (same product + same options)
        const existingIndex = this.findExactMatch(cart, productId, options);
        
        if (existingIndex !== -1) {
            // Update quantity of existing item
            cart[existingIndex].quantity += quantity;
        } else {
            // Add new item
            cart.push({
                product_id: productId,
                product_name: productName,
                base_price: basePrice,
                options: options,
                quantity: quantity,
                total_price: totalPrice,
                cpn: parseInt(cpn) || 1,
                added_at: Date.now()
            });
        }
        
        this.set(cart);
        this.showSuccessFeedback();
        this.scrollToBottom();
        //this.showNotification(`Added ${productName} to cart`);
        return true;
    },

    /**
     * Add free item to cart
     */
    addFreeItem(productId, productName, basePrice, options = [], offerId, linkedTo = null) {
        let cart = this.get();
        
        // Calculate total price - base is free, options may be charged
        let totalPrice = 0;
        options.forEach(opt => {
            totalPrice += parseFloat(opt.option_price || 0);
            if (opt.child_price) {
                totalPrice += parseFloat(opt.child_price);
            }
        });

        // Generate unique key for linking
        const cartKey = `free_${offerId}_${Date.now()}`;
        
        cart.push({
            cart_key: cartKey,
            product_id: productId,
            product_name: productName,
            base_price: 0,  // Base is always free
            original_price: parseFloat(basePrice),  // Store original for display
            options: options,
            quantity: 1,
            total_price: totalPrice,
            cpn: 0,  // Doesn't count toward promotions
            is_free: true,
            offer_id: offerId,
            linked_to: linkedTo,  // For BOGOF: cart_key of paid item
            added_at: Date.now()
        });
        
        this.set(cart);
        this.scrollToBottom();
        return cartKey;
    },

    /**
     * Add BOGOF item - adds paid item + free duplicate
     */
    addBogof(productId, productName, basePrice, options = [], quantity = 1, cpn = 1, offerId) {
        let cart = this.get();
        
        // Calculate total price with options
        let totalPrice = parseFloat(basePrice);
        options.forEach(opt => {
            totalPrice += parseFloat(opt.option_price || 0);
            if (opt.child_price) {
                totalPrice += parseFloat(opt.child_price);
            }
        });
        
        // Check if exact paid item already exists
        const existingPaidIndex = cart.findIndex(item => 
            !item.is_free &&
            item.product_id == productId &&
            item.offer_id === offerId &&
            JSON.stringify(item.options) === JSON.stringify(options)
        );
        
        if (existingPaidIndex !== -1) {
            // Increment paid item
            cart[existingPaidIndex].quantity += quantity;
            
            // Find and increment linked free item
            const paidKey = cart[existingPaidIndex].cart_key;
            const freeIndex = cart.findIndex(item => item.linked_to === paidKey);
            if (freeIndex !== -1) {
                cart[freeIndex].quantity += quantity;
            }
            
            this.set(cart);
        } else {
            // Create new pair
            const paidKey = 'paid_' + Date.now();
            const freeKey = 'free_bogof_' + productId + '_' + Date.now();
            
            // Add paid item
            cart.push({
                cart_key: paidKey,
                product_id: productId,
                product_name: productName,
                base_price: basePrice,
                options: options,
                quantity: quantity,
                total_price: totalPrice,
                cpn: parseInt(cpn) || 1,
                offer_id: offerId,
                added_at: Date.now()
            });
            
            // Add free item
            cart.push({
                cart_key: freeKey,
                product_id: productId,
                product_name: productName,
                base_price: 0,
                original_price: basePrice,
                options: options,
                quantity: quantity,
                total_price: 0,
                cpn: 0,
                is_free: true,
                offer_id: offerId,
                linked_to: paidKey,
                added_at: Date.now()
            });
            
            this.set(cart);
        }
        this.scrollToBottom();
        //this.showNotification(`${productName} (2 for 1) added to cart!`);
    },

    /**
     * Find exact match in cart (same product + same options)
     */
    findExactMatch(cart, productId, options) {
        return cart.findIndex(item => {
            if (item.product_id !== productId) return false;
            
            // Compare options
            if (item.options.length !== options.length) return false;
            
            // Deep compare options
            const itemOptionsStr = JSON.stringify(this.sortOptions(item.options));
            const newOptionsStr = JSON.stringify(this.sortOptions(options));
            
            return itemOptionsStr === newOptionsStr;
        });
    },

    /**
     * Sort options for comparison
     */
    sortOptions(options) {
        return options.sort((a, b) => a.option_id - b.option_id);
    },

    /**
     * Update item quantity
     */
    update(index, quantity) {
        let cart = this.get();
        
        if (index < 0 || index >= cart.length) {
            console.error('Invalid cart index');
            return false;
        }
        
        quantity = parseInt(quantity);
        
        if (quantity <= 0) {
            return this.remove(index);
        }
        
        if (quantity > 20) {
            this.showNotification('Maximum 20 items per product', 'warning');
            quantity = 20;
        }
        
        cart[index].quantity = quantity;
        this.set(cart);
        return true;
    },

    /**
     * Remove item from cart (handles linked BOGOF items)
     */
    remove(index) {
        let cart = this.get();
        
        if (index < 0 || index >= cart.length) {
            console.error('Invalid cart index');
            return false;
        }
        
        const item = cart[index];
        const itemKey = item.cart_key;
        
        // Animate out and remove
        const itemElement = document.querySelector(`[data-cart-index="${index}"]`);
        if (itemElement) {
            itemElement.classList.add('cart-item-removing');
            setTimeout(() => {
                cart = this.get(); // Re-fetch in case of changes
                
                // If this is a paid BOGOF trigger, also remove linked free item
                if (item.is_bogof_trigger && itemKey) {
                    cart = cart.filter(i => i.linked_to !== itemKey);
                }
                
                // Find and remove the item by key or timestamp
                const currentIndex = cart.findIndex(i => 
                    (i.cart_key && i.cart_key === itemKey) || 
                    i.added_at === item.added_at
                );
                if (currentIndex !== -1) {
                    cart.splice(currentIndex, 1);
                }
                
                this.set(cart);
                this.enforceOfferRules();
            }, 400);
        } else {
            // If this is a paid BOGOF trigger, also remove linked free item
            if (item.is_bogof_trigger && itemKey) {
                cart = cart.filter(i => i.linked_to !== itemKey);
            }
            
            cart.splice(index, 1);
            this.set(cart);
            this.enforceOfferRules();
        }
        
        return true;
    },

    /**
     * Clear entire cart (with SweetAlert2 confirmation)
     */
    clear() {
        const cart = this.get();
        if (cart.length === 0) return;
        
        // Use SweetAlert2 if available, otherwise use confirm
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                title: 'Clear Cart?',
                text: 'Remove all items from your cart?',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Yes, clear it',
                confirmButtonColor: '#dc3545',
                cancelButtonText: 'Cancel'
            }).then((result) => {
                if (result.isConfirmed) {
                    localStorage.removeItem(this.getKey());
                    this.updateUI();
                    Swal.fire({
                        title: 'Cleared!',
                        text: 'Your cart is now empty',
                        icon: 'success',
                        timer: 1500,
                        showConfirmButton: false
                    });
                }
            });
        } else {
            // Fallback to native confirm
            if (confirm('Are you sure you want to clear your cart?')) {
                localStorage.removeItem(this.getKey());
                this.updateUI();
                this.showNotification('Cart cleared');
            }
        }
    },

    /**
     * Remove multiple items by product IDs
     */
    removeByProductIds(productIds) {
        if (!Array.isArray(productIds) || productIds.length === 0) return;
        
        let cart = this.get();
        const idsToRemove = productIds.map(id => parseInt(id));
        
        cart = cart.filter(item => !idsToRemove.includes(parseInt(item.product_id)));
        
        localStorage.setItem(this.getKey(), JSON.stringify(cart));
        this.updateUI();
    },

    /**
     * Get items (alias for get)
     */
    getItems() {
        return this.get();
    },
    
    /**
     * Get cart item count
     */
    getCount() {
        const cart = this.get();
        return cart.reduce((total, item) => total + item.quantity, 0);
    },

    /**
     * Get cart subtotal
     */
    getSubtotal() {
        const cart = this.get();
        return cart.reduce((total, item) => {
            return total + (item.total_price * item.quantity);
        }, 0);
    },

    /**
     * Get promotional subtotal (excludes free items)
     * Used for threshold calculations
     */
    getPromoSubtotal() {
        const cart = this.get();
        return cart.reduce((total, item) => {
            // Skip free items for promo calculations
            if (item.is_free) return total;
            return total + (item.total_price * item.quantity);
        }, 0);
    },

    /**
     * Format price (gets currency symbol from page or defaults to £)
     */
    formatPrice(amount) {
        const currencySymbol = document.body.dataset.currency || '£';
        return currencySymbol + parseFloat(amount).toFixed(2);
    },

    /**
     * Scroll cart sidebar to bottom
     */
    scrollToBottom() {
        const cartBody = document.querySelector('.cart-sidebar__body');
        if (cartBody) {
            cartBody.scrollTo({ top: cartBody.scrollHeight - 300, behavior: 'smooth' });
        }
    },

    /**
     * Update all cart UI elements
     */
    updateUI() {
        const cart = this.get();
        const count = this.getCount();
        const subtotal = this.getSubtotal();

        // Update cart count badges
        const badges = document.querySelectorAll('.cart-count');
        badges.forEach(badge => {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        });

        // Update cart sidebar
        this.updateCartSidebar(cart, subtotal);
        
        // Update mobile cart bar visibility
        const mobileCartBar = document.getElementById('mobileCartBar');
        if (mobileCartBar) {
            mobileCartBar.style.display = count > 0 ? 'block' : 'none';
        }
        
        // Update mobile totals
        const mobileTotal = document.getElementById('mobile-cart-total');
        if (mobileTotal) {
            mobileTotal.textContent = this.formatPrice(subtotal);
        }
        const mobileFooterTotal = document.getElementById('mobile-cart-total-footer');
        if (mobileFooterTotal) {
            mobileFooterTotal.textContent = this.formatPrice(subtotal);
        }
        
        // Update offer progress messages
        this.updateOfferProgress();
    },

    /**
     * Update cart sidebar HTML
     */
    updateCartSidebar(cart, subtotal) {
        const cartSidebar = document.getElementById('cart-items');
        if (!cartSidebar) return;

        if (cart.length === 0) {
            const emptyHtml = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-cart-x" style="font-size: 3rem;"></i>
                    <p class="mt-3">Your cart is empty</p>
                </div>
            `;
            
            cartSidebar.innerHTML = emptyHtml;
            
            // Also update mobile cart
            const mobileCartItems = document.getElementById('mobile-cart-items');
            if (mobileCartItems) {
                mobileCartItems.innerHTML = emptyHtml;
            }
            
            const totalEl = document.getElementById('cart-total');
            if (totalEl) totalEl.textContent = this.formatPrice(0);
            
            return;
        }

        let html = '';

        cart.forEach((item, index) => {
            // Build options display with proper nesting
            let optionsHtml = '';
            if (item.options && item.options.length > 0) {
                optionsHtml = '<div class="cart-item-options">';
                
                // Group options: render parent + its children immediately
                const renderedIndices = new Set();
                
                item.options.forEach((opt, optIndex) => {
                    if (renderedIndices.has(optIndex)) return; // Already rendered as child
                    
                    const isChild = !!opt.parent_option_id;
                    if (isChild) return; // Will be rendered with parent
                    
                    // Render parent option
                    const qtyStr = opt.quantity && opt.quantity > 1 ? ` x${opt.quantity}` : '';
                    const quantity = opt.quantity || 1;
                    const unitPrice = (parseFloat(opt.option_price) || 0) + (parseFloat(opt.child_price) || 0);
                    const totalPrice = unitPrice * quantity;
                    const priceStr = totalPrice > 0 ? ` +${Cart.formatPrice(totalPrice)}` : '';
                    
                    optionsHtml += `<small class="text-muted d-block">+ ${opt.option_name}${qtyStr}${priceStr}</small>`;
                    renderedIndices.add(optIndex);
                    
                    // Immediately render children of this parent
                    item.options.forEach((childOpt, childIndex) => {
                        if (childOpt.parent_option_id === opt.option_id) {
                            const childQtyStr = childOpt.quantity && childOpt.quantity > 1 ? ` x${childOpt.quantity}` : '';
                            const childQuantity = childOpt.quantity || 1;
                            const childUnitPrice = (parseFloat(childOpt.option_price) || 0) + (parseFloat(childOpt.child_price) || 0);
                            const childTotalPrice = childUnitPrice * childQuantity;
                            const childPriceStr = childTotalPrice > 0 ? ` +${Cart.formatPrice(childTotalPrice)}` : '';
                            
                            optionsHtml += `<small class="text-muted d-block ps-3">&nbsp;&nbsp;+ ${childOpt.option_name}${childQtyStr}${childPriceStr}</small>`;
                            renderedIndices.add(childIndex);
                        }
                    });
                });
                
                optionsHtml += '</div>';
            }

            const itemTotal = item.total_price * item.quantity;
            
            // Check if this is a free item
            const isFree = item.is_free === true;
            const freeClass = isFree ? ' free-item' : '';
            const freeBadge = isFree ? '<span class="free-badge">FREE</span>' : '';
            const originalPrice = isFree && item.original_price ? 
                `<span class="original-price">${this.formatPrice(item.original_price)}</span> ` : '';
            
            // Free items can't have quantity changed
            const minusIcon = item.quantity === 1 ? 'bi-trash' : 'bi-dash';
            const minusClass = item.quantity === 1 ? ' qty-trash' : '';
            const quantityControls = isFree ? 
                `<span class="quantity-note">Qty: ${item.quantity}</span>` :
                `<div class="cart-qty-selector">
                    <button type="button" class="cart-qty-btn${minusClass}" onclick="Cart.update(${index}, ${item.quantity - 1})">
                        <i class="bi ${minusIcon}"></i>
                    </button>
                    <span class="cart-qty-value">${item.quantity}</span>
                    <button type="button" class="cart-qty-btn" onclick="Cart.update(${index}, ${item.quantity + 1})">
                        <i class="bi bi-plus"></i>
                    </button>
                </div>`;
            
            // Price display for free items
            const priceDisplay = isFree ? 
                (itemTotal > 0 ? `<strong>${this.formatPrice(itemTotal)}</strong>` : '<strong class="text-success">FREE</strong>') :
                `<strong>${this.formatPrice(itemTotal)}</strong>`;
            
            // Each price display
            const eachPrice = isFree ?
                (item.total_price > 0 ? `<span class="text-muted">${originalPrice}+${this.formatPrice(item.total_price)} extras</span>` : 
                    `<span class="text-success">${originalPrice}FREE</span>`) :
                `<span class="text-muted">${this.formatPrice(item.total_price)} each</span>`;
            if (item.is_free && item.linked_to) {
                // Compact free item display
                const truncatedName = item.product_name.length > 30 
                    ? item.product_name.substring(0, 30) + '...' 
                    : item.product_name;
                
                html += `
                    <div class="cart-item cart-item-free-compact mb-2 ps-2 border-start border-success border-3" data-cart-index="${index}">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-truncate me-2">${truncatedName}</span>
                            <span class="badge bg-success">FREE</span>
                        </div>
                        <small class="text-muted">Qty: ${item.quantity}</small>
                    </div>
                `;
                return;
            }
            // Compact free-on-spend item display
            if (item.is_free && !item.linked_to) {
                const truncatedName = item.product_name.length > 30 
                    ? item.product_name.substring(0, 30) + '...' 
                    : item.product_name;
                
                html += `
                    <div class="cart-item cart-item-free-compact mb-2 ps-2 border-start border-info border-3" data-cart-index="${index}">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-truncate me-2">${truncatedName}</span>
                            <div>
                                <span class="badge bg-info me-1">FREE</span>
                                <button class="btn btn-sm btn-link text-danger p-0" onclick="Cart.remove(${index})" title="Remove">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                        <small class="text-muted">Qty: ${item.quantity}</small>
                    </div>
                `;
                return;
            }
            html += `
                <div class="cart-item mb-3 pb-3 border-bottom${freeClass}" data-cart-index="${index}">
                    <h6 class="mb-1">${item.product_name}${freeBadge}</h6>
                    ${optionsHtml}
                    <div class="d-flex justify-content-between align-items-center mt-2">
                        ${priceDisplay}
                        ${quantityControls}
                    </div>
                </div>
            `;
        });

        cartSidebar.innerHTML = html;

        // Also update mobile cart
        const mobileCartItems = document.getElementById('mobile-cart-items');
        if (mobileCartItems) {
            mobileCartItems.innerHTML = html;
        }

        // Update total
        const totalEl = document.getElementById('cart-total');
        if (totalEl) {
            totalEl.textContent = this.formatPrice(subtotal);
        }
    },

    /**
     * Show success feedback (button flash + badge pulse)
     */
    showSuccessFeedback() {
        // Flash the add button
        const lastClickedBtn = document.activeElement;
        if (lastClickedBtn && lastClickedBtn.tagName === 'BUTTON') {
            lastClickedBtn.classList.add('btn-success-flash');
            setTimeout(() => {
                lastClickedBtn.classList.remove('btn-success-flash');
            }, 600);
        }

        // Pulse cart badge
        const badges = document.querySelectorAll('.cart-count');
        badges.forEach(badge => {
            badge.classList.add('cart-badge-pulse');
            setTimeout(() => {
                badge.classList.remove('cart-badge-pulse');
            }, 500);
        });
    },

    /**
     * Show notification
     */
    showNotification(message, type = 'success') {
        // Check if notification container exists
        let container = document.getElementById('cart-notifications');
        
        if (!container) {
            container = document.createElement('div');
            container.id = 'cart-notifications';
            container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
            document.body.appendChild(container);
        }

        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        container.appendChild(alert);

        // Auto dismiss after 3 seconds
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }, 3000);
    },

    /**
     * Check and enforce offer rules after cart changes
     * Removes free items if conditions no longer met
     */
    enforceOfferRules() {
        if (typeof SITE_FEATURES === 'undefined' || !SITE_FEATURES.offers) return;
        if (typeof ACTIVE_OFFERS === 'undefined') return;
        
        let cart = this.get();
        let modified = false;
        const subtotal = this.getPromoSubtotal();
        
        cart = cart.filter(item => {
            if (!item.is_free || !item.offer_id) return true;
            
            const offer = ACTIVE_OFFERS.find(o => o.id === item.offer_id);
            if (!offer) {
                modified = true;
                return false;  // Offer no longer exists
            }
            
            // Check free_on_spend threshold
            if (offer.type === 'free_on_spend') {
                if (subtotal < offer.minSpend) {
                    modified = true;
                    //this.showNotification(`Free item removed - spend £${offer.minSpend.toFixed(2)} to qualify`, 'warning');
                    return false;
                }
            }
            
            // Check BOGOF linked item still exists
            if (offer.type === 'bogof' && item.linked_to) {
                const linkedItem = cart.find(i => i.cart_key === item.linked_to);
                if (!linkedItem) {
                    modified = true;
                    return false;
                }
            }

            // Sync free qty to paid qty for BOGOF
            if (item.is_free && item.linked_to && offer.type === 'bogof') {
                const paidItem = cart.find(i => i.cart_key === item.linked_to);
                if (paidItem && item.quantity !== paidItem.quantity) {
                    item.quantity = paidItem.quantity;
                    modified = true;
                }
            }
            
            return true;
        });
        
        // Check buy_x_get_free quantities
        ACTIVE_OFFERS.filter(o => o.type === 'buy_x_get_free').forEach(offer => {
            const triggerQty = cart
                .filter(i => !i.is_free && (offer.triggerProducts || []).includes(i.product_id))
                .reduce((sum, i) => sum + i.quantity, 0);
            
            const freeItems = cart.filter(i => i.is_free && i.offer_id === offer.id);
            const allowedFree = Math.floor(triggerQty / offer.triggerQuantity);
            
            // Remove excess free items
            if (freeItems.length > allowedFree) {
                const toRemove = freeItems.length - allowedFree;
                for (let i = 0; i < toRemove; i++) {
                    const removeIdx = cart.findIndex(item => 
                        item.is_free && item.offer_id === offer.id
                    );
                    if (removeIdx !== -1) {
                        cart.splice(removeIdx, 1);
                        modified = true;
                    }
                }
                if (toRemove > 0) {
                    //this.showNotification(`Free item removed - need ${offer.triggerQuantity} items to qualify`, 'warning');
                }
            }
        });
        
        if (modified) {
            localStorage.setItem(this.getKey(), JSON.stringify(cart));
            this.updateUI();
        }
    },

    /**
     * Get offer progress messages for display
     */
    getOfferProgress() {
        if (typeof ACTIVE_OFFERS === 'undefined') return [];
        
        const messages = [];
        const cart = this.get();
        const subtotal = this.getPromoSubtotal();
        
        ACTIVE_OFFERS.forEach(offer => {
            switch (offer.type) {
                case 'free_on_spend':
                    const maxQty = offer.maxQuantity || 1;
                    const claimed = cart.filter(i => i.is_free && i.offer_id === offer.id).length;
                    const remaining = maxQty - claimed;
                    
                    if (subtotal < offer.minSpend) {
                        const toSpend = (offer.minSpend - subtotal).toFixed(2);
                        messages.push({
                            type: 'progress',
                            icon: 'gift',
                            text: `Spend £${toSpend} more for a free ${offer.name}!`,
                            offer_id: offer.id
                        });
                    } else if (remaining > 0) {
                        // const itemText = remaining === 1 ? 'item' : 'items';
                        const chooseText = maxQty > 1 ? `Choose ${remaining}` : `Choose your free item`;
                        messages.push({
                            type: 'unlocked',
                            icon: 'gift-fill',
                            text: `${offer.name} available! ${chooseText}`,
                            offer_id: offer.id
                        });
                    }
                    break;
                    
                case 'buy_x_get_free':
                    const triggerQty = cart
                        .filter(i => !i.is_free && (offer.triggerProducts || []).includes(i.product_id))
                        .reduce((sum, i) => sum + i.quantity, 0);
                    
                    if (triggerQty > 0) {
                        const needed = offer.triggerQuantity - (triggerQty % offer.triggerQuantity);
                        if (needed < offer.triggerQuantity && needed > 0) {
                            messages.push({
                                type: 'progress',
                                icon: 'plus-circle',
                                text: `Add ${needed} more for a free one (${offer.name})!`,
                                offer_id: offer.id
                            });
                        }
                    }
                    break;
            }
        });
        
        return messages;
    },

    /**
     * Update offer progress display in cart sidebar
     */
    updateOfferProgress() {
        const container = document.getElementById('offerProgressMessages');
        const mobileContainer = document.getElementById('mobileOfferProgressMessages');
        
        const section = container?.closest('.offer-progress-section') || container?.parentElement;
        const mobileSection = document.getElementById('mobileOfferProgressSection');
        
        const messages = this.getOfferProgress();
        
        if (messages.length === 0) {
            if (section) section.classList.add('d-none');
            if (mobileSection) mobileSection.classList.add('d-none');
            return;
        }
        
        const html = messages.map(msg => {
            const colorClass = msg.type === 'unlocked' ? 'text-success' : 'text-primary';
            return `<div class="${colorClass} mb-1"><i class="bi bi-${msg.icon} me-1"></i>${msg.text}</div>`;
        }).join('');
        
        if (container) container.innerHTML = html;
        if (mobileContainer) mobileContainer.innerHTML = html;
        
        if (section) section.classList.remove('d-none');
        if (mobileSection) mobileSection.classList.remove('d-none');
    },

    /**
     * Initialize cart on page load
     */
    init() {
        this.updateUI();
        
        // Listen for storage events (cart updated in another tab)
        window.addEventListener('storage', (e) => {
            if (e.key === this.getKey()) {
                this.updateUI();
            }
        });
    }
};

// Initialize cart when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Cart.init();
});