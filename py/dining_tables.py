{% extends "base.html" %}

{% block title %}Dining{% endblock %}

{% block content %}

<div class="row mt-2">
    <div class="col-md-12">
        <div class="card flex-fill w-100" style="height: 95vh;">
            <div class="card-header">
                <h5 class="card-title mb-0">{{ back_link|safe}} Restaurant Settings</h5>
            </div>
            <div class="card-body row pb-3 h-100">
                <!-- Left Column - Tables Management -->
                <div class="col-md-4 border-end overflow-auto pe-3" style="height: 100%;">
                    <div class="input-group mb-3 sticky-top z-1">
                        <input type="number" id="tableNumber" class="form-control" placeholder="Table number" min="1" required>
                        <button type="submit" id="saveTableBtn" class="btn btn-primary" onclick="saveTable()">
                            <i class="bi bi-plus-lg"></i> Add Table
                        </button>
                    </div>
                    <div id="dataContainer" class="row row-cols-3 gx-1 mb-3">
                        {% for table in tables %}
                            <div class="col">
                                <div class="card {% if table.table_occupied %}border-danger{% else %}border-success{% endif %}">
                                    <div class="card-body p-2 text-center">
                                        <h5 class="card-title mb-0">Table #{{ table.table_number }}</h5>
                                        <button class="btn btn-sm btn-outline-danger mt-2" 
                                                value="{{ table.table_id }}" 
                                                onclick="deleteTable('{{ table.table_id }}')" 
                                                {% if table.table_occupied %}disabled{% endif %}>
                                            <i class="bi bi-trash"></i> Remove
                                        </button>
                                    </div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                </div>

                <!-- Middle Column - Ordering Methods -->
                <div class="col-md-4 border-end overflow-auto pe-3" style="height: 100%;">
                    <h6 class="fw-bold mb-3">Ordering Methods</h6>
                    <div class="list-group">
                        {% for item in pos_methods %}
                        <div class="list-group-item">
                            
                            <!-- Enabled / Disabled -->
                            <div class="row mb-2 align-items-center">
                                <div class="col-5">
                                    <span class="fw-bold text-capitalize">{{ item.method }}</span>
                                </div>
                                <div class="col-7">
                                    <div class="btn-group btn-group-sm w-100" role="group">
                                        <input type="radio" class="btn-check on-off" name="{{ item.method }}" 
                                            id="{{ item.method }}" data-method="{{ item.method }}" value="on"
                                            {% if item.on == 1 %}checked{% endif %}>
                                        <label class="btn btn-outline-success flex-fill" for="{{ item.method }}">Enabled</label>

                                        <input type="radio" class="btn-check on-off" name="{{ item.method }}" 
                                            id="disabled-{{ item.method }}" data-method="{{ item.method }}" value="off"
                                            {% if item.on == 0 %}checked{% endif %}>
                                        <label class="btn btn-outline-danger flex-fill" for="disabled-{{ item.method }}">Disabled</label>
                                    </div>
                                </div>
                            </div>

                            <!-- Menu Display -->
                            <div class="row align-items-center mb-2">
                                <div class="col-5">
                                    <small class="text-muted">Menu Display</small>
                                </div>
                                <div class="col-7">
                                    <div class="btn-group btn-group-sm w-100" role="group">
                                        <input type="radio" class="btn-check menu-option" name="in-{{ item.method }}" 
                                            id="in-{{ item.method }}" data-method="{{ item.method }}" 
                                            data-property="menu" data-value="0"
                                            {% if item.menu == 0 %}checked{% endif %}>
                                        <label class="btn btn-outline-primary flex-fill" for="in-{{ item.method }}">In Menu</label>

                                        <input type="radio" class="btn-check menu-option" name="in-{{ item.method }}" 
                                            id="out-{{ item.method }}" data-method="{{ item.method }}" 
                                            data-property="menu" data-value="1"
                                            {% if item.menu == 1 %}checked{% endif %}>
                                        <label class="btn btn-outline-secondary flex-fill" for="out-{{ item.method }}">Out Menu</label>
                                    </div>
                                </div>
                            </div>

                            <!-- Total Division Hint (Only for 'dine') -->
                            {% if item.method == 'dine' %}
                            <div class="row align-items-center">
                                <div class="col-5">
                                    <small class="text-muted">Total Division Hint</small>
                                </div>
                                <div class="col-7">
                                    <div class="btn-group btn-group-sm w-100" role="group">
                                        <input type="radio" class="btn-check" name="divisionHint" 
                                            id="divisionHint1"
                                            {% if division_hint %}checked{% endif %}>
                                        <label class="btn btn-outline-secondary flex-fill" for="divisionHint1">On</label>

                                        <input type="radio" class="btn-check" name="divisionHint" 
                                            id="divisionHint2"
                                            {% if not division_hint %}checked{% endif %}>
                                        <label class="btn btn-outline-dark flex-fill" for="divisionHint2">Off</label>
                                    </div>
                                </div>
                            </div>
                            {% endif %}

                        </div>
                        {% endfor %}
                    </div>
                </div>

                <!-- Right Column - System Settings -->
                <div class="col-md-4 overflow-auto" style="height: 100%;">
                    <h6 class="fw-bold mb-3">System Settings</h6>
                    
                    <!-- Charges Section -->
                    <div class="card mb-1">
                        <div class="card-header bg-light">
                            <h6 class="my-0">Charges & Taxes</h6>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label class="form-label">Service Charge (%)</label>
                                <div class="input-group">
                                    <input type="number" class="form-control" id="serviceChargeInput" 
                                           value="{{ service_charge }}" onchange="setTwoNumberDecimal(event)" 
                                           min="0" max="100" step="0.5">
                                    <button class="btn btn-primary" type="button" onclick="saveServiceCharge()">
                                        Save
                                    </button>
                                </div>
                                <small class="text-muted">Applies only to dine-in orders</small>
                            </div>
                            
                            <div class="mb-1">
                                <label class="form-label">VAT Rate (%)</label>
                                <div class="input-group">
                                    <input type="number" class="form-control" id="vatInput" 
                                           value="{{ vat_rate }}" onchange="setTwoNumberDecimal(event)" 
                                           min="0" max="100" step="0.5">
                                    <button class="btn btn-primary" type="button" onclick="saveVat()">
                                        Save
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Interface Settings -->
                    <div class="card">
                        <div class="card-header bg-light">
                            <h6 class="my-0">Interface Options</h6>
                        </div>
                        <div class="card-body">
                            <div class="mb-3">
                                <label class="form-label">Quick Cart Feature</label>
                                <div class="btn-group w-100" role="group">
                                    <input type="radio" class="btn-check" name="quickCartradio" 
                                           id="quickCart1" autocomplete="off" {% if quick_cart %}checked{% endif %}>
                                    <label class="btn btn-outline-success" for="quickCart1">Enabled</label>
                                    
                                    <input type="radio" class="btn-check" name="quickCartradio" 
                                           id="quickCart2" autocomplete="off" {% if not quick_cart %}checked{% endif %}>
                                    <label class="btn btn-outline-danger" for="quickCart2">Disabled</label>
                                </div>
                                <small class="text-muted">Create a takeaway cart just by pressing new</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

