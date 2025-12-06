/**
 * Delivery Method & Postcode Validation
 */

const DeliveryManager = {
    state: {
        selectedMethod: null,
        postcodeData: null,
        minOrder: 0,
        deliveryFee: 0,
        shopClosed: false,
        userAddresses: [],
        deliveryAvailable: true
    },

    init() {
        // Load user addresses from page
        this.state.userAddresses = window.userAddresses || [];
        this.state.deliveryAvailable = window.deliveryAvailable ?? true;
        
        // Check if shop is closed
        const deliverySection = document.querySelector('.delivery-methods-section');
        this.state.shopClosed = deliverySection && deliverySection.querySelector('.alert-danger') !== null;
        
        // Load postcode from sessionStorage
        const stored = sessionStorage.getItem('postcode_data');
        if (stored) {
            try {
                this.state.postcodeData = JSON.parse(stored);
            } catch (e) {
                sessionStorage.removeItem('postcode_data');
            }
        }

        // Load last selected method from sessionStorage
        const storedMethod = sessionStorage.getItem('selected_method');
        if (storedMethod) {
            const methodBtn = document.querySelector(`[data-method="${storedMethod}"]`);
            if (methodBtn) {
                this.selectMethod(methodBtn, true); // true = restoring from storage
            }
        }

        // Override Cart.add to check method selection
        const originalAdd = Cart.add;
        Cart.add = (...args) => {
            if (!DeliveryManager.canAddToCart()) {
                return false;
            }
            return originalAdd.apply(Cart, args);
        };

        // Listen for cart updates
        const originalUpdateUI = Cart.updateUI;
        Cart.updateUI = function() {
            originalUpdateUI.call(this);
            DeliveryManager.updateMinOrderWarning();
            DeliveryManager.updateCheckoutButton();
        };
        
        this.updateCheckoutButton();
    },

    canAddToCart() {
        if (this.state.shopClosed) {
            Swal.fire({
                icon: 'error',
                title: 'Shop Closed',
                text: 'Sorry, we are currently closed for orders.',
                confirmButtonText: 'OK'
            });
            return false;
        }

        const availableButtons = document.querySelectorAll('.delivery-method-btn');
        if (availableButtons.length === 0) {
            Swal.fire({
                icon: 'error',
                title: 'No Service Available',
                text: 'Sorry, ordering is not available at this time.',
                confirmButtonText: 'OK'
            });
            return false;
        }

        if (!this.state.selectedMethod) {
            // If postcode already validated, auto-select delivery and continue
            if (this.state.postcodeData) {
                const deliveryBtn = document.querySelector('[data-method="delivery"]');
                if (deliveryBtn) {
                    this.selectMethod(deliveryBtn);
                    return true;
                }
            }
            
            if (!this.state.deliveryAvailable) {
                this.showPostcodeModal('unavailable');
            } else {
                this.handleDeliverySelection();
            }
            return false;
        }

        if (this.state.selectedMethod === 'delivery' && !this.state.postcodeData) {
            this.showPostcodeModal();
            return false;
        }

        return true;
    },

    selectMethod(button, isRestoring = false) {
        const method = button.dataset.method;
        const minOrder = parseFloat(button.dataset.minOrder);

        // Deselect all buttons
        document.querySelectorAll('.delivery-method-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.method === 'delivery') {
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-outline-primary');
            } else {
                btn.classList.remove('btn-warning');
                btn.classList.add('btn-outline-warning');
            }
        });

        // Select this button
        button.classList.add('active');
        if (method === 'delivery') {
            button.classList.remove('btn-outline-primary');
            button.classList.add('btn-primary');
        } else {
            button.classList.remove('btn-outline-warning');
            button.classList.add('btn-warning');
        }

        this.state.selectedMethod = method;
        this.state.minOrder = minOrder;
        sessionStorage.setItem('selected_method', method);

        // If delivery and no postcode
        if (method === 'delivery' && !this.state.postcodeData) {
            this.handleDeliverySelection(isRestoring);
        } else {
            this.updateMinOrderWarning();
            this.updateCheckoutButton();
        }
    },

    handleDeliverySelection(isRestoring = false) {
        // Check if delivery is available
        if (!this.state.deliveryAvailable) {
            this.showPostcodeModal('unavailable');
            return;
        }

        const addresses = this.state.userAddresses;

        if (addresses.length === 0) {
            // No addresses - show postcode input
            this.showPostcodeModal('input');
        } else if (addresses.length === 1) {
            // Single address - auto-validate silently
            this.autoValidateAddress(addresses[0]);
        } else {
            // Multiple addresses - show selection
            this.showPostcodeModal('select');
        }
    },

    async autoValidateAddress(address) {
        const postcode = address.postcode;
        
        // Show subtle loading indicator
        Cart.showNotification('Checking delivery to ' + postcode + '...', 'info');

        try {
            const response = await fetch(`${BASE_PATH}/checkout/validate-postcode`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `postcode=${encodeURIComponent(postcode)}`
            });

            const result = await response.json();

            if (result.success) {
                this.state.postcodeData = {
                    postcode: postcode,
                    addressId: address.id,
                    distance: result.data.distance,
                    deliveryFee: result.data.deliveryFee,
                    validated: true,
                    timestamp: Date.now()
                };
                sessionStorage.setItem('postcode_data', JSON.stringify(this.state.postcodeData));
                
                this.updateMinOrderWarning();
                this.updateCheckoutButton();
                Cart.showNotification(`Delivery available to ${postcode} (£${result.data.deliveryFee.toFixed(2)} fee)`, 'success');
            } else {
                // Address not in delivery area - show modal with option to enter different postcode
                this.showPostcodeModal('input');
                Cart.showNotification(result.data.message, 'warning');
            }
        } catch (error) {
            console.error('Auto-validate error:', error);
            this.showPostcodeModal('input');
        }
    },

    showPostcodeModal(mode = 'input') {
        const modal = document.getElementById('postcodeModal');
        if (!modal) return;

        const titleEl = document.getElementById('postcodeModalTitle');
        const unavailableSection = document.getElementById('deliveryUnavailableSection');
        const selectSection = document.getElementById('addressSelectSection');
        const inputSection = document.getElementById('postcodeInputSection');
        const validateBtn = document.getElementById('validatePostcodeBtn');
        const errorDiv = document.getElementById('postcodeError');

        // Reset
        unavailableSection.classList.add('d-none');
        selectSection.classList.add('d-none');
        inputSection.classList.add('d-none');
        validateBtn.classList.remove('d-none');
        if (errorDiv) errorDiv.classList.add('d-none');

        if (mode === 'unavailable') {
            titleEl.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Delivery Unavailable';
            unavailableSection.classList.remove('d-none');
            validateBtn.classList.add('d-none');
        } else if (mode === 'select') {
            titleEl.innerHTML = '<i class="bi bi-geo-alt"></i> Select Address';
            selectSection.classList.remove('d-none');
            this.populateAddressList();
            validateBtn.classList.add('d-none');
        } else {
            titleEl.innerHTML = '<i class="bi bi-geo-alt"></i> Delivery Postcode';
            inputSection.classList.remove('d-none');
        }

        const modalInstance = new bootstrap.Modal(modal);
        modalInstance.show();
    },

    populateAddressList() {
        const container = document.getElementById('addressList');
        container.innerHTML = '';

        this.state.userAddresses.forEach(addr => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${addr.address_1}</strong>
                        ${addr.address_2 ? `<br><small class="text-muted">${addr.address_2}</small>` : ''}
                        <br><small class="text-muted">${addr.postcode}</small>
                    </div>
                    <i class="bi bi-chevron-right"></i>
                </div>
            `;
            item.onclick = () => this.selectAddress(addr);
            container.appendChild(item);
        });
    },

    async selectAddress(address) {
        const modal = bootstrap.Modal.getInstance(document.getElementById('postcodeModal'));
        
        // Show loading on the selected item
        const postcode = address.postcode;

        try {
            const response = await fetch(`${BASE_PATH}/checkout/validate-postcode`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `postcode=${encodeURIComponent(postcode)}`
            });

            const result = await response.json();

            if (result.success) {
                this.state.postcodeData = {
                    postcode: postcode,
                    addressId: address.id,
                    distance: result.data.distance,
                    deliveryFee: result.data.deliveryFee,
                    validated: true,
                    timestamp: Date.now()
                };
                sessionStorage.setItem('postcode_data', JSON.stringify(this.state.postcodeData));

                modal.hide();
                this.updateMinOrderWarning();
                this.updateCheckoutButton();
                Cart.showNotification(`Delivery available to ${postcode} (£${result.data.deliveryFee.toFixed(2)} fee)`, 'success');
            } else {
                this.showPostcodeError(result.data.message);
            }
        } catch (error) {
            this.showPostcodeError('Network error. Please try again.');
        }
    },

    showPostcodeInput() {
        // Switch from address list to postcode input
        document.getElementById('addressSelectSection').classList.add('d-none');
        document.getElementById('postcodeInputSection').classList.remove('d-none');
        document.getElementById('validatePostcodeBtn').classList.remove('d-none');
        document.getElementById('postcodeModalTitle').innerHTML = '<i class="bi bi-geo-alt"></i> Delivery Postcode';
    },

    async validatePostcode() {
        const input = document.getElementById('postcodeInput');
        const postcode = input.value.trim().toUpperCase();

        if (!postcode) {
            this.showPostcodeError('Please enter a postcode');
            return;
        }

        const btn = document.getElementById('validatePostcodeBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Checking...';

        try {
            const response = await fetch(`${BASE_PATH}/checkout/validate-postcode`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `postcode=${encodeURIComponent(postcode)}`
            });

            const result = await response.json();

            if (result.success) {
                this.state.postcodeData = {
                    postcode: postcode,
                    distance: result.data.distance,
                    deliveryFee: result.data.deliveryFee,
                    validated: true,
                    timestamp: Date.now()
                };
                sessionStorage.setItem('postcode_data', JSON.stringify(this.state.postcodeData));

                const modal = bootstrap.Modal.getInstance(document.getElementById('postcodeModal'));
                modal.hide();

                this.updateMinOrderWarning();
                this.updateCheckoutButton();
                Cart.showNotification(`Delivery available to ${postcode} (£${result.data.deliveryFee.toFixed(2)} fee)`, 'success');
            } else {
                this.showPostcodeError(result.data.message);
            }
        } catch (error) {
            this.showPostcodeError('Network error. Please try again.');
        } finally {
            btn.disabled = false;
            btn.innerHTML = 'Check Delivery';
        }
    },

    showPostcodeError(message) {
        const errorDiv = document.getElementById('postcodeError');
        errorDiv.textContent = message;
        errorDiv.classList.remove('d-none');
    },

    closePostcodeModal() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('postcodeModal'));
        modal.hide();

        const collectionBtn = document.querySelector('[data-method="collection"]');
        if (collectionBtn) {
            this.selectMethod(collectionBtn);
        }
    },

    updateMinOrderWarning() {
        if (!this.state.selectedMethod) return;

        const cartTotal = Cart.getSubtotal();
        const minOrder = this.state.minOrder;
        
        const warningDiv = document.getElementById('minOrderWarning');
        const warningText = document.getElementById('minOrderText');
        if (warningDiv && warningText) {
            if (minOrder > 0 && cartTotal < minOrder) {
                const remaining = minOrder - cartTotal;
                warningText.textContent = `£${remaining.toFixed(2)} more required for ${this.state.selectedMethod}`;
                warningDiv.classList.remove('d-none');
            } else {
                warningDiv.classList.add('d-none');
            }
        }
    },

    updateCheckoutButton() {
        const checkoutBtns = document.querySelectorAll('#checkout-btn, #mobile-checkout-btn');
        const cartCount = Cart.getCount();
        const cartTotal = Cart.getSubtotal();

        checkoutBtns.forEach(btn => {
            const shouldDisable = 
                cartCount === 0 || 
                this.state.shopClosed || 
                !this.state.selectedMethod ||
                (this.state.minOrder > 0 && cartTotal < this.state.minOrder);

            btn.disabled = shouldDisable;
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    DeliveryManager.init();
});