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
        deliveryAvailable: true,
        validating: false,
        pendingAction: null,
        originalCartAdd: null,
        originalShowModal: null,
        originalShowVariationsModal: null,
        originalProductModalOpen: null,
        originalProductModalQuickAdd: null
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

        // Store original Cart.add and override to check method selection
        this.state.originalCartAdd = Cart.add.bind(Cart);
        Cart.add = (...args) => {
            if (!this.canAddToCart({type: 'cart_add', args: args})) {
                return false;
            }
            return this.state.originalCartAdd(...args);
        };

        // Store original ProductOptions methods and override to check method selection
        if (typeof ProductOptions !== 'undefined') {
            this.state.originalShowModal = ProductOptions.showModal.bind(ProductOptions);
            ProductOptions.showModal = (button) => {
                if (!this.canAddToCart({type: 'show_options', button: button})) {
                    return false;
                }
                return this.state.originalShowModal(button);
            };

            this.state.originalShowVariationsModal = ProductOptions.showVariationsModal.bind(ProductOptions);
            ProductOptions.showVariationsModal = (button) => {
                if (!this.canAddToCart({type: 'show_variations', button: button})) {
                    return false;
                }
                return this.state.originalShowVariationsModal(button);
            };
        }

        // Store original ProductModal methods and override to check method selection
        if (typeof ProductModal !== 'undefined') {
            this.state.originalProductModalOpen = ProductModal.open.bind(ProductModal);
            ProductModal.open = (card) => {
                if (!this.canAddToCart({type: 'product_modal_open', card: card})) {
                    return false;
                }
                return this.state.originalProductModalOpen(card);
            };

            this.state.originalProductModalQuickAdd = ProductModal.quickAdd.bind(ProductModal);
            ProductModal.quickAdd = (card) => {
                if (!this.canAddToCart({type: 'product_modal_quickadd', card: card})) {
                    return false;
                }
                return this.state.originalProductModalQuickAdd(card);
            };
        }

        // Listen for cart updates
        const originalUpdateUI = Cart.updateUI;
        Cart.updateUI = function() {
            originalUpdateUI.call(this);
            DeliveryManager.updateMinOrderWarning();
            DeliveryManager.updateCheckoutButton();
        };

        // Initialize on page load
        this.initializeMethodSelection();
        
        this.updateCheckoutButton();
    },

    /**
     * Initialize method selection on page load
     * Priority: sessionStorage method → validate postcode → wait for user
     */
    async initializeMethodSelection() {
        const storedMethod = sessionStorage.getItem('selected_method');
        
        // If collection is stored and available, select it
        if (storedMethod === 'collection') {
            const collectionBtn = document.querySelector('[data-method="collection"]');
            if (collectionBtn) {
                this.selectMethod(collectionBtn, true);
                return;
            }
        }
        
        // For delivery (or no method stored), try to validate postcode in background
        if (this.state.deliveryAvailable) {
            await this.backgroundValidation();
        } else if (storedMethod === 'delivery') {
            // Delivery was stored but no longer available - clear it
            sessionStorage.removeItem('selected_method');
            sessionStorage.removeItem('postcode_data');
            this.state.postcodeData = null;
        }
    },

    /**
     * Background validation on page load
     * Validates stored postcode or first saved address
     */
    async backgroundValidation() {
        let postcodeToValidate = null;
        let addressId = null;
        
        // Priority 1: sessionStorage postcode
        if (this.state.postcodeData?.postcode) {
            postcodeToValidate = this.state.postcodeData.postcode;
            addressId = this.state.postcodeData.addressId || null;
        }
        // Priority 2: Logged in user's first address
        else if (this.state.userAddresses.length > 0) {
            postcodeToValidate = this.state.userAddresses[0].postcode;
            addressId = this.state.userAddresses[0].id;
        }
        
        // Nothing to validate
        if (!postcodeToValidate) {
            return;
        }
        
        this.state.validating = true;
        this.setButtonsLoading(true);
        try {
            const response = await fetch(`${BASE_PATH}/checkout/validate-postcode`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `postcode=${encodeURIComponent(postcodeToValidate)}`
            });

            const result = await response.json();

            if (result.success) {
                this.state.postcodeData = {
                    postcode: postcodeToValidate,
                    addressId: addressId,
                    distance: result.data.distance,
                    deliveryFee: result.data.deliveryFee,
                    validated: true,
                    timestamp: Date.now()
                };
                sessionStorage.setItem('postcode_data', JSON.stringify(this.state.postcodeData));
                
                // Select delivery button
                const deliveryBtn = document.querySelector('[data-method="delivery"]');
                if (deliveryBtn) {
                    this.selectMethod(deliveryBtn, true);
                    this.updatePostcodeDisplay();
                }
                
                // Process any pending action
                this.processPendingAction();
            } else {
                // Invalid - clear stored data
                sessionStorage.removeItem('postcode_data');
                sessionStorage.removeItem('selected_method');
                this.state.postcodeData = null;
                
                // If there was a pending action, show the modal
                if (this.state.pendingAction) {
                    this.handleDeliverySelection();
                }
            }
        } catch (error) {
            console.error('Background validation failed:', error);
            // On network error, keep existing data but don't auto-select
        } finally {
            this.state.validating = false;
            this.setButtonsLoading(false);
        }
    },

    canAddToCart(action = null) {
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

        // If background validation is in progress, store pending and wait
        if (this.state.validating) {
            if (action) {
                this.state.pendingAction = action;
            }
            Cart.showNotification('Checking delivery availability...', 'info');
            return false;
        }

        // No method selected - need to prompt user
        if (!this.state.selectedMethod) {
            if (action) {
                this.state.pendingAction = action;
            }
            
            // If postcode already validated, auto-select delivery
            if (this.state.postcodeData) {
                const deliveryBtn = document.querySelector('[data-method="delivery"]');
                if (deliveryBtn) {
                    this.selectMethod(deliveryBtn);
                    this.processPendingAction();
                    return false; // We'll process via processPendingAction
                }
            }
            
            // Show modal for user to choose
            if (!this.state.deliveryAvailable) {
                this.showPostcodeModal('unavailable');
            } else {
                this.handleDeliverySelection();
            }
            return false;
        }

        // Delivery selected but no validated postcode
        if (this.state.selectedMethod === 'delivery' && !this.state.postcodeData) {
            if (action) {
                this.state.pendingAction = action;
            }
            this.showPostcodeModal();
            return false;
        }

        return true;
    },

    processPendingAction() {
        if (!this.state.pendingAction) return;
        
        const action = this.state.pendingAction;
        this.state.pendingAction = null;
        
        if (action.type === 'cart_add' && this.state.originalCartAdd) {
            this.state.originalCartAdd(...action.args);
        } else if (action.type === 'show_options' && this.state.originalShowModal) {
            this.state.originalShowModal(action.button);
        } else if (action.type === 'show_variations' && this.state.originalShowVariationsModal) {
            this.state.originalShowVariationsModal(action.button);
        } else if (action.type === 'product_modal_open' && this.state.originalProductModalOpen) {
            this.state.originalProductModalOpen(action.card);
        } else if (action.type === 'product_modal_quickadd' && this.state.originalProductModalQuickAdd) {
            this.state.originalProductModalQuickAdd(action.card);
        }
    },

    clearPendingAction() {
        this.state.pendingAction = null;
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

        // Update postcode display
        this.updatePostcodeDisplay();

        // If delivery and no postcode - prompt for it
        if (method === 'delivery' && !this.state.postcodeData && !isRestoring) {
            this.handleDeliverySelection();
        } else {
            this.updateMinOrderWarning();
            this.updateCheckoutButton();
        }
    },

    handleDeliverySelection() {
        if (!this.state.deliveryAvailable) {
            this.showPostcodeModal('unavailable');
            return;
        }

        const addresses = this.state.userAddresses;

        if (addresses.length === 0) {
            // No addresses - show postcode input
            this.showPostcodeModal('input');
        } else if (addresses.length === 1) {
            // Single address - validate it
            this.validateAddress(addresses[0]);
        } else {
            // Multiple addresses - show selection
            this.showPostcodeModal('select');
        }
    },

    /**
     * Validate an address (used for single address auto-validate and address selection)
     */
    async validateAddress(address, showModal = true) {
        const postcode = address.postcode;
        
        if (showModal) {
            Cart.showNotification('Checking delivery to ' + postcode + '...', 'info');
        }

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
                
                // Close modal if open
                const modalEl = document.getElementById('postcodeModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                }
                
                // Select delivery button
                const deliveryBtn = document.querySelector('[data-method="delivery"]');
                if (deliveryBtn) {
                    this.selectMethod(deliveryBtn);
                }
                
                Cart.showNotification(`Delivery to ${postcode} (£${result.data.deliveryFee.toFixed(2)} fee)`, 'success');
                
                // Process any pending action
                this.processPendingAction();
            } else {
                // Show modal with error if not already showing
                this.showPostcodeModal('input');
                this.showPostcodeError(result.data.message);
            }
        } catch (error) {
            this.showPostcodeError('Network error. Please try again.');
        }
    },

    showPostcodeModal(mode = 'input') {
        const modal = new bootstrap.Modal(document.getElementById('postcodeModal'));
        const errorDiv = document.getElementById('postcodeError');
        const unavailableSection = document.getElementById('deliveryUnavailableSection');
        const addressSection = document.getElementById('addressSelectSection');
        const inputSection = document.getElementById('postcodeInputSection');
        const validateBtn = document.getElementById('validatePostcodeBtn');
        const title = document.getElementById('postcodeModalTitle');
        const input = document.getElementById('postcodeInput');

        // Reset state
        errorDiv.classList.add('d-none');
        unavailableSection.classList.add('d-none');
        addressSection.classList.add('d-none');
        inputSection.classList.add('d-none');
        validateBtn.classList.add('d-none');

        if (mode === 'unavailable') {
            unavailableSection.classList.remove('d-none');
            title.innerHTML = '<i class="bi bi-geo-alt"></i> Delivery Unavailable';
        } else if (mode === 'select') {
            addressSection.classList.remove('d-none');
            title.innerHTML = '<i class="bi bi-geo-alt"></i> Choose Delivery Address';
            this.populateAddressList();
        } else {
            inputSection.classList.remove('d-none');
            validateBtn.classList.remove('d-none');
            title.innerHTML = '<i class="bi bi-geo-alt"></i> Delivery Postcode';
            input.value = '';
        }

        modal.show();
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
            item.onclick = () => this.validateAddress(addr);
            container.appendChild(item);
        });
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

                // Select delivery button
                const deliveryBtn = document.querySelector('[data-method="delivery"]');
                if (deliveryBtn) {
                    this.selectMethod(deliveryBtn);
                }
                
                Cart.showNotification(`Delivery to ${postcode} (£${result.data.deliveryFee.toFixed(2)} fee)`, 'success');
                
                // Process any pending action
                this.processPendingAction();
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

        // Select collection and process pending action
        const collectionBtn = document.querySelector('[data-method="collection"]');
        if (collectionBtn) {
            this.selectMethod(collectionBtn);
            this.processPendingAction();
        } else {
            this.clearPendingAction();
        }
    },

    /**
     * Update the postcode display UI
     * Shows validated postcode with change option when delivery is selected
     */
    updatePostcodeDisplay() {
        let displayEl = document.getElementById('postcodeDisplay');
        
        // Create element if it doesn't exist
        if (!displayEl) {
            const methodsSection = document.querySelector('.delivery-methods-section .card-body');
            if (!methodsSection) return;
            
            displayEl = document.createElement('div');
            displayEl.id = 'postcodeDisplay';
            displayEl.className = 'd-none mt-2 small';
            methodsSection.appendChild(displayEl);
        }
        
        // Show/hide based on state
        if (this.state.selectedMethod === 'delivery' && this.state.postcodeData) {
            const postcode = this.state.postcodeData.postcode;
            const fee = this.state.postcodeData.deliveryFee;
            
            displayEl.innerHTML = `
                <div class="d-flex justify-content-between align-items-center text-muted">
                    <span>
                        <i class="bi bi-geo-alt-fill me-1"></i>
                        ${postcode} (£${fee.toFixed(2)} fee)
                    </span>
                    <button type="button" class="btn btn-link btn-sm p-0" onclick="DeliveryManager.changePostcode()">
                        Change
                    </button>
                </div>
            `;
            displayEl.classList.remove('d-none');
        } else {
            displayEl.classList.add('d-none');
        }
    },

    /**
     * Allow user to change their postcode
     */
    changePostcode() {
        // Clear current postcode data
        this.state.postcodeData = null;
        sessionStorage.removeItem('postcode_data');
        
        // Update display
        this.updatePostcodeDisplay();
        
        // Show modal
        if (this.state.userAddresses.length > 1) {
            this.showPostcodeModal('select');
        } else {
            this.showPostcodeModal('input');
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
        const checkoutBtn = document.getElementById('checkout-btn');
        const mobileCheckoutBtn = document.getElementById('mobile-checkout-btn');
        const cartCount = Cart.getCount();
        const cartTotal = Cart.getSubtotal();
        const availableButtons = document.querySelectorAll('.delivery-method-btn');
        const noMethodsAvailable = availableButtons.length === 0;
        const belowMinOrder = this.state.minOrder > 0 && cartTotal < this.state.minOrder;

        const shouldDisable = 
            cartCount === 0 || 
            this.state.shopClosed || 
            noMethodsAvailable ||
            !this.state.selectedMethod ||
            belowMinOrder;

        // Determine button text based on state
        let desktopText = '<i class="bi bi-credit-card"></i> Checkout';
        let mobileText = '<i class="bi bi-credit-card"></i> Checkout';

        if (this.state.shopClosed) {
            desktopText = '<i class="bi bi-x-circle"></i> Shop Closed';
            mobileText = '<i class="bi bi-x-circle"></i> Closed';
        } else if (noMethodsAvailable) {
            desktopText = '<i class="bi bi-clock"></i> Not Available';
            mobileText = '<i class="bi bi-clock"></i> Not Available';
        } else if (cartCount === 0) {
            desktopText = '<i class="bi bi-credit-card"></i> Checkout';
            mobileText = '<i class="bi bi-credit-card"></i> Checkout';
        } else if (!this.state.selectedMethod) {
            desktopText = '<i class="bi bi-hand-index"></i> Choose Delivery/Collection';
            mobileText = '<i class="bi bi-hand-index"></i> Select Method';
        } else if (belowMinOrder) {
            const remaining = (this.state.minOrder - cartTotal).toFixed(2);
            desktopText = `<i class="bi bi-basket"></i> Spend £${remaining} more`;
            mobileText = `<i class="bi bi-basket"></i> £${remaining} more`;
        }

        if (checkoutBtn) {
            checkoutBtn.disabled = shouldDisable;
            checkoutBtn.innerHTML = desktopText;
        }
        
        if (mobileCheckoutBtn) {
            mobileCheckoutBtn.disabled = shouldDisable;
            mobileCheckoutBtn.innerHTML = mobileText;
        }
    },

    setButtonsLoading(loading) {
        const buttons = document.querySelectorAll('.delivery-method-btn');
        buttons.forEach(btn => {
            if (loading) {
                btn.classList.add('disabled', 'opacity-50');
                btn.style.pointerEvents = 'none';
            } else {
                btn.classList.remove('disabled', 'opacity-50');
                btn.style.pointerEvents = '';
            }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    DeliveryManager.init();
});