{% endblock %}
{% block footer %}
<script src="{{ url_for('static', filename='js/pos.helpers.js') }}"></script>
<script>
document.addEventListener('DOMContentLoaded', () => {
  const onOffButtons = document.querySelectorAll('.on-off');
  onOffButtons.forEach(button => {
    button.addEventListener('click', function() {
      const method = this.dataset.method;
      const value = this.value === 'on' ? 1 : 0;

      fetch('/update_pos_method', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ method, value }),
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
          showToast(method +" updated.", true)
          console.log('Data updated successfully:', data.message);
      })
      .catch(error => {
        showToast('Error updating data:', error.message, false)
        console.error('Error updating data:', error.message);
      });
    });
  });

  const menuOptions = document.querySelectorAll('.menu-option');
  menuOptions.forEach(option => {
    option.addEventListener('click', function() {
      const method = this.dataset.method;
      const property = this.dataset.property;
      const value = parseInt(this.dataset.value);

      fetch('/update_pos_menu_option', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ method, property, value }),
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
          showToast(method +" menu updated.", true)
          console.log('Data updated successfully:', data.message);
      })
      .catch(error => {
          showToast('Error updating data:', error.message, false)
          console.error('Error updating data:', error.message);
      });
    });
  });
});

function deleteTable(id) {
  fetch('/delete_dining_table', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify({ table_id: id })
  })
  .then(response => response.json())
  .then(data => {
      const tablesData = data;
      generateTableButtons(tablesData);
      showToast("Table deleted!", true)
  })
  .catch(error => {
      console.error('Error deleting table:', error.message);
      showToast('Error deleting table: '+ error.message, true)
  });
}

