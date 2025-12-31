    function showCheckout(cartId, discountedTotal, discount, serviceAmount, button) {
        disableButtonWithSpinner(button);
        fetch_payment_methods()
        .then(data => {
            discountedTotal = discountedTotal.toFixed(2);
            let paymentMethodButtonsHtml = '';
            let paymentMethodDivsHtml = '';
            
            data.payment_methods.forEach((method, index) => {
                // Modern payment method buttons with icons
                const methodIcons = {
                    'Card': '<i class="bi bi-credit-card me-2"></i>',
                    'Cash': '<i class="bi bi-cash-coin me-2"></i>',
                    'Split': '<i class="bi bi-calculator me-2"></i>'
                };
                
                paymentMethodButtonsHtml += `
                    <input type="radio" class="btn-check" name="btnradio" id="btnmethod${method.name}" 
                        data-bs-toggle="collapse" data-bs-target="#${method.name}" value="${method.name}" 
                        onclick="resetBalance(${discountedTotal})" ${index === 0 ? 'checked' : ''}>
                    <label class="btn btn-outline-primary btn-lg shadow-sm" for="btnmethod${method.name}">
                        ${methodIcons[method.name] || '<i class="bi bi-wallet2 me-2"></i>'}
                        ${method.name}
                    </label>
                `;
                
                let paymentVendorsHtml = '';
                if (method.name === 'Card') {
                    data.payment_vendors.forEach((vendor, index) => {
                        paymentVendorsHtml += `
                            <div class="col-12 mb-2">
                                <input type="radio" class="btn-check" name="cardPaymentRadio" id="cardPaymentRadio${index + 1}" 
                                    value="${vendor.vendor_name}" onclick="prepareCardPayment(this.value)">
                                <label class="btn btn-outline-danger btn-lg w-100 shadow-sm d-flex align-items-center justify-content-center" 
                                    for="cardPaymentRadio${index + 1}">
                                    <i class="bi bi-credit-card me-2"></i>
                                    Charge to ${vendor.vendor_name}
                                </label>
                            </div>
                        `;
                    });
                    paymentMethodDivsHtml += `
                        <div class="collapse ${index === 0 ? 'show' : ''} fade-in" data-bs-parent="#paymentMethodDiv" id="${method.name}">
                            <div class="card border-0 shadow-sm">
                                <div class="card-body">
                                    <h6 class="card-title text-muted mb-3">
                                        <i class="bi bi-credit-card me-2"></i>Select Card Provider
                                    </h6>
                                    <div class="row">
                                        ${paymentVendorsHtml}
                                    </div>
                                    <div class="alert alert-info mt-3 d-none" role="alert" id="cardMsg">
                                        <i class="bi bi-info-circle me-2"></i>
                                        <span></span>
                                    </div>
                                    <div class="card mt-3" style="display:none;" id="signatureButtons">
                                        <div class="card-header bg-warning text-dark">
                                            <i class="bi bi-pen me-2"></i>Signature Verification Required
                                        </div>
                                        <div class="card-body">
                                            <div class="btn-group w-100" role="group">
                                                <input type="radio" class="btn-check" name="btnsignature" id="btnsignature1" autocomplete="off">
                                                <label class="btn btn-outline-success btn-lg" for="btnsignature1">
                                                    <i class="bi bi-check-lg me-2"></i>Valid
                                                </label>
                                                <input type="radio" class="btn-check" name="btnsignature" id="btnsignature2" autocomplete="off">
                                                <label class="btn btn-outline-danger btn-lg" for="btnsignature2">
                                                    <i class="bi bi-x-lg me-2"></i>Invalid
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                else if (method.name === 'Cash') {
                    paymentMethodDivsHtml += `
                        <div class="collapse ${index === 0 ? 'show' : ''} fade-in" data-bs-parent="#paymentMethodDiv" id="${method.name}">
                            <div class="card border-0 shadow-sm">
                                <div class="card-body">
                                    <!-- Quick Payment Section -->
                                    <div class="mb-4">
                                        <h6 class="text-muted mb-2">Quick Payment</h6>
                                        <div class="row g-2">
                                            ${(() => {
                                                const quickButtons = [
                                                    { value: 'Exact', func: discountedTotal, class: 'btn-success', icon: 'bi bi-bullseye' },
                                                    ...(discountedTotal >= 1.00 ? [{ 
                                                        value: '£' + Math.floor(discountedTotal).toFixed(2), 
                                                        func: Math.floor(discountedTotal), 
                                                        class: 'btn-primary',
                                                        icon: 'bi bi-arrow-down'
                                                    }] : []),
                                                    { 
                                                        value: '£' + Math.ceil(discountedTotal).toFixed(2), 
                                                        func: Math.ceil(discountedTotal), 
                                                        class: 'btn-info',
                                                        icon: 'bi bi-arrow-up'
                                                    }
                                                ];
                                                
                                                return quickButtons.map(({ value, func, class: btnClass, icon }) => 
                                                    `<div class="col-auto">
                                                        <button class="btn ${btnClass} pay-btn shadow-sm" 
                                                                onclick="subtractCashAmountFromBalance(${func})">
                                                            <i class="${icon} me-1"></i>${value}
                                                        </button>
                                                    </div>`
                                                ).join('');
                                            })()}
                                        </div>
                                    </div>
                                    
                                    <!-- Denominations Section -->
                                    <div class="mb-3">
                                        <h6 class="text-muted mb-2">Denominations</h6>
                                        <div class="row g-2">
                                            ${(() => {
                                                const denominations = [
                                                    { value: '£50', func: 50, color: 'secondary' },
                                                    { value: '£20', func: 20, color: 'secondary' },
                                                    { value: '£10', func: 10, color: 'secondary' },
                                                    { value: '£5', func: 5, color: 'secondary' },
                                                    { value: '£2', func: 2, color: 'outline-secondary' },
                                                    { value: '£1', func: 1, color: 'outline-secondary' },
                                                    { value: '50p', func: 0.5, color: 'outline-secondary' },
                                                    { value: '20p', func: 0.2, color: 'outline-secondary' },
                                                    { value: '10p', func: 0.1, color: 'outline-secondary' },
                                                    { value: '5p', func: 0.05, color: 'outline-secondary' },
                                                    { value: '2p', func: 0.02, color: 'outline-secondary' },
                                                    { value: '1p', func: 0.01, color: 'outline-secondary' }
                                                ];
                                                
                                                return denominations.map(({ value, func, color }) => 
                                                    `<div class="col-3 col-xl-2">
                                                        <button class="btn btn-${color} pay-btn w-100 shadow-sm" 
                                                                onclick="subtractCashAmountFromBalance(${func})">
                                                            ${value}
                                                        </button>
                                                    </div>`
                                                ).join('');
                                            })()}
                                        </div>
                                    </div>
                                    
                                    <!-- Clear Button -->
                                    <div class="d-grid">
                                        <button class="btn btn-outline-danger shadow-sm" 
                                                onclick="clearCashBalance(${discountedTotal})">
                                            <i class="bi bi-arrow-clockwise me-2"></i>Clear Payment
                                        </button>
                                    </div>
                                    
                                    <div class="alert alert-danger mt-3 d-none" role="alert" id="cashMsg">
                                        <i class="bi bi-exclamation-triangle me-2"></i>
                                        <span></span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                } else if (method.name === 'Split') {
                    paymentMethodDivsHtml += `
                        <div class="collapse ${index === 0 ? 'show' : ''} fade-in" data-bs-parent="#paymentMethodDiv" id="${method.name}">
                            <div class="card border-0 shadow-sm">
                                <div class="card-body">
                                    <!-- Payment Method Selection -->
                                    <div class="mb-1">
                                        <div class="btn-group w-100" role="group">
                                            <input type="radio" class="btn-check" name="btnsplit" id="btncash" value="Cash">
                                            <label class="btn btn-outline-primary" for="btncash">
                                                <i class="bi bi-cash-coin me-1"></i>Cash
                                            </label>
                                            ${data.payment_vendors.map(vendor => `
                                            <input type="radio" class="btn-check" name="btnsplit" id="btn${vendor.vendor_name.replace(' ', '')}" value="${vendor.vendor_name}">
                                            <label class="btn btn-outline-primary" for="btn${vendor.vendor_name.replace(' ', '')}">
                                                <i class="bi bi-credit-card me-1"></i>${vendor.vendor_name}
                                            </label>
                                            `).join('')}
                                        </div>
                                    </div>
                                    
                                    <!-- Amount Input -->
                                    <div class="mb-1">
                                        <div class="input-group input-group-lg">
                                            <span class="input-group-text">£</span>
                                            <input type="text" class="form-control text-end" placeholder="0.00" id="splitAmount" readonly>
                                            <button class="btn btn-success" id="chargeButton" onclick="addSplitCharge(${discountedTotal})">
                                                <i class="bi bi-plus-lg me-2"></i>Charge
                                            </button>
                                        </div>
                                    </div>
                                    
                                    <div class="alert alert-danger d-none" role="alert" id="splitMessages">
                                        <i class="bi bi-exclamation-triangle me-2"></i>
                                        <span></span>
                                    </div>
                                    
                                    <!-- Calculator -->
                                    <div class="">
                                        <div class="">
                                            <div class="row g-2">
                                                ${['7', '8', '9', '4', '5', '6', '1', '2', '3', 'Delete', '0', '.'].map(value => {
                                                    const isDelete = value === 'Delete';
                                                    const btnClass = isDelete ? 'btn-warning' : 'btn-outline-secondary';
                                                    const icon = isDelete ? '<i class="bi bi-backspace me-1"></i>' : '';
                                                    return `<div class="col-4">
                                                        <button class="btn ${btnClass} calculator-btn w-100 shadow-sm" onclick="addToSplitInput('${value}')">
                                                            ${icon}${value}
                                                        </button>
                                                    </div>`;
                                                }).join('')}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }
                else {
                    paymentMethodDivsHtml += `
                        <div class="collapse ${index === 0 ? 'show' : ''} fade-in" data-bs-parent="#paymentMethodDiv" id="${method.name}">
                            <div class="card border-0 shadow-sm">
                                <div class="card-body text-center">
                                    <i class="bi bi-wallet2 text-muted mb-3" style="font-size: 3rem;"></i>
                                    <h5 class="card-title">${method.name}</h5>
                                    <p class="text-muted">Payment method configuration needed</p>
                                </div>
                            </div>
                        </div>
                    `;
                }
            });
            
            const checkoutHtml = `
                <div class="row g-1">
                    <!-- Payment Methods Section -->
                    <div class="col-lg-8">
                        <div class="card border-0 shadow">
                            <div class="btn-group w-100" role="group" id="paymentMethodGroup">
                                ${paymentMethodButtonsHtml}
                            </div>
                        </div>
                        
                        <div class="mt-3" id="paymentMethodDiv">
                            ${paymentMethodDivsHtml}
                        </div>
                    </div>
                    
                    <!-- Order Summary Section -->
                    <div class="col-lg-4">
                        <div class="card border-0 shadow sticky-top">
                            <div class="card-header bg-dark">
                                <h5 class="card-title mb-0 text-light">
                                    <i class="bi bi-receipt me-2"></i>Order Summary
                                </h5>
                            </div>
                            <div class="card-body p-2">
                                <div class="list-group list-group-flush">
                                    <div class="list-group-item d-flex justify-content-between px-0 border-0">
                                        <span><i class="bi bi-truck me-2 text-muted"></i>Service/Delivery:</span>
                                        <strong>£${serviceAmount}</strong>
                                    </div>
                                    <div class="list-group-item d-flex justify-content-between px-0 border-0">
                                        <span><i class="bi bi-tag me-2 text-success"></i>Discount:</span>
                                        <strong class="text-success">-£${discount}</strong>
                                    </div>
                                    <div class="list-group-item d-flex justify-content-between px-0 border-top">
                                        <span class="fw-bold">Total:</span>
                                        <strong class="fs-5">£${discountedTotal}</strong>
                                    </div>
                                </div>
                                
                                <!-- Payment Status -->
                                <div class="mt-1">
                                    <div class="card bg-light">
                                        <div class="pt-1">
                                            <div class="row text-center">
                                                <div class="col-6 ps-0">
                                                    <div class="text-muted small">Balance Due</div>
                                                    <div class="fs-4 fw-bold text-danger" id="balance" data-original-balance="${discountedTotal}">${discountedTotal}</div>
                                                </div>
                                                <div class="col-6 pe-0">
                                                    <div class="text-muted small">Tendered</div>
                                                    <div class="fs-4 fw-bold text-success" id="tendered">0.00</div>
                                                </div>
                                            </div>
                                            <div class="mt-2 text-center">
                                                <div class="alert alert-info py-2 mb-0" id="balanceMsg" role="alert">
                                                    <i class="bi bi-info-circle me-1"></i>Select payment method to continue
                                                </div>
                                                <input type="hidden" id="changeDue">
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Split Charges List -->
                                <div class="mt-3" id="splitChargesList"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            const footer = `
                <div class="d-grid gap-2 d-md-flex justify-content-md-end w-100">
                    <button class="btn btn-outline-dark btn-lg me-auto" type="button" onclick="completeCheckout('${cartId}', '${discountedTotal}', true, this)">
                        <i class="bi bi-printer me-2"></i>Complete with Print
                    </button>
                    <button class="btn btn-success btn-lg" type="button" onclick="completeCheckout('${cartId}', '${discountedTotal}', false, this)">
                        <i class="bi bi-check me-2"></i>Complete
                    </button>
                </div>
            `;
            
            const header = `
                Balance to pay: £${discountedTotal}
            `;
            
            updateModal(header, checkoutHtml, footer);
            openModal();
            document.getElementById('modalBody').classList.add('overflow-x-hidden');
            enableButtonRemoveSpinner(button);
        })
        .catch(error => {
            console.error('Error:', error.message);
            enableButtonRemoveSpinner(button);
        });
    }

    function clearPaymentMessages() {
        const elementIds = ['splitMessages', 'cashMsg', 'cardMsg', 'splitAmount'];
        elementIds.forEach((id, index) => {
            const element = document.getElementById(id);
            if (element) {
                const messageSpan = element.querySelector('span');
                if (element.tagName === 'INPUT') {
                    element.value = "";
                } else if (messageSpan) {
                    messageSpan.textContent = "";
                    element.classList.add('d-none');
                } else {
                    element.textContent = "";
                    element.classList.add('d-none');
                }
            }
        });
    }

    function resetBalance(balance) {
        splitCharges.length > 0 && (splitCharges = []);
        const balanceElement = document.getElementById('balance');
        const tenderedElement = document.getElementById('tendered');
        const balanceMsg = document.getElementById('balanceMsg');
        balanceElement.innerText = balance.toFixed(2);
        tenderedElement.innerText = '0.00';
        balanceMsg.innerHTML = '<i class="bi bi-info-circle me-1"></i>Select payment method to continue';
        updateSplitChargesList();
        clearPaymentMessages();
        clearCashBalance(balance);
    }

    function clearCashBalance(discountedTotal) {
        const balanceElement = document.getElementById('balance');
        const tenderedElement = document.getElementById('tendered');
        const balanceMsg = document.getElementById('balanceMsg');
        balanceElement.innerText = discountedTotal;
        tenderedElement.innerText = '0.00';
        document.querySelectorAll('.pay-btn').forEach(btn => btn.disabled = false);
        balanceMsg.innerHTML = '<i class="bi bi-info-circle me-1"></i>Select payment method to continue';
        balanceMsg.className = 'alert alert-warning py-2 mb-0';
        document.getElementById('changeDue').value = 0.00;
    }

    function subtractCashAmountFromBalance(amount) {
        const balanceElement = document.getElementById('balance');
        const tenderedElement = document.getElementById('tendered');
        const balanceMsg = document.getElementById('balanceMsg');

        const originalBalance = parseFloat(balanceElement.dataset.originalBalance);
        let amountTendered = parseFloat(tenderedElement.innerText || 0);
        
        amountTendered += amount;
        let remainingBalance = originalBalance - amountTendered;

        if (remainingBalance <= 0) {
            const change = Math.abs(remainingBalance);
            document.getElementById('changeDue').value = change.toFixed(2);
            balanceMsg.innerHTML = change > 0 
                ? `<i class="bi bi-check-circle me-1 text-success"></i>Payment complete.<br>Change due: <strong>£${change.toFixed(2)}</strong>`
                : `<i class="bi bi-check-circle me-1 text-success"></i>Payment complete`;
            balanceMsg.className = 'alert alert-success py-2 mb-0';
            remainingBalance = 0;
        } else {
            balanceMsg.innerHTML = `<i class="bi bi-clock me-1"></i>Remaining balance: £${remainingBalance.toFixed(2)}`;
            balanceMsg.className = 'alert alert-warning py-2 mb-0';
        }

        balanceElement.innerText = remainingBalance.toFixed(2);
        tenderedElement.innerText = amountTendered.toFixed(2);
    }

    function createCalculatorButton(value) {
        const isDelete = value === 'Delete';
        const btnClass = isDelete ? 'btn-warning' : 'btn-outline-secondary';
        const icon = isDelete ? '<i class="bi bi-backspace me-1"></i>' : '';
        return `<button class="btn ${btnClass} calculator-btn me-1 mb-1 shadow-sm" onclick="addToSplitInput('${value}')">${icon}${value}</button>`;
    }

    function prepareCardPayment(selectedValue) {
        const cardMsg = document.getElementById("cardMsg");
        const cardMsgSpan = cardMsg.querySelector('span');
        const balanceElement = document.getElementById('balance');
        const tenderedElement = document.getElementById('tendered');
        const balanceMsg = document.getElementById('balanceMsg');
        let currentBalance = parseFloat(balanceElement.innerText);
        let amountTendered = parseFloat(tenderedElement.innerText || 0);
        
        if (!currentBalance) {
            return;
        }

        cardMsg.classList.remove('d-none');
        
        if (selectedValue === "Card") {
            cardMsgSpan.textContent = `Press complete to finish and charge £${currentBalance.toFixed(2)} as card payment`;
            balanceElement.textContent = '0.00';
            tenderedElement.textContent = currentBalance.toFixed(2);
            balanceMsg.innerHTML = '<small><i class="bi bi-check-circle me-1 text-success"></i>Ready to complete payment</small>';
            balanceMsg.className = 'alert alert-success py-2 mb-0';
        } else {
            cardMsg.className = 'alert alert-info mt-3';
            cardMsgSpan.textContent = "Present card reader...";
            
            fetch('/create_card_transaction', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    amount: currentBalance
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data[2] == "success") {
                    balanceElement.textContent = '0.00';
                    tenderedElement.textContent = currentBalance.toFixed(2);
                    cardMsg.className = 'alert alert-success mt-3';
                    cardMsgSpan.textContent = "Purchase successful! You may now press complete.";
                    balanceMsg.innerHTML = '<small><i class="bi bi-check-circle me-1 text-success"></i>Payment complete</small>';
                    balanceMsg.className = 'alert alert-success py-2 mb-0';
                } else if (data[2] == "signature") {
                    cardMsg.className = 'alert alert-warning mt-3';
                    cardMsgSpan.textContent = "Please verify signature on card and select below:";
                    document.getElementById('signatureButtons').style.display = 'block';
                } else {
                    cardMsg.className = 'alert alert-danger mt-3';
                    cardMsgSpan.textContent = data[2];
                }
            })
            .catch(error => {
                console.error('Error:', error);
                cardMsg.className = 'alert alert-danger mt-3';
                cardMsgSpan.textContent = 'Transaction failed. Please try again.';
            });
        }
    }

    function addToSplitInput(value) {
        const splitAmountInput = document.getElementById('splitAmount');
        let currentAmount = splitAmountInput.value;

        if (value === 'Delete') {
            currentAmount = currentAmount.slice(0, -1);
        } else {
            if (value === '.' && currentAmount.includes('.')) {
                return;
            }
            const decimalIndex = currentAmount.indexOf('.');
            if (decimalIndex !== -1 && currentAmount.length - decimalIndex > 2) {
                return;
            }
            currentAmount += value;
        }
        splitAmountInput.value = currentAmount;
    }

    let splitCharges = [];

    function addSplitCharge(initialBalance) {
        const splitAmountInput = document.getElementById('splitAmount');
        const balanceSpan = document.getElementById('balance');
        const tenderedElement = document.getElementById('tendered');
        const splitMessages = document.getElementById('splitMessages');
        const splitMessagesSpan = splitMessages.querySelector('span');
        const chargeButton = document.getElementById('chargeButton');
        const balanceMsg = document.getElementById('balanceMsg');

        let remainingBalance = parseFloat(balanceSpan.textContent);
        let amountTendered = parseFloat(tenderedElement.innerText || 0);

        if (remainingBalance === initialBalance) {
            splitCharges.length = 0;
        }

        const amount = parseFloat(splitAmountInput.value);

        if (!isNaN(amount) && amount > 0 && amount <= remainingBalance) {
            const paymentMethod = document.querySelector('input[name="btnsplit"]:checked')?.value;
            
            if (paymentMethod) {
                splitCharges.push({ amount, paymentMethod });

                updateSplitChargesList();
                remainingBalance -= amount;
                amountTendered += amount;
                balanceSpan.textContent = remainingBalance.toFixed(2);
                tenderedElement.innerText = amountTendered.toFixed(2);
                splitAmountInput.value = '';
                splitMessages.classList.add('d-none');

                if (remainingBalance <= 0) {
                    balanceMsg.innerHTML = '<i class="bi bi-check-circle me-1 text-success"></i>Payment complete';
                    balanceMsg.className = 'alert alert-success py-2 mb-0';
                    chargeButton.disabled = true;
                    splitAmountInput.disabled = true;
                } else {
                    balanceMsg.innerHTML = `<i class="bi bi-clock me-1"></i>Remaining: £${remainingBalance.toFixed(2)}`;
                    balanceMsg.className = 'alert alert-warning py-2 mb-0';
                }
            } else {
                splitMessages.classList.remove('d-none');
                splitMessagesSpan.textContent = 'Please select a payment method (Cash or Card).';
            }
        } else {
            const exceededAmount = amount > remainingBalance ? amount - remainingBalance : 0;
            splitMessages.classList.remove('d-none');
            splitMessagesSpan.textContent = exceededAmount > 0 
                ? `Amount exceeds remaining balance by £${exceededAmount.toFixed(2)}.`
                : 'Please enter a valid amount.';
            
            if (exceededAmount > 0) {
                splitAmountInput.value = remainingBalance.toFixed(2);
            }
        }
    }

    function updateSplitChargesList() {
        const splitChargesList = document.getElementById('splitChargesList');
        if (splitCharges.length > 0) {
            splitChargesList.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0"><i class="bi bi-list me-2"></i>Split Charges</h6>
                    </div>
                    <div class="card-body p-0">
                        <div class="list-group list-group-flush">
                            ${splitCharges.map(charge => 
                                `<div class="list-group-item d-flex justify-content-between align-items-center">
                                    <span>
                                        <i class="bi bi-${charge.paymentMethod === 'Cash' ? 'cash-stack' : 'credit-card'} me-2 text-muted"></i>
                                        ${charge.paymentMethod}
                                    </span>
                                    <strong>£${charge.amount.toFixed(2)}</strong>
                                </div>`
                            ).join('')}
                        </div>
                    </div>
                </div>
            `;
        } else {
            splitChargesList.innerHTML = '';
        }
    }

    function getSelectedPaymentMethod() {
        const paymentMethodGroup = document.getElementById('paymentMethodGroup');
        const selectedRadioButton = paymentMethodGroup.querySelector('input[name="btnradio"]:checked');
        return selectedRadioButton ? selectedRadioButton.value : null;
    }
