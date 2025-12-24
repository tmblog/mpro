from flask import jsonify
import json, sqlite3, os, csv, data_directory
from . import database
from collections import Counter

data_dir = data_directory.get_data_directory()

def create_pos_settings_file():
    try:
        settings_file_path = os.path.abspath(os.path.join(data_dir, 'pos_settings.json'))
        if not os.path.exists(settings_file_path):
            settings = {
                "pos_methods": [
                    {"method": "takeaway", "on": 1, "menu": 0},
                    {"method": "delivery", "on": 1, "menu": 1},
                    {"method": "dine", "on": 0, "menu": 0},
                    {"method": "waiting", "on": 0, "menu": 0}
                ],
                "service_charge": 0,
                "receipt_printer_settings": [
                    {
                        "page_width": 85,
                        "page_height": 300,
                        "font_size": 20,
                        "font_weight": "normal",
                        "header_text": "",
                        "footer_text": "",
                        "kitchen_print": False,
                        "online_header": False,
                        "online_footer": False
                    }
                ],
                "vat_rate": 20
            }
            with open(settings_file_path, 'w') as f:
                json.dump(settings, f, indent=4)
            return jsonify({"success": True, "message": "Settings file created successfully"}), 200
        else:
            return jsonify({"success": False, "message": "Settings file already exists"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error creating settings file: {str(e)}"}), 500

def add_escpos_settings():
    try:
        settings_file_path = os.path.abspath(os.path.join(data_dir, 'pos_settings.json'))
        
        # Check if the file exists first
        if not os.path.exists(settings_file_path):
            return jsonify({"success": False, "message": "Settings file doesn't exist. Please create it first."}), 404
        
        # Read the existing settings
        with open(settings_file_path, 'r') as f:
            settings = json.load(f)
        
        # Check if escpos_printer_settings already exists
        if "escpos_printer_settings" not in settings:
            # Add the new settings array
            settings["escpos_printer_settings"] = [
                {
                    "width": 48, # number of characters per line (24-48)
                    "font_style": "a", # 'a' (12x24) or 'b' (9x17)
                    "font_size_height": 1, # (width, height) multipliers (1-8) max support 2
                    "font_size_width": 1
                }
            ]
            
            # Write the updated settings back to the file
            with open(settings_file_path, 'w') as f:
                json.dump(settings, f, indent=4)
                
            return jsonify({"success": True, "message": "ESCPOS printer settings added successfully"}), 200
        else:
            return jsonify({"success": False, "message": "ESCPOS printer settings already exist"}), 200
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Error updating settings file: {str(e)}"}), 500

# used in pos/async_settings.py
def create_async_settings_file():
    try:
        settings_file_path = os.path.abspath(os.path.join(data_dir, 'async_settings.json'))
        if not os.path.exists(settings_file_path):
            with open(settings_file_path, 'w') as f:
                settings = {
                    "payment_methods":{
                        "1":{"name":"Cash","on":1},
                        "2":{"name":"Card","on":1},
                        "3":{"name":"Split","on":1}
                        },
                    "payment_vendors":{
                        "1":{"vendor_name":"Dojo","on":0},
                        "2":{"vendor_name":"Card","on":1},
                        "3":{"vendor_name":"Verofy Cloud","on":0},
                        "4":{"vendor_name":"Verofy LAN","on":0},
                        "5":{"vendor_name":"Viva","on":0}
                        }
                    }
                json.dump(settings, f, indent=4)
            return jsonify({"success": True, "message": "Settings file created successfully"}), 200
        else:
            return jsonify({"success": False, "message": "Settings file already exists"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error creating settings file: {str(e)}"}), 500

def clean_name(name):
    return name.split('+')[0].strip()

def process_and_insert_products_json_data(add_price):
    try:
        database.empty_product_categories()
        upload_folder = os.path.join(data_dir, 'uploads')
        json_file_path = os.path.join(upload_folder, 'products.json')

        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)

        conn, cursor = database.get_database_connection()
        total_inserted = 0

        for category_name, category_data in data.items():
            try:
                category_order = category_data[0].get('order', 0)
            except (IndexError, KeyError):
                category_order = 0

            cursor.execute('''
                INSERT INTO category (category_name, category_order)
                VALUES (?, ?)
            ''', (category_name, category_order))
            conn.commit()
            category_id = cursor.lastrowid

            for product in category_data:
                out_price_addition = add_price

                if 'vari' not in product:
                    in_price = float(product['price'])
                    out_price = in_price + float(out_price_addition)
                    cpn = product.get('cpn', 0)
                    cursor.execute('''
                        INSERT INTO products (category_id, product_name, in_price, out_price, cpn)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (category_id, product['name'], in_price, out_price, cpn))
                    conn.commit()
                    product_id = cursor.lastrowid

                    options_str = product.get('options', '')
                    if options_str:
                        for index, option_id_str in enumerate(options_str.split(',')):
                            option_id = int(option_id_str.strip())
                            cursor.execute("SELECT option_type FROM options WHERE option_id = ?", (option_id,))
                            row = cursor.fetchone()
                            option_item_max = 1 if not row else (1 if row[0] == "dropdown" else 99)

                            cursor.execute('''
                                INSERT INTO product_options (product_id, option_id, option_order, option_item_max)
                                VALUES (?, ?, ?, ?)
                            ''', (product_id, option_id, index, option_item_max))

                    total_inserted += 1

                else:
                    for vari_item in product['vari']:
                        product_name = f"{product['name']} {vari_item['name']}"
                        in_price = float(vari_item['price'])
                        out_price = in_price + float(out_price_addition)
                        cpn = vari_item.get('cpn', 0)

                        cursor.execute('''
                            INSERT INTO products (category_id, product_name, in_price, out_price, cpn)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (category_id, product_name, in_price, out_price, cpn))
                        conn.commit()
                        product_id = cursor.lastrowid

                        options_str = vari_item.get('options', '')
                        if options_str:
                            for index, option_id_str in enumerate(options_str.split(',')):
                                option_id = int(option_id_str.strip())
                                cursor.execute("SELECT option_type FROM options WHERE option_id = ?", (option_id,))
                                row = cursor.fetchone()
                                option_item_max = 1 if not row else (1 if row[0] == "dropdown" else 99)

                                cursor.execute('''
                                    INSERT INTO product_options (product_id, option_id, option_order, option_item_max)
                                    VALUES (?, ?, ?, ?)
                                ''', (product_id, option_id, index, option_item_max))

                        total_inserted += 1

        conn.commit()
        conn.close()

        if total_inserted > 0:
            print(f"{total_inserted} products inserted successfully.")
        else:
            print("No data inserted into the database.")
    except Exception as e:
        print(f"Error processing and inserting JSON data: {str(e)}")

def process_and_insert_options_json_data(add_price):
    try:
        database.empty_options_items()
        # upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
        # json_file_path = os.path.join(upload_folder, 'options.json')
        upload_folder = os.path.join(data_dir, 'uploads')
        json_file_path = os.path.join(upload_folder, 'options.json')
        with open(json_file_path, 'r') as json_file:
            options_json = json.load(json_file)

        conn, cursor = database.get_database_connection()
        total_inserted = 0

        for option_data in options_json:
            option_id = int(option_data['id'])
            option_name = option_data['name']
            option_order = option_data['order']
            #option_type = option_data['type']
            # always check, qty defined in product edit
            option_type = "check"
            required = 1 if option_data['required'] == "required" else 0

            cursor.execute("INSERT INTO options (option_id, option_name, option_order, option_type, required) VALUES (?, ?, ?, ?, ?)",
                           (option_id, option_name, option_order, option_type, required))
            option_id = cursor.lastrowid

            # Process and insert option items
            for option_item in option_data['options']:
                option_item_name = option_item['name'].split('+')[0].strip()  # Remove '+' and trailing spaces
                option_item_in_price = float(option_item['price'])
                if option_item_in_price > 0:
                    option_item_out_price = option_item_in_price + float(add_price)
                else:
                    option_item_out_price = option_item_in_price

                cursor.execute("INSERT INTO option_items (option_id, option_item_name, option_item_in_price, option_item_out_price) VALUES (?, ?, ?, ?)",
                               (option_id, option_item_name, option_item_in_price, option_item_out_price))

        conn.commit()
        total_inserted += cursor.rowcount
        conn.close()
        if total_inserted > 0:
                print("Options data processed and inserted into the database successfully.")
        else:
            print("No data inserted into the database.")
    except Exception as e:
        return str(e)
# process options and maintain options id to match to product import
def process_and_insert_options_json_data_new():
    try:
        upload_folder = os.path.join(data_dir, 'uploads')
        json_file_path = os.path.join(upload_folder, 'options.json')
        with open(json_file_path, 'r') as json_file:
            options_data = json.load(json_file)

        conn, cursor = database.get_database_connection()

        cursor.executescript("""
            DELETE FROM option_item_groups;
            DELETE FROM product_options;
            DELETE FROM options;
            DELETE FROM option_items;
            -- Reset autoincrement counters
            DELETE FROM sqlite_sequence WHERE name IN ('options', 'option_items');
        """)

        # Cache for option_items to avoid re-adding duplicates
        existing_items = {}

        for option in options_data:
            option_id = option["id"]
            name = clean_name(option["name"])
            option_type = option["type"]
            option_order = option.get("order", 0)
            required = 1 if option.get("required") == "required" else 0

            # Insert into options with fixed ID
            cursor.execute("""
                INSERT INTO options (option_id, option_name, option_type, option_order, required)
                VALUES (?, ?, ?, ?, ?)
            """, (option_id, name, option_type, option_order, required))

            for item in option["options"]:
                item_name = clean_name(item["name"])
                item_price = item["price"]

                # Reuse or insert new option_item
                if item_name not in existing_items:
                    cursor.execute("""
                        INSERT INTO option_items (option_item_name, vatable)
                        VALUES (?, 0)
                    """, (item_name,))
                    option_item_id = cursor.lastrowid
                    existing_items[item_name] = option_item_id
                else:
                    option_item_id = existing_items[item_name]

                # Link to option via option_item_groups
                cursor.execute("""
                    INSERT INTO option_item_groups (
                        option_id, option_item_id, option_item_in_price, option_item_out_price, vatable
                    )
                    VALUES (?, ?, ?, ?, 0)
                """, (option_id, option_item_id, item_price, item_price))

        conn.commit()
        conn.close()
        print("✅ Import completed. Tables overwritten.")
    except Exception as e:
        print("Error executing SQL query:", e)
    except sqlite3.Error as e:
        print("Error executing SQL query:", e)
    finally:
        if conn:
            conn.close()

def process_csv_products_to_insert(csv_file):
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            is_valid, error_message = validate_csv_products_data(row)
            if not is_valid:
                print(f"Validation Error: {error_message}")
                continue
            conn, cursor = database.get_database_connection()
            cursor.execute('''
                INSERT INTO category (category_name) VALUES (:category_name)
                ON CONFLICT(category_name) DO NOTHING
            ''', {'category_name': row['category_name'].title()})
            cursor.execute('SELECT category_id FROM category WHERE category_name = :category_name', {'category_name': row['category_name']})
            category_id = cursor.fetchone()[0]

            cursor.execute('''
                INSERT INTO products (category_id, product_name, in_price, out_price, is_favourite)
                VALUES (:category_id, :product_name, :in_price, :out_price, :is_favourite)
            ''', {
                'category_id': category_id,
                'product_name': row['product_name'].title(),
                'in_price': float(row['in_price']),
                'out_price': float(row['out_price']),
                'is_favourite': int(row['is_favourite']),
            })
        conn.commit()
        conn.close()

def validate_csv_products_data(row):
    mandatory_fields = ['category_name', 'product_name', 'in_price']
    for field in mandatory_fields:
        if field not in row or not row[field]:
            return False, f"Missing or empty value for {field}"
    try:
        float(row['in_price'])
    except ValueError:
        return False, "in_price must be a number (int or float)"

    row['out_price'] = row.get('out_price', row['in_price'])
    row['is_favourite'] = row.get('is_favourite', 0)

    return True, None

def get_pos_settings(setting=None):
    # Accepts the key of the json file as an optional parameter
    json_file_path = os.path.join(data_dir, 'pos_settings.json')
    try:
        with open(json_file_path, 'r') as file:
            settings = json.load(file)
            if setting is not None:
                return settings.get(setting, [])
            else:
                return settings
    except FileNotFoundError:
        print(f"File not found: {json_file_path}")
        return []

def get_multiple_pos_settings(*settings):
    json_file_path = os.path.join(data_dir, 'pos_settings.json')
    try:
        with open(json_file_path, 'r') as file:
            all_settings = json.load(file)
            
            if not settings:
                return all_settings
                
            result = {}
            for setting in settings:
                result[setting] = all_settings.get(setting, [])
            return result
                
    except FileNotFoundError:
        print(f"File not found: {json_file_path}")
        return {}

def pos_methods(cart_id, change=None):
    pos_methods = get_pos_settings("pos_methods")
    quick_cart = get_pos_settings("quick_cart")
    if cart_id:
        current_cart_response = database.get_current_cart_data(cart_id)
        current_cart_data = json.loads(current_cart_response.get_data(as_text=True))
    else:
        current_cart_data = {}
    filtered_pos_methods = [method for method in pos_methods if method.get('on', 0) == 1]
    for method in filtered_pos_methods:
        if method.get('method') == 'dine' and method.get('on', 0) == 1:
            if change:
                method['tables'] = database.get_all_tables()
            else:
                method['tables'] = database.get_free_tables()
    return jsonify({
        "methods": filtered_pos_methods,
        "quick_cart": quick_cart,
        "current_cart_data": current_cart_data
    })

def get_discounts():
    pos_discounts = get_pos_settings("discounts")
    return json.dumps(pos_discounts)

def service_charge():
    try:
        service_charge = get_pos_settings("service_charge")
        return float(service_charge)
    except (TypeError, ValueError):
        return 0.0

def get_pos_methods():
    pos_methods = get_pos_settings("pos_methods")
    return json.dumps(pos_methods)

def get_vat_rate():
    try:
        vat_rate = get_pos_settings("vat_rate")
        return float(vat_rate) / 100
    except (TypeError, ValueError):
        return 0.0

def quick_cart():
    try:
        quick_cart = get_pos_settings("quick_cart")
        return bool(quick_cart)
    except (TypeError, ValueError):
        return False

def get_division_hint():
    try:
        division_hint = get_pos_settings("division_hint")
        return bool(division_hint)
    except (TypeError, ValueError):
        return False

def save_pos_methods(updated_pos_methods):
    #blueprint_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(data_dir, 'pos_settings.json')
    with open(json_file_path, 'r+') as file:
        data = json.load(file)

        data['pos_methods'] = updated_pos_methods
        file.seek(0)
        file.truncate()
        json.dump(data, file, indent=2)

def update_pos_method(method, value):
    pos_methods_str = get_pos_methods()
    pos_methods = json.loads(pos_methods_str)

    for pos_method in pos_methods:
        if pos_method['method'] == method:
            pos_method['on'] = value
            break
    save_pos_methods(pos_methods)

def update_pos_menu_option(method, value):
    pos_methods_str = get_pos_methods()
    pos_methods = json.loads(pos_methods_str)
    for pos_method in pos_methods:
        if pos_method['method'] == method:
            pos_method['menu'] = value
            break
    save_pos_methods(pos_methods)

def update_service_charge(service_charge):
    #blueprint_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(data_dir, 'pos_settings.json')
    try:
        with open(json_file_path, 'w') as file:
            json.dump(service_charge, file, indent=2)
    except Exception as e:
        print(f"Error updating settings: {str(e)}")

def update_vat(vat_amount):
    json_file_path = os.path.join(data_dir, 'pos_settings.json')
    try:
        with open(json_file_path, 'w') as file:
            json.dump(vat_amount, file, indent=2)
    except Exception as e:
        print(f"Error updating settings: {str(e)}")

def get_pos_printer_settings():
    receipt_printer_settings = get_pos_settings("receipt_printer_settings")
    return receipt_printer_settings

def update_printer_settings(page_width, page_height, font_size, font_weight, header_text, footer_text, kitchen_print, online_header, online_footer):
    json_file_path = os.path.join(data_dir, 'pos_settings.json')
    
    try:
        with open(json_file_path, 'r+') as file:
            pos_settings = json.load(file)
            pos_settings['receipt_printer_settings'][0]['page_width'] = page_width
            pos_settings['receipt_printer_settings'][0]['page_height'] = page_height
            pos_settings['receipt_printer_settings'][0]['font_size'] = font_size
            pos_settings['receipt_printer_settings'][0]['font_weight'] = font_weight
            pos_settings['receipt_printer_settings'][0]['header_text'] = header_text
            pos_settings['receipt_printer_settings'][0]['footer_text'] = footer_text
            pos_settings['receipt_printer_settings'][0]['kitchen_print'] = kitchen_print
            pos_settings['receipt_printer_settings'][0]['online_header'] = online_header
            pos_settings['receipt_printer_settings'][0]['online_footer'] = online_footer
            
            file.seek(0)  # Move the file pointer to the beginning
            json.dump(pos_settings, file, indent=4)
            file.truncate()  # Truncate the file to remove any extra data
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Error updating settings: {str(e)}'}), 500

# updates or creates new key add_new_property_to_settings_file() potentially redundant
def update_pos_settings(new_key, new_value):
    json_file_path = os.path.join(data_dir, 'pos_settings.json')
    try:
        # Read the existing settings
        settings = get_pos_settings()
        
        # Update the settings dictionary
        settings[new_key] = new_value
        
        # Write the updated settings back to the file
        with open(json_file_path, 'w') as file:
            json.dump(settings, file, indent=4)
        
        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Error updating settings: {str(e)}'}), 500
    
def update_multiple_pos_setting(setting_key, updates):
    """
    Updates the first item of the specified setting list in pos_settings.json.
    If the setting is not a list (e.g. vat_rate), it updates the value directly.

    Returns a dict indicating success and the updated value.
    """
    json_file_path = os.path.join(data_dir, 'pos_settings.json')

    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {json_file_path}"}

    # Handle list-based settings (like receipt_printer_settings)
    if setting_key in ["receipt_printer_settings", "escpos_printer_settings"]:
        if setting_key not in data or not isinstance(data[setting_key], list):
            data[setting_key] = [{}]
        if not data[setting_key]:
            data[setting_key].append({})
        data[setting_key][0].update(updates)
        updated_value = data[setting_key][0]

    # Handle single-value settings (like vat_rate)
    else:
        data[setting_key] = updates
        updated_value = updates

    try:
        with open(json_file_path, 'w') as f:
            json.dump(data, f, indent=4)
        return {"success": True, "message": "Updated successfully","updated": {setting_key: updated_value}}
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_new_property_to_settings_file(settings_file, setting_property, setting_value):
    try:
        # Validate JSON-serializable value
        try:
            json.dumps(setting_value)
        except (TypeError, ValueError):
            print("Invalid setting value; must be JSON-serializable.")
            return jsonify({
                "success": False,
                "message": "Invalid setting value; must be JSON-serializable"
            }), 400

        settings_file_path = os.path.abspath(os.path.join(data_dir, settings_file))

        if not os.path.exists(settings_file_path):
            print("Settings file doesn't exist. Please create it first.")
            return jsonify({
                "success": False,
                "message": "Settings file doesn't exist. Please create it first."
            }), 404

        with open(settings_file_path, 'r') as f:
            settings = json.load(f)

        # ---- Handle pos_methods ----
        if setting_property == "pos_methods":
            if not isinstance(settings.get("pos_methods"), list):
                print("pos_methods is not a list, initializing it as an empty list.")
                return jsonify({
                    "success": False,
                    "message": "pos_methods is not a list"
                }), 400

            if not isinstance(setting_value, dict) or "method" not in setting_value:
                print("Invalid setting_value for pos_methods; must be a dict with a 'method' key.")
                return jsonify({
                    "success": False,
                    "message": "When adding to pos_methods, value must be a dict with a 'method' key"
                }), 400

            existing_methods = [m["method"] for m in settings["pos_methods"] if "method" in m]

            # Skip if method already exists
            if setting_value["method"] in existing_methods:
                print(f"Method '{setting_value['method']}' already exists in pos_methods.")
                return jsonify({
                    "success": False,
                    "message": f"Method '{setting_value['method']}' already exists"
                }), 200

            settings["pos_methods"].append(setting_value)
            print(f"Added new method '{setting_value['method']}' to pos_methods.")

        # ---- Handle top-level properties ----
        else:
            if setting_property in settings:
                print(f"Setting '{setting_property}' already exists.")
                return jsonify({
                    "success": False,
                    "message": f"Setting '{setting_property}' already exists"
                }), 200

            settings[setting_property] = setting_value

        # Save changes
        with open(settings_file_path, 'w') as f:
            json.dump(settings, f, indent=4)
        print(f"New setting '{setting_property}' added successfully.")
        return jsonify({
            "success": True,
            "message": f"New setting '{setting_property}' added successfully"
        }), 200

    except Exception as e:
        print(f"Error updating settings file: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error updating settings file: {str(e)}"
        }), 500
