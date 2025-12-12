/**
 * Upsells Manager - "Customers also love" carousel with threshold intelligence
 * Reads product data from data attributes (server-rendered)
 * Only handles filtering, threshold calculation, and visibility
 */

const UpsellsManager = {
    config: {
        enabled: false,
        title: 'Customers also love'
    },

    /**
     * Initialize upsells manager
     */
    init(config) {
        if (!config || !config.enabled) return;
        
        this.config = config;
        
        // Hook into Cart.updateUI to refresh upsells
        const originalUpdateUI = Cart.updateUI.bind(Cart);
        Cart.updateUI = () => {
            originalUpdateUI();
            UpsellsManager.update();
        };
        
        // Initial update
        this.update();
    },

    /**
     * Get cart product IDs
     */
    getCartProductIds() {
        const cart = Cart.get();
        return cart.map(item => parseInt(item.product_id));
    },

    /**
     * Find the next promo threshold above current subtotal
     */
    getNextThreshold(currentSubtotal) {
        if (typeof window.autoPromos === 'undefined') return null;
        
        const applicablePromos = window.autoPromos
            .filter(promo => {
                if (!promo.minOrder || promo.minOrder <= 0) return false;
                if (promo.minOrder <= currentSubtotal) return false;
                if (promo.type === 'delivery_fee') return false;
                return true;
            })
            .sort((a, b) => a.minOrder - b.minOrder);
        
        if (applicablePromos.length === 0) return null;
        
        const nextPromo = applicablePromos[0];
        
        return {
            threshold: nextPromo.minOrder,
            type: nextPromo.type,
            value: nextPromo.value,
            maxDiscount: nextPromo.maxDiscount || null
        };
    },

    /**
     * Calculate the benefit of adding an upsell
     */
    calculateBenefit(productPrice, currentSubtotal) {
        const nextThreshold = this.getNextThreshold(currentSubtotal);
        if (!nextThreshold) return null;
        
        const newSubtotal = currentSubtotal + productPrice;
        
        if (newSubtotal < nextThreshold.threshold) return null;
        
        let discount = 0;
        if (nextThreshold.type === 'percent') {
            discount = newSubtotal * (nextThreshold.value / 100);
            if (nextThreshold.maxDiscount) {
                discount = Math.min(discount, nextThreshold.maxDiscount);
            }
        } else if (nextThreshold.type === 'fixed') {
            discount = nextThreshold.value;
        }
        
        const netCost = productPrice - discount;
        
        return {
            discountType: nextThreshold.type,
            discountValue: nextThreshold.value,
            discountAmount: discount,
            netCost: netCost
        };
    },

    /**
     * Format currency
     */
    formatPrice(amount) {
        const symbol = document.body.dataset.currency || '£';
        return symbol + Math.abs(amount).toFixed(2);
    },

    /**
     * Update upsells visibility and badges
     */
    update() {
        const desktopSection = document.getElementById('upsellsSection');
        const mobileSection = document.getElementById('mobileUpsellsSection');
        
        if (!desktopSection && !mobileSection) return;
        
        const cart = Cart.get();
        
        // Hide if cart is empty
        if (cart.length === 0) {
            if (desktopSection) desktopSection.classList.add('d-none');
            if (mobileSection) mobileSection.classList.add('d-none');
            return;
        }
        
        const cartProductIds = this.getCartProductIds();
        const currentSubtotal = Cart.getPromoSubtotal();
        
        // Process desktop cards
        let visibleCount = 0;
        visibleCount += this.processCarousel('upsellsCarousel', cartProductIds, currentSubtotal);
        
        // Process mobile cards (separate set)
        this.processCarousel('mobileUpsellsCarousel', cartProductIds, currentSubtotal);
        
        // Show/hide sections
        if (visibleCount === 0) {
            if (desktopSection) desktopSection.classList.add('d-none');
            if (mobileSection) mobileSection.classList.add('d-none');
        } else {
            if (desktopSection) desktopSection.classList.remove('d-none');
            if (mobileSection) mobileSection.classList.remove('d-none');
        }
    },

    /**
     * Process a carousel - filter, badge, sort
     */
    processCarousel(carouselId, cartProductIds, currentSubtotal) {
        const carousel = document.getElementById(carouselId);
        if (!carousel) return 0;
        
        const allCards = carousel.querySelectorAll('.upsell-card');
        const cardData = [];
        
        allCards.forEach(card => {
            const productId = parseInt(card.dataset.productId);
            const productPrice = parseFloat(card.dataset.productPrice);
            
            // Hide if already in cart
            if (cartProductIds.includes(productId)) {
                card.classList.add('d-none');
                return;
            }
            
            // Calculate benefit
            const benefit = this.calculateBenefit(productPrice, currentSubtotal);
            
            // Update benefit badge
            this.updateBenefitBadge(card, benefit, productPrice);
            
            card.classList.remove('d-none');
            
            cardData.push({
                card: card,
                benefit: benefit,
                price: productPrice
            });
        });
        
        // Sort cards: threshold-unlockers first (best deal first), then by price
        cardData.sort((a, b) => {
            if (a.benefit && !b.benefit) return -1;
            if (!a.benefit && b.benefit) return 1;
            if (a.benefit && b.benefit) {
                return a.benefit.netCost - b.benefit.netCost;
            }
            return a.price - b.price;
        });
        
        // Reorder cards in DOM
        cardData.forEach(({ card }) => {
            carousel.appendChild(card);
        });
        
        return cardData.length;
    },

    /**
     * Update benefit badge on a card
     */
    updateBenefitBadge(card, benefit, productPrice) {
        let badgeContainer = card.querySelector('.upsell-card__benefit');
        
        // Remove existing badge
        if (badgeContainer) {
            badgeContainer.remove();
        }
        
        if (!benefit) return;
        
        // Create new badge
        const badge = document.createElement('div');
        badge.className = 'upsell-card__benefit';
        
        if (benefit.netCost <= 0) {
            badge.classList.add('upsell-card__benefit--amazing');
            badge.innerHTML = `<i class="bi bi-stars"></i><span>FREE + save ${this.formatPrice(-benefit.netCost)}!</span>`;
        } else if (benefit.netCost < productPrice * 0.5) {
            badge.classList.add('upsell-card__benefit--great');
            badge.innerHTML = `<i class="bi bi-lightning-fill"></i><span>Only ${this.formatPrice(benefit.netCost)} net!</span>`;
        } else {
            badge.innerHTML = `<i class="bi bi-unlock-fill"></i><span>Unlocks ${benefit.discountValue}% off!</span>`;
        }
        
        // Insert before the price
        const footer = card.querySelector('.upsell-card__footer');
        if (footer) {
            footer.insertBefore(badge, footer.firstChild);
        }
    },

    /**
     * Add upsell product to cart (called from onclick)
     */
    addToCart(button, event) {
        event.stopPropagation();
        
        const card = button.closest('.upsell-card');
        if (!card) return;
        
        const productId = card.dataset.productId;
        const name = card.dataset.productName;
        const price = parseFloat(card.dataset.productPrice);
        const cpn = parseInt(card.dataset.productCpn) || 1;
        
        // Visual feedback - swap icon
        const icon = button.querySelector('i');
        if (icon) {
            icon.classList.remove('bi-plus');
            icon.classList.add('bi-check');
            button.classList.add('added');
        }
        
        // Add to cart
        Cart.add(productId, name, price, [], 1, cpn);
    }
};
