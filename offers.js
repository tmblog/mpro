/**
 * Offers Manager - Handles free item carousel and offer logic
 * New file: assets/js/offers.js
 */

const OffersManager = {
    
    /**
     * Initialize offers manager
     */
    init() {
        if (typeof SITE_FEATURES === 'undefined' || !SITE_FEATURES.offers) return;
        
        this.setupCartListener();
        this.checkUnlocks();
        
        // Intercept Cart.add for BOGOF
        const originalAdd = Cart.add.bind(Cart);
        Cart.add = (productId, productName, basePrice, options = [], quantity = 1, cpn = 1) => {
            const bogofOffer = OffersManager.getBogofOffer(parseInt(productId));
            
            if (bogofOffer) {
                return Cart.addBogof(productId, productName, basePrice, options, quantity, cpn, bogofOffer.id);
            }
            
            return originalAdd(productId, productName, basePrice, options, quantity, cpn);
        };
    },
    
    /**
     * Setup listener for cart changes
     */
    setupCartListener() {
        // Override Cart.set to trigger offer checks
        const originalSet = Cart.set.bind(Cart);
        Cart.set = (cart) => {
            originalSet(cart);
            this.checkUnlocks();
            this.updateProgress();
            Cart.enforceOfferRules();
        };
    },
    
    /**
     * Check and update carousel unlock states
     */
    checkUnlocks() {
        if (typeof ACTIVE_OFFERS === 'undefined') return;
        
        const subtotal = Cart.getPromoSubtotal();
        const cart = Cart.get();
        
        ACTIVE_OFFERS.filter(o => o.type === 'free_on_spend').forEach(offer => {
            const isUnlocked = subtotal >= offer.minSpend;
            const maxQty = offer.maxQuantity || 1;
            
            const inCart = cart.filter(i => i.is_free && i.offer_id === offer.id).length;
            const claimed = inCart >= maxQty;
            
            offer.eligibleProducts.forEach(productId => {
                this.updateCardState(productId, offer.id, isUnlocked, claimed);
            });
        });
    },
    
    /**
     * Update individual card state
     */
    updateCardState(productId, offerId, isUnlocked, claimed = false) {
        const card = document.getElementById(`offerCard_${productId}`);
        if (!card) return;
        
        const overlay = card.querySelector('.locked-overlay');
        const addBtn = card.querySelector('.btn-add-free');
        const requirement = card.querySelector('.offer-requirement');
        
        if (claimed) {
            // Already added to cart
            card.classList.remove('locked');
            card.classList.add('unlocked');
            if (overlay) overlay.classList.add('d-none');
            if (addBtn) addBtn.classList.add('d-none');
            if (requirement) requirement.innerHTML = '<span class="text-success"><i class="bi bi-check-circle me-1"></i>Free Item in cart</span>';
        } else if (isUnlocked) {
            // Can add
            card.classList.remove('locked');
            card.classList.add('unlocked');
            if (overlay) overlay.classList.add('d-none');
            if (addBtn) addBtn.classList.remove('d-none');
            if (requirement) requirement.innerHTML = '<span class="text-success"><i class="bi bi-unlock me-1"></i>Unlocked!</span>';
        } else {
            // Locked
            card.classList.add('locked');
            card.classList.remove('unlocked');
            if (overlay) overlay.classList.remove('d-none');
            if (addBtn) addBtn.classList.add('d-none');
            
            const offer = ACTIVE_OFFERS.find(o => o.id === offerId);
            if (offer && requirement) {
                const subtotal = Cart.getPromoSubtotal();
                const remaining = (offer.minSpend - subtotal).toFixed(2);
                requirement.textContent = `Spend £${remaining} more to unlock`;
            }
        }
    },
    
    /**
     * Update progress messages near cart
     */
    updateProgress() {
        Cart.updateOfferProgress();
    },
    
    /**
     * Add free item from carousel
     */
    addFreeItem(productId, offerId) {
        // Find the product data
        const product = this.findProduct(productId);
        if (!product) {
            console.error('Product not found:', productId);
            return;
        }
        
        // Check if product has options
        if (product.options && product.options.length > 0) {
            // Open options modal for free item
            this.openFreeOptionsModal(product, offerId);
        } else {
            // Add directly
            Cart.addFreeItem(
                product.id,
                product.name,
                parseFloat(product.price),
                [],
                offerId
            );
            
            this.showAddedFeedback(productId);
            Cart.showNotification(`Added FREE ${product.name} to cart!`);
        }
    },
    
    /**
     * Show visual feedback when item added
     */
    showAddedFeedback(productId) {
        const card = document.getElementById(`offerCard_${productId}`);
        if (!card) return;
        
        card.classList.add('added-flash');
        setTimeout(() => card.classList.remove('added-flash'), 600);
        
        // Re-check unlocks (may have hit max quantity)
        setTimeout(() => this.checkUnlocks(), 100);
    },
    
    /**
     * Find product in PRODUCTS data
     */
    findProduct(productId) {
        const card = document.querySelector(`[data-product-id="${productId}"]`);
        if (!card) return null;
        
        return {
            id: productId,
            name: card.dataset.productName,
            price: card.dataset.productPrice
        };
    },

    getBogofOffer(productId) {
        if (typeof ACTIVE_OFFERS === 'undefined') return null;
        
        return ACTIVE_OFFERS.find(o => 
            o.type === 'bogof' && 
            o.active &&
            (o.products || []).includes(productId)
        ) || null;
    },
    
    /**
     * Check if product should trigger BOGOF
     */
    isBogofProduct(productId) {
        if (typeof ACTIVE_OFFERS === 'undefined') return null;
        
        const bogofOffer = ACTIVE_OFFERS.find(o => 
            o.type === 'bogof' && 
            o.products.includes(productId)
        );
        
        return bogofOffer || null;
    },

    isVariationBogof(variationId) {
        if (typeof ACTIVE_OFFERS === 'undefined') return null;
        
        return ACTIVE_OFFERS.find(o => 
            o.type === 'bogof' && 
            (o.products || []).includes(variationId)
        ) || null;
    },
    
    /**
     * Check buy-x-get-free status
     */
    checkBuyXGetFree() {
        if (typeof ACTIVE_OFFERS === 'undefined') return;
        
        const cart = Cart.get();
        
        ACTIVE_OFFERS.filter(o => o.type === 'buy_x_get_free').forEach(offer => {
            // Count qualifying items
            const triggerQty = cart
                .filter(i => !i.is_free && offer.triggerProducts.includes(i.product_id))
                .reduce((sum, i) => sum + i.quantity, 0);
            
            // Count existing free items for this offer
            const freeQty = cart.filter(i => i.is_free && i.offer_id === offer.id).length;
            
            // How many free items should they have?
            const shouldHaveFree = Math.floor(triggerQty / offer.triggerQuantity);
            
            // Auto-add free items if cheapestFree
            if (offer.cheapestFree && freeQty < shouldHaveFree) {
                // Find cheapest qualifying item in cart
                const qualifyingItems = cart.filter(i => 
                    !i.is_free && offer.triggerProducts.includes(i.product_id)
                );
                
                if (qualifyingItems.length > 0) {
                    const cheapest = qualifyingItems.reduce((min, item) => 
                        item.total_price < min.total_price ? item : min
                    );
                    
                    // Add free copy
                    Cart.addFreeItem(
                        cheapest.product_id,
                        cheapest.product_name,
                        cheapest.base_price,
                        cheapest.options,
                        offer.id
                    );
                    
                    Cart.showNotification(`You got a FREE ${cheapest.product_name}!`);
                }
            }
        });
    }
};

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    OffersManager.init();
});