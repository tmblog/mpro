/**
 * Product Modal System v2.0 (Modern Layout)
 * Handles product detail modal with proper child view navigation
 * Based on existing OptionsModal patterns
 */

const ProductModal = {
    state: {
        // Product info
        productId: null,
        productName: '',
        basePrice: 0,
        productData: null,
        cpn: 1,
        
        // Variations
        hasVariations: false,
        variations: [],
        selectedVariation: null,
        parentProduct: null,
        
        // Options
        productConfig: [],
        allOptionGroups: [],
        visibleGroupIds: [],
        initialGroupIds: [],
        
        // Selections (same structure as existing OptionsModal)
        selections: {
            main: {},    // { groupId: { optionId: quantity } }
            child: {}    // { parentOptionId: { groupId: { optionId: quantity } } }
        },
        
        // UI state
        quantity: 1,
        totalPrice: 0,
        modalInstance: null,
        descriptionExpanded: false,
        
        // View management
        currentView: 'main',  // 'variations' | 'main' | 'child'
        childViewParentGroupId: null,
        childViewParentOptionId: null,
        childViewGroupIds: []
    },

    /**
     * Initialize modal instance
     */
    init() {
        const modalEl = document.getElementById('productModal');
        if (modalEl && !this.state.modalInstance) {
            this.state.modalInstance = new bootstrap.Modal(modalEl);
            
            modalEl.addEventListener('hidden.bs.modal', () => {
                this.resetState();
            });
        }
    },

    /**
     * Open modal from product card click
     */
    async open(cardElement) {
        this.init();
        
        const isAvailable = cardElement.dataset.available === '1';
        if (!isAvailable) return;
        
        const productData = JSON.parse(cardElement.dataset.product);
        const hasVariations = cardElement.dataset.hasVariations === '1';
        
        this.resetState();
        
        this.state.productData = productData;
        this.state.productName = productData.name;
        this.state.hasVariations = hasVariations;
        
        if (hasVariations) {
            this.state.variations = JSON.parse(cardElement.dataset.variations);
            this.state.parentProduct = productData;
            this.state.currentView = 'variations';
            this.state.productId = null;
            this.state.basePrice = 0;
            this.state.productConfig = [];
        } else {
            this.state.productId = productData.id;
            this.state.basePrice = parseFloat(productData.price) || 0;
            this.state.productConfig = productData.options || [];
            this.state.currentView = 'main';
            this.state.cpn = productData.cpn || 1;
            
            // Set up initially visible groups
            const initialGroupIds = this.state.productConfig
                .filter(cfg => cfg.initially_visible)
                .map(cfg => cfg.group_id);
            this.state.initialGroupIds = initialGroupIds;
            this.state.visibleGroupIds = [...initialGroupIds];
        }
        
        await this.loadOptionGroups();
        this.updateModalUI();
        this.state.modalInstance.show();
    },

    /**
     * Quick add - opens modal for products with options, direct add for simple
     */
    quickAdd(cardElement) {
        const isAvailable = cardElement.dataset.available === '1';
        if (!isAvailable) return;
        
        const productData = JSON.parse(cardElement.dataset.product);
        const hasVariations = cardElement.dataset.hasVariations === '1';
        const hasOptions = productData.options && productData.options.length > 0;
        
        if (hasVariations || hasOptions) {
            this.open(cardElement);
            return;
        }
        
        // Simple product - add directly
        Cart.add(
            productData.id,
            productData.name,
            productData.price,
            [],
            1,
            productData.cpn || 1
        );
        
        // Show checkmark feedback
        const btn = cardElement.querySelector('.menu-product-card__quick-add');
        if (btn) {
            btn.classList.add('added');
            setTimeout(() => btn.classList.remove('added'), 1500);
        }
    },

    /**
     * Load option groups from API
     */
    async loadOptionGroups() {
        try {
            const response = await fetch(`${BASE_PATH}/api/options.php`);
            if (!response.ok) throw new Error('Failed to load options');
            this.state.allOptionGroups = await response.json();
        } catch (error) {
            console.error('Error loading options:', error);
            this.state.allOptionGroups = [];
        }
    },

    // ==========================================
    // UI RENDERING
    // ==========================================

    updateModalUI() {
        // Image
        const imgEl = document.getElementById('modalProductImage');
        const placeholderEl = document.querySelector('.product-modal__image-placeholder');
        
        if (this.state.productData.img) {
            imgEl.src = `${BASE_PATH}/assets/images/products/${this.state.productData.img}`;
            imgEl.alt = this.state.productName;
            imgEl.classList.remove('d-none');
            placeholderEl.classList.add('d-none');
        } else {
            imgEl.classList.add('d-none');
            placeholderEl.classList.remove('d-none');
        }
        
        // Title
        document.getElementById('modalProductTitle').textContent = this.state.productName;
        
        // Description
        this.renderDescription();
        
        // Allergens
        this.renderAllergens();
        
        // Render current view
        this.renderCurrentView();
        
        // Update footer visibility
        this.updateFooterVisibility();
        
        // Update price
        this.updatePrice();
        
        // Reset quantity
        this.state.quantity = 1;
        document.getElementById('modalQtyValue').value = 1;
        document.getElementById('modalQtyMinus').disabled = true;
    },

    renderDescription() {
        const descEl = document.getElementById('modalProductDescription');
        const readMoreEl = document.getElementById('modalReadMore');
        const description = this.state.productData.dsc || '';
        
        if (description) {
            descEl.textContent = description;
            descEl.classList.remove('d-none');
            
            if (description.length > 150) {
                descEl.classList.add('truncated');
                readMoreEl.classList.remove('d-none');
                readMoreEl.textContent = 'Read more';
                this.state.descriptionExpanded = false;
            } else {
                descEl.classList.remove('truncated');
                readMoreEl.classList.add('d-none');
            }
        } else {
            descEl.classList.add('d-none');
            readMoreEl.classList.add('d-none');
        }
    },

    renderAllergens() {
        const allergensEl = document.getElementById('modalAllergens');
        const allergens = this.state.productData.allergens || [];
        
        if (allergens.length > 0) {
            allergensEl.innerHTML = allergens.map(a => 
                `<span class="product-modal__allergen"><i class="bi bi-exclamation-triangle-fill"></i>${a}</span>`
            ).join('');
            allergensEl.classList.remove('d-none');
        } else {
            allergensEl.classList.add('d-none');
        }
    },

    renderCurrentView() {
        const container = document.getElementById('modalOptionsContainer');
        container.innerHTML = '';
        
        if (this.state.currentView === 'variations') {
            this.renderVariationsView(container);
        } else if (this.state.currentView === 'main') {
            this.renderMainView(container);
        } else if (this.state.currentView === 'child') {
            this.renderChildView(container);
        }
    },

    updateFooterVisibility() {
        const footer = document.querySelector('.product-modal__footer');
        if (!footer) return;
        
        if (this.state.currentView === 'variations' || this.state.currentView === 'child') {
            footer.classList.add('d-none');
        } else {
            footer.classList.remove('d-none');
        }
    },

    // ==========================================
    // VARIATIONS VIEW
    // ==========================================

    renderVariationsView(container) {
        const header = document.createElement('div');
        header.className = 'mb-3';
        header.innerHTML = `<p class="text-muted">Choose a size to continue</p>`;
        container.appendChild(header);
        
        const list = document.createElement('div');
        list.className = 'variation-list';
        
        this.state.variations.forEach(variation => {
            const hasOptions = variation.options && variation.options.length > 0;
            const isOutOfStock = variation.stock === 0;
            
            // Check for BOGOF offer on this variation
            const bogofOffer = typeof OffersManager !== 'undefined' 
                ? OffersManager.getBogofOffer(variation.id) 
                : null;
            const bogofBadge = bogofOffer 
                ? `<span class="badge bg-danger ms-2">${bogofOffer.badge || '2 FOR 1'}</span>` 
                : '';
            
            const item = document.createElement('div');
            item.className = 'variation-item d-flex justify-content-between align-items-center py-3 border-bottom';
            
            let buttonHtml = '';
            if (isOutOfStock) {
                buttonHtml = `<button class="btn btn-secondary btn-sm" disabled>Out of Stock</button>`;
            } else if (hasOptions) {
                buttonHtml = `
                    <button class="btn btn-primary btn-sm btn-select-variation" data-variation-id="${variation.id}">
                        <i class="bi bi-sliders me-1"></i>Customize
                    </button>`;
            } else {
                buttonHtml = `
                    <button class="btn btn-success btn-sm btn-add-simple-variation" data-variation-id="${variation.id}">
                        <i class="bi bi-cart-plus me-1"></i>Add
                    </button>`;
            }
            
            item.innerHTML = `
                <div>
                    <strong>${variation.name}</strong>${bogofBadge}
                    <span class="text-primary ms-2">£${parseFloat(variation.price).toFixed(2)}</span>
                    ${variation.dsc ? `<br><small class="text-muted">${variation.dsc}</small>` : ''}
                </div>
                ${buttonHtml}
            `;
            
            list.appendChild(item);
        });
        
        container.appendChild(list);
        
        // Event listeners
        container.querySelectorAll('.btn-select-variation').forEach(btn => {
            btn.addEventListener('click', () => this.selectVariation(parseInt(btn.dataset.variationId)));
        });
        
        container.querySelectorAll('.btn-add-simple-variation').forEach(btn => {
            btn.addEventListener('click', () => this.addSimpleVariation(parseInt(btn.dataset.variationId)));
        });
    },

    selectVariation(variationId) {
        const variation = this.state.variations.find(v => v.id === variationId);
        if (!variation) return;
        
        this.state.selectedVariation = variation;
        this.state.productId = variation.id;
        this.state.productName = `${this.state.parentProduct.name} - ${variation.name}`;
        this.state.basePrice = parseFloat(variation.price);
        this.state.cpn = variation.cpn || 1;
        
        // Parse variation options config
        let productConfig = [];
        if (Array.isArray(variation.options)) {
            productConfig = variation.options;
        }
        
        this.state.productConfig = productConfig;
        
        const initialGroupIds = productConfig
            .filter(cfg => cfg.initially_visible)
            .map(cfg => cfg.group_id);
        
        this.state.initialGroupIds = initialGroupIds;
        this.state.visibleGroupIds = [...initialGroupIds];
        this.state.selections = { main: {}, child: {} };
        
        // Switch to main view
        this.state.currentView = 'main';
        
        // Update title
        document.getElementById('modalProductTitle').textContent = this.state.productName;
        
        this.renderCurrentView();
        this.updateFooterVisibility();
        this.updatePrice();
        
        // Scroll to top
        document.getElementById('modalOptionsContainer').scrollTop = 0;
    },

    addSimpleVariation(variationId) {
        const variation = this.state.variations.find(v => v.id === variationId);
        if (!variation) return;
        
        const fullName = `${this.state.parentProduct.name} - ${variation.name}`;
        
        Cart.add(variation.id, fullName, variation.price, [], 1, variation.cpn || 1);
        
        this.state.modalInstance.hide();
    },

    // ==========================================
    // MAIN VIEW
    // ==========================================

    renderMainView(container) {
        // Back to variations button if applicable
        if (this.state.hasVariations) {
            const backBtn = document.createElement('div');
            backBtn.className = 'mb-3';
            backBtn.innerHTML = `
                <button type="button" class="btn btn-outline-secondary btn-sm" id="backToVariationsBtn">
                    <i class="bi bi-arrow-left me-1"></i>Back to sizes
                </button>
            `;
            container.appendChild(backBtn);
            document.getElementById('backToVariationsBtn')?.addEventListener('click', () => this.backToVariations());
        }
        
        // Render visible option groups
        this.state.visibleGroupIds.forEach(groupId => {
            const group = this.state.allOptionGroups.find(g => g.id === groupId);
            if (!group) return;
            
            const groupEl = this.renderOptionGroup(group, 'main', null);
            container.appendChild(groupEl);
        });
    },

    backToVariations() {
        this.state.currentView = 'variations';
        this.state.selectedVariation = null;
        this.state.productId = null;
        this.state.basePrice = 0;
        this.state.productConfig = [];
        this.state.selections = { main: {}, child: {} };
        this.state.visibleGroupIds = [];
        this.state.productName = this.state.parentProduct.name;
        
        document.getElementById('modalProductTitle').textContent = this.state.productName;
        
        this.renderCurrentView();
        this.updateFooterVisibility();
        this.updatePrice();
    },

    // ==========================================
    // CHILD VIEW
    // ==========================================

    openChildView(parentGroupId, parentOptionId, groupIds) {
        this.state.childViewParentGroupId = parentGroupId;
        this.state.childViewParentOptionId = parentOptionId;
        this.state.childViewGroupIds = groupIds;
        this.state.currentView = 'child';
        
        // Animate transition
        const container = document.getElementById('modalOptionsContainer');
        container.classList.add('view-transitioning');
        container.style.opacity = '0';
        container.style.transform = 'translateX(1rem)';
        
        setTimeout(() => {
            this.renderCurrentView();
            this.updateFooterVisibility();
            container.scrollTop = 0;
            
            requestAnimationFrame(() => {
                container.style.transition = 'opacity 200ms ease, transform 200ms ease';
                container.style.opacity = '1';
                container.style.transform = 'translateX(0)';
                
                setTimeout(() => {
                    container.classList.remove('view-transitioning');
                    container.style.transition = '';
                }, 200);
            });
        }, 50);
    },

    renderChildView(container) {
        const parentOption = this.getParentOptionInfo();
        
        // Header with back button
        const header = document.createElement('div');
        header.className = 'mb-3 pb-3 border-bottom';
        header.innerHTML = `
            <button type="button" class="btn btn-outline-secondary btn-sm mb-2" id="childViewBackBtn">
                <i class="bi bi-arrow-left me-1"></i>Back
            </button>
            <h5 class="mb-0">Options for ${parentOption.name}</h5>
        `;
        container.appendChild(header);
        
        document.getElementById('childViewBackBtn')?.addEventListener('click', () => this.cancelChildView());
        
        // Render child option groups
        this.state.childViewGroupIds.forEach(groupId => {
            const group = this.state.allOptionGroups.find(g => g.id === groupId);
            if (!group) return;
            
            const groupEl = this.renderOptionGroup(group, 'child', this.state.childViewParentOptionId);
            container.appendChild(groupEl);
        });
        
        // Done button
        const footer = document.createElement('div');
        footer.className = 'mt-4 pt-3 border-top';
        footer.innerHTML = `
            <button type="button" class="btn btn-primary w-100" id="childViewDoneBtn">
                <i class="bi bi-check2 me-1"></i>Confirm
            </button>
        `;
        container.appendChild(footer);
        
        document.getElementById('childViewDoneBtn')?.addEventListener('click', () => this.confirmChildView());
    },

    getParentOptionInfo() {
        const group = this.state.allOptionGroups.find(g => g.id === this.state.childViewParentGroupId);
        const option = group?.options.find(o => o.id === this.state.childViewParentOptionId);
        return option || { name: 'Option' };
    },

    confirmChildView() {
        // Validate child selections
        const errors = this.validateChildSelections();
        
        if (errors.length > 0) {
            this.displayValidationErrors(errors, 'child');
            return;
        }
        
        const parentGroupId = this.state.childViewParentGroupId;
        
        // Animate transition back to main
        const container = document.getElementById('modalOptionsContainer');
        container.style.opacity = '0';
        container.style.transform = 'translateX(-1rem)';
        
        setTimeout(() => {
            this.state.currentView = 'main';
            this.renderCurrentView();
            this.updateFooterVisibility();
            this.updatePrice();
            
            requestAnimationFrame(() => {
                container.style.transition = 'opacity 200ms ease, transform 200ms ease';
                container.style.opacity = '1';
                container.style.transform = 'translateX(0)';
                
                setTimeout(() => {
                    container.style.transition = '';
                    // Scroll to next required section in main view
                    this.autoScrollToNextRequired(parentGroupId);
                }, 200);
            });
        }, 50);
    },

    cancelChildView() {
        // Clear child selections for this parent option
        delete this.state.selections.child[this.state.childViewParentOptionId];
        
        // Also deselect the parent option
        const parentGroupId = this.state.childViewParentGroupId;
        const parentOptionId = this.state.childViewParentOptionId;
        
        if (this.state.selections.main[parentGroupId]) {
            delete this.state.selections.main[parentGroupId][parentOptionId];
        }
        
        // Animate transition back to main
        const container = document.getElementById('modalOptionsContainer');
        container.style.opacity = '0';
        container.style.transform = 'translateX(-1rem)';
        
        setTimeout(() => {
            this.state.currentView = 'main';
            this.renderCurrentView();
            this.updateFooterVisibility();
            this.updatePrice();
            
            requestAnimationFrame(() => {
                container.style.transition = 'opacity 200ms ease, transform 200ms ease';
                container.style.opacity = '1';
                container.style.transform = 'translateX(0)';
                
                setTimeout(() => {
                    container.style.transition = '';
                }, 200);
            });
        }, 50);
    },

    validateChildSelections() {
        const errors = [];
        const parentOptionId = this.state.childViewParentOptionId;
        
        this.state.childViewGroupIds.forEach(groupId => {
            const config = this.state.productConfig.find(c => c.group_id === groupId);
            if (!config || config.min === 0) return;
            
            const selections = this.state.selections.child[parentOptionId]?.[groupId] || {};
            const count = Object.values(selections).reduce((sum, qty) => sum + qty, 0);
            
            if (count < config.min) {
                const group = this.state.allOptionGroups.find(g => g.id === groupId);
                errors.push({
                    type: 'option',
                    groupId: groupId,
                    message: `Please select ${config.min === 1 ? 'an option' : config.min + ' options'} for ${group?.name || 'this group'}`
                });
            }
        });
        
        return errors;
    },

    // ==========================================
    // OPTION GROUP RENDERING
    // ==========================================

    renderOptionGroup(group, context, parentOptionId) {
        const div = document.createElement('div');
        div.className = 'option-group mb-4';
        div.dataset.groupId = group.id;
        div.dataset.context = context;
        
        const config = this.getGroupConfig(group.id);
        const groupType = config && config.max === 1 ? 'single' : 'multiple';
        const isRequired = config && config.min > 0;
        
        // Header
        const header = document.createElement('div');
        header.className = 'option-group__header';
        header.innerHTML = `
            <h4 class="option-group__title" id="groupTitle_${group.id}">${group.name}</h4>
            <span class="option-group__badge${isRequired ? ' required' : ''}" id="groupBadge_${group.id}">
                ${isRequired ? 'Required' : 'Optional'}
            </span>
        `;
        div.appendChild(header);
        
        // Constraint hint
        if (config && config.max !== 1) {
            const hint = document.createElement('div');
            hint.className = 'option-group__hint';
            if (config.min > 0 && config.max > 0) {
                hint.textContent = `Choose ${config.min}${config.max > config.min ? '-' + config.max : ''}`;
            } else if (config.max > 0) {
                hint.textContent = `Choose up to ${config.max}`;
            } else if (config.max === 0) {
                hint.textContent = 'Choose as many as you like';
            }
            div.appendChild(hint);
        }
        
        // Options
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'option-buttons';
        
        group.options.forEach(option => {
            const btn = this.renderOptionButton(group.id, option, context, parentOptionId, groupType);
            optionsContainer.appendChild(btn);
        });
        
        div.appendChild(optionsContainer);
        
        return div;
    },

    renderOptionButton(groupId, option, context, parentOptionId, groupType) {
        const selections = this.getSelections(context, parentOptionId);
        const quantity = selections[groupId]?.[option.id] || 0;
        const isSelected = quantity > 0;
        const price = this.getOptionPrice(option, groupId);
        
        // For multi-select with quantity > 0, wrap in container with decrement button
        if (groupType === 'multiple' && isSelected) {
            const wrapper = document.createElement('div');
            wrapper.className = 'option-btn-wrapper';
            
            // Decrement button
            const minusBtn = document.createElement('button');
            minusBtn.type = 'button';
            minusBtn.className = 'option-btn-minus';
            minusBtn.innerHTML = '<i class="bi bi-dash"></i>';
            minusBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleMultipleSelect(groupId, option.id, 'decrement', context, parentOptionId);
            });
            
            // Main button
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'option-btn selected';
            btn.dataset.groupId = groupId;
            btn.dataset.optionId = option.id;
            
            let priceHtml = price > 0 ? `<span class="option-btn__price">+£${price.toFixed(2)}</span>` : '';
            let qtyBadge = `<span class="option-btn__qty">${quantity}</span>`;
            
            btn.innerHTML = `${option.name}${priceHtml}${qtyBadge}`;
            btn.addEventListener('click', () => {
                this.handleMultipleSelect(groupId, option.id, 'increment', context, parentOptionId);
            });
            
            wrapper.appendChild(minusBtn);
            wrapper.appendChild(btn);
            return wrapper;
        }
        
        // Standard button (single select or multi-select with quantity 0)
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `option-btn${isSelected ? ' selected' : ''}`;
        btn.dataset.groupId = groupId;
        btn.dataset.optionId = option.id;
        btn.dataset.context = context;
        btn.dataset.parentOptionId = parentOptionId || '';
        
        // Check for child selection count badge (only in main context)
        let badge = '';
        if (isSelected && context === 'main') {
            const revealedGroupIds = this.getRevealedByForOption(option.id);
            if (revealedGroupIds.length > 0) {
                const childCount = this.getChildSelectionCount(option.id, revealedGroupIds);
                if (childCount > 0) {
                    badge = `<span class="option-btn__badge">✓ ${childCount}</span>`;
                }
            }
        }
        
        let priceHtml = '';
        if (price > 0) {
            priceHtml = `<span class="option-btn__price">+£${price.toFixed(2)}</span>`;
        }
        
        btn.innerHTML = `${option.name}${priceHtml}${badge}`;
        
        // Event listener
        btn.addEventListener('click', () => {
            if (groupType === 'single') {
                this.handleSingleSelect(groupId, option.id, context, parentOptionId);
            } else {
                this.handleMultipleSelect(groupId, option.id, 'increment', context, parentOptionId);
            }
        });
        
        return btn;
    },

    getGroupConfig(groupId) {
        return this.state.productConfig.find(cfg => cfg.group_id === groupId) || null;
    },

    getOptionPrice(option, groupId) {
        const basePrice = parseFloat(option.price) || 0;
        if (basePrice === 0) return 0;
        const config = this.getGroupConfig(groupId);
        const adjustment = config ? (parseFloat(config.price_adjustment) || 0) : 0;
        return basePrice + adjustment;
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

    // ==========================================
    // SELECTION HANDLERS
    // ==========================================

    handleSingleSelect(groupId, optionId, context, parentOptionId) {
        const selections = this.getSelections(context, parentOptionId);
        
        // Get previously selected option in this group
        const oldOptionId = Object.keys(selections[groupId] || {})[0];
        const oldOptionIdInt = oldOptionId ? parseInt(oldOptionId) : null;
        
        // Clear existing selection in group
        if (context === 'main') {
            // Clear child selections for old option
            if (oldOptionIdInt && oldOptionIdInt !== optionId) {
                delete this.state.selections.child[oldOptionIdInt];
            }
            if (this.state.selections.main[groupId]) {
                this.state.selections.main[groupId] = {};
            }
        } else {
            if (this.state.selections.child[parentOptionId]?.[groupId]) {
                this.state.selections.child[parentOptionId][groupId] = {};
            }
        }
        
        // Set new selection
        this.setSelection(context, parentOptionId, groupId, optionId, 1);
        
        // Check for revealed groups (child view)
        if (context === 'main') {
            const revealedGroupIds = this.getRevealedByForOption(optionId);
            
            if (revealedGroupIds.length > 0) {
                // Open child view
                this.openChildView(groupId, optionId, revealedGroupIds);
                return;
            }
        }
        
        // Re-render and update
        this.clearGroupError(groupId);
        this.renderCurrentView();
        this.updatePrice();
        
        // Auto-scroll to next required (works for both main and child)
        if (context === 'main') {
            this.autoScrollToNextRequired(groupId);
        } else {
            this.autoScrollToNextRequiredChild(groupId);
        }
    },

    handleMultipleSelect(groupId, optionId, action, context, parentOptionId) {
        const selections = this.getSelections(context, parentOptionId);
        const currentQty = selections[groupId]?.[optionId] || 0;
        const config = this.getGroupConfig(groupId);
        const maxAllowed = config?.max || 999;
        
        // Count total selections in group
        const totalInGroup = Object.values(selections[groupId] || {}).reduce((sum, qty) => sum + qty, 0);
        
        let newQty = currentQty;
        
        if (action === 'increment') {
            if (maxAllowed === 0 || totalInGroup < maxAllowed) {
                newQty = currentQty + 1;
            }
        } else if (action === 'decrement') {
            newQty = Math.max(0, currentQty - 1);
        }
        
        this.setSelection(context, parentOptionId, groupId, optionId, newQty);
        
        this.clearGroupError(groupId);
        this.renderCurrentView();
        this.updatePrice();
        
        // Auto-scroll to next required
        if (action === 'increment') {
            if (context === 'main') {
                this.autoScrollToNextRequired(groupId);
            } else {
                this.autoScrollToNextRequiredChild(groupId);
            }
        }
    },

    autoScrollToNextRequired(justCompletedGroupId) {
        setTimeout(() => {
            const container = document.getElementById('modalOptionsContainer');
            if (!container) return;
            
            const allGroups = container.querySelectorAll('.option-group');
            let foundCurrent = false;
            
            for (const groupEl of allGroups) {
                const gId = parseInt(groupEl.dataset.groupId);
                
                if (gId === parseInt(justCompletedGroupId)) {
                    foundCurrent = true;
                    continue;
                }
                
                if (!foundCurrent) continue;
                
                // Scroll to next section (required or optional)
                const containerRect = container.getBoundingClientRect();
                const groupRect = groupEl.getBoundingClientRect();
                const scrollTop = container.scrollTop + (groupRect.top - containerRect.top) - 20;
                container.scrollTo({ top: scrollTop, behavior: 'smooth' });
                break;
            }
        }, 150);
    },

    autoScrollToNextRequiredChild(justCompletedGroupId) {
        setTimeout(() => {
            const config = this.getGroupConfig(parseInt(justCompletedGroupId));
            if (!config) return;
            
            const parentOptionId = this.state.childViewParentOptionId;
            const currentSelections = Object.values(this.state.selections.child[parentOptionId]?.[justCompletedGroupId] || {}).reduce((s, q) => s + q, 0);
            if (config.min > 0 && currentSelections < config.min) return;
            
            const allGroups = document.querySelectorAll('#modalOptionsContainer .option-group');
            let foundCurrent = false;
            
            for (const groupEl of allGroups) {
                const gId = parseInt(groupEl.dataset.groupId);
                
                if (gId === parseInt(justCompletedGroupId)) {
                    foundCurrent = true;
                    continue;
                }
                
                if (!foundCurrent) continue;
                
                // Scroll to next group regardless of required status
                groupEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                break;
            }
        }, 300);
    },

    // ==========================================
    // VALIDATION
    // ==========================================

    validate() {
        const errors = [];
        
        // Check variation selected
        if (this.state.hasVariations && !this.state.selectedVariation) {
            errors.push({ type: 'variation', message: 'Please select a size' });
        }
        
        // Check main option groups
        this.state.visibleGroupIds.forEach(groupId => {
            const config = this.getGroupConfig(groupId);
            if (!config || config.min === 0) return;
            
            const selections = this.state.selections.main[groupId] || {};
            const count = Object.values(selections).reduce((sum, qty) => sum + qty, 0);
            
            if (count < config.min) {
                const group = this.state.allOptionGroups.find(g => g.id === groupId);
                errors.push({
                    type: 'option',
                    groupId: groupId,
                    message: `Please select ${config.min === 1 ? 'an option' : config.min + ' options'} for ${group?.name || 'this group'}`
                });
            }
        });
        
        // Check child selections for selected options with revealed_by groups
        Object.keys(this.state.selections.main).forEach(groupId => {
            Object.keys(this.state.selections.main[groupId]).forEach(optionId => {
                const revealedGroupIds = this.getRevealedByForOption(parseInt(optionId));
                
                revealedGroupIds.forEach(revealedGroupId => {
                    const config = this.state.productConfig.find(c => c.group_id === revealedGroupId);
                    if (!config || config.min === 0) return;
                    
                    const childSelections = this.state.selections.child[optionId]?.[revealedGroupId] || {};
                    const count = Object.values(childSelections).reduce((sum, qty) => sum + qty, 0);
                    
                    if (count < config.min) {
                        const group = this.state.allOptionGroups.find(g => g.id === revealedGroupId);
                        const parentGroup = this.state.allOptionGroups.find(g => g.id === parseInt(groupId));
                        const parentOption = parentGroup?.options.find(o => o.id === parseInt(optionId));
                        
                        errors.push({
                            type: 'child',
                            groupId: revealedGroupId,
                            parentOptionId: optionId,
                            message: `Please complete options for ${parentOption?.name || 'your selection'}`
                        });
                    }
                });
            });
        });
        
        return errors;
    },

    displayValidationErrors(errors, context = 'main') {
        this.clearValidationErrors();
        
        errors.forEach(error => {
            if (error.type === 'variation') {
                // Highlight variation section
            } else if (error.type === 'option' || error.type === 'child') {
                const title = document.getElementById(`groupTitle_${error.groupId}`);
                const badge = document.getElementById(`groupBadge_${error.groupId}`);
                if (title) title.classList.add('has-error');
                if (badge) badge.classList.add('has-error');
            }
        });
        
        // Scroll to first error
        const firstError = document.querySelector('.has-error');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },

    clearValidationErrors() {
        document.querySelectorAll('.has-error').forEach(el => el.classList.remove('has-error'));
    },

    clearGroupError(groupId) {
        const title = document.getElementById(`groupTitle_${groupId}`);
        const badge = document.getElementById(`groupBadge_${groupId}`);
        if (title) title.classList.remove('has-error');
        if (badge) badge.classList.remove('has-error');
    },

    // ==========================================
    // PRICE & QUANTITY
    // ==========================================

    updatePrice() {
        let total = this.state.basePrice;
        
        // Main selections
        Object.entries(this.state.selections.main).forEach(([groupId, options]) => {
            const group = this.state.allOptionGroups.find(g => g.id === parseInt(groupId));
            if (!group) return;
            
            Object.entries(options).forEach(([optionId, quantity]) => {
                const option = group.options.find(o => o.id === parseInt(optionId));
                if (option) {
                    total += this.getOptionPrice(option, parseInt(groupId)) * quantity;
                }
            });
        });
        
        // Child selections
        Object.entries(this.state.selections.child).forEach(([parentOptionId, groups]) => {
            Object.entries(groups).forEach(([groupId, options]) => {
                const group = this.state.allOptionGroups.find(g => g.id === parseInt(groupId));
                if (!group) return;
                
                Object.entries(options).forEach(([optionId, quantity]) => {
                    const option = group.options.find(o => o.id === parseInt(optionId));
                    if (option) {
                        total += this.getOptionPrice(option, parseInt(groupId)) * quantity;
                    }
                });
            });
        });
        
        this.state.totalPrice = total * this.state.quantity;
        document.getElementById('modalTotalPrice').textContent = `£${this.state.totalPrice.toFixed(2)}`;
    },

    toggleDescription() {
        const descEl = document.getElementById('modalProductDescription');
        const readMoreEl = document.getElementById('modalReadMore');
        
        this.state.descriptionExpanded = !this.state.descriptionExpanded;
        
        if (this.state.descriptionExpanded) {
            descEl.classList.remove('truncated');
            readMoreEl.textContent = 'Read less';
        } else {
            descEl.classList.add('truncated');
            readMoreEl.textContent = 'Read more';
        }
    },

    incrementQty() {
        this.state.quantity++;
        document.getElementById('modalQtyValue').value = this.state.quantity;
        document.getElementById('modalQtyMinus').disabled = false;
        this.updatePrice();
    },

    decrementQty() {
        if (this.state.quantity > 1) {
            this.state.quantity--;
            document.getElementById('modalQtyValue').value = this.state.quantity;
            document.getElementById('modalQtyMinus').disabled = this.state.quantity === 1;
            this.updatePrice();
        }
    },

    // ==========================================
    // ADD TO CART
    // ==========================================

    buildOptionsArray() {
        const optionsArray = [];
        
        // Main selections
        Object.entries(this.state.selections.main).forEach(([groupId, options]) => {
            const group = this.state.allOptionGroups.find(g => g.id === parseInt(groupId));
            if (!group) return;
            
            Object.entries(options).forEach(([optionId, quantity]) => {
                const option = group.options.find(o => o.id === parseInt(optionId));
                if (!option) return;
                
                const price = this.getOptionPrice(option, parseInt(groupId));
                
                optionsArray.push({
                    option_id: parseInt(optionId),
                    option_name: option.name,
                    option_price: price,
                    quantity: quantity,
                    group_id: parseInt(groupId),
                    group_name: group.name
                });
            });
        });
        
        // Child selections
        Object.entries(this.state.selections.child).forEach(([parentOptionId, groups]) => {
            const parentOptId = parseInt(parentOptionId);
            
            // Find parent option info
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
                    
                    const price = this.getOptionPrice(option, parseInt(groupId));
                    
                    optionsArray.push({
                        option_id: parseInt(optionId),
                        option_name: option.name,
                        option_price: price,
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

    addToCart() {
        const errors = this.validate();
        
        if (errors.length > 0) {
            this.displayValidationErrors(errors);
            return;
        }
        
        const options = this.buildOptionsArray();
        
        Cart.add(
            this.state.productId,
            this.state.productName,
            this.state.basePrice,
            options,
            this.state.quantity,
            this.state.cpn
        );
        
        this.state.modalInstance.hide();
    },

    // ==========================================
    // STATE MANAGEMENT
    // ==========================================

    resetState() {
        this.state.productId = null;
        this.state.productName = '';
        this.state.basePrice = 0;
        this.state.productData = null;
        this.state.cpn = 1;
        this.state.hasVariations = false;
        this.state.variations = [];
        this.state.selectedVariation = null;
        this.state.parentProduct = null;
        this.state.productConfig = [];
        this.state.visibleGroupIds = [];
        this.state.initialGroupIds = [];
        this.state.selections = { main: {}, child: {} };
        this.state.quantity = 1;
        this.state.totalPrice = 0;
        this.state.descriptionExpanded = false;
        this.state.currentView = 'main';
        this.state.childViewParentGroupId = null;
        this.state.childViewParentOptionId = null;
        this.state.childViewGroupIds = [];
        
        document.getElementById('modalOptionsContainer').innerHTML = '';
        this.clearValidationErrors();
    }
};

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ProductModal.init();
});

window.ProductModal = ProductModal;
