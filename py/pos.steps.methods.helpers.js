    async function fetchPosMethods(cartId = 0) {
        const existingCart = cartId;
        const url = existingCart ? `/get_pos_methods?cart_id=${encodeURIComponent(cartId)}` : '/get_pos_methods';

        const res = await fetch(url);
        const data = await res.json();

        // Quick cart handling (unchanged)
        if (data.quick_cart && !existingCart) {
            let customer = {
                customerSearch: "",
                postcodeSearch: "",
                customerName: "",
                customerPhone: "",
                customerId: ""
            };
            setCurrentCartMenu(data.methods[0].menu);
            createNewCart(data.methods[0].method, data.methods[0].menu, "", customer, '0', getCurrentCartMenu());
            return;
        }

        const activeMethods = data.methods.filter(m => m.on === 1);
        const total = activeMethods.length;
        let rowColsClass = "row-cols-1";
        if (total === 2) rowColsClass = "row-cols-2";
        else if (total === 3) rowColsClass = "row-cols-3";
        else if (total >= 4) rowColsClass = "row-cols-2 row-cols-md-3 row-cols-lg-4";
        const currentCartData = data.current_cart_data;
        const hasCartData = currentCartData && Object.keys(currentCartData).length > 0;
        // Updated body for Step 1 (Method Selection)
        const body = `
            <div class="container" id="methodSelectionStep">
                <div class="row ${rowColsClass} g-2">
                    ${activeMethods.map(m => renderMethodCard(m, cartId)).join('')}
                </div>
            </div>
            <div id="methodInputsStep" style="display:none">
                ${generateAllInputs(hasCartData ? currentCartData : undefined)}
            </div>
        `;

        updateModal("Choose Order Type", body, "", "modal-lg");
        openModal();
    }

    function renderMethodCard(method, cartId) {
        const labels = {
            takeaway: { icon: "bi-bag", label: "Takeaway" },
            delivery: { icon: "bi-truck", label: "Delivery" },
            dine:     { icon: "bi-cup-straw", label: "Dine In" },
            waiting:  { icon: "bi-clock", label: "Waiting" },
            sale:  { icon: "bi-receipt", label: "General" }
        };
        const { icon, label } = labels[method.method] || { icon: "bi-question", label: method.method };
        const encodedTables = encodeURIComponent(JSON.stringify(method.tables || []));
        return `
            <div>
                <div class="card method-card text-center border hover-shadow p-2"
                    onclick="selectMethod('${method.method}', ${method.menu}, decodeURIComponent('${encodedTables}'), '${cartId}')" 
                    style="cursor:pointer">
                    <div class="card-body p-0 mb-0">
                        <i class="bi ${icon} fs-2 mb-0"></i>
                        <h6 class="fw-bold">${label}</h6>
                    </div>
                </div>
            </div>
        `;
    }

    function generateAllInputs(prefill = {}) {
        let name, phone, address, postcode, customerId, addressId;

        if (prefill.customer_id > 1) {
            name = prefill.customer_name || '';
            phone = prefill.customer_telephone || '';
            address = prefill.address || '';
            postcode = prefill.postcode || '';
            customerId = prefill.customer_id || '';
            addressId = prefill.address_id || '';
        } else {
            name = '';
            phone = '';
            address = '';
            postcode = '';
            customerId = '';
            addressId = '';
        }
        
        return `
            <div id="methodInputs">
                
                <!-- Common Customer Search & Postcode (for takeaway, delivery, waiting) -->
                <div id="inputsForSearch" style="display: none;">
                    <div class="row g-2">
                        <div class="col-md-6 position-relative">
                            <label for="customerSearch" class="form-label fw-bold">Customer Search:</label>
                            <input type="text" class="form-control form-control-sm border border-2 border-primary mb-2" 
                                id="customerSearch" placeholder="Search existing customers" autocomplete="off">
                            <div class="list-group position-absolute overflow-auto h-50 top-50" id="customerSuggestionsContainer"></div>
                        </div>
                        <div id="postcodeSearchContainer" class="col-md-6 position-relative" style="display: none;">
                            <label for="postcodeSearch" class="form-label fw-bold">Postcode Search:</label>
                            <input type="text" class="form-control form-control-sm border border-2 border-warning mb-2" 
                                id="postcodeSearch" placeholder="Postcode then door number" autocomplete="off">
                            <div class="suggestions-container list-group position-absolute overflow-auto h-50 top-50" id="suggestionsContainer"></div>
                        </div>
                    </div>
                </div>

                <!-- Common Customer Info (for takeaway, delivery, waiting) -->
                <div id="inputsForCustomer" style="display: none;">
                    <div class="row g-2 mb-1">
                        <div class="col-md-6">
                            <input class="form-control form-control-sm" placeholder="Name" id="customerName" value="${name}">
                        </div>
                        <div class="col-md-6">
                            <input class="form-control form-control-sm" placeholder="Phone" id="customerPhone" value="${phone}">
                        </div>
                    </div>
                </div>

                <!-- Delivery-specific inputs -->
                <div id="inputsForDelivery" style="display: none;">
                    <div class="row g-2 mb-1">
                        <div class="col-md-6">
                            <input class="form-control form-control-sm" placeholder="Address" id="customerAddress" value="${address}" required>
                        </div>
                        <div class="col-md-6">
                            <input class="form-control form-control-sm" placeholder="Post Code" id="customerPostcode" value="${postcode}" required>
                        </div>
                    </div>
                </div>

                <!-- Dine-in specific inputs -->
                <div id="inputsForDine" style="display: none;">
                    <div class="row">
                        <div class="col-md-6" id="tableSelectionContainer">
                            <!-- Tables will be populated dynamically -->
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">How many people?</label>
                            <input type="text" class="form-control form-control-sm mb-2" id="covers" placeholder="e.g. 2" readonly>
                            <div class="simple-keyboard"></div>
                        </div>
                    </div>
                </div>

                <!-- Hidden fields -->
                <input id="customerId" type="hidden" value="${customerId}">
                <input id="addressId" type="hidden" value="${addressId}">
                <input type="hidden" id="addressDistance">
                <input type="hidden" id="deliveryPrice">
            </div>
        `;
    }

    function hideAllInputSections() {
        const sections = [
            'inputsForSearch', 
            'inputsForCustomer', 
            'inputsForDelivery', 
            'inputsForDine',
            'postcodeSearchContainer'
        ];
        
        sections.forEach(sectionId => {
            const element = document.getElementById(sectionId);
            if (element) {
                element.style.display = 'none';
            }
        });
    }

    function showInputSectionsForMethod(method, tables = []) {
        // First hide all sections
        hideAllInputSections();
        
        // Then show the relevant ones
        switch(method) {
            case 'delivery':
                document.getElementById('inputsForSearch').style.display = 'block';
                document.getElementById('postcodeSearchContainer').style.display = 'block';
                document.getElementById('inputsForCustomer').style.display = 'block';
                document.getElementById('inputsForDelivery').style.display = 'block';
                break;
                
            case 'takeaway':
            case 'sale':
            case 'waiting':
                document.getElementById('inputsForSearch').style.display = 'block';
                document.getElementById('inputsForCustomer').style.display = 'block';
                // Optional fields indication
                document.getElementById('customerName').placeholder = 'Name (optional)';
                document.getElementById('customerPhone').placeholder = 'Phone (optional)';
                break;
                
            case 'dine':
                document.getElementById('inputsForDine').style.display = 'block';
                generateTableSelection(tables);
                break;
        }

        // Initialize components after a brief delay
        setTimeout(() => {
            initializeComponentsForMethod(method);
        }, 50);
    }

    function generateTableSelection(tables) {
        const container = document.getElementById('tableSelectionContainer');
        
        if (!tables.length) {
            container.innerHTML = `<div class="alert alert-warning">No free tables available. Please try again later.</div>`;
            return;
        }
        container.innerHTML = `
            <label class="form-label fw-bold">Select a Table <i class="bi bi-grid-3x3-gap-fill"></i></label>
            <div class="row row-cols-2 row-cols-sm-3 row-cols-md-4 g-1">
                ${tables.map(t => `
                    <div class="col">
                        <div class="form-check form-check-outline w-100 ps-0">
                            <input
                                class="btn-check"
                                type="radio"
                                name="selectedTable"
                                id="table${t.table_id}"
                                value="${t.table_number}"
                                ${t.table_occupied ? 'disabled' : ''}
                            >
                            <label
                                class="btn ${t.table_occupied ? 'btn-outline-secondary' : 'btn-outline-primary'} w-100"
                                for="table${t.table_id}"
                            >${t.table_number}</label>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    function initializeComponentsForMethod(method) {
        // Initialize customer search for methods that need it
        if (['delivery', 'takeaway', 'waiting', 'sale'].includes(method)) {
            initCustomerSearch?.('#myModal');
        }
        
        // Initialize postcode search for delivery
        if (method === 'delivery') {
            initPostcodeSearch?.();
        }
        
        // Initialize simple keyboard for dine-in
        if (method === 'dine') {
            // Destroy existing keyboard instance if it exists
            if (window.simpleKeyboardInstance) {
                window.simpleKeyboardInstance.destroy();
                window.simpleKeyboardInstance = null;
            }
            window.simpleKeyboardInstance = createSimpleKeyboardNew({
                inputIds: 'covers',
                intNumpad: true,
                maxLength: 5
            });
        }
    }

    function selectMethod(method, menu, tablesJSON, cartId) {
        const tables = JSON.parse(tablesJSON);
        document.getElementById('modalTitle').innerText = `Order Type: ${method.charAt(0).toUpperCase() + method.slice(1)}`;

        // Transition from Step 1 (Method Selection) → Step 2 (Inputs)
        const methodSelection = document.getElementById('methodSelectionStep');
        const inputsStep = document.getElementById('methodInputsStep');

        methodSelection.style.opacity = '0';
        methodSelection.style.transition = `opacity 300ms ease`;

        setTimeout(() => {
            methodSelection.style.display = 'none';
            inputsStep.style.display = 'block';
            inputsStep.style.opacity = '0';

            // Configure inputs for the selected method (unchanged logic)
            showInputSectionsForMethod(method, tables);

            setTimeout(() => {
                inputsStep.style.opacity = '1';
                inputsStep.style.transition = `opacity 300ms ease`;
            }, 10);
        }, 300);

        // Update footer with Back + Submit buttons
        let footer = `
            <div class="me-auto">
                <button class="btn btn-outline-dark" onclick="backToMethodSelection()">
                    <i class="bi bi-arrow-left"></i> Back
                </button>
            </div>
            <div id="postcodeResponse" class="me-auto text-dark"></div>
            <button class="btn btn-info" onclick="
                console.log('Button clicked!');
                fetch('/show-keyboard', {method: 'POST'})
                    .then(r => r.json())
                    .then(d => console.log(d))
                    .catch(e => console.error(e));
            ">Show Keyboard</button>
        `;

        // In your selectMethod function, change the footer generation to:
        if (cartId == 0) {
            footer += `<button class="btn btn-success" onclick="submitMethod('${method}', ${menu}, undefined, undefined, this)">Start ${method} Order</button>`;
        } else {
            footer += `<button class="btn btn-success" onclick="submitMethod('${method}', ${menu}, ${cartId}, ${getCurrentCartMenu()}, this)">Change Order to ${method}</button>`;
        }

        document.querySelector(".modal-footer").innerHTML = footer;
    }

    function submitMethod(method, menu, cartId = 0, currentMenu = '', button) {
        let customerData = {};
        let error = null;

        // Common fields (used in all methods except dine-in)
        if (['delivery', 'takeaway', 'waiting', 'sale'].includes(method)) {
            customerData.customerName = document.getElementById("customerName")?.value || "";
            customerData.customerPhone = document.getElementById("customerPhone")?.value || "";
            customerData.customerId = document.getElementById("customerId")?.value || "";
            customerData.addressId = document.getElementById("addressId")?.value || "";
        }

        // DELIVERY: Additional fields + validation
        if (method === 'delivery') {
            customerData.customerAddress = document.getElementById("customerAddress")?.value.trim();
            customerData.customerPostcode = document.getElementById("customerPostcode")?.value.trim();
            customerData.deliveryCharge = parseFloat(document.getElementById("deliveryPrice")?.value || 0);
            customerData.addressDistance = document.getElementById('addressDistance')?.value || 0;

            if (!customerData.customerAddress || !customerData.customerPostcode) {
                error = "Address and Postcode are required for delivery.";
            }
        }

        // DINE-IN: Table and covers required
        if (method === 'dine') {
            const selected = document.querySelector("input[name='selectedTable']:checked");
            customerData.table = selected?.value;
            customerData.cover = document.getElementById("covers")?.value || "";
            customerData.customerName = "";
            customerData.customerPhone = "";

            if (!customerData.table) {
                error = "Please select a table.";
            }
        }

        // If any validation failed, show error and exit
        if (error) {
            showToast(error, false);
            enableButtonRemoveSpinner?.(button);
            return;
        }

        // Call your cart creation logic
        createNewCart(method, menu, "", customerData, cartId, currentMenu);
        closeModal();
    }

    function backToMethodSelection() {
        const methodSelection = document.getElementById('methodSelectionStep');
        const inputsStep = document.getElementById('methodInputsStep');
        document.getElementById('modalTitle').innerText = `Choose Order Type`;
        inputsStep.style.opacity = '0';
        inputsStep.style.transition = `opacity 300ms ease`;

        setTimeout(() => {
            inputsStep.style.display = 'none';
            methodSelection.style.display = 'block';
            methodSelection.style.opacity = '0';

            setTimeout(() => {
                methodSelection.style.opacity = '1';
            }, 10);

            // Reset footer to default
            document.querySelector(".modal-footer").innerHTML = `
                <div class="text-dark">Select an order type to continue</div>
            `;
        }, 300);
    }
