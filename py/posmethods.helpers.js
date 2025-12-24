    async function fetchPosMethods(cartId = 0) {
        const res = await fetch("/get_pos_methods");
        const data = await res.json();
        // potentially if takeaway isn't on then it'll be a problem
        if (data.quick_cart) {
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
        let rowColsClass = "row-cols-1"; // default
        if (total === 2) rowColsClass = "row-cols-2";
        else if (total === 3) rowColsClass = "row-cols-3";
        else if (total >= 4) rowColsClass = "row-cols-2 row-cols-md-3 row-cols-lg-4"; // responsive for larger sets
        const body = `
            <div class="container">
                <div class="row ${rowColsClass} g-2">
                    ${activeMethods.map(m => renderMethodCard(m, cartId)).join('')}
                </div>
                ${generateAllInputs()}
            </div>
        `;
        // Set up modal using the helper
        updateModal("Choose Order Type", body, "", "modal-lg");
        openModal();
    }

    function renderMethodCard(method, cartId) {
        const labels = {
            takeaway: { icon: "bi-bag", label: "Takeaway" },
            delivery: { icon: "bi-truck", label: "Delivery" },
            dine:     { icon: "bi-cup-straw", label: "Dine In" },
            waiting:  { icon: "bi-clock", label: "Waiting" }
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

    function generateAllInputs() {
        return `
            <div id="methodInputs" class="mb-3" style="opacity: 0; transform: translateY(-20px); transition: opacity 0.5s ease, transform 0.5s ease; pointer-events: none;">
                
                <!-- Common Customer Search & Postcode (for takeaway, delivery, waiting) -->
                <div id="inputsForSearch" style="display: none;">
                    <div class="row g-2">
                        <div class="col-md-6 position-relative">
                            <label for="customerSearch" class="form-label fw-bold">Customer Search:</label>
                            <input type="text" class="form-control form-control-sm border border-2 border-primary mb-2" 
                                id="customerSearch" placeholder="Search existing customers" autocomplete="off">
                            <div class="list-group position-absolute h-75 top-50" id="customerSuggestionsContainer"></div>
                        </div>
                        <div id="postcodeSearchContainer" class="col-md-6 position-relative" style="display: none;">
                            <label for="postcodeSearch" class="form-label fw-bold">Postcode Search:</label>
                            <input type="text" class="form-control form-control-sm border border-2 border-warning mb-2" 
                                id="postcodeSearch" placeholder="Postcode then door number" autocomplete="off">
                            <div class="suggestions-container list-group position-absolute h-75 top-50" id="suggestionsContainer"></div>
                        </div>
                    </div>
                </div>

                <!-- Common Customer Info (for takeaway, delivery, waiting) -->
                <div id="inputsForCustomer" style="display: none;">
                    <div class="row g-2 mb-1">
                        <div class="col-md-6">
                            <input class="form-control form-control-sm" placeholder="Name" id="customerName">
                        </div>
                        <div class="col-md-6">
                            <input class="form-control form-control-sm" placeholder="Phone" id="customerPhone">
                        </div>
                    </div>
                </div>

                <!-- Delivery-specific inputs -->
                <div id="inputsForDelivery" style="display: none;">
                    <div class="row g-2 mb-1">
                        <div class="col-md-6">
                            <input class="form-control form-control-sm" placeholder="Address" id="customerAddress" required>
                        </div>
                        <div class="col-md-6">
                            <input class="form-control form-control-sm" placeholder="Post Code" id="customerPostcode" required>
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
                            <label class="form-label fw-bold">Covers</label>
                            <input type="text" class="form-control form-control-sm mb-2" id="covers" placeholder="e.g. 2" readonly>
                            <div class="simple-keyboard"></div>
                        </div>
                    </div>
                </div>

                <!-- Hidden fields -->
                <input id="customerId" type="hidden">
                <input id="addressId" type="hidden">
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
        hideAllInputSections();
        
        const methodInputs = document.getElementById('methodInputs');
        
        methodInputs.style.opacity = '0';
        methodInputs.style.transform = 'translateY(-20px)';
        methodInputs.style.pointerEvents = 'none';
        
        setTimeout(() => {
            // Configure sections based on method
            switch(method) {
                case 'delivery':
                    document.getElementById('inputsForSearch').style.display = 'block';
                    document.getElementById('postcodeSearchContainer').style.display = 'block';
                    document.getElementById('inputsForCustomer').style.display = 'block';
                    document.getElementById('inputsForDelivery').style.display = 'block';
                    break;
                    
                case 'takeaway':
                case 'waiting':
                    document.getElementById('inputsForSearch').style.display = 'block';
                    document.getElementById('inputsForCustomer').style.display = 'block';
                    // Make name and phone optional for these methods
                    document.getElementById('customerName').placeholder = 'Name (optional)';
                    document.getElementById('customerPhone').placeholder = 'Phone (optional)';
                    break;
                    
                case 'dine':
                    document.getElementById('inputsForDine').style.display = 'block';
                    generateTableSelection(tables);
                    break;
            }
            
            
            // Small delay to ensure display is set before opacity change
            setTimeout(() => {
                methodInputs.style.opacity = '1';
                methodInputs.style.transform = 'translateY(0)';
                methodInputs.style.pointerEvents = 'auto';
                
                // Initialize components after fade in
                setTimeout(() => {
                    initializeComponentsForMethod(method);
                }, 100);
            }, 50);
            
        }, 100); // Half of the transition duration
    }

    function generateTableSelection(tables) {
        const container = document.getElementById('tableSelectionContainer');
        
        if (!tables.length) {
            container.innerHTML = `<div class="alert alert-warning">No free tables available. Please try again later.</div>`;
            return;
        }
        
        container.innerHTML = `
            <label class="form-label fw-bold">Select a Table</label>
            <div class="row row-cols-2 row-cols-sm-3 row-cols-md-4 g-1">
                ${tables.map(t => `
                    <div class="col">
                        <div class="form-check form-check-outline w-100">
                            <input
                                class="btn-check"
                                type="radio"
                                name="selectedTable"
                                id="table${t.table_id}"
                                value="${t.table_number}"
                            >
                            <label
                                class="btn btn-outline-primary w-100"
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
        if (['delivery', 'takeaway', 'waiting'].includes(method)) {
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
        // Update visual selection
        document.querySelectorAll(".method-card").forEach(card => card.classList.remove("border-primary"));
        event.currentTarget.classList.add("border-primary");

        const tables = JSON.parse(tablesJSON);
        
        showInputSectionsForMethod(method, tables);
        
        let footer = `<div id="postcodeResponse" class="me-auto ms-2"></div>`;

        if (cartId == 0) {
            footer += `<button class="btn btn-success" onclick="submitMethod('${method}', ${menu})">Start Order</button>`;
        } else {
            footer += `<button class="btn btn-success" onclick="submitMethod('${method}', ${menu}, ${cartId}, ${getCurrentCartMenu()})">Start Order</button>`;
        }
        
        document.querySelector(".modal-footer").innerHTML = footer;
    }

    function submitMethod(method, menu, cartId = 0, currentMenu = '', button) {
        let customerData = {};
        let error = null;

        // Common fields (used in all methods except dine-in)
        if (['delivery', 'takeaway', 'waiting'].includes(method)) {
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

        createNewCart(method, menu, "", customerData, cartId, currentMenu);
        closeModal();
    }
