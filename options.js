/**
 * Options Modal System v2.0
 * All bugs fixed + View swap + Nested structure
 */

const OptionsModal = {
    state: {
        productId: null,
        productName: null,
        basePrice: 0,
        productConfig: [],
        hasVariations: false,
        variations: [],
        selectedVariation: null,
        parentProduct: null,
        allOptionGroups: [],
        visibleGroupIds: [],
        initialGroupIds: [],
        selections: {
            main: {},
            child: {}
        },
        totalPrice: 0,
        modalInstance: null,
        validationActive: false,
        currentView: 'main',
        childViewParentGroupId: null,
        childViewParentOptionId: null,
        childViewGroupIds: [],
        childViewBackup: null,
        cpn: 1
    },

    async open(productId, productName, basePrice, productConfig, cpn = 1) {
        this.state.productId = productId;
        this.state.productName = productName;
        this.state.basePrice = parseFloat(basePrice);
        this.state.productConfig = productConfig;
        this.state.selections = { main: {}, child: {} };
        this.state.visibleGroupIds = [];
        this.state.validationActive = false;
        this.state.currentView = 'main';
        this.state.hasVariations = false;
        this.state.variations = [];
        this.state.selectedVariation = null;
        this.state.parentProduct = null;
        this.state.childViewParentGroupId = null;
        this.state.childViewParentOptionId = null;
        this.state.childViewGroupIds = [];
        this.state.childViewBackup = null;
        this.state.cpn = cpn;

        await this.loadOptionGroups();
        
        const initialGroupIds = productConfig
            .filter(cfg => cfg.initially_visible)
            .map(cfg => cfg.group_id);
        
        this.state.initialGroupIds = initialGroupIds;
        this.state.visibleGroupIds = [...initialGroupIds];
        
        this.buildModalUI();
        const footer = document.querySelector('#optionsModal .modal-footer');
        if (footer) footer.classList.remove('hide-footer');
        this.updatePrice();
        
        // Clear any existing validation UI from previous modal sessions
        const mainValidationAlerts = document.getElementById('validationAlerts');
        if (mainValidationAlerts) {
            mainValidationAlerts.classList.add('d-none');
            mainValidationAlerts.innerHTML = '';
        }
        const childValidationAlerts = document.getElementById('childValidationAlerts');
        if (childValidationAlerts) {
            childValidationAlerts.classList.add('d-none');
            childValidationAlerts.innerHTML = '';
        }
        this.clearErrorHighlights();
        
        const modalEl = document.getElementById('optionsModal');
        if (!this.state.modalInstance) {
            this.state.modalInstance = new bootstrap.Modal(modalEl);
        }

        const resetScroll = () => {
            const container = document.getElementById('optionsContainer');
            if (container) container.scrollTop = 0;
        };

        modalEl.addEventListener('shown.bs.modal', resetScroll, { once: true });
        this.state.modalInstance.show();
    },

    /**
     * Open modal with variations list
     */
    async openWithVariations(parentProduct, variations) {
        this.state.parentProduct = parentProduct;
        this.state.variations = variations;
        this.state.hasVariations = true;
        this.state.productId = null;
        this.state.productName = parentProduct.name;
        this.state.basePrice = 0;
        this.state.productConfig = [];
        this.state.selections = { main: {}, child: {} };
        this.state.visibleGroupIds = [];
        this.state.validationActive = false;
        this.state.currentView = 'variations';
        this.state.selectedVariation = null;

        await this.loadOptionGroups();
        
        this.buildModalUI();
        
        // Clear validation UI
        const mainValidationAlerts = document.getElementById('validationAlerts');
        if (mainValidationAlerts) {
            mainValidationAlerts.classList.add('d-none');
            mainValidationAlerts.innerHTML = '';
        }
        this.clearErrorHighlights();
        
        const modalEl = document.getElementById('optionsModal');
        if (!this.state.modalInstance) {
            this.state.modalInstance = new bootstrap.Modal(modalEl);
        }

        const resetScroll = () => {
            const container = document.getElementById('optionsContainer');
            if (container) container.scrollTop = 0;
        };

        modalEl.addEventListener('shown.bs.modal', resetScroll, { once: true });
        const footer = document.querySelector('#optionsModal .modal-footer');
        if (footer) footer.classList.add('hide-footer');
        this.state.modalInstance.show();
    },

    async loadOptionGroups() {
        try {
            const response = await fetch(`${BASE_PATH}/api/options.php`);
            if (!response.ok) throw new Error('Failed to load options');
            this.state.allOptionGroups = await response.json();
        } catch (error) {
            console.error('Error loading options:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to load product options. Please refresh and try again.'
            });
        }
    },

    getGroupConfig(groupId) {
        return this.state.productConfig.find(cfg => cfg.group_id === groupId) || null;
    },

    getOptionPrice(option, groupId) {
        const basePrice = parseFloat(option.price) || 0;
        if (basePrice === 0) return 0;
        const groupConfig = this.getGroupConfig(groupId);
        const adjustment = groupConfig ? (parseFloat(groupConfig.price_adjustment) || 0) : 0;
        return basePrice + adjustment;
    },

    getGroupType(groupId) {
        const groupConfig = this.getGroupConfig(groupId);
        if (!groupConfig) return 'single';
        return groupConfig.max === 1 ? 'single' : 'multiple';
    },

    isGroupRequired(groupId) {
        const groupConfig = this.getGroupConfig(groupId);
        return groupConfig ? groupConfig.min > 0 : false;
    },

    getRevealedByForOption(optionId) {
        const groupsToReveal = [];
        this.state.productConfig.forEach(cfg => {
            if (cfg.revealed_by && Array.isArray(cfg.revealed_by)) {
                if (cfg.revealed_by.includes(optionId)) {
                    groupsToReveal.push(cfg.group_id);
                }
            }
        });
        return groupsToReveal;
    },

    buildModalUI() {
        const container = document.getElementById('optionsContainer');
        
        if (!document.getElementById('viewContainer')) {
            const viewContainer = document.createElement('div');
            viewContainer.id = 'viewContainer';
            container.innerHTML = '';
            container.appendChild(viewContainer);
        }
        
        this.renderCurrentView();
        const titleText = this.state.currentView === 'variations'
            ? this.state.productName
            : this.state.productName;
        document.getElementById('modalProductName').textContent = titleText;
        this.updatePrice();
    },

    renderCurrentView() {
        const viewContainer = document.getElementById('viewContainer');
        if (!viewContainer) return;
        
        viewContainer.innerHTML = '';
        
        if (this.state.currentView === 'variations') {
            this.renderVariationsView(viewContainer);
        } else if (this.state.currentView === 'main') {
            this.renderMainView(viewContainer);
        } else {
            this.renderChildView(viewContainer);
        }
    },

    triggerViewAnimation() {
        const viewContainer = document.getElementById('viewContainer');
        if (!viewContainer) return;
        
        viewContainer.classList.remove('animate-in');
        void viewContainer.offsetWidth; // Force reflow
        viewContainer.classList.add('animate-in');
    },

    renderMainView(container) {
        if (this.state.hasVariations) {
            const backBtn = document.createElement('div');
            backBtn.className = 'mb-3';
            backBtn.innerHTML = `
                <button type="button" class="btn btn-outline-secondary btn-sm" id="backToVariationsBtn">
                    <i class="bi bi-arrow-left me-1"></i>Back to variations
                </button>
            `;
            container.appendChild(backBtn);
            
            document.getElementById('backToVariationsBtn').addEventListener('click', () => {
                this.backToVariations();
            });
        }
        this.state.visibleGroupIds.forEach(groupId => {
            const group = this.state.allOptionGroups.find(g => g.id === groupId);
            if (!group) return;
            const groupEl = this.renderOptionGroup(group, 'main', null);
            container.appendChild(groupEl);
        });
    },

    renderChildView(container) {
        const header = document.createElement('div');
        header.className = 'mb-3 pb-3 border-bottom';
        
        const parentOption = this.getParentOptionInfo();
        
        header.innerHTML = `
            <h5 class="mb-0">Choose options for ${parentOption.name}</h5>
        `;
        container.appendChild(header);
                
        const alerts = document.createElement('div');
        alerts.id = 'childValidationAlerts';
        alerts.className = 'validation-alerts d-none mb-3';
        container.appendChild(alerts);
        
        this.state.childViewGroupIds.forEach(groupId => {
            const group = this.state.allOptionGroups.find(g => g.id === groupId);
            if (!group) return;
            const groupEl = this.renderOptionGroup(group, 'child', this.state.childViewParentOptionId);
            container.appendChild(groupEl);
        });
        
        const footer = document.createElement('div');
        footer.className = 'mt-4 pt-3 border-top';
        footer.innerHTML = `
            <div class="d-flex gap-2">
                <button type="button" class="btn btn-outline-secondary" style="flex: 0 0 33%;" id="childViewBackBtn">
                    <i class="bi bi-arrow-left me-1"></i>Back
                </button>
                <button type="button" class="btn btn-primary" style="flex: 1;" id="childViewDoneBtn">Done</button>
            </div>
        `;
        container.appendChild(footer);
        
        document.getElementById('childViewDoneBtn').addEventListener('click', () => this.confirmChildView());
        document.getElementById('childViewBackBtn').addEventListener('click', () => this.cancelChildView());
        this.updateChildViewValidation();
    },

    renderVariationsView(container) {
        // Hide footer at variations level
        const footer = document.querySelector('#optionsModal .modal-footer');
        if (footer) footer.classList.add('hide-footer');
        
        const header = document.createElement('div');
        header.className = 'mb-3';
        header.innerHTML = `
            <p class="text-muted mb-3">Choose a variation to add to your cart</p>
        `;
        container.appendChild(header);
        
        const variationsList = document.createElement('div');
        variationsList.className = 'variations-list';
        
        this.state.variations.forEach(variation => {
            const varDiv = document.createElement('div');
            varDiv.className = 'd-flex justify-content-between align-items-center mb-3 pb-3 border-bottom';
            
            const hasOptions = variation.options && variation.options.length > 0;
            const isOutOfStock = variation.stock === 0;
            
            let buttonHtml = '';
            if (isOutOfStock) {
                buttonHtml = `
                    <button class="btn btn-secondary" disabled>
                        <i class="bi bi-x-circle"></i> Out of Stock
                    </button>
                `;
            } else if (hasOptions) {
                // Count option groups
                const optionCount = Array.isArray(variation.options) 
                    ? variation.options.length 
                    : variation.options.split(',').length;
                
                buttonHtml = `
                    <button class="btn btn-primary btn-select-variation" 
                            data-variation-id="${variation.id}">
                        <i class="bi bi-sliders"></i> Customize
                        <span class="badge bg-light text-primary ms-1">${optionCount} option${optionCount > 1 ? 's' : ''}</span>
                    </button>
                `;
            } else {
                buttonHtml = `
                    <button class="btn btn-success btn-add-simple-variation" 
                            data-variation-id="${variation.id}">
                        <i class="bi bi-cart-plus"></i> Add to Cart
                    </button>
                `;
            }
            const bogofOffer = typeof OffersManager !== 'undefined' ? OffersManager.isVariationBogof(variation.id) : null;
            const bogofBadge = bogofOffer ? `<span class="badge bg-danger ms-2">${bogofOffer.badge || '2 FOR 1'}</span>` : '';
            varDiv.innerHTML = `
                <div>
                    <strong>${variation.name}</strong>
                    <span class="text-primary ms-2">£${parseFloat(variation.price).toFixed(2)}</span>
                    ${bogofBadge} ${variation.dsc ? `<br><small class="text-muted">${variation.dsc}</small>` : ''}
                </div>
                ${buttonHtml}
            `;
            
            variationsList.appendChild(varDiv);
        });
        
        container.appendChild(variationsList);
        
        // Attach event listeners
        container.querySelectorAll('.btn-select-variation').forEach(btn => {
            btn.addEventListener('click', () => {
                const variationId = parseInt(btn.dataset.variationId);
                this.selectVariation(variationId);
            });
        });
        
        container.querySelectorAll('.btn-add-simple-variation').forEach(btn => {
            btn.addEventListener('click', () => {
                const variationId = parseInt(btn.dataset.variationId);
                this.addSimpleVariation(variationId);
            });
        });
    },

    selectVariation(variationId) {
        const variation = this.state.variations.find(v => v.id === variationId);
        if (!variation) return;
        
        this.state.selectedVariation = variation;
        this.state.productId = variation.id;
        this.state.productName = `${this.state.parentProduct.name} - ${variation.name}`;
        this.state.basePrice = parseFloat(variation.price);
        
        // Parse variation options config
        let productConfig = [];
        try {
            if (typeof variation.options === 'string') {
                // If it's a comma-separated string like "1,2,3"
                const groupIds = variation.options.split(',').map(id => parseInt(id.trim()));
                productConfig = groupIds.map(gId => ({
                    group_id: gId,
                    min: 0,
                    max: 0,
                    price_adjustment: 0,
                    initially_visible: true
                }));
            } else if (Array.isArray(variation.options)) {
                // If it's already an array of config objects
                productConfig = variation.options;
            }
        } catch (e) {
            console.error('Failed to parse variation options:', e);
        }
        
        this.state.productConfig = productConfig;
        
        // Set up initial visible groups
        const initialGroupIds = productConfig
            .filter(cfg => cfg.initially_visible)
            .map(cfg => cfg.group_id);
        
        this.state.initialGroupIds = initialGroupIds;
        this.state.visibleGroupIds = [...initialGroupIds];
        this.state.selections = { main: {}, child: {} };
        this.state.validationActive = false;
        
        // Switch to main options view
        this.state.currentView = 'main';
        
        // Show footer
        const footer = document.querySelector('#optionsModal .modal-footer');
        if (footer) footer.classList.remove('hide-footer');
        
        this.triggerViewAnimation();
        this.renderCurrentView();
        this.updatePrice();
        
        const container = document.getElementById('optionsContainer');
        if (container) container.scrollTop = 0;
    },

    addSimpleVariation(variationId) {
        const variation = this.state.variations.find(v => v.id === variationId);
        if (!variation) return;
        
        const fullName = `${this.state.parentProduct.name} - ${variation.name}`;
        
        // Find the button that was clicked
        const btn = document.querySelector(`.btn-add-simple-variation[data-variation-id="${variationId}"]`);
        
        if (btn) {
            // Animate button
            btn.classList.remove('btn-success');
            btn.classList.add('btn-success', 'btn-success-flash');
            btn.innerHTML = '<i class="bi bi-check-circle-fill"></i> Added!';
            btn.disabled = true;
            
            // Add to cart
            Cart.add(
                variation.id,
                fullName,
                variation.price,
                [],
                1,
                variation.cpn ?? 1
            );
            
            // Close modal after animation
            setTimeout(() => {
                if (this.state.modalInstance) {
                    this.state.modalInstance.hide();
                }
            }, 600);
        } else {
            // Fallback if button not found
            Cart.add(variation.id, fullName, variation.price, [], 1);
            if (this.state.modalInstance) {
                this.state.modalInstance.hide();
            }
        }
    },

    backToVariations() {
        // Reset state
        this.state.currentView = 'variations';
        this.state.selectedVariation = null;
        this.state.productId = null;
        this.state.basePrice = 0;
        this.state.productConfig = [];
        this.state.selections = { main: {}, child: {} };
        this.state.visibleGroupIds = [];
        this.state.validationActive = false;
        
        // Clear validation
        const mainValidationAlerts = document.getElementById('validationAlerts');
        if (mainValidationAlerts) {
            mainValidationAlerts.classList.add('d-none');
            mainValidationAlerts.innerHTML = '';
        }
        this.clearErrorHighlights();
        
        // Hide footer
        const footer = document.querySelector('#optionsModal .modal-footer');
        if (footer) footer.classList.add('hide-footer');
        
        this.triggerViewAnimation();
        this.renderCurrentView();
        
        const container = document.getElementById('optionsContainer');
        if (container) container.scrollTop = 0;
    },

    getParentOptionInfo() {
        const group = this.state.allOptionGroups.find(g => g.id === this.state.childViewParentGroupId);
        const option = group ? group.options.find(o => o.id === this.state.childViewParentOptionId) : null;
        return option || { name: 'Option' };
    },

    renderOptionGroup(group, context, parentOptionId) {
        const div = document.createElement('div');
        div.className = 'option-group mb-4 pb-3 border-bottom';
        div.dataset.groupId = group.id;
        div.dataset.context = context;

        const groupConfig = this.getGroupConfig(group.id);
        const groupType = this.getGroupType(group.id);
        const isRequired = this.isGroupRequired(group.id);

        let headerHtml = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0 fw-bold">
                    ${group.name}
                    ${isRequired ? '<span class="text-danger ms-1">*</span>' : ''}
                </h6>
                ${this.renderGroupConstraints(group.id)}
            </div>
        `;

        let optionsHtml = '';
        if (groupType === 'single') {
            optionsHtml += '<div class="btn-group-toggle-grid" role="group">';
            group.options.forEach(opt => {
                optionsHtml += this.renderSingleOption(group.id, opt, context, parentOptionId);
            });
            optionsHtml += '</div>';
        } else {
            optionsHtml += '<div class="btn-group-toggle-grid">';
            group.options.forEach(opt => {
                optionsHtml += this.renderMultipleOption(group.id, opt, context, parentOptionId);
            });
            optionsHtml += '</div>';
        }

        div.innerHTML = headerHtml + optionsHtml;
        this.attachEventListeners(div, group, context, parentOptionId);
        
        return div;
    },

    renderGroupConstraints(groupId) {
        const groupConfig = this.getGroupConfig(groupId);
        if (!groupConfig) return '';
        const groupType = this.getGroupType(groupId);
        if (groupType === 'single') return '<small class="text-muted">Select one</small>';
        
        let text = '';
        const min = groupConfig.min;
        const max = groupConfig.max;
        
        if (min > 0 && max > 0) text = `Select ${min}-${max}`;
        else if (min > 0 && max === 0) text = `Min ${min}`;
        else if (max > 0) text = `Max ${max}`;
        else if (max === 0 && min === 0) text = 'Optional';
        
        return text ? `<small class="text-muted">${text}</small>` : '';
    },

    renderSingleOption(groupId, option, context, parentOptionId) {
        const selections = this.getSelections(context, parentOptionId);
        const isSelected = selections[groupId]?.[option.id] > 0;
        const price = this.getOptionPrice(option, groupId);
        const priceStr = price > 0 ? ` <small class="text-muted">+£${price.toFixed(2)}</small>` : '';
        const buttonId = context === 'main' 
            ? `option_main_${groupId}_${option.id}`
            : `option_child_${parentOptionId}_${groupId}_${option.id}`;
        
        let badge = '';
        if (isSelected && context === 'main') {
            const revealedGroupIds = this.getRevealedByForOption(option.id);
            if (revealedGroupIds.length > 0) {
                const childCount = this.getChildSelectionCount(option.id, revealedGroupIds);
                if (childCount > 0) {
                    badge = ` <span class="badge bg-success ms-1">✓ (${childCount})</span>`;
                }
            }
        }
        
        return `
            <button type="button" 
                    class="btn ${isSelected ? 'btn-primary' : 'btn-outline-primary'} option-toggle-btn"
                    id="${buttonId}"
                    data-group-id="${groupId}"
                    data-option-id="${option.id}"
                    ${option.stock === 0 ? 'disabled' : ''}>
                ${option.name}${priceStr}${badge}
                ${option.stock === 0 ? '<span class="badge bg-secondary ms-2">Out of Stock</span>' : ''}
            </button>
        `;
    },

    getChildSelectionCount(parentOptionId, groupIds) {
        let count = 0;
        if (this.state.selections.child[parentOptionId]) {
            groupIds.forEach(gId => {
                if (this.state.selections.child[parentOptionId][gId]) {
                    count += Object.values(this.state.selections.child[parentOptionId][gId]).reduce((a, b) => a + b, 0);
                }
            });
        }
        return count;
    },

    renderMultipleOption(groupId, option, context, parentOptionId) {
        const selections = this.getSelections(context, parentOptionId);
        const quantity = selections[groupId]?.[option.id] || 0;
        const isSelected = quantity > 0;
        const price = this.getOptionPrice(option, groupId);
        const priceStr = price > 0 ? ` <small class="text-muted">£${price.toFixed(2)}</small>` : '';
        const buttonId = context === 'main'
            ? `option_main_${groupId}_${option.id}`
            : `option_child_${parentOptionId}_${groupId}_${option.id}`;
        
        return `
            <div class="d-flex gap-2 mb-2">
                <button type="button" 
                        class="btn ${isSelected ? 'btn-primary' : 'btn-outline-primary'} flex-grow-1 option-toggle-btn"
                        id="${buttonId}"
                        data-group-id="${groupId}"
                        data-option-id="${option.id}"
                        data-action="increment"
                        ${option.stock === 0 ? 'disabled' : ''}>
                    ${option.name} ${priceStr}
                    ${isSelected ? `<span class="badge bg-light text-dark ms-2">${quantity}</span>` : ''}
                    ${option.stock === 0 ? '<span class="badge bg-secondary ms-2">Out of Stock</span>' : ''}
                </button>
                ${option.stock > 0 && isSelected ? `
                    <button type="button" 
                            class="btn btn-outline-danger btn-decrement"
                            data-group-id="${groupId}"
                            data-option-id="${option.id}"
                            data-action="decrement">
                        <i class="bi bi-dash"></i>
                    </button>
                ` : ''}
            </div>
        `;
    },

    getSelections(context, parentOptionId) {
        if (context === 'main') {
            return this.state.selections.main;
        } else {
            return this.state.selections.child[parentOptionId] || {};
        }
    },

    setSelection(context, parentOptionId, groupId, optionId, quantity) {
        if (context === 'main') {
            if (!this.state.selections.main[groupId]) {
                this.state.selections.main[groupId] = {};
            }
            if (quantity === 0) {
                delete this.state.selections.main[groupId][optionId];
            } else {
                this.state.selections.main[groupId][optionId] = quantity;
            }
        } else {
            if (!this.state.selections.child[parentOptionId]) {
                this.state.selections.child[parentOptionId] = {};
            }
            if (!this.state.selections.child[parentOptionId][groupId]) {
                this.state.selections.child[parentOptionId][groupId] = {};
            }
            if (quantity === 0) {
                delete this.state.selections.child[parentOptionId][groupId][optionId];
            } else {
                this.state.selections.child[parentOptionId][groupId][optionId] = quantity;
            }
        }
    },

    attachEventListeners(groupElement, group, context, parentOptionId) {
        const groupType = this.getGroupType(group.id);

        if (groupType === 'single') {
            groupElement.querySelectorAll('.option-toggle-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const groupId = parseInt(btn.dataset.groupId);
                    const optionId = parseInt(btn.dataset.optionId);
                    this.handleSingleSelect(groupId, optionId, context, parentOptionId);
                });
            });
        } else {
            groupElement.querySelectorAll('[data-action="increment"]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const groupId = parseInt(btn.dataset.groupId);
                    const optionId = parseInt(btn.dataset.optionId);
                    this.handleMultipleSelect(groupId, optionId, 'increment', context, parentOptionId);
                });
            });

            groupElement.querySelectorAll('[data-action="decrement"]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const groupId = parseInt(btn.dataset.groupId);
                    const optionId = parseInt(btn.dataset.optionId);
                    this.handleMultipleSelect(groupId, optionId, 'decrement', context, parentOptionId);
                });
            });
        }
    },

    handleSingleSelect(groupId, optionId, context, parentOptionId) {
        const selections = this.getSelections(context, parentOptionId);
        
        const oldOptionId = Object.keys(selections[groupId] || {})[0];
        const oldOptionIdInt = oldOptionId ? parseInt(oldOptionId) : null;
        
        // For single-select groups, clear ALL existing selections in the group first
        if (context === 'main') {
            if (this.state.selections.main[groupId]) {
                // Clear child selections for the old option
                if (oldOptionIdInt && oldOptionIdInt !== optionId) {
                    if (this.state.selections.child[oldOptionIdInt]) {
                        delete this.state.selections.child[oldOptionIdInt];
                    }
                }
                // Clear the entire group selection
                this.state.selections.main[groupId] = {};
            }
        } else {
            // For child context, clear the group selection
            if (this.state.selections.child[parentOptionId]?.[groupId]) {
                this.state.selections.child[parentOptionId][groupId] = {};
            }
        }
        
        this.setSelection(context, parentOptionId, groupId, optionId, 1);
        
        if (context === 'main') {
            const revealedGroupIds = this.getRevealedByForOption(optionId);
            
            if (revealedGroupIds.length > 0) {
                this.openChildView(groupId, optionId, revealedGroupIds);
                return;
            }
        }
        
        this.renderCurrentView();
        
        if (context === 'main') {
            this.updatePrice();
            this.autoScroll(groupId, context);
        } else {
            this.updateChildViewValidation();
            this.autoScroll(groupId, context);
        }
        
        if (this.state.validationActive && context === 'main') {
            const errors = this.validate();
            this.displayValidationErrors(errors);
        }
    },

    handleMultipleSelect(groupId, optionId, action, context, parentOptionId) {
        const selections = this.getSelections(context, parentOptionId);
        
        const currentQty = selections[groupId]?.[optionId] || 0;
        let newQty = currentQty;

        if (action === 'increment') {
            newQty = currentQty + 1;
        } else if (action === 'decrement') {
            newQty = Math.max(0, currentQty - 1);
        }

        const groupConfig = this.getGroupConfig(groupId);
        const max = groupConfig ? groupConfig.max : 0;
        
        if (max > 0) {
            const totalInGroup = Object.values(selections[groupId] || {}).reduce((a, b) => a + b, 0);
            const otherSelections = totalInGroup - currentQty;
            
            if (otherSelections + newQty > max) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Maximum Reached',
                    text: `You can select a maximum of ${max} item(s) for this option group.`,
                    timer: 2000,
                    showConfirmButton: false
                });
                return;
            }
        }

        this.setSelection(context, parentOptionId, groupId, optionId, newQty);

        this.renderCurrentView();
        
        if (context === 'main') {
            this.updatePrice();
            this.autoScroll(groupId, context);
        } else {
            this.updateChildViewValidation();
            this.autoScroll(groupId, context);
        }
        
        if (this.state.validationActive && context === 'main') {
            const errors = this.validate();
            this.displayValidationErrors(errors);
        }
    },

    openChildView(parentGroupId, parentOptionId, revealedGroupIds) {
        this.state.childViewBackup = this.state.selections.child[parentOptionId] 
            ? JSON.parse(JSON.stringify(this.state.selections.child[parentOptionId]))
            : null;
        
        this.state.currentView = 'child';
        this.state.childViewParentGroupId = parentGroupId;
        this.state.childViewParentOptionId = parentOptionId;
        this.state.childViewGroupIds = revealedGroupIds;
        
        this.triggerViewAnimation();
        this.renderCurrentView();
        
        const container = document.getElementById('optionsContainer');
        if (container) container.scrollTop = 0;
    },

    cancelChildView() {
        if (this.state.childViewBackup) {
            this.state.selections.child[this.state.childViewParentOptionId] = 
                JSON.parse(JSON.stringify(this.state.childViewBackup));
        } else {
            delete this.state.selections.child[this.state.childViewParentOptionId];
        }
        
        const parentGroupId = this.state.childViewParentGroupId;
        const parentOptionId = this.state.childViewParentOptionId;
        if (this.state.selections.main[parentGroupId]) {
            delete this.state.selections.main[parentGroupId][parentOptionId];
        }
        
        this.state.currentView = 'main';
        this.state.childViewParentGroupId = null;
        this.state.childViewParentOptionId = null;
        this.state.childViewGroupIds = [];
        this.state.childViewBackup = null;
        
        this.renderCurrentView();
        this.updatePrice();
        
        const container = document.getElementById('optionsContainer');
        if (container) container.scrollTop = 0;
    },

    confirmChildView() {
        const errors = this.validateChildView();
        
        if (errors.length > 0) {
            this.displayChildValidationErrors(errors);
            return;
        }
        
        const savedParentGroupId = this.state.childViewParentGroupId;
        
        this.state.currentView = 'main';
        this.state.childViewParentGroupId = null;
        this.state.childViewParentOptionId = null;
        this.state.childViewGroupIds = [];
        this.state.childViewBackup = null;
        
        const footer = document.querySelector('#optionsModal .modal-footer');
        if (footer) footer.classList.remove('hide-footer');
        
        this.renderCurrentView();
        this.updatePrice();
        
        const container = document.getElementById('optionsContainer');
        if (container) container.scrollTop = 0;
        
        setTimeout(() => {
            if (savedParentGroupId) {
                this.autoScroll(savedParentGroupId, 'main');
            }
        }, 100);
    },

    autoScroll(currentGroupId, context) {
        const groupIds = context === 'main' 
            ? this.state.visibleGroupIds 
            : this.state.childViewGroupIds;
        
        const currentIndex = groupIds.indexOf(currentGroupId);
        if (currentIndex === -1 || currentIndex === groupIds.length - 1) return;
        
        const groupConfig = this.getGroupConfig(currentGroupId);
        const min = groupConfig ? groupConfig.min : 0;
        
        const parentOptionId = context === 'child' ? this.state.childViewParentOptionId : null;
        const selections = this.getSelections(context, parentOptionId);
        const selectedCount = Object.values(selections[currentGroupId] || {}).reduce((a, b) => a + b, 0);
        
        if (min > 0 && selectedCount < min) {
            return;
        }
        
        const nextGroupId = groupIds[currentIndex + 1];
        const selector = `[data-group-id="${nextGroupId}"][data-context="${context}"]`;
        const nextGroupEl = document.querySelector(selector);
        
        if (nextGroupEl) {
            setTimeout(() => {
                nextGroupEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 300);
        }
    },

    validateChildView() {
        const errors = [];
        const parentOptionId = this.state.childViewParentOptionId;

        this.state.childViewGroupIds.forEach(groupId => {
            const group = this.state.allOptionGroups.find(g => g.id === groupId);
            if (!group) return;

            const groupConfig = this.getGroupConfig(groupId);
            if (!groupConfig) return;

            const selections = this.state.selections.child[parentOptionId]?.[groupId] || {};
            const selectedCount = Object.values(selections).reduce((a, b) => a + b, 0);

            if (groupConfig.min > 0 && selectedCount < groupConfig.min) {
                errors.push({
                    groupId: groupId,
                    groupName: group.name,
                    message: `${group.name} requires at least ${groupConfig.min} selection(s)`
                });
            }

            if (groupConfig.max > 0 && selectedCount > groupConfig.max) {
                errors.push({
                    groupId: groupId,
                    groupName: group.name,
                    message: `${group.name} allows maximum ${groupConfig.max} selection(s)`
                });
            }
        });

        return errors;
    },

    updateChildViewValidation() {
        const errors = this.validateChildView();
        const doneBtn = document.getElementById('childViewDoneBtn');
        
        if (doneBtn) {
            if (errors.length > 0) {
                doneBtn.disabled = true;
                doneBtn.textContent = 'Complete required options';
            } else {
                doneBtn.disabled = false;
                doneBtn.textContent = 'Done';
            }
        }
    },

    displayChildValidationErrors(errors) {
        const alertsContainer = document.getElementById('childValidationAlerts');
        if (!alertsContainer) return;

        if (errors.length === 0) {
            alertsContainer.classList.add('d-none');
            alertsContainer.innerHTML = '';
            return;
        }

        let html = '<div class="alert alert-danger mb-0" role="alert">';
        html += '<div class="d-flex align-items-start">';
        html += '<i class="bi bi-exclamation-triangle-fill me-2 flex-shrink-0" style="font-size: 1.2rem;"></i>';
        html += '<div class="flex-grow-1">';
        
        if (errors.length === 1) {
            html += `<strong>${errors[0].message}</strong>`;
        } else {
            html += '<strong>Please complete the following:</strong>';
            html += '<ul class="mb-0 mt-2 ps-3">';
            errors.forEach(error => {
                html += `<li>${error.message}</li>`;
            });
            html += '</ul>';
        }
        
        html += '</div></div></div>';

        alertsContainer.innerHTML = html;
        alertsContainer.classList.remove('d-none');
    },

    updatePrice() {
        let total = this.state.basePrice;

        Object.entries(this.state.selections.main).forEach(([groupId, options]) => {
            const group = this.state.allOptionGroups.find(g => g.id === parseInt(groupId));
            if (!group) return;

            Object.entries(options).forEach(([optionId, quantity]) => {
                const option = group.options.find(o => o.id === parseInt(optionId));
                if (!option) return;

                const price = this.getOptionPrice(option, parseInt(groupId));
                total += price * quantity;
            });
        });

        Object.values(this.state.selections.child).forEach(parentSelections => {
            Object.entries(parentSelections).forEach(([groupId, options]) => {
                const group = this.state.allOptionGroups.find(g => g.id === parseInt(groupId));
                if (!group) return;

                Object.entries(options).forEach(([optionId, quantity]) => {
                    const option = group.options.find(o => o.id === parseInt(optionId));
                    if (!option) return;

                    const price = this.getOptionPrice(option, parseInt(groupId));
                    total += price * quantity;
                });
            });
        });

        this.state.totalPrice = total;

        const priceEl = document.getElementById('modalTotalPrice');
        if (priceEl) {
            priceEl.textContent = `£${total.toFixed(2)}`;
        }
    },

    validate() {
        const errors = [];

        this.state.visibleGroupIds.forEach(groupId => {
            const group = this.state.allOptionGroups.find(g => g.id === groupId);
            if (!group) return;

            const groupConfig = this.getGroupConfig(groupId);
            if (!groupConfig) return;

            const selections = this.state.selections.main[groupId] || {};
            const selectedCount = Object.values(selections).reduce((a, b) => a + b, 0);

            if (groupConfig.min > 0 && selectedCount < groupConfig.min) {
                errors.push({
                    groupId: groupId,
                    groupName: group.name,
                    message: `${group.name} requires at least ${groupConfig.min} selection(s)`
                });
            }

            if (groupConfig.max > 0 && selectedCount > groupConfig.max) {
                errors.push({
                    groupId: groupId,
                    groupName: group.name,
                    message: `${group.name} allows maximum ${groupConfig.max} selection(s)`
                });
            }
        });

        return errors;
    },

    displayValidationErrors(errors) {
        const alertsContainer = document.getElementById('validationAlerts');
        if (!alertsContainer) return;

        if (errors.length === 0) {
            alertsContainer.classList.add('d-none');
            alertsContainer.innerHTML = '';
            this.clearErrorHighlights();
            return;
        }

        let html = '<div class="alert alert-danger mb-0" role="alert">';
        html += '<div class="d-flex align-items-start">';
        html += '<i class="bi bi-exclamation-triangle-fill me-2 flex-shrink-0" style="font-size: 1.2rem;"></i>';
        html += '<div class="flex-grow-1">';
        
        if (errors.length === 1) {
            html += `<strong>${errors[0].message}</strong>`;
        } else {
            html += '<strong>Please complete the following:</strong>';
            html += '<ul class="mb-0 mt-2 ps-3">';
            errors.forEach(error => {
                html += `<li data-error-group="${error.groupId}">${error.message}</li>`;
            });
            html += '</ul>';
        }
        
        html += '</div></div></div>';

        alertsContainer.innerHTML = html;
        alertsContainer.classList.remove('d-none');

        this.highlightErrorGroups(errors);
        this.scrollToFirstError(errors);
    },

    highlightErrorGroups(errors) {
        this.clearErrorHighlights();
        errors.forEach(error => {
            const groupEl = document.querySelector(`[data-group-id="${error.groupId}"]`);
            if (groupEl) {
                groupEl.classList.add('has-error');
            }
        });
    },

    clearErrorHighlights() {
        document.querySelectorAll('.option-group.has-error').forEach(el => {
            el.classList.remove('has-error');
        });
    },

    scrollToFirstError(errors) {
        if (errors.length === 0) return;

        const firstErrorGroupId = errors[0].groupId;
        
        setTimeout(() => {
            const firstErrorGroup = document.querySelector(`[data-group-id="${firstErrorGroupId}"]`);
            
            if (firstErrorGroup) {
                firstErrorGroup.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }, 100);
    },

    addToCart() {
        this.state.validationActive = true;

        const errors = this.validate();
        
        if (errors.length > 0) {
            this.displayValidationErrors(errors);
            return;
        }

        this.displayValidationErrors([]);

        const options = this.buildOptionsArray();

        Cart.add(
            this.state.productId,
            this.state.productName,
            this.state.basePrice,
            options,
            1,
            this.state.cpn
        );
        
        if (this.state.modalInstance) {
            this.state.modalInstance.hide();
        }
    },

    buildOptionsArray() {
        const optionsArray = [];

        Object.entries(this.state.selections.main).forEach(([groupId, options]) => {
            const group = this.state.allOptionGroups.find(g => g.id === parseInt(groupId));
            if (!group) return;
            
            Object.entries(options).forEach(([optionId, quantity]) => {
                const option = group.options.find(o => o.id === parseInt(optionId));
                if (!option) return;
                
                const adjustedPrice = this.getOptionPrice(option, parseInt(groupId));
                
                optionsArray.push({
                    option_id: parseInt(optionId),
                    option_name: option.name,
                    option_price: adjustedPrice,
                    quantity: quantity,
                    group_id: parseInt(groupId),
                    group_name: group.name
                });
            });
        });

        Object.entries(this.state.selections.child).forEach(([parentOptionId, groups]) => {
            const parentOptId = parseInt(parentOptionId);
            
            let parentOptionName = '';
            let parentGroupId = null;
            let parentGroupName = '';
            
            for (const [gId, opts] of Object.entries(this.state.selections.main)) {
                if (opts[parentOptId]) {
                    parentGroupId = parseInt(gId);
                    const parentGroup = this.state.allOptionGroups.find(g => g.id === parentGroupId);
                    if (parentGroup) {
                        parentGroupName = parentGroup.name;
                        const parentOpt = parentGroup.options.find(o => o.id === parentOptId);
                        if (parentOpt) parentOptionName = parentOpt.name;
                    }
                    break;
                }
            }
            
            Object.entries(groups).forEach(([groupId, options]) => {
                const group = this.state.allOptionGroups.find(g => g.id === parseInt(groupId));
                if (!group) return;
                
                Object.entries(options).forEach(([optionId, quantity]) => {
                    const option = group.options.find(o => o.id === parseInt(optionId));
                    if (!option) return;
                    
                    const adjustedPrice = this.getOptionPrice(option, parseInt(groupId));
                    
                    optionsArray.push({
                        option_id: parseInt(optionId),
                        option_name: option.name,
                        option_price: adjustedPrice,
                        quantity: quantity,
                        group_id: parseInt(groupId),
                        group_name: group.name,
                        parent_option_id: parentOptId,
                        parent_option_name: parentOptionName,
                        parent_group_id: parentGroupId,
                        parent_group_name: parentGroupName
                    });
                });
            });
        });

        return optionsArray;
    },

    /**
     * Reset modal state (called on modal hide)
     */
    resetState() {
        this.state.hasVariations = false;
        this.state.variations = [];
        this.state.selectedVariation = null;
        this.state.parentProduct = null;
        this.state.currentView = 'main';
        this.state.validationActive = false;
        
        // Show footer by default
        const footer = document.querySelector('#optionsModal .modal-footer');
        if (footer) footer.classList.remove('hide-footer');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const modalEl = document.getElementById('optionsModal');
    if (modalEl) {
        modalEl.addEventListener('hidden.bs.modal', () => {
            OptionsModal.resetState();
        });
    }
});

window.OptionsModal = OptionsModal;

window.ProductOptions = {
    showModal(button) {
        const productId = button.dataset.productId || button.getAttribute('data-product-id');
        const productName = button.dataset.productName || button.getAttribute('data-product-name');
        const basePrice = button.dataset.productPrice || button.getAttribute('data-product-price');
        const optionsJson = button.dataset.productOptions || button.dataset.options || button.getAttribute('data-product-options') || button.getAttribute('data-options') || '[]';
        const cpn = button.dataset.cpn || button.getAttribute('data-cpn') || '1';

        let productConfig = [];
        try {
            productConfig = JSON.parse(optionsJson);
        } catch (e) {
            console.error('Failed to parse product options config:', e);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to load product configuration. Please refresh and try again.'
            });
            return;
        }
        
        OptionsModal.open(productId, productName, basePrice, productConfig, parseInt(cpn) || 1);
    },
    
    showVariationsModal(button) {
        const parentProductJson = button.dataset.parentProduct || button.getAttribute('data-parent-product');
        const variationsJson = button.dataset.variations || button.getAttribute('data-variations');
        
        let parentProduct, variations;
        try {
            parentProduct = JSON.parse(parentProductJson);
            variations = JSON.parse(variationsJson);
        } catch (e) {
            console.error('Failed to parse product/variations data:', e);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Failed to load product information. Please refresh and try again.'
            });
            return;
        }
        
        OptionsModal.openWithVariations(parentProduct, variations);
    },
    
    open: OptionsModal.open.bind(OptionsModal),
    openWithVariations: OptionsModal.openWithVariations.bind(OptionsModal)
};