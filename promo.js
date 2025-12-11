/**
 * Promo Management - Live discount preview on order-online page
 */

const PromoManager = {
    state: {
        autoPromos: [],
        appliedPromos: [],
        discountableSubtotal: 0,
        selectedMethod: null
    },

    init() {
        this.state.autoPromos = window.autoPromos || [];
        
        // Hook into cart updates
        const originalUpdateUI = Cart.updateUI;
        Cart.updateUI = () => {
            originalUpdateUI.call(Cart);
            PromoManager.updateDiscountPreview();
        };

        // Hook into delivery method changes
        const originalSelectMethod = DeliveryManager.selectMethod;
        DeliveryManager.selectMethod = (button, isRestoring) => {
            originalSelectMethod.call(DeliveryManager, button, isRestoring);
            PromoManager.state.selectedMethod = DeliveryManager.state.selectedMethod;
            PromoManager.updateDiscountPreview();
            PromoManager.updatePromoBadges();
        };

        // Initial state
        this.state.selectedMethod = DeliveryManager.state.selectedMethod;
        this.updateDiscountPreview();
        this.updatePromoBadges();
    },

    /**
     * Calculate subtotal of discountable items only (cpn: 1)
     */
    getDiscountableSubtotal() {
        const cart = Cart.get();
        let subtotal = 0;
        
        cart.forEach(item => {
            // Default to discountable if cpn not set
            if (item.cpn !== 0) {
                subtotal += item.total_price * item.quantity;
            }
        });
        
        return subtotal;
    },

    /**
     * Get full subtotal (all items)
     */
    getFullSubtotal() {
        return Cart.getSubtotal();
    },

    /**
     * Check if promo applies to current method
     */
    appliesToMethod(promo) {
        // null or empty = applies to all
        if (!promo.methods || promo.methods.length === 0) {
            return true;
        }
        
        // No method selected yet - show all
        if (!this.state.selectedMethod) {
            return true;
        }
        
        return promo.methods.includes(this.state.selectedMethod);
    },

    /**
     * Calculate discount for a promo
     */
    calculateDiscount(promo, discountableSubtotal, deliveryFee = 0) {
        if (discountableSubtotal < promo.minOrder) {
            return 0;
        }

        let discount = 0;
        
        if (promo.type === 'percent') {
            discount = discountableSubtotal * promo.value / 100;
            if (promo.maxDiscount) {
                discount = Math.min(discount, promo.maxDiscount);
            }
        } else if (promo.type === 'fixed') {
            discount = promo.value;
        } else if (promo.type === 'delivery_fee') {
            discount = deliveryFee * promo.value / 100;
        }
        
        return Math.round(discount * 100) / 100;
    },

    /**
     * Update the discount preview in cart sidebar (desktop + mobile)
     */
    updateDiscountPreview() {
        const previewContainer = document.getElementById('discountPreview');
        const progressContainer = document.getElementById('discountProgress');
        const appliedContainer = document.getElementById('appliedDiscounts');
        
        // Mobile elements
        const mobilePreviewContainer = document.getElementById('mobileDiscountPreview');
        const mobileProgressContainer = document.getElementById('mobileDiscountProgress');
        const mobileAppliedContainer = document.getElementById('mobileAppliedDiscounts');
        
        if (!previewContainer) return;

        const discountableSubtotal = this.getDiscountableSubtotal();
        const fullSubtotal = this.getFullSubtotal();
        const deliveryFee = DeliveryManager.state.postcodeData?.deliveryFee || 0;
        
        let progressMessages = [];
        let appliedMessages = [];
        let totalDiscount = 0;

        // Separate stackable and non-stackable
        let stackablePromos = [];
        let nonStackablePromos = [];

        this.state.autoPromos.forEach(promo => {
            if (!this.appliesToMethod(promo)) return;
            
            const discount = this.calculateDiscount(promo, discountableSubtotal, deliveryFee);
            
            if (discount > 0) {
                const promoData = {
                    code: promo.code,
                    description: promo.description,
                    discount: discount,
                    type: promo.type,
                    stackable: promo.stackable
                };
                
                if (promo.stackable) {
                    stackablePromos.push(promoData);
                } else {
                    nonStackablePromos.push(promoData);
                }
            } else if (promo.minOrder > discountableSubtotal) {
                // Show progress towards promo
                const remaining = promo.minOrder - discountableSubtotal;
                let savingText = '';
                
                if (promo.type === 'percent') {
                    savingText = `${promo.value}% off`;
                } else if (promo.type === 'fixed') {
                    savingText = `£${promo.value.toFixed(2)} off`;
                } else if (promo.type === 'delivery_fee') {
                    savingText = 'free delivery';
                }
                
                let methodHint = '';
                if (promo.methods && promo.methods.length === 1) {
                    methodHint = ` (${promo.methods[0]})`;
                }
                
                progressMessages.push(`Spend £${remaining.toFixed(2)} more for ${savingText}${methodHint}`);
            }
        });

        // Apply stacking logic
        if (nonStackablePromos.length > 0) {
            // Sort by discount descending, pick best one
            nonStackablePromos.sort((a, b) => b.discount - a.discount);
            const bestPromo = nonStackablePromos[0];
            
            totalDiscount = bestPromo.discount;
            appliedMessages.push({
                code: bestPromo.code,
                label: bestPromo.type === 'delivery_fee' ? 'Free Delivery' : bestPromo.code,
                discount: bestPromo.discount,
                type: bestPromo.type
            });
            
            // Non-stackable means alone - ignore all stackable
        } else {
            // No non-stackable, apply all stackable
            stackablePromos.forEach(promo => {
                totalDiscount += promo.discount;
                appliedMessages.push({
                    code: promo.code,
                    label: promo.type === 'delivery_fee' ? 'Free Delivery' : promo.code,
                    discount: promo.discount,
                    type: promo.type
                });
            });
        }

        // Update UI
        if (progressMessages.length === 0 && appliedMessages.length === 0) {
            previewContainer.classList.add('d-none');
            if (mobilePreviewContainer) mobilePreviewContainer.classList.add('d-none');
            return;
        }

        previewContainer.classList.remove('d-none');
        if (mobilePreviewContainer) mobilePreviewContainer.classList.remove('d-none');

        // Render progress messages
        if (progressMessages.length > 0) {
            const progressHtml = progressMessages.map(msg => 
                `<div class="text-primary"><i class="bi bi-info-circle me-1"></i>${msg}</div>`
            ).join('');
            progressContainer.innerHTML = progressHtml;
            progressContainer.classList.remove('d-none');
            if (mobileProgressContainer) {
                mobileProgressContainer.innerHTML = progressHtml;
                mobileProgressContainer.classList.remove('d-none');
            }
        } else {
            progressContainer.classList.add('d-none');
            if (mobileProgressContainer) mobileProgressContainer.classList.add('d-none');
        }

        // Render applied discounts
        if (appliedMessages.length > 0) {
            const appliedHtml = appliedMessages.map(item => 
                `<div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="badge bg-success"><i class="bi bi-tag-fill me-1"></i>${item.label}</span>
                    <span class="text-success fw-bold">-£${item.discount.toFixed(2)}</span>
                </div>`
            ).join('');
            appliedContainer.innerHTML = appliedHtml;
            appliedContainer.classList.remove('d-none');
            if (mobileAppliedContainer) {
                mobileAppliedContainer.innerHTML = appliedHtml;
                mobileAppliedContainer.classList.remove('d-none');
            }
        } else {
            appliedContainer.classList.add('d-none');
            if (mobileAppliedContainer) mobileAppliedContainer.classList.add('d-none');
        }

        // Update subtotal display with strikethrough if discount applied
        const cartTotalOriginal = document.getElementById('cart-total-original');
        if (cartTotalOriginal) {
            const cartTotal = document.getElementById('cart-total');
            if (cartTotal && totalDiscount > 0) {
                cartTotalOriginal.textContent = `£${fullSubtotal.toFixed(2)}`;
                cartTotalOriginal.classList.remove('d-none');
                cartTotal.textContent = `£${(fullSubtotal - totalDiscount).toFixed(2)}`;
                cartTotal.classList.add('text-success');
            } else {
                cartTotalOriginal.classList.add('d-none');
                if (cartTotal) cartTotal.classList.remove('text-success');
            }
        }
        
        // Mobile strikethrough
        const mobileTotalOriginal = document.getElementById('mobile-cart-total-original');
        if (mobileTotalOriginal) {
            const mobileTotal = document.getElementById('mobile-cart-total-footer');
            if (mobileTotal && totalDiscount > 0) {
                mobileTotalOriginal.textContent = `£${fullSubtotal.toFixed(2)}`;
                mobileTotalOriginal.classList.remove('d-none');
                mobileTotal.textContent = `£${(fullSubtotal - totalDiscount).toFixed(2)}`;
                mobileTotal.classList.add('text-success');
            } else {
                mobileTotalOriginal.classList.add('d-none');
                if (mobileTotal) mobileTotal.classList.remove('text-success');
            }
        }

        // Update min order warning to use post-discount total
        this.updateMinOrderCheck(fullSubtotal - totalDiscount);
    },

    /**
     * Update min order check with post-discount total
     */
    updateMinOrderCheck(postDiscountTotal) {
        if (!DeliveryManager.state.selectedMethod) return;
        
        const minOrder = DeliveryManager.state.minOrder;
        const warningDiv = document.getElementById('minOrderWarning');
        const warningText = document.getElementById('minOrderText');
        
        if (warningDiv && warningText) {
            if (minOrder > 0 && postDiscountTotal < minOrder) {
                const remaining = minOrder - postDiscountTotal;
                warningText.textContent = `£${remaining.toFixed(2)} more required for ${DeliveryManager.state.selectedMethod}`;
                warningDiv.classList.remove('d-none');
            } else {
                warningDiv.classList.add('d-none');
            }
        }
    },

    /**
     * Update promo badge visibility based on selected method
     */
    updatePromoBadges() {
        const badges = document.querySelectorAll('[data-promo-code]');
        
        badges.forEach(badge => {
            const methodsAttr = badge.dataset.promoMethods;
            let methods = null;
            
            try {
                methods = JSON.parse(methodsAttr);
            } catch (e) {
                methods = null;
            }
            
            // null = show always
            if (!methods || methods.length === 0) {
                badge.classList.remove('opacity-50');
                return;
            }
            
            // No method selected - show all
            if (!this.state.selectedMethod) {
                badge.classList.remove('opacity-50');
                return;
            }
            
            // Check if current method matches
            if (methods.includes(this.state.selectedMethod)) {
                badge.classList.remove('opacity-50');
            } else {
                badge.classList.add('opacity-50');
            }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    PromoManager.init();
});