function saveTable() {
  const tableNumberInput = document.getElementById('tableNumber');

  const tableNumber = tableNumberInput.value.trim();
  if (tableNumber === '') {
    displayError('Table number cannot be empty.');
    return;
  }

  const tableNumberInt = parseInt(tableNumber, 10);
  if (isNaN(tableNumberInt) || tableNumberInt <= 0) {
    displayError('Table number must be a positive integer.');
    return;
  }

  const existingTableNumbers = Array.from(document.querySelectorAll('#dataContainer button'))
    .map(button => button.textContent.split(' ')[0]);

  if (existingTableNumbers.includes(tableNumber)) {
    displayError('Table number already exists.');
    return;
  }

  fetch('/add_new_table', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ tableNumber: tableNumberInt }),
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to save table. Please try again.');
      }
      return response.json();
    })
    .then(data => {
      const tablesData = data.tables;
      generateTableButtons(tablesData);
      showToast("Table saved successfully!", true)
      tableNumberInput.value = tablesData.length + 1;
    })
    .catch(error => {
      console.error('Error saving table:', error.message);
      displayError(error.message);
    });
}

function displayError(message) {
    showToast(message, false)
}

function setTwoNumberDecimal(event) {
    event.target.value = parseFloat(event.target.value).toFixed(2);
}

function generateTableButtons(tablesData) {
    const dataContainer = document.getElementById('dataContainer');
    dataContainer.innerHTML = '';
    const buttonsHTML = tablesData.map(table => `
        <div class="col">
            <div class="card ${table.table_occupied ? 'border-danger' : 'border-success'}">
                <div class="card-body p-1 text-center">
                    <h5 class="card-title mb-0">Table #${table.table_number}</h5>
                    <button class="btn btn-sm btn-outline-danger mt-2" 
                            value="${table.table_id}" 
                            onclick="deleteTable('${table.table_id}')" 
                            ${table.table_occupied ? 'disabled' : ''}>
                        <i class="bi bi-trash"></i> Remove
                    </button>
                </div>
            </div>
        </div>`).join('');
    dataContainer.innerHTML = buttonsHTML;
}

function saveServiceCharge() {
    const serviceChargeInput = document.getElementById('serviceChargeInput');
    const serviceChargeValue = serviceChargeInput.value.trim() === '' ? 0 : parseFloat(serviceChargeInput.value);

    fetch('/update_service_charge', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ serviceCharge: serviceChargeValue })
    })
    .then(response => response.json())
    .then(data => {
        showToast("Service charge updated successfully!", true)
    })
    .catch(error => {
        showToast("Failed to update service charge.", false)
    });
}

function saveVat() {
    const vatInput = document.getElementById('vatInput');
    const vatValue = vatInput.value.trim() === '' ? 0 : parseFloat(vatInput.value);

    fetch('/update_vat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ vat: vatValue })
    })
    .then(response => response.json())
    .then(data => {
        showToast("VAT updated.", true)
    })
    .catch(error => {
        showToast("Failed to update VAT.", false)
    });
}

document.querySelectorAll('input[name="quickCartradio"]').forEach(radio => {
    radio.addEventListener('change', function () {
        const quickCartEnabled = document.getElementById('quickCart1').checked;

        fetch('/update_quick_cart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quick_cart: quickCartEnabled })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast("Quick Cart setting updated", true);
            } else {
                showToast("Failed to update setting", false);
            }
        })
        .catch(err => {
            console.error(err);
            showToast("An error occurred", false);
        });
    });
});

document.querySelectorAll('input[name="divisionHint"]').forEach(radio => {
    radio.addEventListener('change', function () {
        const divisionHintEnabled = document.getElementById('divisionHint1').checked;

        fetch('/update_division_hint', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ division_hint: divisionHintEnabled })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast("Division hint setting updated", true);
            } else {
                showToast("Failed to update setting", false);
            }
        })
        .catch(err => {
            console.error(err);
            showToast("An error occurred", false);
        });
    });
});
</script>  

{% endblock %}
