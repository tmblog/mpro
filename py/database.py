import sqlite3, json, os, io, helpers, data_directory, time, random
from flask import jsonify, session
from datetime import datetime, timedelta, timezone
from . import json_utils, async_settings
from collections import defaultdict
from logging_utils import logger, log_error

data_dir = data_directory.get_data_directory()

def get_database_connection():
    try:
        pdb_db_path = os.path.join(data_dir, "pos_database.db")
        conn = sqlite3.connect(pdb_db_path)
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        raise Exception(f"Error connecting to the database: {str(e)}")

def create_pos_database():
    try:
        conn, cursor = get_database_connection()

        # Create the 'employee' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pin INTEGER UNIQUE,
                name TEXT,
                hourly_rate REAL DEFAULT 0,
                role INTEGER, 
                app_theme TEXT DEFAULT 'light'
                )
        ''')

        # Insert the super admin
        employee_name = 'super'
        employee_role = 5
        cursor.execute("SELECT * FROM employees WHERE name = ? AND role = ?", (employee_name, employee_role))
        employee_data = cursor.fetchone()
        if not employee_data:
            cursor.execute("INSERT INTO employees (pin, name, hourly_rate, role) VALUES (?, ?, ?, ?)", (2960, employee_name, 1.00, employee_role))
            conn.commit()

        # Create the 'attendance' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                clock_in DATETIME DEFAULT CURRENT_TIMESTAMP,
                clock_out DATETIME NULL, -- Nullable
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
        ''')

        # Create the 'category' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "category" (
                "category_id"	INTEGER,
                "category_name"	TEXT,
                "category_order"	INTEGER DEFAULT 0,
                "category_colour"	TEXT,
                "category_text_colour"	TEXT,
                "is_hidden"	INTEGER DEFAULT 0,
                PRIMARY KEY("category_id" AUTOINCREMENT)
            )
        ''')

        # Create the 'options' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "options" (
                "option_id"	INTEGER,
                "option_name"	TEXT,
                "option_order" INTEGER DEFAULT 0,
                "option_type"	TEXT,
                "required"	INTEGER DEFAULT 0,
                "is_hidden"	INTEGER DEFAULT 0,
                PRIMARY KEY("option_id" AUTOINCREMENT)
            )
        ''')

        # Create the 'cart_dining_tables' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "cart_dining_tables" (
                order_table_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id INTEGER,
                table_number TEXT,
                table_cover INTEGER
            )
        ''')

        # Create the 'customer_addresses' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "customer_addresses" (
                address_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT,
                address TEXT,
                postcode TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
            )
        ''')

        # Create the customers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "customers" (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                customer_telephone TEXT
            )
        ''')

        # Insert the guest customer to use with all orders without customer name and phone
        customer_name = 'Guest'
        customer_telephone = '00000'
        cursor.execute("SELECT * FROM customers WHERE customer_name = ? AND customer_telephone = ?", (customer_name, customer_telephone))
        customer_data = cursor.fetchone()
        if not customer_data:
            cursor.execute("INSERT INTO customers (customer_name, customer_telephone) VALUES (?, ?)", (customer_name, customer_telephone))
            conn.commit()

        # Create the dining tables table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "dining_tables" (
                table_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_number TEXT,
                table_occupied INTEGER DEFAULT 0
            )
        ''')

        # Create the 'product_modifiers' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "product_modifiers" (
                modifier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                modifier_name TEXT
            )
        ''')

        # Create the 'card_terminals' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "card_terminals" (
                tid TEXT PRIMARY KEY,
                terminal_location TEXT
            , selected TEXT DEFAULT 0)
        ''')

        # Create the 'cart' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "cart" (
                "cart_id"	INTEGER,
                "order_type"	NUMERIC,
                "order_menu"	INTEGER,
                "order_date"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "overall_note"	TEXT,
                "customer_id"	INTEGER,
                "cart_discount_type"	TEXT DEFAULT 'fixed',
                "cart_discount"	DECIMAL(10, 2) DEFAULT 0,
                "cart_service_charge"	INTEGER DEFAULT 0,
                "cart_status"	TEXT DEFAULT 'processing',
                "cart_charge_updated"	TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "cart_started_by"	INTEGER,
                "cart_updated_by"	INTEGER,
                "in_use"	INTEGER DEFAULT 0, vat_amount DECIMAL(10,2) DEFAULT 0, sync_status TEXT DEFAULT 'pending',
                PRIMARY KEY("cart_id" AUTOINCREMENT)
            )
        ''')

        # Create the 'cart_items' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "cart_item" (
                "cart_item_id"	INTEGER,
                "cart_id"	INTEGER,
                "product_id"	INTEGER,
                "product_name"	TEXT,
                "price"	DECIMAL(10, 2),
                "quantity"	INTEGER,
                "options"	TEXT,
                "product_note"	TEXT,
                "product_discount_type"	TEXT DEFAULT 'fixed',
                "product_discount"	DECIMAL(10, 2) DEFAULT 0,
                "category_order"	INTEGER, vatable INTEGER DEFAULT 0,
                PRIMARY KEY("cart_item_id" AUTOINCREMENT),
                FOREIGN KEY("cart_id") REFERENCES "cart"("cart_id") ON DELETE CASCADE ON UPDATE CASCADE
            )
        ''')

        # Create the 'cart_payments' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "cart_payments" (
                "cart_payments_id"	INTEGER,
                "cart_id"	INTEGER,
                "payment_method"	TEXT,
                "discounted_total"	DECIMAL(10, 2),
                PRIMARY KEY("cart_payments_id" AUTOINCREMENT),
                FOREIGN KEY("cart_id") REFERENCES "cart"("cart_id")
            )
        ''')

        # Create the 'products' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "products" (
                "product_id"	INTEGER,
                "category_id"	INTEGER,
                "product_name"	TEXT,
                "in_price"	REAL,
                "out_price"	REAL,
                "cpn"	INTEGER,
                "is_favourite"	INTEGER DEFAULT 0,
                "is_hidden"	INTEGER DEFAULT 0,
                "vatable"	INTEGER DEFAULT 0,
                "barcode"	TEXT,
                FOREIGN KEY("category_id") REFERENCES "category"("category_id"),
                PRIMARY KEY("product_id" AUTOINCREMENT)
            )
        ''')

        # Create the 'option_items' table if it does not exist 1st
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "option_items" (
                "option_item_id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "option_item_name" TEXT,
                "vatable" INTEGER DEFAULT 0
            )
        ''')

        # Create the 'product_options' table if it does not exist 2nd
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "product_options" (
                "product_id" INTEGER,
                "option_id" INTEGER,
                "is_hidden" INTEGER DEFAULT 0,
                "option_item_max" INTEGER DEFAULT 1,
                FOREIGN KEY("option_id") REFERENCES "options"("option_id"),
                FOREIGN KEY("product_id") REFERENCES "products"("product_id")
            )
        ''')

        # Create the 'option_item_groups' table if it does not exist 3rd
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "option_item_groups" (
                "option_id" INTEGER,
                "option_item_id" INTEGER,
                "option_item_in_price" REAL DEFAULT 0,
                "option_item_out_price" REAL DEFAULT 0,
                "is_hidden" INTEGER DEFAULT 0,
                "vatable" INTEGER DEFAULT 0,
                PRIMARY KEY("option_id", "option_item_id"),
                FOREIGN KEY("option_id") REFERENCES "options"("option_id") ON DELETE CASCADE,
                FOREIGN KEY("option_item_id") REFERENCES "option_items"("option_item_id") ON DELETE CASCADE
            )
        ''')

        # Create the 'settings' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Create the 'discount_presets' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discount_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount REAL
            )
        ''')

        # Create the 'gallery' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gallery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                image_order INTEGER DEFAULT 1,
                duration INTEGER DEFAULT 7,
                active INTEGER DEFAULT 1
            )
        ''')

        # Create the 'kitchen_orders' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kitchen_orders (
                order_id INT,
                item_id INT,
                kitchen_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (order_id, item_id),
                FOREIGN KEY (order_id) REFERENCES cart(cart_id),
                FOREIGN KEY (item_id) REFERENCES cart_item(cart_item_id)
            )
        ''')

        # create discount_presets table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discount_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount REAL
            )
        ''')

        # create refunds table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id INTEGER,
                payment_type TEXT,
                amount DECIMAL(10, 2),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create the 'delivery_rules' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delivery_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_group INTEGER,              -- optional: groups related rules together
                rule_type TEXT NOT NULL,         -- 'base', 'per_mile', 'discount_amount', 'discount_percent'
                base_price REAL,                 -- for 'base' rule
                x_amount REAL,                   -- used as price per chunk or discount value
                y_mile REAL,                     -- distance chunk size for 'per_mile' (e.g., per 2 miles)
                min_order_total REAL,           -- threshold for applying discount
                discount_value REAL,            -- discount amount or percentage
                max_distance REAL,              -- max distance this rule applies to (optional)
                active INTEGER DEFAULT 1        -- 1 = active, 0 = inactive
            )
        ''')

        # Create the 'option groups' table if it does not exist used to create option builder/groups
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                group_description TEXT
            );
        ''')

        # Create the 'option_group_items' table if it does not exist used to link options to groups for templates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS option_group_items (
                group_id INTEGER,
                option_id INTEGER,
                option_item_max INTEGER DEFAULT 1,
                option_order INTEGER DEFAULT 0,
                FOREIGN KEY (group_id) REFERENCES option_groups(group_id),
                FOREIGN KEY (option_id) REFERENCES options(option_id)
            );
        ''')

        # create the caller id table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caller_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caller_id TEXT NOT NULL,
                line INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # create the menus table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS menus (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            sort INTEGER DEFAULT 0 CHECK(sort >= 0),
            menu_colour TEXT
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menus_sort ON menus(sort)")

        # create the menus table
        cursor.execute('''
           CREATE TABLE IF NOT EXISTS menu_categories (
                menu_id     INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                sort        INTEGER DEFAULT 0 CHECK(sort >= 0),
                PRIMARY KEY (menu_id, category_id),
                FOREIGN KEY (menu_id)     REFERENCES menus(id)      ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE CASCADE
            );
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_categories_menu ON menu_categories(menu_id, sort)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_categories_cat  ON menu_categories(category_id)")

        # Create dining_rooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dining_rooms (
                room_id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_label TEXT NOT NULL UNIQUE,
                room_order INTEGER DEFAULT 0
            )
        ''')

        # Add room_id to dining_tables (if not exists)
        cursor.execute("PRAGMA table_info(dining_tables)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'room_id' not in columns:
            cursor.execute('ALTER TABLE dining_tables ADD COLUMN room_id INTEGER REFERENCES dining_rooms(room_id)')

        # Add table_id to cart_dining_tables (if not exists)  
        cursor.execute("PRAGMA table_info(cart_dining_tables)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'table_id' not in columns:
            cursor.execute('ALTER TABLE cart_dining_tables ADD COLUMN table_id INTEGER REFERENCES dining_tables(table_id)')

        # Add print_group to category table (if not exists)
        cursor.execute("PRAGMA table_info(category)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'print_group' not in columns:
            cursor.execute('ALTER TABLE category ADD COLUMN print_group INTEGER DEFAULT 1')

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

        message = "Database 'pos_database.db' and tables created successfully."
        return jsonify({"success": True, "message": message}), 200
        
    except sqlite3.Error as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500


def empty_product_categories():
    try:
        # Connect to the SQLite database
        conn, cursor = get_database_connection()

        # Delete all records from the "categories" table and get the number of rows affected
        cursor.execute('DELETE FROM category')
        num_categories_deleted = cursor.rowcount

        # Delete all records from the "products" table and get the number of rows affected
        cursor.execute('DELETE FROM products')
        num_products_deleted = cursor.rowcount

        # Commit the changes and close the database connection
        conn.commit()
        conn.close()

        if num_categories_deleted > 0 or num_products_deleted > 0:
            print("Category and Product Tables emptied successfully.")
        else:
            print("No records found to delete.")
    except Exception as e:
        print(f"Error emptying tables: {str(e)}")

def empty_options_items():
    try:
        # Connect to the SQLite database
        conn, cursor = get_database_connection()

        cursor.execute('DELETE FROM option_item_groups')
        option_groups_deleted = cursor.rowcount

        # Delete all records from the "options" table and get the number of rows affected
        cursor.execute('DELETE FROM options')
        options_deleted = cursor.rowcount

        # Delete all records from the "option_items" table and get the number of rows affected
        cursor.execute('DELETE FROM option_items')
        items_deleted = cursor.rowcount

         # Delete all records from the "product_options" table and get the number of rows affected
        cursor.execute('DELETE FROM product_options')
        product_options_deleted = cursor.rowcount

        # Commit the changes and close the database connection
        conn.commit()
        conn.close()

        if options_deleted > 0 or items_deleted > 0 or product_options_deleted > 0:
            print("Option Tables emptied successfully.")
        else:
            print("No records found to delete.")
    except Exception as e:
        print(f"Error emptying tables: {str(e)}")

def get_all_categories():
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='category'")
        table_exists = cursor.fetchone()
        if not table_exists:
            return {}
        
        cursor.execute('''SELECT
            c.category_id,
            c.category_name,
            c.category_colour,
            c.category_text_colour,
            COUNT(CASE WHEN p.is_hidden = 0 THEN p.product_id END) AS product_count,
            c.category_order,
            COALESCE(c.print_group, 1) AS print_group
        FROM
            category c
        LEFT JOIN
            products p ON c.category_id = p.category_id
        WHERE
            c.is_hidden = 0
        GROUP BY
            c.category_id, c.category_name, c.category_colour
        ORDER BY
            c.category_order;
        ''')
        categories = cursor.fetchall()
        conn.close()
        categories_data = [{'category_id': row[0], 'category_name': row[1], 'category_colour': row[2], 'category_text_colour': row[3], 'product_count': row[4], 'category_order': row[5], 'print_group': row[6]} for row in categories]
        return categories_data
    except Exception as e:
        return [{'error': str(e)}]

def add_or_update_category(category, colour, text_colour, category_order=None, category_id=None, delete_category=None, print_group=1):
    try:
        conn, cursor = get_database_connection()
        if category_id and delete_category:
            cursor.execute(
                "DELETE FROM category WHERE category_id = ?",
                (category_id,)
            )
        elif category_id:
            cursor.execute(
                "UPDATE category SET category_name = ?, category_colour = ?, category_text_colour = ?, category_order = ?, print_group = ? WHERE category_id = ?",
                (category.title(), colour, text_colour, category_order, print_group, category_id)
            )
        else:
            cursor.execute(
                "INSERT INTO category (category_name, category_colour, category_text_colour, print_group) VALUES (?, ?, ?, ?)",
                (category.title(), colour, text_colour, print_group)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Error executing SQL query:", e)
    except sqlite3.Error as e:
        print("Error executing SQL query:", e)
    finally:
        if conn:
            conn.close()

def update_category_order(category_orders):
    try:
        conn, cursor = get_database_connection()
        for category_data in category_orders:
            category_id = category_data['id']
            category_order = category_data['category_order']
            cursor = conn.cursor()
            cursor.execute('UPDATE category SET category_order = ? WHERE category_id = ?', (category_order, category_id))
            conn.commit()
        conn.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
def update_category_colours():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('UPDATE category SET category_colour = ?, category_text_colour = ?', ("", "white"))
        conn.commit()
        conn.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# for products edit
def products_by_category(category_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT product_id, product_name, in_price, out_price, product_colour
            FROM products
            WHERE category_id = ?
            AND is_hidden = ?
            ORDER BY product_order, product_name
        ''', (category_id,0))
        
        products = cursor.fetchall()

        conn.close()
        products_data = [{'product_id': row[0], 'product_name': row[1], 'in_price': row[2], 'out_price': row[3], 'product_colour': row[4]} for row in products]

        return jsonify({'products': products_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def excluded_products_by_category(category_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT product_id, product_name, in_price, out_price, product_colour
            FROM products p
            WHERE category_id = ?
            AND is_hidden = ?
            AND NOT EXISTS (
                SELECT 1 
                FROM excluded_kitchen_products ekp 
                WHERE ekp.product_id = p.product_id
            )
            ORDER BY product_order, product_name
        ''', (category_id,0))
        
        products = cursor.fetchall()

        conn.close()
        products_data = [{'product_id': row[0], 'product_name': row[1], 'in_price': row[2], 'out_price': row[3], 'product_colour': row[4]} for row in products]

        return jsonify({'products': products_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# older version of get_products_for_pos

def get_products_for_pos(category_id, menu):
    conn, cursor = get_database_connection()
    if category_id:
        sql_query = """
            SELECT p.product_id,
                p.product_name,
                CASE
                    WHEN ? = 1 THEN p.out_price
                    WHEN ? = 0 THEN p.in_price
                    ELSE p.in_price
                END AS adjusted_price,
                GROUP_CONCAT(po.option_id) AS option_ids,
                c.category_order,
                p.vatable,
                p.product_colour
            FROM products p
            LEFT JOIN product_options po ON p.product_id = po.product_id AND po.is_hidden = 0
            LEFT JOIN category c ON p.category_id = c.category_id
            WHERE p.category_id = ? AND p.is_hidden = 0
            GROUP BY p.product_id, p.product_name, adjusted_price
            ORDER BY is_favourite DESC, p.product_order, p.product_name ASC
        """
    else:
        # category_id made 1 to represent parameter for is_favourite
        category_id = 1
        sql_query = """
            SELECT p.product_id,
                p.product_name,
                CASE
                    WHEN ? = 1 THEN p.out_price
                    WHEN ? = 0 THEN p.in_price
                    ELSE p.in_price
                END AS adjusted_price,
                GROUP_CONCAT(po.option_id) AS option_ids,
                c.category_order,
                p.vatable,
                p.product_colour
            FROM products p
            LEFT JOIN product_options po ON p.product_id = po.product_id AND po.is_hidden = 0
            LEFT JOIN category c ON p.category_id = c.category_id
            WHERE p.is_favourite = ?
            GROUP BY p.product_id, p.product_name, adjusted_price
            ORDER BY p.product_order, p.product_name
        """

    cursor.execute(sql_query, (menu, menu, category_id))
    products = cursor.fetchall()
    conn.close()
    return jsonify(products)
   
def get_products_for_pos_v2(category_id, menu):
    conn, cursor = get_database_connection()
    if category_id:
        sql_query = """
            SELECT p.product_id,
                p.product_name,
                CASE
                    WHEN ? = 1 THEN p.out_price
                    WHEN ? = 0 THEN p.in_price
                    ELSE p.in_price
                END AS adjusted_price,
                (
                    SELECT GROUP_CONCAT(option_id)
                    FROM (
                        SELECT po.option_id
                        FROM product_options po
                        WHERE po.product_id = p.product_id AND po.is_hidden = 0
                        ORDER BY po.option_order
                    )
                ) AS option_ids,
                c.category_order,
                p.vatable,
                p.product_colour,
                p.track_inventory,
                p.stock_quantity,
                p.low_stock_threshold
            FROM products p
            LEFT JOIN category c ON p.category_id = c.category_id
            WHERE p.category_id = ? 
            AND p.is_hidden = 0
            GROUP BY p.product_id, p.product_name, adjusted_price
            ORDER BY is_favourite DESC, p.product_order, p.product_name ASC
        """
    else:
        category_id = 1
        sql_query = """
            SELECT p.product_id,
                p.product_name,
                CASE
                    WHEN ? = 1 THEN p.out_price
                    WHEN ? = 0 THEN p.in_price
                    ELSE p.in_price
                END AS adjusted_price,
                (
                    SELECT GROUP_CONCAT(option_id)
                    FROM (
                        SELECT po.option_id
                        FROM product_options po
                        WHERE po.product_id = p.product_id AND po.is_hidden = 0
                        ORDER BY po.option_order
                    )
                ) AS option_ids,
                c.category_order,
                p.vatable,
                p.product_colour,
                p.track_inventory,
                p.stock_quantity,
                p.low_stock_threshold
            FROM products p
            LEFT JOIN category c ON p.category_id = c.category_id
            WHERE p.is_favourite = ?
            AND p.is_hidden = 0
            GROUP BY p.product_id, p.product_name, adjusted_price
            ORDER BY p.product_order, p.product_name
        """
    cursor.execute(sql_query, (menu, menu, category_id))
    products = cursor.fetchall()
    conn.close()
    return jsonify(products)

def get_product_details(product_id):
    conn, cursor = get_database_connection()

    product_query = """
            SELECT
                p.*,
                GROUP_CONCAT(po.option_id) AS option_ids,
                GROUP_CONCAT(po.option_item_max) AS option_item_max
            FROM
                products p
            LEFT JOIN
                product_options po ON p.product_id = po.product_id
            WHERE
                p.product_id = ?
            AND
                p.is_hidden = ?
            GROUP BY
                p.product_id, p.product_name;
        """
    product_result = cursor.execute(product_query, (product_id,0)).fetchone()

    options_query = "SELECT option_id, option_name, option_type FROM options WHERE is_hidden = 0;"
    options_result = cursor.execute(options_query).fetchall()
    conn.close()
    # 9 is barcode, 15 is ids, 16 is max
    result_dict = {
        "product_id": product_result[0],
        "product_name": product_result[2],
        "in_price": product_result[3],
        "out_price": product_result[4],
        "cpn": product_result[5],
        "is_favourite": product_result[6],
        "vatable": product_result[8],
        "barcode": product_result[9],
        "track_inventory": product_result[12],
        "stock_quantity": product_result[13],
        "low_stock_threshold": product_result[14],
        "option_ids": product_result[15].split(",") if product_result[15] else [],
        "options": [{"option_id": row[0], "option_name": row[1], "option_type": row[2]} for row in options_result],
        "option_item_max": product_result[16].split(",") if product_result[16] else []
    }

    result_json = json.dumps(result_dict, indent=2)
    return result_json

def get_dining_tables():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''SELECT * FROM dining_tables ORDER BY CAST(table_number AS INTEGER)
        ''')
        tables = cursor.fetchall()
        conn.close()
        table_data = [{'table_id': row[0], 'table_number': row[1], 'table_occupied': row[2]} for row in tables]
        return table_data
    except Exception as e:
        return [{'error': str(e)}]

def get_guest_customer():
    conn, cursor = get_database_connection()
    customer_name = 'Guest'
    customer_telephone = '00000'
    cursor.execute("SELECT customer_id FROM customers WHERE customer_name = ? AND customer_telephone = ?", (customer_name, customer_telephone))
    
    return cursor.fetchone()[0]

def fix_guest_customer():
    try:
        conn, cursor = get_database_connection()
        # set customer_name to Guest and customer_telephone to 00000 for customer_id 1
        cursor.execute("UPDATE customers SET customer_name = ?, customer_telephone = ? WHERE customer_id = ?", ('Guest', '00000', 1))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error fixing guest customer: {str(e)}")

def new_cart(cartData):
    """Updated to handle both single table and tables array"""
    conn = None
    try:
        data = cartData
        conn, cursor = get_database_connection()
        
        customer = cartData['customer']
        service_charge = customer.get('deliveryCharge', 0)
        customer_name = customer.get('customerName', '')
        customer_phone = customer.get('customerPhone', '')
        posted_customer = customer.get('customerId', '')
        posted_cart_id = int(cartData['cart_id'])
        current_menu = cartData['current_menu']
       
        conn.execute("BEGIN TRANSACTION")
        
        address_id = None
        
        if data['order_type'] == "dine":
            service_charge = json_utils.service_charge()
            customer_id = get_guest_customer()
        elif customer_name == "" and customer_phone == "" and data['order_type'] != "delivery":
            customer_id = get_guest_customer()
        elif posted_customer:
            customer_id = int(posted_customer)
            if customer_id > 1 and customer_name != "" and customer_phone != "":
                cursor.execute("UPDATE customers SET customer_name = ?, customer_telephone = ? WHERE customer_id = ?", (customer_name, customer_phone, customer_id))
        else:
            cursor.execute("INSERT INTO customers (customer_name, customer_telephone) VALUES (?, ?)", (customer_name, customer_phone))
            customer_id = cursor.lastrowid

        if 'customerAddress' in customer and customer['customerAddress'] != '' and 'customerPostcode' in customer and customer['customerPostcode'] != '' and customer['addressId'] == "":
            address = customer['customerAddress']
            postcode = customer['customerPostcode']
            distance = customer.get('addressDistance', 0)
            cursor.execute('''
                INSERT INTO customer_addresses (customer_id, address, postcode, distance)
                VALUES (?, ?, ?, ?)
            ''', (customer_id, address, postcode, distance))
            address_id = cursor.lastrowid
            
        if 'addressId' in customer and customer['addressId'] != '' and data['order_type'] == "delivery":
            address_id = customer['addressId']
            cursor.execute('''
                UPDATE customer_addresses SET address = ?, postcode = ? WHERE address_id = ?
            ''', (customer['customerAddress'], customer['customerPostcode'], address_id))

        employee_id = session.get('employee_id', 0)
        cursor.execute('''
            INSERT INTO cart (order_type, order_menu, order_date, overall_note, customer_id, cart_service_charge, cart_started_by, address_id)
            VALUES (?, ?, datetime('now', 'localtime'), ?, ?, ?, ?, ?)
            ''', (data['order_type'], data['order_menu'], data.get('overall_note', ''), customer_id, service_charge, employee_id, address_id if data['order_type'] == "delivery" else ""))
        
        cart_id = cursor.lastrowid
        
        # Handle dine-in tables (supports both single and multiple)
        if data['order_type'] == "dine":
            tables = customer.get('tables', [])
            
            # If using old single-table format, convert to array
            if not tables and customer.get('table'):
                tables = [{
                    'table_number': customer.get('table'),
                    'table_id': None,  # Will lookup by table_number
                    'cover': customer.get('cover', 0)
                }]
            
            for table_data in tables:
                table_number = table_data.get('table_number')
                table_id = table_data.get('table_id')
                cover = int(table_data.get('cover', 0))
                
                # If no table_id, look it up
                if not table_id and table_number:
                    cursor.execute('SELECT table_id FROM dining_tables WHERE table_number = ?', (table_number,))
                    result = cursor.fetchone()
                    table_id = result[0] if result else None
                
                # Mark table as occupied
                cursor.execute(
                    "UPDATE dining_tables SET table_occupied = ? WHERE table_number = ?",
                    (cart_id, table_number)
                )
                
                # Insert into junction table
                cursor.execute('''
                    INSERT INTO cart_dining_tables (cart_id, table_id, table_number, table_cover)
                    VALUES (?, ?, ?, ?)
                ''', (cart_id, table_id, table_number, cover))

        # Handle cart transfer (menu change) - price recalculation
        if posted_cart_id and current_menu != data['order_menu']:
            first_query = f"SELECT product_id, options FROM cart_item WHERE cart_id = {posted_cart_id}"
            cursor.execute(first_query)
            rows = cursor.fetchall()

            parameters_list = []
            for product_id, options_str in rows:
                second_query = f"SELECT in_price, out_price FROM products WHERE product_id = {product_id}"
                cursor.execute(second_query)
                result = cursor.fetchone()
                if result is None:
                    continue
                else:
                    in_price, out_price = result
                    new_item_price = in_price if int(data['order_menu']) == 0 else out_price

                if options_str:
                    options_list = options_str.split(',')
                    new_options = []
                    for option in options_list:
                        try:
                            option_id, name, _, option_set, quantity, vatable = option.split('|')
                            option_id = int(option_id)
                            option_set = int(option_set)
                            quantity = int(quantity)
                            vatable = bool(int(vatable))
                        except ValueError as e:
                            log_error(f"Skipping malformed option: {option} - Error: {str(e)}")
                            continue
                        
                        if not option_id:
                            continue
                        try:
                            cursor.execute(
                                "SELECT option_item_in_price, option_item_out_price FROM option_item_groups WHERE option_item_id = ?",
                                (option_id,)
                            )
                            in_price, out_price = cursor.fetchone()
                            new_price = in_price if int(data['order_menu']) == 0 else out_price
                            updated_option = f"{option_id}|{name}|{new_price}|{option_set}|{quantity}|{int(vatable)}"
                            new_options.append(updated_option)
                        except Exception as e:
                            log_error(f"Failed to process option {option_id}: {str(e)}")
                            continue

                    updated_options_str = ', '.join(new_options)
                else:
                    updated_options_str = ""

                parameters_list.append((new_item_price, updated_options_str, posted_cart_id, product_id))

            update_query = "UPDATE cart_item SET price = ?, options = ? WHERE cart_id = ? AND product_id = ?"
            cursor.executemany(update_query, parameters_list)
        
        # Transfer items from old cart
        cursor.execute('UPDATE cart_item SET cart_id = ? WHERE cart_id = ?', (cart_id, posted_cart_id))

        # Transfer notes
        cursor.execute('SELECT overall_note FROM cart WHERE cart_id = ?', (posted_cart_id,))
        source_overall_note = cursor.fetchone()
        if source_overall_note is not None:
            cursor.execute('UPDATE cart SET overall_note = ? WHERE cart_id = ?', (source_overall_note[0], cart_id))

        # Clear old cart's tables
        cursor.execute("UPDATE dining_tables SET table_occupied = 0 WHERE table_occupied = ?", (posted_cart_id,))
        
        # Delete old cart
        cursor.execute('DELETE FROM cart WHERE cart_id = ?', (posted_cart_id,))
        cursor.execute('DELETE FROM cart_dining_tables WHERE cart_id = ?', (posted_cart_id,))
        
        conn.commit()
        log_deleted_cart(posted_cart_id)
        return jsonify({'cart_id': cart_id})
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

def get_current_cart_data(cart_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT
                c.cart_id,
                c.order_type,
                c.order_menu,
                c.order_date,
                COUNT(ci.cart_id) AS cart_item_count,
                c.customer_id,
                cu.customer_name,
                cu.customer_telephone,
                CASE
                    WHEN c.order_type = 'delivery'
                    THEN ca.address_id
                    ELSE NULL
                END AS address_id,
                CASE
                    WHEN c.order_type = 'delivery'
                    THEN ca.address
                    ELSE NULL
                END AS address,
                CASE
                    WHEN c.order_type = 'delivery'
                    THEN ca.postcode
                    ELSE NULL
                END AS postcode,
                c.cart_charge_updated,
                e.name
            FROM cart c
            LEFT JOIN cart_item ci ON c.cart_id = ci.cart_id
            LEFT JOIN customers cu ON c.customer_id = cu.customer_id
            LEFT JOIN customer_addresses ca ON ca.address_id = c.address_id
            LEFT JOIN employees e ON cart_started_by = e.employee_id
            WHERE c.cart_id = ?
            GROUP BY c.cart_id
            ORDER BY c.order_date;
            ''', (cart_id,))
        
        cart_data = cursor.fetchone()
        if cart_data:
            # Get tables for dine-in orders
            tables = []
            table_display = None
            total_covers = 0
            
            if cart_data[1] == 'dine':  # order_type
                tables = get_cart_tables(cart_id)
                table_display = format_table_display(tables)
                total_covers = sum(t.get('cover', 0) for t in tables)
            
            cart_dict = {
                'cart_id': cart_data[0],
                'order_type': cart_data[1],
                'cart_menu': cart_data[2],
                'order_date': cart_data[3],
                'cart_item_count': cart_data[4],
                'customer_id': cart_data[5],
                'customer_name': cart_data[6],
                'customer_telephone': cart_data[7],
                'address_id': cart_data[8],
                'address': cart_data[9],
                'postcode': cart_data[10],
                'charge_updated': cart_data[11],
                'employee_name': cart_data[12],
                # New multi-table fields
                'table_display': table_display,
                'total_covers': total_covers,
                # Legacy fields for backwards compatibility
                'table_number': table_display or (tables[0]['table_number'] if tables else None),
                'table_cover': total_covers or (tables[0]['cover'] if tables else None)
            }
            conn.close()
            return jsonify(cart_dict)
        else:
            conn.close()
            return jsonify({'error': 'Cart not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def all_carts():
    """Updated to show merged tables in display"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''  
            SELECT
                c.cart_id,
                c.order_type,
                c.order_menu,
                c.order_date,
                c.customer_id,
                COUNT(ci.cart_id) AS cart_item_count,
                cu.customer_name
            FROM cart c
            LEFT JOIN cart_item ci ON c.cart_id = ci.cart_id
            LEFT JOIN customers cu ON c.customer_id = cu.customer_id
            WHERE c.cart_status = "processing"
            GROUP BY c.cart_id, c.order_type, c.order_menu, c.order_date, c.customer_id, cu.customer_name
            ORDER BY c.order_type;
        ''')
        
        results = cursor.fetchall()
        
        # For dine-in orders, get table display
        enriched_results = []
        for row in results:
            cart_id = row[0]
            order_type = row[1]
            
            table_display = None
            if order_type == 'dine':
                tables = get_cart_tables(cart_id)
                table_display = format_table_display(tables)
            
            # Convert to tuple with table_display added
            enriched_results.append(row + (table_display,))
        
        conn.close()
        return enriched_results
    except Exception as e:
        return []

def fetch_option_data(option_id, current_menu,product_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT
                options.*,                       
                GROUP_CONCAT(
                    'option_item_id: ' || option_items.option_item_id || ', ' ||
                    'option_item_name: ' || option_items.option_item_name || ', ' ||
                    'option_item_price: ' || 
                        CASE 
                            WHEN ? = 1 THEN oig.option_item_out_price 
                            ELSE oig.option_item_in_price 
                        END || ', ' ||
                    'vatable: ' || oig.vatable
                ) AS option_items_json, 
                po.option_item_max
            FROM 
                options
            LEFT JOIN 
                option_item_groups oig ON options.option_id = oig.option_id
            LEFT JOIN 
                option_items ON oig.option_item_id = option_items.option_item_id
            LEFT JOIN 
                product_options AS po ON options.option_id = po.option_id
            WHERE 
                options.option_id = ? 
                AND oig.is_hidden = ?
                AND po.product_id = ?
                AND po.option_id = ?
            GROUP BY 
                options.option_id;
        ''', (current_menu, option_id, 0, product_id, option_id))

        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        print("Error:", str(e))
        return None

def add_item_to_cart(item):
    try:
        data = item
        productId = data['productId']
        cartId = data['cartId']
        productName = data['productName']
        formattedPrice = data['formattedPrice']
        quantity = data['quantity']
        options = data['options']
        productNote = data['productNote']
        categoryOrder = data['categoryOrder']
        vatable = data['vatable']
        
        conn, cursor = get_database_connection()
        
        # Check inventory before adding
        cursor.execute(
            "SELECT track_inventory, stock_quantity FROM products WHERE product_id = ?",
            (productId,)
        )
        product = cursor.fetchone()
        
        if product:
            track_inventory = product[0]
            stock_quantity = product[1]
            
            if track_inventory == 1 and stock_quantity <= 0:
                conn.close()
                return {"error": f"{productName} is out of stock"}, 400
        
        # Check if item already exists in cart
        cursor.execute(
            "SELECT * FROM cart_item WHERE cart_id = ? AND product_id = ? AND options = ?",
            (cartId, productId, options)
        )
        existing_record = cursor.fetchone()
        
        if existing_record:
            new_quantity = existing_record[5] + 1
            
            # Check if enough stock for the new quantity
            if product and track_inventory == 1 and stock_quantity < new_quantity:
                conn.close()
                return {"error": f"Only {stock_quantity} of {productName} available"}, 400
            
            cursor.execute(
                "UPDATE cart_item SET quantity = ? WHERE cart_id = ? AND product_id = ? AND options = ?",
                (new_quantity, cartId, productId, options)
            )
        else:
            cursor.execute(
                "INSERT INTO cart_item (cart_id, product_id, product_name, price, quantity, options, product_note, category_order, vatable) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cartId, productId, productName, formattedPrice, quantity, options, productNote, categoryOrder, vatable)
            )
        
        # Update cart timestamp and sync status
        cursor.execute(
            """
            UPDATE cart
            SET cart_charge_updated = ?,
                sync_status = CASE WHEN sync_status != 'pending' THEN 'pending' ELSE sync_status END
            WHERE cart_id = ?
            """,
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cartId)
        )
       
        conn.commit()
        conn.close()
        return {"message": "Item added to cart successfully."}, 200
    except Exception as e:
        return {"error": str(e)}, 500

def get_item_by_barcode(barcode):
    try:
        conn, cursor = get_database_connection()
        cursor.execute(
            """SELECT 
                p.product_id, 
                p.product_name, 
                p.out_price, 
                c.category_order,
                p.vatable,
                p.track_inventory,
                p.stock_quantity
               FROM products p
               JOIN category c ON p.category_id = c.category_id
               WHERE p.barcode = ? AND p.is_hidden = 0""",
            (barcode,)
        )
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            return jsonify({'found': False, 'message': 'Product not found'}), 404
        
        # Check inventory
        track_inventory = product[5]
        stock_quantity = product[6]
        
        if track_inventory == 1 and stock_quantity <= 0:
            return jsonify({
                'found': False, 
                'message': f'{product[1]} is out of stock'
            }), 404
        
        return jsonify({
            'found': True,
            'productId': product[0],
            'productName': product[1],
            'formattedPrice': product[2],
            'options': 'null',
            'categoryOrder': product[3],
            'vatable': product[4]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# ROOM CRUD FUNCTIONS
# ============================================

# def create_dining_rooms_table():
#     """Create the dining_rooms table if it doesn't exist"""
#     try:
#         conn, cursor = get_database_connection()
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS dining_rooms (
#                 room_id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 room_label TEXT NOT NULL UNIQUE,
#                 room_order INTEGER DEFAULT 0
#             )
#         ''')
#         conn.commit()
#         conn.close()
#         return True
#     except Exception as e:
#         print(f"Error creating dining_rooms table: {e}")
#         return False

# def migrate_dining_tables_add_room_id():
#     """Add room_id column to dining_tables if it doesn't exist"""
#     try:
#         conn, cursor = get_database_connection()
#         # Check if column exists
#         cursor.execute("PRAGMA table_info(dining_tables)")
#         columns = [col[1] for col in cursor.fetchall()]
        
#         if 'room_id' not in columns:
#             cursor.execute('ALTER TABLE dining_tables ADD COLUMN room_id INTEGER REFERENCES dining_rooms(room_id)')
#             conn.commit()
#         conn.close()
#         return True
#     except Exception as e:
#         print(f"Error migrating dining_tables: {e}")
#         return False

# def migrate_cart_dining_tables_add_table_id():
#     """Add table_id column to cart_dining_tables if it doesn't exist"""
#     try:
#         conn, cursor = get_database_connection()
#         cursor.execute("PRAGMA table_info(cart_dining_tables)")
#         columns = [col[1] for col in cursor.fetchall()]
        
#         if 'table_id' not in columns:
#             cursor.execute('ALTER TABLE cart_dining_tables ADD COLUMN table_id INTEGER REFERENCES dining_tables(table_id)')
#             conn.commit()
#         conn.close()
#         return True
#     except Exception as e:
#         print(f"Error migrating cart_dining_tables: {e}")
#         return False

def get_all_rooms():
    """Get all dining rooms ordered by room_order"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT room_id, room_label, room_order FROM dining_rooms ORDER BY room_order, room_label')
        rooms = cursor.fetchall()
        conn.close()
        return [{'room_id': r[0], 'room_label': r[1], 'room_order': r[2]} for r in rooms]
    except Exception as e:
        print(f"Error getting rooms: {e}")
        return []

def add_room(room_label):
    """Add a new dining room"""
    try:
        conn, cursor = get_database_connection()
        # Get max order
        cursor.execute('SELECT COALESCE(MAX(room_order), 0) + 1 FROM dining_rooms')
        next_order = cursor.fetchone()[0]
        
        cursor.execute('INSERT INTO dining_rooms (room_label, room_order) VALUES (?, ?)', 
                      (room_label.strip(), next_order))
        room_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'room_id': room_id, 'rooms': get_all_rooms()})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Room already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_room(room_id, room_label):
    """Update a room's label"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('UPDATE dining_rooms SET room_label = ? WHERE room_id = ?', 
                      (room_label.strip(), room_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'rooms': get_all_rooms()})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Room name already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def delete_room(room_id):
    """Delete a room (only if no tables are assigned)"""
    try:
        conn, cursor = get_database_connection()
        # Check if any tables use this room
        cursor.execute('SELECT COUNT(*) FROM dining_tables WHERE room_id = ?', (room_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            conn.close()
            return jsonify({'error': f'Cannot delete room: {count} table(s) assigned'}), 400
        
        cursor.execute('DELETE FROM dining_rooms WHERE room_id = ?', (room_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'rooms': get_all_rooms()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_room_order(room_orders):
    """Update room display order"""
    try:
        conn, cursor = get_database_connection()
        for item in room_orders:
            cursor.execute('UPDATE dining_rooms SET room_order = ? WHERE room_id = ?',
                          (item['order'], item['room_id']))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_room_order(room_orders):
    """Update room_order for multiple rooms"""
    try:
        conn, cursor = get_database_connection()
        for room in room_orders:
            cursor.execute(
                'UPDATE dining_rooms SET room_order = ? WHERE room_id = ?',
                (room['room_order'], room['room_id'])
            )
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# ============================================
# UPDATED TABLE FUNCTIONS
# ============================================

def get_dining_tables_with_rooms():
    """Get all tables with room information, grouped by room"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT 
                dt.table_id, 
                dt.table_number, 
                dt.table_occupied,
                dt.room_id,
                COALESCE(dr.room_label, '') as room_label,
                COALESCE(dr.room_order, 999) as room_order
            FROM dining_tables dt
            LEFT JOIN dining_rooms dr ON dt.room_id = dr.room_id
            ORDER BY dr.room_order, dr.room_label, CAST(dt.table_number AS INTEGER)
        ''')
        tables = cursor.fetchall()
        conn.close()
        
        return [{
            'table_id': t[0], 
            'table_number': t[1], 
            'table_occupied': t[2],
            'room_id': t[3],
            'room_label': t[4],
            'room_order': t[5]
        } for t in tables]
    except Exception as e:
        print(f"Error getting tables with rooms: {e}")
        return []


def add_table_with_room(table_number, room_id):
    """Add a new table with room assignment"""
    try:
        conn, cursor = get_database_connection()
        
        # Check for duplicate table number within the same room
        cursor.execute('''
            SELECT * FROM dining_tables 
            WHERE table_number = ? AND (room_id = ? OR (room_id IS NULL AND ? IS NULL))
        ''', (table_number, room_id, room_id))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Table number already exists in this room'}), 400
        
        cursor.execute('INSERT INTO dining_tables (table_number, room_id) VALUES (?, ?)', 
                      (table_number, room_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'tables': get_dining_tables_with_rooms()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def update_table_room(table_id, room_id):
    """Update a table's room assignment"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('UPDATE dining_tables SET room_id = ? WHERE table_id = ?', 
                      (room_id, table_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'tables': get_dining_tables_with_rooms()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_free_tables_grouped():
    """Get free tables grouped by room for POS selection"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT 
                dt.table_id, 
                dt.table_number, 
                dt.table_occupied,
                dt.room_id,
                COALESCE(dr.room_label, '') as room_label,
                COALESCE(dr.room_order, 999) as room_order
            FROM dining_tables dt
            LEFT JOIN dining_rooms dr ON dt.room_id = dr.room_id
            WHERE dt.table_occupied = 0
            ORDER BY dr.room_order, dr.room_label, CAST(dt.table_number AS INTEGER)
        ''')
        tables = cursor.fetchall()
        conn.close()
        
        # Group by room
        grouped = {}
        for t in tables:
            room = t[4] if t[4] else 'Other'
            if room not in grouped:
                grouped[room] = []
            grouped[room].append({
                'table_id': t[0],
                'table_number': t[1],
                'room_id': t[3],
                'room_label': t[4],
                'room_order': t[5]
            })
        
        return grouped
    except Exception as e:
        print(f"Error getting free tables: {e}")
        return {}


# ============================================
# MULTI-TABLE CART CREATION
# ============================================

def new_cart_multi_table(cartData):
    """
    Create a new cart with support for multiple tables.
    Replaces the dine-in portion of new_cart()
    
    cartData['customer']['tables'] = [
        {'table_id': 1, 'table_number': '1', 'cover': 2},
        {'table_id': 2, 'table_number': '2', 'cover': 2},
    ]
    """
    conn = None
    try:
        data = cartData
        conn, cursor = get_database_connection()
        
        customer = cartData['customer']
        service_charge = customer.get('deliveryCharge', 0)
        posted_cart_id = int(cartData.get('cart_id', 0))
        current_menu = cartData.get('current_menu', '')
        
        conn.execute("BEGIN TRANSACTION")
        
        if data['order_type'] == "dine":
            service_charge = json_utils.service_charge()
            customer_id = get_guest_customer()
        else:
            # Handle other order types as before...
            customer_name = customer.get('customerName', '')
            customer_phone = customer.get('customerPhone', '')
            posted_customer = customer.get('customerId', '')
            
            if customer_name == "" and customer_phone == "":
                customer_id = get_guest_customer()
            elif posted_customer:
                customer_id = int(posted_customer)
                if customer_id > 1 and customer_name != "" and customer_phone != "":
                    cursor.execute("UPDATE customers SET customer_name = ?, customer_telephone = ? WHERE customer_id = ?", 
                                 (customer_name, customer_phone, customer_id))
            else:
                cursor.execute("INSERT INTO customers (customer_name, customer_telephone) VALUES (?, ?)", 
                             (customer_name, customer_phone))
                customer_id = cursor.lastrowid
        
        address_id = None
        if 'customerAddress' in customer and customer['customerAddress'] != '':
            address = customer['customerAddress']
            postcode = customer['customerPostcode']
            distance = customer.get('addressDistance', 0)
            
            if customer.get('addressId') == "":
                cursor.execute('''
                    INSERT INTO customer_addresses (customer_id, address, postcode, distance)
                    VALUES (?, ?, ?, ?)
                ''', (customer_id, address, postcode, distance))
                address_id = cursor.lastrowid
            else:
                address_id = customer['addressId']
                cursor.execute('''
                    UPDATE customer_addresses SET address = ?, postcode = ? WHERE address_id = ?
                ''', (address, postcode, address_id))
        
        employee_id = session.get('employee_id', 0)
        cursor.execute('''
            INSERT INTO cart (order_type, order_menu, order_date, overall_note, customer_id, 
                            cart_service_charge, cart_started_by, address_id)
            VALUES (?, ?, datetime('now', 'localtime'), ?, ?, ?, ?, ?)
        ''', (data['order_type'], data['order_menu'], data.get('overall_note', ''), 
              customer_id, service_charge, employee_id, 
              address_id if data['order_type'] == "delivery" else None))
        
        cart_id = cursor.lastrowid
        
        # Handle multiple tables for dine-in
        if data['order_type'] == "dine":
            tables = customer.get('tables', [])
            
            # If old single-table format, convert it
            if not tables and customer.get('table'):
                tables = [{
                    'table_number': customer.get('table'),
                    'cover': customer.get('cover', 0)
                }]
            
            total_covers = 0
            for table_data in tables:
                table_number = table_data.get('table_number')
                table_id = table_data.get('table_id')
                cover = int(table_data.get('cover', 0))
                total_covers += cover
                
                # Mark table as occupied
                cursor.execute(
                    "UPDATE dining_tables SET table_occupied = ? WHERE table_number = ?",
                    (cart_id, table_number)
                )
                
                # Insert into junction table
                cursor.execute('''
                    INSERT INTO cart_dining_tables (cart_id, table_id, table_number, table_cover)
                    VALUES (?, ?, ?, ?)
                ''', (cart_id, table_id, table_number, cover))
        
        # Handle cart transfer if switching order type
        if posted_cart_id and current_menu != data['order_menu']:
            # ... price recalculation logic (same as original)
            pass
        
        # Transfer items from previous cart
        cursor.execute('UPDATE cart_item SET cart_id = ? WHERE cart_id = ?', (cart_id, posted_cart_id))
        
        # Transfer notes
        cursor.execute('SELECT overall_note FROM cart WHERE cart_id = ?', (posted_cart_id,))
        source_note = cursor.fetchone()
        if source_note and source_note[0]:
            cursor.execute('UPDATE cart SET overall_note = ? WHERE cart_id = ?', (source_note[0], cart_id))
        
        # Clear old cart's tables
        cursor.execute("UPDATE dining_tables SET table_occupied = 0 WHERE table_occupied = ?", (posted_cart_id,))
        cursor.execute('DELETE FROM cart WHERE cart_id = ?', (posted_cart_id,))
        cursor.execute('DELETE FROM cart_dining_tables WHERE cart_id = ?', (posted_cart_id,))
        
        conn.commit()
        return jsonify({'cart_id': cart_id})
        
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# ============================================
# TABLE MERGE FUNCTION
# ============================================

def merge_tables_to_cart(cart_id, tables_to_add):
    """
    Add additional tables to an existing cart (merge)
    
    tables_to_add = [
        {'table_id': 3, 'table_number': '3', 'cover': 2},
        {'table_id': 4, 'table_number': '4', 'cover': 2},
    ]
    """
    conn = None
    try:
        conn, cursor = get_database_connection()
        conn.execute("BEGIN TRANSACTION")
        
        # Verify cart exists and is dine-in
        cursor.execute('SELECT order_type FROM cart WHERE cart_id = ? AND cart_status = ?', 
                      (cart_id, 'processing'))
        cart = cursor.fetchone()
        
        if not cart:
            return jsonify({'error': 'Cart not found or already completed'}), 404
        
        if cart[0] != 'dine':
            return jsonify({'error': 'Can only merge tables for dine-in orders'}), 400
        
        for table_data in tables_to_add:
            table_number = table_data.get('table_number')
            table_id = table_data.get('table_id')
            cover = int(table_data.get('cover', 0))
            
            # Check table is free
            cursor.execute('SELECT table_occupied FROM dining_tables WHERE table_id = ?', (table_id,))
            table = cursor.fetchone()
            
            if not table:
                conn.rollback()
                return jsonify({'error': f'Table {table_number} not found'}), 404
            
            if table[0] != 0:
                conn.rollback()
                return jsonify({'error': f'Table {table_number} is already occupied'}), 400
            
            # Mark table as occupied
            cursor.execute('UPDATE dining_tables SET table_occupied = ? WHERE table_id = ?',
                          (cart_id, table_id))
            
            # Add to junction table
            cursor.execute('''
                INSERT INTO cart_dining_tables (cart_id, table_id, table_number, table_cover)
                VALUES (?, ?, ?, ?)
            ''', (cart_id, table_id, table_number, cover))
        
        conn.commit()
        
        # Return updated table list for this cart
        tables = get_cart_tables(cart_id)
        return jsonify({'success': True, 'tables': tables})
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# ============================================
# TABLE SPLIT FUNCTION
# ============================================

def split_tables_from_cart(source_cart_id, tables_to_split, items_to_move=None, new_covers=None):
    """
    Split table(s) from a cart into a new order, optionally moving items.
    
    tables_to_split = [
        {'table_id': 3, 'table_number': '3', 'cover': 1},
    ]
    items_to_move = [
        {'cart_item_id': 123, 'quantity': 1},  # Move 1 of this item
        {'cart_item_id': 124, 'quantity': 2},  # Move 2 of this item
    ]
    new_covers = {'3': 2}  # table_number -> cover for the split tables
    """
    conn = None
    try:
        conn, cursor = get_database_connection()
        conn.execute("BEGIN TRANSACTION")
        
        # Get source cart info
        cursor.execute('''
            SELECT order_type, order_menu, cart_service_charge, customer_id 
            FROM cart WHERE cart_id = ? AND cart_status = ?
        ''', (source_cart_id, 'processing'))
        source_cart = cursor.fetchone()
        
        if not source_cart:
            return jsonify({'error': 'Source cart not found'}), 404
        
        if source_cart[0] != 'dine':
            return jsonify({'error': 'Can only split dine-in orders'}), 400
        
        # Verify we're not splitting ALL tables
        cursor.execute('SELECT COUNT(*) FROM cart_dining_tables WHERE cart_id = ?', (source_cart_id,))
        total_tables = cursor.fetchone()[0]
        
        if len(tables_to_split) >= total_tables:
            return jsonify({'error': 'Cannot split all tables. Use transfer instead.'}), 400
        
        # Create new cart for split tables
        employee_id = session.get('employee_id', 0)
        cursor.execute('''
            INSERT INTO cart (order_type, order_menu, order_date, customer_id, 
                            cart_service_charge, cart_started_by)
            VALUES (?, ?, datetime('now', 'localtime'), ?, ?, ?)
        ''', (source_cart[0], source_cart[1], source_cart[3], source_cart[2], employee_id))
        
        new_cart_id = cursor.lastrowid
        
        # Move tables to new cart
        for table_data in tables_to_split:
            table_id = table_data.get('table_id')
            table_number = table_data.get('table_number')
            
            # Get cover - use new_covers if provided, otherwise use existing
            if new_covers and str(table_number) in new_covers:
                cover = int(new_covers[str(table_number)])
            else:
                cursor.execute('''
                    SELECT table_cover FROM cart_dining_tables 
                    WHERE cart_id = ? AND table_id = ?
                ''', (source_cart_id, table_id))
                existing = cursor.fetchone()
                cover = existing[0] if existing else table_data.get('cover', 0)
            
            # Update dining_tables to point to new cart
            cursor.execute('UPDATE dining_tables SET table_occupied = ? WHERE table_id = ?',
                          (new_cart_id, table_id))
            
            # Remove from source cart's junction
            cursor.execute('DELETE FROM cart_dining_tables WHERE cart_id = ? AND table_id = ?',
                          (source_cart_id, table_id))
            
            # Add to new cart's junction
            cursor.execute('''
                INSERT INTO cart_dining_tables (cart_id, table_id, table_number, table_cover)
                VALUES (?, ?, ?, ?)
            ''', (new_cart_id, table_id, table_number, cover))
        
        # Move items if specified
        if items_to_move:
            for item_data in items_to_move:
                cart_item_id = item_data.get('cart_item_id')
                qty_to_move = int(item_data.get('quantity', 1))
                
                # Get current item
                cursor.execute('''
                    SELECT product_id, product_name, price, quantity, options, 
                           product_note, product_discount_type, product_discount,
                           category_order, vatable
                    FROM cart_item WHERE cart_item_id = ?
                ''', (cart_item_id,))
                item = cursor.fetchone()
                
                if not item:
                    continue
                
                current_qty = item[3]
                
                if qty_to_move >= current_qty:
                    # Move entire item
                    cursor.execute('UPDATE cart_item SET cart_id = ? WHERE cart_item_id = ?',
                                  (new_cart_id, cart_item_id))
                else:
                    # Split the item
                    # Reduce quantity in source
                    cursor.execute('UPDATE cart_item SET quantity = ? WHERE cart_item_id = ?',
                                  (current_qty - qty_to_move, cart_item_id))
                    
                    # Create new item in destination
                    cursor.execute('''
                        INSERT INTO cart_item (cart_id, product_id, product_name, price, quantity,
                                              options, product_note, product_discount_type,
                                              product_discount, category_order, vatable)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (new_cart_id, item[0], item[1], item[2], qty_to_move,
                          item[4], item[5], item[6], item[7], item[8], item[9]))
        
        conn.commit()
        
        return jsonify({
            'success': True,
            'new_cart_id': new_cart_id,
            'source_tables': get_cart_tables(source_cart_id),
            'new_tables': get_cart_tables(new_cart_id)
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_cart_tables(cart_id):
    """Get all tables associated with a cart"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT cdt.table_id, cdt.table_number, cdt.table_cover,
                   COALESCE(dr.room_label, '') as room_label
            FROM cart_dining_tables cdt
            LEFT JOIN dining_tables dt ON cdt.table_id = dt.table_id
            LEFT JOIN dining_rooms dr ON dt.room_id = dr.room_id
            WHERE cdt.cart_id = ?
            ORDER BY dr.room_order, CAST(cdt.table_number AS INTEGER)
        ''', (cart_id,))
        tables = cursor.fetchall()
        conn.close()
        
        return [{
            'table_id': t[0],
            'table_number': t[1],
            'cover': t[2],
            'room_label': t[3]
        } for t in tables]
    except Exception as e:
        print(f"Error getting cart tables: {e}")
        return []


def format_table_display(tables):
    """
    Format tables for display. Groups by room and creates ranges.
    
    Input: [{'room_label': 'Main', 'table_number': '1'}, ...]
    Output: "Main 1-3, Patio 5, 7"
    """
    if not tables:
        return ""
    
    # Group by room
    by_room = {}
    for t in tables:
        room = t.get('room_label', '') or 'Other'
        if room not in by_room:
            by_room[room] = []
        by_room[room].append(t.get('table_number'))
    
    parts = []
    for room, numbers in by_room.items():
        # Try to convert to integers for sorting/ranging
        try:
            nums = sorted([int(n) for n in numbers])
            formatted = format_number_ranges(nums)
        except (ValueError, TypeError):
            # Non-numeric table numbers
            formatted = ', '.join(sorted(numbers))
        
        if room and room != 'Other':
            parts.append(f"{room} {formatted}")
        else:
            parts.append(formatted)
    
    return ', '.join(parts)

def format_number_ranges(numbers):
    """
    Convert list of numbers to range string.
    [1, 2, 3, 5, 7, 8] -> "1-3, 5, 7-8"
    """
    if not numbers:
        return ""
    
    numbers = sorted(set(numbers))
    ranges = []
    start = numbers[0]
    end = numbers[0]
    
    for num in numbers[1:]:
        if num == end + 1:
            end = num
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = end = num
    
    # Don't forget the last range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ', '.join(ranges)

def get_cart_items_for_split(cart_id):
    """
    Get cart items formatted for split selection UI.
    Items with quantity > 1 are expanded into individual selectable units.
    """
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT cart_item_id, product_name, price, quantity, options, product_note
            FROM cart_item
            WHERE cart_id = ?
            ORDER BY category_order, product_name
        ''', (cart_id,))
        items = cursor.fetchall()
        conn.close()
        
        result = []
        for item in items:
            cart_item_id, name, price, qty, options, note = item
            
            # Parse options for display
            option_names = []
            if options:
                for opt in options.split(', '):
                    parts = opt.split('|')
                    if len(parts) >= 2:
                        option_names.append(parts[1])
            
            # Expand into individual units
            for i in range(qty):
                result.append({
                    'cart_item_id': cart_item_id,
                    'product_name': name,
                    'price': price,
                    'options': option_names,
                    'note': note,
                    'unit_index': i + 1,
                    'total_units': qty
                })
        
        return result
    except Exception as e:
        print(f"Error getting cart items for split: {e}")
        return []

def update_cart_tables(cart_id, table_updates):
    """
    Update covers and/or swap table for an existing cart.
    For single-table orders: can update covers and swap to free table
    For merged orders: can only update covers (no swap)
    
    table_updates = [
        {'table_id': 1, 'new_table_id': 5, 'cover': 2},  # Swap table 1 → 5, set covers
        {'table_id': 2, 'cover': 3},  # Just update covers, no swap
    ]
    """
    conn = None
    try:
        conn, cursor = get_database_connection()
        conn.execute("BEGIN TRANSACTION")
        
        # Verify cart exists and is dine-in
        cursor.execute('SELECT order_type FROM cart WHERE cart_id = ? AND cart_status = ?', 
                      (cart_id, 'processing'))
        cart = cursor.fetchone()
        
        if not cart:
            return jsonify({'error': 'Cart not found or already completed'}), 404
        
        if cart[0] != 'dine':
            return jsonify({'error': 'Can only edit tables for dine-in orders'}), 400
        
        for update in table_updates:
            table_id = update.get('table_id')
            new_table_id = update.get('new_table_id')
            cover = update.get('cover')
            
            # Update covers if provided
            if cover is not None:
                cursor.execute('''
                    UPDATE cart_dining_tables 
                    SET table_cover = ? 
                    WHERE cart_id = ? AND table_id = ?
                ''', (int(cover), cart_id, table_id))
            
            # Swap table if new_table_id provided and different
            if new_table_id and new_table_id != table_id:
                # Check new table is free
                cursor.execute('SELECT table_occupied, table_number FROM dining_tables WHERE table_id = ?', 
                              (new_table_id,))
                new_table = cursor.fetchone()
                
                if not new_table:
                    conn.rollback()
                    return jsonify({'error': f'Table not found'}), 404
                
                if new_table[0] != 0:
                    conn.rollback()
                    return jsonify({'error': f'Table {new_table[1]} is occupied'}), 400
                
                new_table_number = new_table[1]
                
                # Clear old table
                cursor.execute('UPDATE dining_tables SET table_occupied = 0 WHERE table_id = ?', 
                              (table_id,))
                
                # Occupy new table
                cursor.execute('UPDATE dining_tables SET table_occupied = ? WHERE table_id = ?', 
                              (cart_id, new_table_id))
                
                # Update junction table
                cursor.execute('''
                    UPDATE cart_dining_tables 
                    SET table_id = ?, table_number = ?
                    WHERE cart_id = ? AND table_id = ?
                ''', (new_table_id, new_table_number, cart_id, table_id))
        
        conn.commit()
        
        # Return updated table list
        tables = get_cart_tables(cart_id)
        return jsonify({'success': True, 'tables': tables})
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# ============================================
# UPDATED get_current_cart_data
# ============================================

def get_current_cart_data_v2(cart_id):
    """Updated to return multiple tables"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT
                c.cart_id, c.order_type, c.order_menu, c.order_date,
                COUNT(ci.cart_id) AS cart_item_count,
                c.customer_id, cu.customer_name, cu.customer_telephone,
                ca.address_id, ca.address, ca.postcode,
                c.cart_charge_updated, e.name
            FROM cart c
            LEFT JOIN cart_item ci ON c.cart_id = ci.cart_id
            LEFT JOIN customers cu ON c.customer_id = cu.customer_id
            LEFT JOIN customer_addresses ca ON ca.address_id = c.address_id
            LEFT JOIN employees e ON cart_started_by = e.employee_id
            WHERE c.cart_id = ?
            GROUP BY c.cart_id
        ''', (cart_id,))
        
        cart_data = cursor.fetchone()
        
        if not cart_data:
            conn.close()
            return jsonify({'error': 'Cart not found'}), 404
        
        # Get tables for this cart
        tables = get_cart_tables(cart_id)
        table_display = format_table_display(tables)
        total_covers = sum(t.get('cover', 0) for t in tables)
        
        cart_dict = {
            'cart_id': cart_data[0],
            'order_type': cart_data[1],
            'cart_menu': cart_data[2],
            'order_date': cart_data[3],
            'cart_item_count': cart_data[4],
            'customer_id': cart_data[5],
            'customer_name': cart_data[6],
            'customer_telephone': cart_data[7],
            'address_id': cart_data[8],
            'address': cart_data[9],
            'postcode': cart_data[10],
            'charge_updated': cart_data[11],
            'employee_name': cart_data[12],
            # New fields for multi-table
            'tables': tables,
            'table_display': table_display,
            'total_covers': total_covers,
            # Legacy single-table fields for backwards compat
            'table_number': table_display,
            'table_cover': total_covers
        }
        
        conn.close()
        return jsonify(cart_dict)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# UPDATED delete_cart_and_items
# ============================================

def delete_cart_and_items_v2(cart_id):
    """Updated to clear all associated tables"""
    try:
        conn, cursor = get_database_connection()
        
        # Clear all tables for this cart
        cursor.execute("UPDATE dining_tables SET table_occupied = 0 WHERE table_occupied = ?", (cart_id,))
        
        # Delete cart data
        cursor.execute("DELETE FROM cart WHERE cart_id = ?", (cart_id,))
        cursor.execute("DELETE FROM cart_item WHERE cart_id = ?", (cart_id,))
        cursor.execute("DELETE FROM cart_dining_tables WHERE cart_id = ?", (cart_id,))
        cursor.execute("DELETE FROM cart_payments WHERE cart_id = ?", (cart_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": f"Cart {cart_id} and associated data deleted."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def complete_checkout_v2(cart_id, payment_method, discounted_total, split_charges=None):
    try:
        employee_id = session.get('employee_id', 0)
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn, cursor = get_database_connection()
        
        # 1. First update cart status and clear dining table
        cursor.execute("""
            UPDATE cart 
            SET cart_status = 'completed', 
                cart_charge_updated = ?, 
                cart_updated_by = ?,
                sync_status = 'pending'
            WHERE cart_id = ?""", 
            (current_timestamp, employee_id, cart_id))
        
        cursor.execute("""
            UPDATE dining_tables 
            SET table_occupied = 0 
            WHERE table_occupied = ?""", 
            (cart_id,))
        
        # VAT Calculation with multi-option support
        vat_rate = json_utils.get_vat_rate()
        if vat_rate > 0:
            cursor.execute("""
                SELECT 
                    ci.price, ci.quantity, ci.product_discount_type, 
                    ci.product_discount, ci.vatable, ci.options,
                    c.order_type, c.cart_discount_type, c.cart_discount
                FROM cart_item ci
                JOIN cart c ON ci.cart_id = c.cart_id
                WHERE ci.cart_id = ?""", (cart_id,))
            items = cursor.fetchall()
            
            if items:
                cart_total = 0
                vatable_total = 0
                order_type = items[0][6]
                
                for item in items:
                    base_price, base_qty, disc_type, disc_amount, base_vatable, options_str, _, _, _ = item
                    options = helpers.parse_options(options_str)
                    
                    # 1. Calculate base item
                    base_total = base_price * base_qty
                    base_vat_amount = base_total if (order_type == 'dine' or base_vatable) else 0
                    
                    # 2. Calculate all options
                    options_total = 0
                    options_vat_amount = 0
                    for opt in options:
                        opt_total = opt['price'] * opt['quantity']
                        options_total += opt_total
                        if order_type == 'dine' or opt['vatable']:
                            options_vat_amount += opt_total
                    
                    # 3. Combined total before discounts
                    combined_total = base_total + options_total
                    combined_vatable = base_vat_amount + options_vat_amount
                    
                    # 4. Apply item-level discount proportionally
                    if disc_amount > 0:
                        combined_total = helpers.calculate_cart_discounts(disc_amount, disc_type, combined_total)
                        if combined_total > 0:
                            discount_ratio = combined_total / (combined_total + disc_amount)
                            combined_vatable *= discount_ratio
                    
                    # Add to totals
                    cart_total += combined_total
                    vatable_total += combined_vatable
                
                # Apply cart discount proportionally
                cart_disc = items[0][8]
                if cart_disc > 0:
                    cart_disc_type = items[0][7]
                    cart_total = helpers.calculate_cart_discounts(cart_disc, cart_disc_type, cart_total)
                    if cart_total > 0:
                        vatable_total *= (cart_total / (cart_total + cart_disc))
                
                # Update VAT
                vat_base = cart_total if order_type == 'dine' else vatable_total
                vat_amount = round(vat_base * vat_rate, 2)
                cursor.execute("UPDATE cart SET vat_amount = ? WHERE cart_id = ?", (vat_amount, cart_id))
        
        # 3. Process payments
        if payment_method == 'Split' and split_charges and len(split_charges) > 0:
            for charge in split_charges:
                charge_payment_method = charge.get('paymentMethod', payment_method)
                charge_discounted_total = charge.get('amount', 0)
                cursor.execute("""
                    INSERT INTO cart_payments 
                    (cart_id, payment_method, discounted_total) 
                    VALUES (?, ?, ?)""",
                    (cart_id, charge_payment_method, charge_discounted_total))
        else:
            cursor.execute("""
                INSERT INTO cart_payments 
                (cart_id, payment_method, discounted_total) 
                VALUES (?, ?, ?)""",
                (cart_id, payment_method, discounted_total))
        
        # 4. Create kitchen order if enabled
        if get_setting('kitchen_screen') == "1":
            cursor.execute("""
                INSERT INTO kitchen_orders (order_id, item_id)
                SELECT cart_id, cart_item_id
                FROM cart_item
                WHERE cart_id = ?""", 
                (cart_id,))

        conn.commit()
        deduct_inventory(cart_id)
        return {'status': 'success'}
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        if conn:
            conn.close()

async def get_all_cart_items(cart_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute(
            """SELECT 
                cart_item.cart_item_id,
                cart_item.cart_id,
                cart_item.product_id,
                cart_item.product_name,
                cart_item.price,
                cart_item.quantity,
                cart_item.options,
                cart_item.product_note,
                cart_item.product_discount_type,
                cart_item.product_discount,
                cart_item.category_order,
                cart_item.vatable,
                COALESCE(cart_item.kitchen_printed_qty, 0) AS kitchen_printed_qty,
                COALESCE(cart_item.bar_printed_qty, 0) AS bar_printed_qty,
                COALESCE(products.cpn, 0) AS cpn,
                products.category_id
            FROM cart_item
            LEFT JOIN products ON cart_item.product_id = products.product_id
            WHERE cart_item.cart_id = ?
            ORDER BY cart_item.category_order""",
            (cart_id,)
        )
        items = cursor.fetchall()
        sorted_items = sorted(items, key=lambda x: (x[10], x[3]))
        # Convert the items to a list of dictionaries
        items_list = []
        for item in sorted_items:
            item_dict = {
                'cart_item_id': item[0],
                'cart_id': item[1],
                'product_id': item[2],
                'product_name': item[3],
                'price': item[4],
                'quantity': item[5],
                'options': item[6],
                'product_note': item[7],
                'product_discount_type': item[8],
                'product_discount': item[9],
                'category_order': item[10],
                'vat': item[11],
                'kitchen_printed_qty': item[12],
                'bar_printed_qty': item[13],
                'cpn': item[14],
                'category_id': item[15]
            }
            items_list.append(item_dict)
        cursor.execute(
            "SELECT overall_note, cart_discount_type, cart_discount, cart_service_charge, order_type FROM cart WHERE cart_id = ?",
            (cart_id,)
        )
        cart_data = cursor.fetchone()
        conn.close()
        vendor = await async_settings.get_active_payment_vendor()
        card_vendor = vendor['vendor_name']
        response_data = {
            "items": items_list,
            "cart_data": {
                "overall_note": cart_data[0],
                "cart_discount_type": cart_data[1],
                "cart_discount": cart_data[2],
                "cart_service_charge": cart_data[3],
                "order_type": cart_data[4]
            },
            "card_vendor": card_vendor
        }
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def delete_cart_and_items(cart_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute("DELETE FROM cart WHERE cart_id = ?", (cart_id,))
        cursor.execute("DELETE FROM cart_item WHERE cart_id = ?", (cart_id,))
        cursor.execute("DELETE FROM cart_dining_tables WHERE cart_id = ?", (cart_id,))
        cursor.execute("DELETE FROM cart_payments WHERE cart_id = ?", (cart_id,))
        cursor.execute("UPDATE dining_tables SET table_occupied = 0 WHERE table_occupied = ?", (cart_id,))
        conn.commit()
        conn.close()
        success_message = f"Cart with cart_id {cart_id} and associated cart items and payments deleted."
        return jsonify({"message": success_message})
    except Exception as e:
        error_message = f"Error deleting cart: {e}"
        return jsonify({"error": error_message}), 500

def delete_cart_item(cart_item_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute(
            "DELETE FROM cart_item WHERE cart_item_id = ?",
            (cart_item_id,)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Item successfully deleted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
def get_modifiers():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT * FROM product_modifiers')
        mods = cursor.fetchall()
        conn.close()
        return mods
    except Exception as e:
        return f"Error getting modifiers: {e}"

def add_mod(modifier):
    conn, cursor = get_database_connection()
    cursor.execute(
            "INSERT INTO product_modifiers (modifier_name) VALUES (?)",
                (modifier,)
            )
    conn.commit()
    conn.close()

def delete_mod(mod_id):
    conn, cursor = get_database_connection()
    cursor.execute('DELETE FROM product_modifiers WHERE modifier_id = ?', (mod_id,))
    conn.commit()
    conn.close()

def get_options():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT * FROM options WHERE is_hidden = 0')
        options = cursor.fetchall()
        conn.close()
        return options
    except Exception as e:
        print("Error fetching options:", e)
        return jsonify([]), 500

def get_option_items(option_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT oig.option_item_id, option_id, option_item_name, option_item_in_price, option_item_out_price, is_hidden, oig.vatable, oig.option_item_colour FROM option_items oi JOIN option_item_groups oig ON oi.option_item_id = oig.option_item_id WHERE oig.option_id = ? AND oig.is_hidden = ? ORDER BY option_item_group_order, option_item_name;', (option_id,0))
        option_items = cursor.fetchall()
        conn.close()
        return option_items
    except Exception as e:
        return f"Error getting option items: {e}"

def copy_option_items_to_new_option(copy_option_id, new_option_id, in_price, out_price):
    try:
        conn, cursor = get_database_connection()
        cursor.execute(
            """
            INSERT INTO option_item_groups (option_id, option_item_id, option_item_in_price, option_item_out_price, is_hidden, vatable)
            SELECT 
                ? AS option_id, 
                option_item_id, 
                ? AS option_item_in_price,
                ? AS option_item_out_price,
                is_hidden, 
                vatable
            FROM option_item_groups
            WHERE option_id = ?
            """,
            (new_option_id, in_price, out_price, copy_option_id))
        conn.commit()
        return True
    except Exception as e:
        print("Error copying option items:", str(e))
        return False
    finally:
        conn.close()

def get_products_not_assigned_options():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT p.product_id, p.product_name, in_price FROM products p LEFT JOIN product_options po ON p.product_id = po.product_id AND po.is_hidden = 0 WHERE po.product_id IS NULL')
        products = cursor.fetchall()
        conn.close()
        return products
    except Exception as e:
        return f"Error getting options: {e}"

def get_products_with_options():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT 
                p.product_id, 
                p.product_name, 
                p.in_price,
                o.option_id,
                o.option_name
            FROM 
                products p
            INNER JOIN 
                product_options po ON p.product_id = po.product_id
            INNER JOIN 
                options o ON po.option_id = o.option_id
            ORDER BY product_name
        ''')
        rows = cursor.fetchall()
        conn.close()

        products = {}
        for row in rows:
            product_id, product_name, in_price, option_id, option_name = row
            if product_id not in products:
                products[product_id] = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'in_price': in_price,
                    'options': []
                }
            products[product_id]['options'].append({'option_id': option_id, 'option_name': option_name})
        return list(products.values())
    
    except Exception as e:
        return str(e)

def update_cart_item(item_id, combined_mods, quantity):
    """
    Update cart item with inventory validation
    """
    conn = None
    try:
        conn, cursor = get_database_connection()
        
        # Get the product_id and current cart_id for this cart item
        cursor.execute("""
            SELECT product_id, cart_id, quantity as current_quantity 
            FROM cart_item 
            WHERE cart_item_id = ?
        """, (item_id,))
        
        cart_item = cursor.fetchone()
        if not cart_item:
            return jsonify({"error": "Cart item not found"}), 404
        
        product_id = cart_item[0]
        cart_id = cart_item[1]
        current_quantity = cart_item[2]
        
        # Check if product has inventory tracking enabled
        cursor.execute("""
            SELECT track_inventory, stock_quantity, product_name 
            FROM products 
            WHERE product_id = ?
        """, (product_id,))
        
        product = cursor.fetchone()
        if not product:
            return jsonify({"error": "Product not found"}), 404
        
        track_inventory = product[0]
        stock_quantity = product[1]
        product_name = product[2]
        
        # If inventory tracking is enabled, validate stock
        if track_inventory == 1:
            # Calculate total quantity of this product in the cart (excluding current item)
            cursor.execute("""
                SELECT COALESCE(SUM(quantity), 0) 
                FROM cart_item 
                WHERE cart_id = ? 
                AND product_id = ? 
                AND cart_item_id != ?
            """, (cart_id, product_id, item_id))
            
            other_items_quantity = cursor.fetchone()[0]
            
            # Calculate total quantity if we apply this update
            new_total_quantity = other_items_quantity + int(quantity)
            
            # Check if new quantity exceeds stock
            if new_total_quantity > stock_quantity:
                available = stock_quantity - other_items_quantity
                return jsonify({
                    "error": f"Insufficient stock for {product_name}. Available: {available}, Requested: {quantity}"
                }), 400
        
        # Stock is sufficient or tracking is disabled, proceed with update
        cursor.execute("""
            UPDATE cart_item 
            SET product_note = ?, quantity = ? 
            WHERE cart_item_id = ?
        """, (combined_mods, quantity, item_id))
        
        conn.commit()
        return jsonify({"message": "Item modified successfully"}), 200
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error updating item: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

def get_free_tables():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT table_id, table_number, table_occupied FROM dining_tables')
        dining_tables = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]
        conn.close()
        return dining_tables
    except Exception as e:
        return f"Error free getting tables: {e}"
    
def get_all_tables():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT * FROM dining_tables')
        dining_tables = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]
        conn.close()
        return dining_tables
    except Exception as e:
        return f"Error all getting tables: {e}"

def get_all_tables_grouped():
    """Get ALL tables (free and occupied) grouped by room"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            SELECT 
                dt.table_id, 
                dt.table_number, 
                dt.table_occupied,
                dt.room_id,
                COALESCE(dr.room_label, '') as room_label
            FROM dining_tables dt
            LEFT JOIN dining_rooms dr ON dt.room_id = dr.room_id
            ORDER BY dr.room_order, dr.room_label, CAST(dt.table_number AS INTEGER)
        ''')
        tables = cursor.fetchall()
        conn.close()
        
        # Group by room
        grouped = {}
        for t in tables:
            room = t[4] if t[4] else ''
            if room not in grouped:
                grouped[room] = []
            grouped[room].append({
                'table_id': t[0],
                'table_number': t[1],
                'table_occupied': t[2],
                'room_id': t[3],
                'room_label': t[4]
            })
        
        return grouped
    except Exception as e:
        print(f"Error getting all tables grouped: {e}")
        return {}

def add_table(table_number):
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT * FROM dining_tables WHERE table_number = ?', (table_number,))
        existing_table = cursor.fetchone()
        
        if existing_table:
            conn.close()
            return jsonify({'error': 'Table number already exists'}), 400

        cursor.execute('INSERT INTO dining_tables (table_number) VALUES (?)', (table_number,))
        conn.commit()

        cursor.execute('SELECT table_id, table_number, table_occupied FROM dining_tables')
        columns = [column[0] for column in cursor.description]
        tables_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': 'Table saved successfully', 'tables': tables_data})

    except Exception as e:
        print(str(e))
    return jsonify({'error': 'Failed to save table. Try a different number'}), 500

def get_cart_discount(cart_id):
    try:
        conn, cursor = get_database_connection()
        # Query to retrieve the discount and the total_price without options price
        cursor.execute(
            """
            SELECT cart.cart_discount_type, cart.cart_discount, COALESCE(SUM(cart_item.quantity * cart_item.price), 0) AS total_price
            FROM cart
            LEFT JOIN cart_item ON cart.cart_id = cart_item.cart_id
            WHERE cart.cart_id = ?
            GROUP BY cart.cart_id
            """,
            (cart_id,)
        )
        cart_discount = cursor.fetchone()
        discount_type, discount_value, total_price = cart_discount
        
        total_price = 0
        item_discount_total = 0
        cursor.execute(
            """
            SELECT product_discount_type, product_discount, price, quantity, options
            FROM cart_item
            WHERE cart_id = ?
            """,
            (cart_id,)
        )

        results = cursor.fetchall()

        for row in results:
            product_discount_type, product_discount, price, quantity, options = row

            options_total_price = 0  # Reset options_total_price to 0 for each item

            # Calculate options total price
            if options:
                options_list = options.split(',')
                for option in options_list:
                    option_data = option.split('|')
                    if len(option_data) == 6:
                        option_price = float(option_data[2]) * int(option_data[4])
                        options_total_price += option_price

            each_item_price = (price + options_total_price) * quantity

            if product_discount > 0:
                if product_discount_type == 'fixed':
                    discounted_amount = product_discount * quantity
                elif product_discount_type == 'percentage':
                    discounted_amount = (product_discount / 100) * each_item_price
                # Sum the discounted amounts
                item_discount_total += discounted_amount

            # Sum the total price including options for all items
            total_price += each_item_price

        result = {
            "cart_discount_type": discount_type,
            "cart_discount": discount_value,
            "total_price": total_price,
            "item_discount_total": item_discount_total
        }
        
        conn.close()
        return json.dumps(result)
    except Exception as e:
        error_message = {"error": f"Error getting discounts: {str(e)}"}
        return json.dumps(error_message)

def apply_discount(cart_id, discount_type, discount_value):
    try:
        if cart_id is not None and discount_type is not None and discount_value is not None:
            conn, cursor = get_database_connection()
            cursor.execute("UPDATE cart SET cart_discount_type = ?, cart_discount = ? WHERE cart_id = ?", (discount_type, discount_value, cart_id))
            conn.commit()
            conn.close()

            return jsonify({"message": "Discount applied successfully."}), 200
        else:
            return jsonify({"error": "Invalid data provided."}), 400
    except Exception as e:
        return jsonify({"error": "An error occurred while applying the discount."}), 500

def apply_item_discount(cart_item_id, discount_type, discount_value):
    try:
        if cart_item_id is not None and discount_type is not None and discount_value is not None:
            conn, cursor = get_database_connection()
            cursor.execute("UPDATE cart_item SET product_discount_type = ?, product_discount = ? WHERE cart_item_id = ?", (discount_type, discount_value, cart_item_id))
            conn.commit()
            conn.close()

            return jsonify({"message": "Discount applied successfully."}), 200
        else:
            return jsonify({"error": "Invalid data provided."}), 400
    except Exception as e:
        return jsonify({"error": "An error occurred while applying the discount."}), 500

def remove_discount(cart_or_item, id):
    try:
        conn, cursor = get_database_connection()
        if cart_or_item == "cart":
            update_query = """
                UPDATE cart SET cart_discount = 0, cart_discount_type = 'fixed' WHERE cart_id = ?
            """
        else:
            update_query = """
                UPDATE cart_item SET product_discount = 0, product_discount_type = 'fixed' WHERE cart_item_id = ?
            """
        cursor.execute(update_query,
                       (id,))
        conn.commit()
        return jsonify({"message": "discount removed"}), 200
    except Exception as e:
        return f"Error removing discount: {e}"
    finally:
        conn.close()

def get_cart_service_delivery_charge(cart_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute(
            """
            SELECT cart_service_charge
            FROM cart
            WHERE cart_id = ?
            """,
            (cart_id,)
        )
        service_charge = cursor.fetchone()
        if service_charge:
            return service_charge[0]
        else:
            return 0.0
    except Exception as e:
        print("Error fetching service charge:", str(e))
        return 0.0
    finally:
        conn.close()

def apply_service_delivery_charge(cart_id, service_delivery_charge):
    try:
        if cart_id is not None and service_delivery_charge is not None:
            conn, cursor = get_database_connection()
            cursor.execute("UPDATE cart SET cart_service_charge = ? WHERE cart_id = ?", (service_delivery_charge, cart_id))
            conn.commit()
            conn.close()

            return jsonify({"message": "Charge applied successfully."}), 200
        else:
            return jsonify({"error": "Invalid data provided."}), 400
    except Exception as e:
        return jsonify({"error": "An error occurred while applying the service charge."}), 500

def search_customers(search_term):
    try:
        conn, cursor = get_database_connection()

        search_terms = search_term.split()

        query = """
        SELECT
            c.customer_id,
            c.customer_name,
            c.customer_telephone,
            a.address,
            a.postcode,
            a.address_id
        FROM
            customers c
        LEFT JOIN
            customer_addresses a ON c.customer_id = a.customer_id
        WHERE
            """
        query += " OR ".join([
            f"c.customer_name LIKE ?" for _ in search_terms
        ])
        query += " OR "
        query += " OR ".join([
            f"c.customer_telephone LIKE ?" for _ in search_terms
        ])
        query += " OR "
        query += " OR ".join([
            f"a.address LIKE ?" for _ in search_terms
        ])
        query += " OR "
        query += " OR ".join([
            f"a.postcode LIKE ?" for _ in search_terms
        ])

        query += " LIMIT 5"

        search_params = tuple(f"%{term}%" for term in search_terms * 4)

        cursor.execute(query, search_params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            customer_id, customer_name, customer_telephone, address, postcode, address_id = row
            result_dict = {
                'customer_id': customer_id,
                'customer_name': customer_name,
                'customer_telephone': customer_telephone,
                'address': address,
                'postcode': postcode,
                'address_id': address_id
            }
            results.append(result_dict)

        return results

    except Exception as e:
        return [{'error': str(e)}]

def get_orders_by_customer_id(customer_id):
    try:
        conn, cursor = get_database_connection()
        order_query = """
        SELECT
            c.cart_id,
            c.order_type,
            c.order_date,
            ci.product_id,
            ci.product_name,
            ci.price,
            ci.quantity,
            ci.options,
            ci.product_note,
            ci.category_order
        FROM
            cart c
        JOIN
            cart_item ci ON c.cart_id = ci.cart_id
        WHERE
            c.customer_id = ? AND c.cart_status = ?
        ORDER BY c.cart_id DESC
        LIMIT 10
        """
        cursor.execute(order_query, (customer_id, "completed"))
        orders = cursor.fetchall()

        customer_query = """
        SELECT
            COALESCE(c.customer_name, '') AS customer_name,
            COALESCE(c.customer_telephone, '') AS customer_telephone,
            COALESCE(a.address_id, '') AS address_id,
            COALESCE(a.address, '') AS address,
            COALESCE(a.postcode, '') AS postcode
        FROM
            customers c
        LEFT JOIN
            customer_addresses a ON c.customer_id = a.customer_id
        WHERE
            c.customer_id = ?
        """
        cursor.execute(customer_query, (customer_id,))
        customer_info = cursor.fetchone()

        conn.close()

        # Create the orders list
        orders_list = [
            {
                'order_id': order[0],
                'order_type': order[1],
                'order_date': order[2],
                'product_id': order[3],
                'product_name': order[4],
                'price': order[5],
                'quantity': order[6],
                'options': order[7],
                'product_note': order[8],
                'category_order': order[9]
            }
            for order in orders
        ]

        # Combine orders and customer info into one response
        response = {
            'orders': orders_list,
            'customer_info': {
                'customer_name': customer_info[0],
                'customer_telephone': customer_info[1],
                'address_id': customer_info[2],
                'address': customer_info[3],
                'postcode': customer_info[4]
            }
        }

        response_json = json.dumps(response)

        return response_json

    except Exception as e:
        return json.dumps({'error': str(e)})

def reorder_customer_order(cart):
    try:
        reorder_items = cart.get('reorderItems', [])
        cart_id = cart.get('cartId', 0)
        cart_menu = int(cart.get('cartMenu', 0))
        conn, cursor = get_database_connection()

        for item in reorder_items:
            product_id = item['product_id']
            quantity = item['quantity']
            category_order = item['category_order']
            note = item['note']

            cursor.execute("""
                SELECT product_name, in_price, out_price
                FROM products
                WHERE product_id = ?
            """, (product_id,))
            product = cursor.fetchone()

            option_strings = []
            if item['options']:
                for option in item['options']:
                    cleaned_option = option.strip('"')
                    cursor.execute("""
                        SELECT option_item_name, option_item_in_price, option_item_out_price
                        FROM option_items
                        WHERE option_item_id = ?
                    """, (int(cleaned_option),))
                    option_item = cursor.fetchone()
                    option_string = f"{cleaned_option}|{option_item[0]}|"
                    option_string += str(option_item[1]) if cart_menu == 0 else str(option_item[2])
                    option_string += f"|1"

                    option_strings.append(option_string)

            options_final = ", ".join(option_strings)

            cursor.execute("""
                INSERT INTO cart_item (cart_id, product_id, product_name, price, quantity, options, product_note, category_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cart_id, product_id, product[0], product[1] if cart_menu == 0 else product[2], quantity, options_final, note, category_order))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Reorder successful'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Reorder failed: {str(e)}'})

def update_customer(customer):
    conn, cursor = get_database_connection()
    name = customer.get('name')
    phone = customer.get('phone')
    postcode = customer.get('postcode')
    address = customer.get('address')
    customer_id = int(customer.get('customerId'))

    try:
        # Always update customer name and phone
        cursor.execute('''
            UPDATE customers
            SET customer_name = ?, customer_telephone = ?
            WHERE customer_id = ?
        ''', (name, phone, customer_id))

        address_id_raw = customer.get('addressId')
        if address_id_raw and str(address_id_raw).isdigit():
            address_id = int(address_id_raw)
            # Update existing address
            cursor.execute('''
                UPDATE customer_addresses
                SET address = ?, postcode = ?
                WHERE address_id = ?
            ''', (address, postcode, address_id))
        else:
            # Insert new address
            cursor.execute('''
                INSERT INTO customer_addresses (customer_id, address, postcode)
                VALUES (?, ?, ?)
            ''', (customer_id, address, postcode))

        conn.commit()
        response = {'success': True}
    except Exception as e:
        conn.rollback()
        print(f"An error occurred: {e}")
        response = {'success': False, 'error': str(e)}
    finally:
        conn.close()

    return jsonify(response)

def complete_checkout(cart_id, payment_method, discounted_total, split_charges=None):
    try:
        employee_id = session.get('employee_id', 0)
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn, cursor = get_database_connection()
        
        # 1. First update cart status and clear dining table
        cursor.execute("""
            UPDATE cart 
            SET cart_status = 'completed', 
                cart_charge_updated = ?, 
                cart_updated_by = ?,
                sync_status = 'pending'
            WHERE cart_id = ?""", 
            (current_timestamp, employee_id, cart_id))
        
        cursor.execute("""
            UPDATE dining_tables 
            SET table_occupied = 0 
            WHERE table_occupied = ?""", 
            (cart_id,))
        
        # VAT Calculation with multi-option support
        vat_rate = json_utils.get_vat_rate()
        if vat_rate > 0:
            cursor.execute("""
                SELECT 
                    ci.price, ci.quantity, ci.product_discount_type, 
                    ci.product_discount, ci.vatable, ci.options,
                    c.order_type, c.cart_discount_type, c.cart_discount
                FROM cart_item ci
                JOIN cart c ON ci.cart_id = c.cart_id
                WHERE ci.cart_id = ?""", (cart_id,))
            items = cursor.fetchall()
            
            if items:
                cart_total = 0
                vatable_total = 0
                order_type = items[0][6]
                
                for item in items:
                    base_price, base_qty, disc_type, disc_amount, base_vatable, options_str, _, _, _ = item
                    options = helpers.parse_options(options_str)
                    
                    # 1. Calculate base item
                    base_total = base_price * base_qty
                    base_vat_amount = base_total if (order_type == 'dine' or base_vatable) else 0
                    
                    # 2. Calculate all options
                    options_total = 0
                    options_vat_amount = 0
                    for opt in options:
                        opt_total = opt['price'] * opt['quantity']
                        options_total += opt_total
                        if order_type == 'dine' or opt['vatable']:
                            options_vat_amount += opt_total
                    
                    # 3. Combined total before discounts
                    combined_total = base_total + options_total
                    combined_vatable = base_vat_amount + options_vat_amount
                    
                    # 4. Apply item-level discount proportionally
                    if disc_amount > 0:
                        combined_total = helpers.calculate_cart_discounts(disc_amount, disc_type, combined_total)
                        if combined_total > 0:
                            discount_ratio = combined_total / (combined_total + disc_amount)
                            combined_vatable *= discount_ratio
                    
                    # Add to totals
                    cart_total += combined_total
                    vatable_total += combined_vatable
                
                # Apply cart discount proportionally
                cart_disc = items[0][8]
                if cart_disc > 0:
                    cart_disc_type = items[0][7]
                    cart_total = helpers.calculate_cart_discounts(cart_disc, cart_disc_type, cart_total)
                    if cart_total > 0:
                        vatable_total *= (cart_total / (cart_total + cart_disc))
                
                # Update VAT
                vat_base = cart_total if order_type == 'dine' else vatable_total
                vat_amount = round(vat_base * vat_rate, 2)
                cursor.execute("UPDATE cart SET vat_amount = ? WHERE cart_id = ?", (vat_amount, cart_id))
        
        # 3. Process payments
        if payment_method == 'Split' and split_charges and len(split_charges) > 0:
            for charge in split_charges:
                charge_payment_method = charge.get('paymentMethod', payment_method)
                charge_discounted_total = charge.get('amount', 0)
                cursor.execute("""
                    INSERT INTO cart_payments 
                    (cart_id, payment_method, discounted_total) 
                    VALUES (?, ?, ?)""",
                    (cart_id, charge_payment_method, charge_discounted_total))
        else:
            cursor.execute("""
                INSERT INTO cart_payments 
                (cart_id, payment_method, discounted_total) 
                VALUES (?, ?, ?)""",
                (cart_id, payment_method, discounted_total))
        
        # 4. Create kitchen order if enabled
        if get_setting('kitchen_screen') == "1":
            cursor.execute("""
                INSERT INTO kitchen_orders (order_id, item_id)
                SELECT cart_id, cart_item_id
                FROM cart_item
                WHERE cart_id = ?""", 
                (cart_id,))

        conn.commit()
        deduct_inventory(cart_id)
        return {'status': 'success'}
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        if conn:
            conn.close()

def deduct_inventory(cart_id):
    conn, cursor = get_database_connection()
    
    # Get all items in cart
    cursor.execute("""
        SELECT ci.product_id, ci.quantity, p.stock_quantity, p.track_inventory, p.product_name
        FROM cart_item ci
        JOIN products p ON ci.product_id = p.product_id
        WHERE ci.cart_id = ?
    """, (cart_id,))
    
    items = cursor.fetchall()
    
    for product_id, qty, current_stock, track_inv, name in items:
        if track_inv == 1:  # Only if inventory tracking enabled
            new_stock = current_stock - qty
            
            # Optional: Prevent negative stock
            if new_stock < 0:
                conn.close()
                return {"error": f"{name} out of stock"}, 400
            
            cursor.execute("""
                UPDATE products 
                SET stock_quantity = ? 
                WHERE product_id = ?
            """, (new_stock, product_id))
    
    conn.commit()
    conn.close()
    return {"message": "Inventory updated"}, 200

def update_vat_price(cart_id, vat_amount):
    try:
        conn, cursor = get_database_connection()
        cursor.execute("UPDATE cart SET vat_amount = ? WHERE cart_id = ?",
                       (vat_amount, cart_id))
        conn.commit()
        return jsonify({"message": "vat updated"}), 200
    except Exception as e:
        return f"Error updating vat: {e}"
    finally:
        conn.close()

def get_order_history(start_date=None, end_date=None, payment_method=None):
    conn, cursor = get_database_connection()
    
    # Base query
    query = '''
        SELECT
            main.cart_id,
            main.order_type,
            main.formatted_order_date,
            main.customer_name,
            main.payment_info,
            sub.total_discounted_amount,
            vat_amount
        FROM (
            SELECT
                c.cart_id,
                c.order_type,
                c.vat_amount,
                strftime('%H:%M %d-%m-%Y', c.cart_charge_updated) AS formatted_order_date,
                cu.customer_name,
                cp.payment_info
            FROM cart c
            LEFT JOIN customers cu ON c.customer_id = cu.customer_id
            LEFT JOIN (
                SELECT cart_id, GROUP_CONCAT(payment_method || ': £' || printf("%.2f", discounted_total)) AS payment_info
                FROM cart_payments
                GROUP BY cart_id
            ) cp ON c.cart_id = cp.cart_id
            WHERE c.cart_status IN ('completed', 'refunded', 'partial_refund')
    '''
    
    params = []
    
    # Add date range filter if both dates are provided
    if start_date and end_date:
        query += ' AND c.cart_charge_updated BETWEEN ? AND ?'
        params.extend([start_date, end_date])
    elif start_date or end_date:
        conn.close()
        raise ValueError("Both start_date and end_date must be provided, or neither")
    
    # Add payment method filter if provided
    if payment_method is not None:
        if payment_method == "Cash":
            query += '''
                AND c.cart_id IN (
                    SELECT DISTINCT cart_id 
                    FROM cart_payments 
                    WHERE payment_method = ?
                )
            '''
            params.append("Cash")
        else:
            query += '''
                AND c.cart_id IN (
                    SELECT DISTINCT cart_id 
                    FROM cart_payments 
                    WHERE payment_method != 'Cash'
                )
            '''
    
    # Complete the query
    query += '''
            GROUP BY c.cart_id, c.order_type, c.order_menu, c.cart_charge_updated, c.customer_id, cu.customer_name
            ORDER BY c.cart_charge_updated DESC
        ) main
        LEFT JOIN (
            SELECT
                cart_id,
                SUM(discounted_total) AS total_discounted_amount
            FROM cart_payments
            GROUP BY cart_id
        ) sub ON main.cart_id = sub.cart_id;
    '''
    
    cursor.execute(query, params)
    orders = cursor.fetchall()
    conn.close()
    return orders

def get_payment_info(cart_id):
    conn, cursor = get_database_connection()
    cursor.execute('''
        SELECT payment_method, discounted_total FROM cart_payments WHERE cart_id = ?
    ''', (cart_id,))

    payments = cursor.fetchall()
    conn.close()
    return payments

def create_refund(cart_id):
    try:
        conn, cursor = get_database_connection()
        employee_id = session.get('employee_id', 0)
        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE cart SET cart_status = ?, cart_charge_updated = ?, cart_updated_by = ? WHERE cart_id = ?
        ''', ('refunded', current_timestamp, employee_id, cart_id))
        # add receipt print
        conn.commit()
        return jsonify({"message": "Refund complete"}), 200
    except Exception as e:
        return f"Error refunding: {e}"
    finally:
        conn.close()

def create_new_product(form_data):
    """
    Updated function to handle all product fields including barcode and inventory tracking
    """
    try:
        # Extract checkbox values (only present if checked)
        cpn = 1 if 'discountable' in form_data else 0
        favourite = 1 if 'favourite' in form_data else 0
        vatable = 1 if 'vatable' in form_data else 1
        track_inventory = 1 if 'track_inventory' in form_data else 0
        
        # Extract form values
        name = form_data.get('name')
        inprice = form_data.get('inprice')
        outprice = form_data.get('outprice')
        category = form_data.get('newCategory')
        barcode = form_data.get('barcode', '')  # Optional field
        stock_quantity = int(form_data.get('stock_quantity', 0))
        low_stock_threshold = int(form_data.get('low_stock_threshold', 5))
        
        # Validation
        if not outprice:
            outprice = inprice
            
        conn, cursor = get_database_connection()
        
        # Updated SQL to include new fields
        cursor.execute(
            """INSERT INTO products 
            (category_id, product_name, in_price, out_price, cpn, is_favourite, vatable, 
             barcode, track_inventory, stock_quantity, low_stock_threshold) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (category, name, inprice, outprice, cpn, favourite, vatable, 
             barcode, track_inventory, stock_quantity, low_stock_threshold)
        )
        
        conn.commit()
        conn.close()
        
        return {"message": "New product added successfully."}, 200
        
    except Exception as e:
        return {"error": str(e)}, 500

def update_product_options(product_id, new_options):
    try:
        conn, cursor = get_database_connection()

        # Clear all existing options for this product
        cursor.execute("DELETE FROM product_options WHERE product_id = ?", (product_id,))

        # Insert updated options with order and max
        for i, option in enumerate(new_options):
            option_id = int(option["optionId"])
            max_value = int(option["max"])
            order_value = i  # zero-based order

            cursor.execute("""
                INSERT INTO product_options (product_id, option_id, option_item_max, option_order)
                VALUES (?, ?, ?, ?)
            """, (product_id, option_id, max_value, order_value))

        conn.commit()
    except Exception as e:
        print("Error updating product options:", str(e))
    finally:
        conn.close()

def update_product(product_id, product):
    try:
        conn, cursor = get_database_connection()

        # Extract barcode safely
        barcode = product.get('barcode', None)

        # Base SQL without barcode
        sql = """
            UPDATE products
            SET product_name = ?, 
                in_price = ?, 
                out_price = ?, 
                cpn = ?, 
                is_favourite = ?, 
                vatable = ?, 
                category_id = ?,
                track_inventory = ?,
                stock_quantity = ?,
                low_stock_threshold = ?
        """

        values = [
            product['product_name'],
            float(product['in_price']),
            float(product['out_price']),
            product['cpn'],
            product['is_favourite'],
            product['is_vatable'],
            int(product['category_id']),
            product.get('track_inventory', 0),
            int(product.get('stock_quantity', 0)),
            int(product.get('low_stock_threshold', 5))
        ]

        # Only update barcode if provided AND not empty
        if barcode:
            sql += ", barcode = ?"
            values.append(barcode)

        # Add WHERE clause
        sql += " WHERE product_id = ?"
        values.append(product_id)

        cursor.execute(sql, tuple(values))
        conn.commit()

        return jsonify({"message": "Product updated"}), 200

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return f"Error updating product: {e}"
    finally:
        conn.close()

def get_cart_note(cart_id):
    conn, cursor = get_database_connection()
    cursor.execute("SELECT overall_note FROM cart WHERE cart_id=?", (cart_id,))
    cart = cursor.fetchone()
    conn.close()
    return cart

def update_cart_note(cart_id, new_note):
    conn, cursor = get_database_connection()
    cursor.execute("UPDATE cart SET overall_note=? WHERE cart_id=?", (new_note, cart_id))
    conn.commit()
    conn.close()

def fetch_totals(start_date, end_date):
    conn, cursor = get_database_connection()
    cut_off_hour = get_setting('cut_off_hour')
    if cut_off_hour is None:
        cut_off_hour = set_setting('cut_off_hour', 0)
    
    try:
        cut_off_hour = int(cut_off_hour)
    except (ValueError, TypeError):
        cut_off_hour = 0
    
    if start_date is None:
        start_date = datetime.now().date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if end_date is None:
        end_date = datetime.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    effective_start = datetime.combine(start_date, datetime.min.time()) + timedelta(hours=cut_off_hour)
    effective_end = datetime.combine(end_date, datetime.min.time()) + timedelta(days=1, hours=cut_off_hour)
    
    start_str = effective_start.strftime('%Y-%m-%d %H:%M:%S')
    end_str = effective_end.strftime('%Y-%m-%d %H:%M:%S')
    
    query = """
        SELECT
            SUM(cp.discounted_total) AS grand_total,
            COUNT(DISTINCT c.cart_id) AS total_orders,
            COUNT(DISTINCT CASE WHEN c.order_type = 'dine' THEN c.cart_id END) AS dine_count,
            COUNT(DISTINCT CASE WHEN c.order_type = 'takeaway' THEN c.cart_id END) AS takeaway_count,
            COUNT(DISTINCT CASE WHEN c.order_type = 'delivery' THEN c.cart_id END) AS delivery_count,
            COUNT(DISTINCT CASE WHEN c.order_type = 'waiting' THEN c.cart_id END) AS waiting_count,
            COUNT(DISTINCT CASE WHEN c.order_type = 'sale' THEN c.cart_id END) AS sale_count,
            SUM(CASE WHEN cp.payment_method LIKE 'Card%' THEN 1 ELSE 0 END) AS card_payments_count,
            SUM(CASE WHEN cp.payment_method LIKE 'Card%' THEN cp.discounted_total ELSE 0 END) AS card_payments_total,
            SUM(CASE WHEN cp.payment_method = 'Cash' THEN 1 ELSE 0 END) AS cash_payments_count,
            SUM(CASE WHEN cp.payment_method = 'Cash' THEN cp.discounted_total ELSE 0 END) AS cash_payments_total,
            SUM(CASE WHEN c.cart_status IN ('refunded', 'partial_refund') THEN 1 ELSE 0 END) AS refunded_orders_count,
            COALESCE(SUM(r.amount), 0) AS total_refunds,
            SUM(c.vat_amount) AS total_vat_amount,
            -- Processing orders (not filtered by date)
            (SELECT COUNT(DISTINCT cart_id) FROM cart WHERE cart_status = 'processing') AS processing_orders_count,
            COALESCE(
                (SELECT SUM(ci.price) 
                FROM cart_item ci 
                JOIN cart c2 ON ci.cart_id = c2.cart_id
                WHERE c2.cart_status = 'processing'),
            0) AS processing_orders_total
        FROM
            cart c
        JOIN
            cart_payments cp ON c.cart_id = cp.cart_id
        LEFT JOIN
            refunds r ON c.cart_id = r.cart_id
        WHERE
            c.cart_charge_updated BETWEEN ? AND ?
            AND c.cart_status IN ('completed', 'refunded', 'partial_refund');
            """
    
    cursor.execute(query, (start_str, end_str))
    result = cursor.fetchone()

    conn.close()
    return result

def get_inventory():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT product_id, product_name, in_price, out_price, is_hidden FROM products WHERE is_hidden = 1')
        products = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]

        cursor.execute('SELECT category_id, category_name, is_hidden FROM category WHERE is_hidden = 1')
        categories = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]

        cursor.execute('SELECT option_id, option_name, is_hidden FROM options WHERE is_hidden = 1')
        options = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]

        conn.close()
        inventory_dict = {
            'products': products,
            'categories': categories,
            'options': options
        }
        return inventory_dict
    except Exception as e:
        return f"Error getting inventory: {e}"

def update_inventory_item_by_id(inventory_item_id, type, undo):
    try:
        conn, cursor = get_database_connection()
        if type == 'p':
            cursor.execute("UPDATE products SET is_hidden = ? WHERE product_id = ?",
                        (undo, inventory_item_id))
        elif type == 'c':
            cursor.execute("UPDATE category SET is_hidden = ? WHERE category_id = ?",
                        (undo, inventory_item_id))
        elif type == 'o':
            cursor.execute("UPDATE options SET is_hidden = ? WHERE option_id = ?",
                        (undo, inventory_item_id))
            cursor.execute("UPDATE product_options SET is_hidden = ? WHERE option_id = ?",
                        (undo, inventory_item_id))
        conn.commit()
        return jsonify({"message": "inventory item updated"}), 200
    except Exception as e:
        return f"Error updating product: {e}"
    finally:
        conn.close()

def delete_dining_table_by_id(table_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute("DELETE FROM dining_tables WHERE table_id = ?", (table_id, ))
        conn.commit()
        return get_dining_tables(), 200
    except Exception as e:
        return f"Error deleting table: {e}"
    finally:
        conn.close()

def update_delete_save_option_item(data):
    try:
        conn, cursor = get_database_connection()
        method = data.get('method')
        item_id = data.get('id')
        option_name = data.get('optionName', '')
        in_price = data.get('inPrice',0)
        out_price = data.get('outPrice',0)
        option_id = data.get('parentId',0)
        vatable = data.get('vatable',1)
        option_item_id = data.get('option_item_id',0)

        if method == 'update':
            cursor.execute("UPDATE option_items SET option_item_name = ? WHERE option_item_id = ?", (option_name, item_id))

            cursor.execute("UPDATE option_item_groups SET option_item_in_price = ?, option_item_out_price = ?, vatable = ? WHERE option_item_id = ? AND option_id = ?", (in_price, out_price, vatable, item_id, option_id))

            conn.commit()
            return jsonify({'message': 'Update successful'})

        elif method == 'delete':
            cursor.execute("UPDATE option_item_groups SET is_hidden = 1 WHERE option_item_id = ?", (item_id, ))
            conn.commit()
            return jsonify({'message': 'Delete successful'})
        
        elif method == 'new':
            if option_item_id:
                cursor.execute(
                    "SELECT COUNT() FROM option_item_groups WHERE option_id = ? AND option_item_id = ?",
                    (option_id, option_item_id)
                )
                count = cursor.fetchone()[0]
                if count > 0:
                    return jsonify({'message': 'exists'})
            else:     
                cursor.execute(
                    "INSERT INTO option_items (option_item_name) VALUES (?)",
                        (option_name,)
                    )
                option_item_id = cursor.lastrowid
                
            cursor.execute(
                "INSERT INTO option_item_groups (option_id, option_item_id, option_item_in_price, option_item_out_price, vatable) VALUES (?, ?, ?, ?, ?)",
                    (option_id, option_item_id, in_price, out_price, vatable)
                )
            conn.commit()
            return jsonify({'message': 'New item insert successful'})
        else:
            return jsonify({'error': 'Unsupported method'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

def update_save_new_option(data):
    try:
        conn, cursor = get_database_connection()
        method = data.get('method')
        option_id = data.get('id', 0)
        option_name = data.get('optionName', '')
        option_type = data.get('type', 'check')
        option_order = int(data.get('order', 1))
        if method == 'update':
            cursor.execute("UPDATE options SET option_name = ?, option_type = ?, option_order = ? WHERE option_id = ?", (option_name, option_type, option_order, option_id))
            conn.commit()
            return jsonify({'message': 'Update successful'})
        
        elif method == 'new':
            cursor.execute(
            "INSERT INTO options (option_name, option_type) VALUES (?, ?)",
                (option_name, option_type)
            )
            conn.commit()
            return jsonify({'message': 'New item insert successful'})
        else:
            return jsonify({'error': 'Unsupported method'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

def get_refunded_orders(start_date, end_date):
    conn = None
    try:
        conn, cursor = get_database_connection()
        sql_query = """
        SELECT 
            c.order_type, 
            strftime('%H:%M %d-%m-%Y', c.order_date) AS formatted_order_date, 
            c.cart_status, 
            strftime('%H:%M %d-%m-%Y', c.cart_charge_updated) AS formatted_charge_date, 
            cu.customer_name, 
            cp.payment_method, 
            cp.discounted_total,
            e.name
        FROM 
            cart c
        JOIN 
            customers cu ON c.customer_id = cu.customer_id
        JOIN 
            cart_payments cp ON c.cart_id = cp.cart_id
        JOIN 
            employees e ON c.cart_updated_by = e.employee_id
        WHERE 
            c.cart_status = 'refunded'
            AND c.cart_charge_updated BETWEEN ? AND ?
        """
        cursor.execute(sql_query, (start_date, end_date))
        result = cursor.fetchall()
        refunds = [dict(zip([desc[0] for desc in cursor.description], row)) for row in result]
        return refunds
    except sqlite3.Error as e:
        print("Error executing SQL query:", e)
        return []  # Return an empty list in case of error
    finally:
        if conn:
            conn.close()

# def save_product_options_bulk(data):
#     try:
#         selected_options = data['selectedOptions']
#         selected_products = data['selectedProducts']
#         print("products", selected_products)
#         print("options", selected_options)
#         conn, cursor = get_database_connection()
#         for product_id in selected_products:
#             for option_id in selected_options:
#                 cursor.execute("INSERT INTO product_options (product_id, option_id) VALUES (?, ?)", (product_id, option_id))
#         conn.commit()
#         conn.close()
#         return jsonify({'message': 'Data inserted successfully'}), 200
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
            
def save_product_options_bulk(data):
    try:
        selected_options = data['selectedOptions'].split(',')
        selected_products = data['selectedProducts'].split(',')
        conn, cursor = get_database_connection()
        for product_id_str in selected_products:
            try:
                product_id = int(product_id_str)
            except ValueError:
                # Skip non-integer values
                continue
            for option_id_str in selected_options:
                try:
                    option_id = int(option_id_str)
                except ValueError:
                    # Skip non-integer values
                    continue
                cursor.execute("INSERT INTO product_options (product_id, option_id) VALUES (?, ?)", (product_id, option_id))
            conn.commit()
        conn.close()
        return jsonify({'message': 'Data inserted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def save_bulk_products(products, in_prices, out_prices, category_id):
    try:
        for i in range(len(out_prices)):
            if out_prices[i] == '':
                out_prices[i] = in_prices[i]
        
        conn, cursor = get_database_connection()
        for product_name, in_price, out_price in zip(products, in_prices, out_prices):
            product_name = product_name.capitalize()
            cursor.execute("INSERT INTO products (category_id, product_name, in_price, out_price, cpn) VALUES (?, ?, ?, ?, 1)",
                           (category_id, product_name, in_price, out_price))
        conn.commit()
        conn.close()

        response_data = {'message': 'Products added successfully'}
        status_code = 200
    except Exception as e:
        response_data = {'error': str(e)}
        status_code = 500
    
    return jsonify(response_data), status_code

def save_bulk_categories(categories):
    try:
        conn, cursor = get_database_connection()
        for category in categories:
            category = category.capitalize()
            cursor.execute("INSERT INTO category (category_name) VALUES (?)", (category,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Categories inserted successfully.'}), 200
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'error': f'Error inserting categories: {str(e)}'}), 500   

def save_terminals(terminals):
    try:
        conn, cursor = get_database_connection()
        for terminal in terminals.get('terminals', []):
            location = terminal.get('location')
            tid = terminal.get('tid')
            if location and tid:
                cursor.execute("INSERT OR IGNORE INTO card_terminals (tid, terminal_location) VALUES (?, ?)", (tid, location))

        conn.commit()
        conn.close()

        message = {"status": "success", "message": "Data inserted into card_terminals table successfully."}
    except Exception as e:
        message = {"status": "error", "message": f"An error occurred: {e}"}
    return json.dumps(message)

def get_terminals_from_db():
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT * FROM card_terminals")
        result = cursor.fetchall()
        terminals = [dict(zip([desc[0] for desc in cursor.description], row)) for row in result]
        return terminals
    except sqlite3.Error as e:
        print("Error all terminals query:", e)
        return []
    finally:
        if conn:
            conn.close()

def get_selected_terminal():
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT terminal_location FROM card_terminals WHERE selected = 1")
        result = cursor.fetchone()
        if result:
            terminal_location = result[0]
            return terminal_location
        else:
            return None
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()
    
def export_sqlite_db():
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        export_file = io.BytesIO()

        for table in tables:
            table_name = table[0]
            # Write SQL to create the table
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table_name}';")
            create_table_sql = cursor.fetchone()[0]
            export_file.write(f"{create_table_sql};\n\n".encode())

            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            for row in rows:
                export_file.write(f"INSERT INTO {table_name} VALUES {row};\n".encode())

        conn.close()

        export_file.seek(0)

        return export_file
    except Exception as e:
        print(f"Export failed: {e}")
        return None

def export_products_db():
    try:
        conn, cursor = get_database_connection()
        
        # Define the tables you want to export
        allowed_tables = {"category", "options", "products", "option_items", "product_options", "option_item_groups", "option_group_items", "option_groups"}

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall() if table[0] in allowed_tables]

        export_file = io.BytesIO()

        for table_name in tables:
            # Add DROP TABLE IF EXISTS before creating
            export_file.write(f"DROP TABLE IF EXISTS {table_name};\n".encode())

            # Write SQL to create the table
            cursor.execute("SELECT sql FROM sqlite_master WHERE name=?;", (table_name,))
            create_table_sql = cursor.fetchone()
            if create_table_sql and create_table_sql[0]:
                export_file.write(f"{create_table_sql[0]};\n\n".encode())

            # Insert data
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            for row in rows:
                escaped_values = []
                for value in row:
                    if isinstance(value, str):
                        # Escape single quotes by doubling them
                        value = value.replace("'", "''")
                        escaped_values.append(f"'{value}'")
                    elif value is None:
                        escaped_values.append("NULL")
                    else:
                        escaped_values.append(str(value))
                
                values = ", ".join(escaped_values)
                export_file.write(f"INSERT INTO {table_name} VALUES ({values});\n".encode())

        conn.close()
        export_file.seek(0)

        return export_file
    except Exception as e:
        print(f"Export failed: {e}")
        return None

def restore_sqlite_db(filepath):
    try:
        conn, cursor = get_database_connection()

        with open(filepath, "r", encoding="utf-8") as f:
            sql_script = f.read()
            cursor.executescript(sql_script)

        conn.commit()
        conn.close()
        return True, "Database successfully restored!"
    except Exception as e:
        return False, f"Restore failed: {str(e)}"

def delete_cart_data(cart_id):
    try:
        conn, cursor = get_database_connection()
        conn.execute('BEGIN TRANSACTION')
        
        cursor.execute('DELETE FROM cart WHERE cart_id = ?', (cart_id,))
        cursor.execute('DELETE FROM cart_item WHERE cart_id = ?', (cart_id,))
        cursor.execute('DELETE FROM cart_payments WHERE cart_id = ?', (cart_id,))

        conn.commit()
        response = {'success': True, 'message': 'Cart data deleted successfully'}
        return json.dumps(response)

    except sqlite3.Error as e:
        conn.rollback()
        error_response = {'success': False, 'message': 'Error: ' + str(e)}
        return json.dumps(error_response)

    finally:
        conn.close()

def get_customers():
    conn = None
    try:
        conn, cursor = get_database_connection()
        sql_query = """
        SELECT c.customer_id, customer_name, customer_telephone, address, postcode 
        FROM customers c
        LEFT JOIN customer_addresses a ON c.customer_id = a.customer_id 
        WHERE c.customer_telephone != '00000'
        """
        cursor.execute(sql_query)
        result = cursor.fetchall()
        customers = [dict(zip([desc[0] for desc in cursor.description], row)) for row in result]
        return customers
    except sqlite3.Error as e:
        print("Error executing customers SQL query:", e)
        return []  # Return an empty list in case of error
    finally:
        if conn:
            conn.close()

# all option names and products for adding to new option group
def get_all_option_templates():
    conn = None
    cursor = None
    try:
        conn, cursor = get_database_connection()
        if not conn or not cursor:
            raise Exception("Failed to get database connection.")

        # Fetch option items
        sql_query = """
            SELECT DISTINCT oi.option_item_id, 
                option_item_name, 
                option_item_in_price, 
                option_item_out_price, 
                o.option_name 
            FROM option_items oi
            LEFT JOIN option_item_groups oig ON oi.option_item_id = oig.option_item_id
            LEFT JOIN options o ON o.option_id = oig.option_id
            WHERE o.is_hidden = 0
            ORDER BY oi.option_item_name;
        """
        cursor.execute(sql_query)
        option_items = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]

        # Fetch product items
        sql_query = """
            SELECT DISTINCT(product_name), in_price, out_price 
            FROM products
            WHERE is_hidden = 0
            ORDER BY product_name
        """
        cursor.execute(sql_query)
        product_items = [dict(zip([desc[0] for desc in cursor.description], row)) for row in cursor.fetchall()]

        # Organize option_items by option_name
        grouped_option_items = defaultdict(list)
        for option_item in option_items:
            grouped_option_items[option_item['option_name']].append(option_item)

        data = {"options": grouped_option_items, "products": product_items}
        # Return JSON response
        return data
        
    except sqlite3.Error as e:
        print("Error executing SQL query:", e)
        return jsonify({"error": "Database query failed."}), 500  # Return a JSON error message with a 500 status code
    except Exception as e:
        print("Unexpected error:", e)
        return jsonify({"error": str(e)}), 500  # General error handling
    finally:
        if cursor:
            cursor.close()  # Close the cursor
        if conn:
            conn.close()  # Close the connection

def delete_customer(customer_id):
    try:
        conn, cursor = get_database_connection()
        conn.execute("BEGIN")

        cursor.execute(
            "SELECT cart_id FROM cart WHERE customer_id = ?",
            (customer_id,)
        )
        cart_ids = cursor.fetchall()

        if cart_ids:
            cart_ids_tuple = tuple([cart_id[0] for cart_id in cart_ids])  # Convert to tuple
            cursor.execute(
                "DELETE FROM cart_item WHERE cart_id IN ({seq})".format(
                    seq=','.join(['?'] * len(cart_ids_tuple))
                ),
                cart_ids_tuple
            )

        cursor.execute(
            "DELETE FROM customer_addresses WHERE customer_id = ?",
            (customer_id,)
        )

        cursor.execute(
            "DELETE FROM cart WHERE customer_id = ?",
            (customer_id,)
        )

        cursor.execute(
            "DELETE FROM customers WHERE customer_id = ?",
            (customer_id,)
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "All customer data successfully deleted"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    
def get_recent_orders_for_pos():
    conn = None
    try:
        conn, cursor = get_database_connection()
        sql_query = """
        SELECT
            c.cart_id,
            c.order_type,
            c.order_date,
            SUM(cp.discounted_total) AS total_payments
        FROM
            cart c
        LEFT JOIN
            cart_payments cp ON c.cart_id = cp.cart_id
        WHERE cart_status = "completed"
        GROUP BY
            c.cart_id, c.order_type
        ORDER BY
            c.cart_id DESC
        LIMIT 10
        """
        cursor.execute(sql_query)
        result = cursor.fetchall()
        orders = [dict(zip([desc[0] for desc in cursor.description], row)) for row in result]
        return orders
    except sqlite3.Error as e:
        print("Error executing orders SQL query:", e)
        return []  # Return an empty list in case of error
    finally:
        if conn:
            conn.close()

def create_settings_table():
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        return jsonify({"message": "Settings table created successfully"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": f"Error creating settings table: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

def get_setting(key):
    """Retrieve a setting from the database."""
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None  # Returning None if no value is found
    except sqlite3.Error as e:
        print(f"Error executing SQL query: {e}")
        return None  # Return None on error, better than an empty list
    finally:
        if conn:
            conn.close()

def set_setting(key, value):
    """Store or update a setting in the database."""
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                       "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                       (key, value))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error executing SQL query: {e}")
    finally:
        if conn:
            conn.close()

# boolean setting helper to check and add if not exists
def get_bool_setting(key, default=0):
    val = get_setting(key)
    if val is None:
        set_setting(key, default)
        val = default
    return str(val) == "1"

# newest helpers for settings

def get_setting_bool(key, default=False):
    """Get a setting as boolean, handling None/missing/empty cases"""
    val = get_setting(key)
    if val is None or val == '':
        return default
    if isinstance(val, str):
        return val.lower() in ('1', 'true', 'yes', 'on')
    return bool(val)

def get_setting_str(key, default=''):
    """Get a setting as string, handling None case"""
    val = get_setting(key)
    return val if val is not None else default

# recent orders for remote sync
def get_recent_orders():
    """Fetch orders updated in the last 15 minutes"""
    conn = None
    minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=15)
    try:
        conn, cursor = get_database_connection()
        cursor.execute("""
            SELECT 
                c.cart_id, 
                c.order_date, 
                c.cart_status, 
                c.cart_discount, 
                c.vat_amount,
                c.cart_discount_type, 
                COALESCE((
                    SELECT SUM(
                        CASE 
                            WHEN ci.product_discount_type = 'percentage' THEN 
                                (ci.price * ci.quantity) * (1 - ci.product_discount/100)
                            ELSE 
                                (ci.price * ci.quantity) - ci.product_discount
                        END
                    ) 
                    FROM cart_item ci 
                    WHERE ci.cart_id = c.cart_id
                ), 0) AS total_amount,
                (SELECT COUNT(*) FROM cart_item WHERE cart_id = c.cart_id) AS item_count
            FROM cart c
            WHERE c.sync_status = 'pending'
            GROUP BY c.cart_id
        """)
        # cursor.execute("""
        #     SELECT c.cart_id, c.order_date, c.cart_status, c.cart_discount, c.vat_amount,
        #         SUM(ci.price * ci.quantity - ci.product_discount) AS total_amount,
        #         COUNT(ci.cart_id) AS item_count
        #     FROM cart c
        #     LEFT JOIN cart_item ci ON c.cart_id = ci.cart_id
        #     WHERE c.sync_status = 'pending'
        #     GROUP BY c.cart_id
        # """)
        orders = cursor.fetchall()
        return orders
    except sqlite3.Error as e:
        print(f"Error fetching recent orders: {e}")
        return []
    finally:
        if conn:
            conn.close()

# get all items from settings table
def get_all_settings():
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT key, value FROM settings")
        settings = cursor.fetchall()
        return settings
    except sqlite3.Error as e:
        print(f"Error fetching settings: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_sync_status(cart_ids, status):
    # Update the sync status of the carts after remote sync
    if not cart_ids:
        return  # No IDs to update

    conn, cursor = get_database_connection()
    try:
        cursor.executemany("UPDATE cart SET sync_status = ? WHERE cart_id = ?", [(status, cid) for cid in cart_ids])
        conn.commit()
    except Exception as e:
        print(f"Error updating sync status: {e}")
    finally:
        if conn:
            conn.close()

def log_deleted_cart(cart_id):
    try:
        deleted_ids = get_setting("deleted_carts")

        if deleted_ids is None:
            deleted_ids = ""
            set_setting("deleted_carts", deleted_ids)

        # Convert to list
        deleted_ids = deleted_ids.split(",") if deleted_ids else []

        # Ensure the ID is not duplicated
        if str(cart_id) not in deleted_ids:
            deleted_ids.append(str(cart_id))

        # Store updated list back in the settings table
        set_setting("deleted_carts", ",".join(deleted_ids))
    except Exception as e:
        print(f"Error logging deleted cart: {e}")

def get_deleted_cart_ids():
    try:
        deleted_ids = get_setting("deleted_carts")

        # Initialize key if missing
        if deleted_ids is None:
            set_setting("deleted_carts", "")
            return []

        return deleted_ids.split(",") if deleted_ids else []
    except Exception as e:
        print(f"Error retrieving deleted cart IDs: {e}")
        return []

def get_discount_presets():
    conn = None
    try:
        # create table if not exists, discount_presets (id, type, amount)
        conn, cursor = get_database_connection()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discount_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount REAL
            )
        ''')
        conn.commit()

        conn, cursor = get_database_connection()
        cursor.execute("SELECT * FROM discount_presets WHERE type <> 'misc' AND type IS NOT NULL")
        presets = cursor.fetchall()
        return presets
    except sqlite3.Error as e:
        print(f"Error fetching discount presets: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_misc_amount_presets():
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT * FROM discount_presets WHERE type = 'misc' AND type IS NOT NULL")
        presets = cursor.fetchall()
        return presets
    except sqlite3.Error as e:
        print(f"Error fetching misc presets from discounts: {e}")
        return []
    finally:
        if conn:
            conn.close()

def create_discount_preset(discount_type, amount):
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT 1 FROM discount_presets WHERE type = ? AND amount = ?", (discount_type, amount))
        if cursor.fetchone():
            conn.close()
            return False  # Preset already exists
        cursor.execute("INSERT INTO discount_presets (type, amount) VALUES (?, ?)", (discount_type, amount))
        conn.commit()
        return True
    except sqlite3.Error as e:
        return False
    finally:
        if conn:
            conn.close()

def delete_discount_preset(preset_id):
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("DELETE FROM discount_presets WHERE id = ?", (preset_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        return False
    finally:
        if conn:
            conn.close()

def create_kitchen_orders_table():
    conn = None
    try:
        conn, cursor = get_database_connection()
        
        # Create kitchen_orders table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kitchen_orders (
                order_id INT,
                item_id INT,
                kitchen_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (order_id, item_id),
                FOREIGN KEY (order_id) REFERENCES cart(cart_id),
                FOREIGN KEY (item_id) REFERENCES cart_item(cart_item_id)
            )
        ''')

        # Create excluded_kitchen_products table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS excluded_kitchen_products (
                product_id INTEGER PRIMARY KEY REFERENCES products(product_id)
            )
        ''')

        # Create indexes to optimize queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_id ON products(product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_excluded_product_id ON excluded_kitchen_products(product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cart_item_product_id ON cart_item(product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cart_item_cart_id ON cart_item(cart_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_kitchen_orders_order_id ON kitchen_orders(order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_kitchen_orders_item_id ON kitchen_orders(item_id)')

        conn.commit()
        return jsonify({"message": "Kitchen orders and excluded products tables created successfully"}), 200

    except sqlite3.Error as e:
        return jsonify({"error": f"Error creating tables: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()

def get_kitchen_screen_orders(status=None):
    # Preserve is pre-serve, one below served status
    where_clause = ""
    exclude_clause = ""

    if status is None:
        where_clause = "WHERE ko.kitchen_status IN ('ready', 'preready', 'pending', 'preserve')"
    else:
        status_list = status.split(',')
        status_sql = "', '".join(status_list)  # Convert list to SQL format ('pending', 'preready')
        where_clause = f"WHERE ko.kitchen_status IN ('{status_sql}')"
        exclude_clause = "AND ekp.product_id IS NULL"  # Exclude items found in excluded_kitchen_products
    try:
        conn, cursor = get_database_connection()
        query = f'''
            SELECT
                c.cart_id,
                c.order_date,
                c.cart_charge_updated,
                c.overall_note,
                c.order_type,
                ci.cart_item_id,
                ci.product_name,
                ci.quantity,
                ci.options,
                ci.product_note,
                ko.kitchen_status,
                CASE WHEN ekp.product_id IS NOT NULL THEN 1 ELSE 0 END AS is_excluded
            FROM
                cart_item ci
            JOIN
                kitchen_orders ko ON ci.cart_id = ko.order_id AND ci.cart_item_id = ko.item_id
            JOIN
                cart c ON ci.cart_id = c.cart_id
            JOIN
                products p ON ci.product_id = p.product_id  -- Ensure product_id is retrieved
            LEFT JOIN
                excluded_kitchen_products ekp ON p.product_id = ekp.product_id  -- Exclude logic
            {where_clause}
            {exclude_clause}
            ORDER BY
                ci.cart_id,
                ci.category_order
        '''
        cursor.execute(query)
        orders = cursor.fetchall()
        
        # Convert to list of dictionaries
        if orders:
            orders = [dict(zip([desc[0] for desc in cursor.description], row)) for row in orders]
            return orders
        else:
            return []
    except sqlite3.Error as e:
        print(f"Error fetching kitchen orders: {e}")
        return []
    finally:
        if conn:
            conn.close()

def mark_kitchen_item_ready(cart_item_id, kitchen_status='ready'):
    """Mark a single kitchen item as ready or with custom status"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn, cursor = get_database_connection()
       
        # Update the item's status in the cart_items table
        cursor.execute(
            "UPDATE kitchen_orders SET kitchen_status = ?, updated_at = ? WHERE item_id = ?",
            (kitchen_status, current_time, cart_item_id)
        )
       
        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result
    except Exception as e:
        print(f"Database error marking item status: {str(e)}")
        return False

def mark_kitchen_order_ready(cart_id, kitchen_status='ready'):
    """Mark all items in an order as ready"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn, cursor = get_database_connection()

        if kitchen_status == 'served':
            # Just delete directly if status is 'served'
            cursor.execute(
                "DELETE FROM kitchen_orders WHERE order_id = ?",
                (cart_id,)
            )
        else:
            cursor.execute(
                "UPDATE kitchen_orders SET kitchen_status = ?, updated_at = ? WHERE order_id = ?",
                (kitchen_status, current_time, cart_id)
            )

        conn.commit()
        result = cursor.rowcount > 0
        conn.close()
        return result
    except Exception as e:
        print(f"Database error marking order ready: {str(e)}")
        return False
    
def create_verofy_table():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verofy_setting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                verofy_ip_address TEXT,
                verofy_terminal_id TEXT,
                pairing_code TEXT
            )
        ''')
        conn.commit()
        conn.close()
        return jsonify({"message": "Verofy table created successfully"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": f"Error creating verofy table: {str(e)}"}), 500
    
def save_verofy_credentials(ip, terminal_id, code):
    conn, cursor = get_database_connection()
    try:
        cursor.execute("""
            INSERT INTO verofy_setting (id, verofy_ip_address, verofy_terminal_id, pairing_code)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET 
                verofy_ip_address = excluded.verofy_ip_address,
                verofy_terminal_id = excluded.verofy_terminal_id,
                pairing_code = excluded.pairing_code
        """, (ip, terminal_id, code))
        conn.commit()
    finally:
        conn.close()

def get_verofy_credentials():
    conn, cursor = get_database_connection()
    try:
        cursor.execute("SELECT verofy_ip_address, verofy_terminal_id FROM verofy_setting LIMIT 1")
        
        result = cursor.fetchone()
        
        if result:
            # Return a tuple of (ip, terminal_id)
            return result[0], result[1]  # (verofy_ip_address, verofy_terminal_id)
        else:
            return None, None

    except Exception as e:
        print("Error fetching credentials:", e)
        return None, None
    finally:
        conn.close()

def delete_verofy_terminal(tid):
    conn, cursor = get_database_connection()
    try:
        cursor.execute('DELETE FROM verofy_setting WHERE verofy_terminal_id = ?', (tid,))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'error': 'Terminal not found'}), 404

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def create_viva_table():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS viva_setting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                viva_terminal_id TEXT,
                merchant_id TEXT,
                source_code TEXT,
                isv_number REAL,
                selected INTEGER DEFAULT 1
            )
        ''')
        conn.commit()
        conn.close()
        return jsonify({"message": "Viva table created successfully"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": f"Error creating viva table: {str(e)}"}), 500

def check_viva_terminal_exists(terminal_id):
    conn, cursor = get_database_connection()
    try:
        cursor.execute("SELECT 1 FROM viva_setting WHERE viva_terminal_id = ? LIMIT 1", (terminal_id,))
        result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()

def save_viva_credentials(terminal_id, merchant_id, source_code, isv_number):
    conn, cursor = get_database_connection()
    try:
        cursor.execute("""
            INSERT INTO viva_setting (viva_terminal_id, merchant_id, source_code, isv_number)
            VALUES (?, ?, ?, ?)
        """, (terminal_id, merchant_id, source_code, isv_number))
        conn.commit()
    finally:
        conn.close()

def get_viva_credentials(selected=False):
    conn, cursor = get_database_connection()
    try:
        if selected:
            cursor.execute("SELECT * FROM viva_setting WHERE selected = 1 LIMIT 1")
            result = cursor.fetchone()  # Fetch a single row
        else:
            cursor.execute("SELECT * FROM viva_setting")
            result = cursor.fetchall()  # Fetch all rows

        return result
    except Exception as e:
        print("Error fetching credentials:", e)
        return None
    finally:
        conn.close()

def end_day_carts():
    conn, cursor = get_database_connection()
    try:
        cursor.execute('''  
            SELECT
                c.cart_id,
                c.order_type,
                c.order_date,
                c.customer_id,
                COUNT(ci.cart_id) AS cart_item_count,
                cu.customer_name,
                CASE 
                    WHEN c.order_type = "dine" THEN (SELECT table_number FROM dining_tables d WHERE table_occupied = c.cart_id)
                    ELSE NULL
                END AS table_number,
                SUM(ci.price) AS cart_total,
                e.name
            FROM cart c
            LEFT JOIN cart_item ci ON c.cart_id = ci.cart_id
            LEFT JOIN customers cu ON c.customer_id = cu.customer_id
            LEFT JOIN employees e ON c.cart_started_by = e.employee_id
            WHERE c.cart_status = "processing"
            GROUP BY c.cart_id, c.order_type, c.order_date, c.customer_id, cu.customer_name, e.name
            ORDER BY c.order_type;
        ''')

        columns = [col[0] for col in cursor.description]  # Get column names
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]  # Convert to list of dictionaries
        for cart in results:
            if cart["order_date"]:
                cart["order_date"] = datetime.strptime(cart["order_date"], "%Y-%m-%d %H:%M:%S").strftime("%d %b, %I:%M %p")
        return jsonify(results) if results else jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# for the UI
def get_excluded_products():
    try:
        conn, cursor = get_database_connection()
        query = '''
            SELECT 
                ekp.product_id, 
                p.product_name
            FROM 
                excluded_kitchen_products ekp
            JOIN 
                products p ON ekp.product_id = p.product_id
        '''
        cursor.execute(query)
        excluded_products = cursor.fetchall()
        
        # Convert to list of dictionaries
        if excluded_products:
            excluded_products = [dict(zip(["product_id", "product_name"], row)) for row in excluded_products]
            return excluded_products
        else:
            return []
    except sqlite3.Error as e:
        print(f"Error fetching excluded products: {e}")
        return []
    finally:
        if conn:
            conn.close()

# for prints
def get_excluded_kitchen_product_ids():
    """
    Returns a set of product_ids that should be excluded from kitchen printing.
    """
    conn, cursor = get_database_connection()
    try:
        cursor.execute("SELECT product_id FROM excluded_kitchen_products")
        return set(row[0] for row in cursor.fetchall())
    finally:
        conn.close()

def sales_analytics(start_date=None, end_date=None): 
    today = datetime.now().date()
    if not start_date:
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
    if not end_date:
        end_date = today.strftime('%Y-%m-%d')

    conn, cursor = get_database_connection()
    try:
        # 1. Most Popular Products
        popular_products = cursor.execute('''
            SELECT 
                ci.product_id,
                ci.product_name,
                SUM(ci.quantity) AS total_quantity_sold,
                COUNT(DISTINCT c.cart_id) AS number_of_orders,
                SUM(ci.quantity * ci.price) AS total_revenue
            FROM 
                cart_item ci
            JOIN 
                cart c ON ci.cart_id = c.cart_id
            WHERE 
                c.cart_status = 'completed'
                AND DATE(c.order_date) BETWEEN ? AND ?
            GROUP BY 
                ci.product_id, ci.product_name
            ORDER BY 
                total_quantity_sold DESC
            LIMIT 20
        ''', (start_date, end_date)).fetchall()
        popular_products_dicts = [dict(zip([col[0] for col in cursor.description], row)) for row in popular_products]
        # 2. Revenue by Product (with discounts)
        product_revenue = cursor.execute('''
            SELECT 
                ci.product_id,
                ci.product_name,
                SUM(ci.quantity * (ci.price - 
                    CASE WHEN ci.product_discount_type = 'fixed' THEN ci.product_discount 
                         WHEN ci.product_discount_type = 'percentage' THEN ci.price * (ci.product_discount/100)
                         ELSE 0 END)) AS net_revenue
            FROM 
                cart_item ci
            JOIN 
                cart c ON ci.cart_id = c.cart_id
            WHERE 
                c.cart_status = 'completed'
                AND DATE(c.order_date) BETWEEN ? AND ?
            GROUP BY 
                ci.product_id, ci.product_name
            ORDER BY 
                net_revenue DESC
            LIMIT 20
        ''', (start_date, end_date)).fetchall()
        product_revenue_dicts = [dict(zip([col[0] for col in cursor.description], row)) for row in product_revenue]
        
        # 3. Sales Trends
        sales_trends = cursor.execute('''
            SELECT 
                DATE(c.order_date) AS sale_date,
                SUM(ci.quantity * ci.price) AS daily_revenue,
                COUNT(DISTINCT c.cart_id) AS orders_count
            FROM 
                cart c
            JOIN 
                cart_item ci ON c.cart_id = ci.cart_id
            WHERE 
                c.cart_status = 'completed'
                AND DATE(c.order_date) BETWEEN ? AND ?
            GROUP BY 
                DATE(c.order_date)
            ORDER BY 
                sale_date
        ''', (start_date, end_date)).fetchall()
        sales_trends_dicts = [dict(zip([col[0] for col in cursor.description], row)) for row in sales_trends]
        
        # 4. Average Order Value
        avg_order_value = cursor.execute('''
            SELECT 
                AVG(order_total) AS avg_order_value
            FROM (
                SELECT 
                    c.cart_id,
                    SUM(ci.quantity * ci.price) AS order_total
                FROM 
                    cart c
                JOIN 
                    cart_item ci ON c.cart_id = ci.cart_id
                WHERE 
                    c.cart_status = 'completed'
                    AND DATE(c.order_date) BETWEEN ? AND ?
                GROUP BY 
                    c.cart_id
            )
        ''', (start_date, end_date)).fetchone()[0] or 0
        
        # 5. Discount Usage
        discount_usage = discount_usage = cursor.execute('''
            WITH cart_summary AS (
                    SELECT 
                        c.cart_id,
                        c.cart_discount_type,
                        c.cart_discount,
                        SUM(ci.quantity * ci.price) AS cart_subtotal,
                        CASE
                            WHEN c.cart_discount_type = 'percentage' AND c.cart_discount > 0 
                            THEN ROUND(SUM(ci.quantity * ci.price) * (c.cart_discount/100.0), 2)
                            WHEN c.cart_discount_type = 'fixed' AND c.cart_discount > 0
                            THEN ROUND(c.cart_discount, 2)
                            ELSE 0
                        END AS calculated_discount
                    FROM cart c
                    JOIN cart_item ci ON c.cart_id = ci.cart_id
                    WHERE c.cart_status = 'completed'
                    AND DATE(c.order_date) BETWEEN ? AND ?
                    GROUP BY c.cart_id
                )
                SELECT 
                    cart_discount_type,
                    COUNT(DISTINCT cart_id) AS order_count,
                    AVG(calculated_discount) AS avg_discount_amount,
                    SUM(cart_subtotal) AS gross_sales,
                    SUM(calculated_discount) AS total_discounts_applied,
                    SUM(cart_subtotal - calculated_discount) AS net_sales
                FROM cart_summary
                GROUP BY cart_discount_type
                HAVING SUM(calculated_discount) > 0
                ORDER BY total_discounts_applied DESC
        ''', (start_date, end_date)).fetchall()
        discount_usage_dicts = [dict(zip([col[0] for col in cursor.description], row)) for row in discount_usage]
        
        # 6. Products Bought Together
        products_together = cursor.execute('''
            SELECT 
                a.product_id AS product1_id,
                a.product_name AS product1_name,
                b.product_id AS product2_id,
                b.product_name AS product2_name,
                COUNT(*) AS times_bought_together
            FROM 
                cart_item a
            JOIN 
                cart_item b ON a.cart_id = b.cart_id AND a.product_id < b.product_id
            JOIN 
                cart c ON a.cart_id = c.cart_id
            WHERE 
                c.cart_status = 'completed'
                AND DATE(c.order_date) BETWEEN ? AND ?
            GROUP BY 
                a.product_id, a.product_name, b.product_id, b.product_name
            ORDER BY 
                times_bought_together DESC
            LIMIT 10
        ''', (start_date, end_date)).fetchall()
        products_together_dicts = [dict(zip([col[0] for col in cursor.description], row)) for row in products_together]
        
        refunds = list(cursor.execute('''
            SELECT 
                COUNT(*) as refund_count,
                SUM(amount) as total_refunded,
                AVG(amount) as avg_refund,
                (
                    SELECT json_group_array(json_object(
                        'refund_date', timestamp,
                        'order_id', cart_id,
                        'amount', amount
                    ))
                    FROM refunds
                    ORDER BY timestamp DESC
                    LIMIT 10
                ) as details
            FROM refunds
            WHERE timestamp BETWEEN ? AND ?
        ''', (start_date, end_date)).fetchone())

        # Safely load JSON details
        refunds[3] = json.loads(refunds[3]) if refunds[3] else []
        refunds = {
            "refund_count": refunds[0],
            "total_refunded": refunds[1],
            "avg_refund": refunds[2],
            "details": refunds[3]
        }

        # Convert rows to dictionaries for JSON serialization
        result = {
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "popular_products": popular_products_dicts,
            "product_revenue": product_revenue_dicts,
            "sales_trends": sales_trends_dicts,
            "average_order_value": avg_order_value,
            "discount_usage": discount_usage_dicts,
            "products_bought_together": products_together_dicts,
            "refunds": refunds
        }

        return result
    
    except Exception as e:
        print(f"Error in sales_analytics: {str(e)}")
        return str(e)
    
    finally:
        conn.close()

def create_refunds_table():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id INTEGER,
                payment_type TEXT,
                amount DECIMAL(10, 2),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        return jsonify({"message": "refunds table created successfully"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": f"Error creating refunds table: {str(e)}"}), 500
    
def get_refunds_by_cart_id(cart_id):
    try:
        conn, cursor = get_database_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Fetch all refunds
        cursor.execute("""
            SELECT id, cart_id, payment_type, amount, timestamp
            FROM refunds
            WHERE cart_id = ?
            ORDER BY timestamp ASC
        """, (cart_id,))
        refunds = [dict(row) for row in cursor.fetchall()]

        # Total refunded amount
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total_refunded
            FROM refunds
            WHERE cart_id = ?
        """, (cart_id,))
        total_refunded = float(cursor.fetchone()["total_refunded"])

        # Total initial payment (from cart_payments)
        cursor.execute("""
            SELECT COALESCE(SUM(discounted_total), 0) AS initial_paid
            FROM cart_payments
            WHERE cart_id = ?
        """, (cart_id,))
        initial_paid = float(cursor.fetchone()["initial_paid"])

        return {
            "refunds": refunds,
            "total_refunded": total_refunded,
            "initial_paid": initial_paid
        }

    except Exception as e:
        print("Error fetching refunds or payment info:", e)
        return {
            "refunds": [],
            "total_refunded": 0.0,
            "initial_paid": 0.0
        }

    finally:
        if conn:
            conn.close()

def process_refund(cart_id, amount, payment_type):
    try:
        conn, cursor = get_database_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Insert refund
        cursor.execute("""
            INSERT INTO refunds (cart_id, payment_type, amount)
            VALUES (?, ?, ?)
        """, (cart_id, payment_type, amount))

        # Get total refunded
        cursor.execute("SELECT COALESCE(SUM(amount), 0) AS total_refunded FROM refunds WHERE cart_id = ?", (cart_id,))
        total_refunded = float(cursor.fetchone()["total_refunded"])

        # Get total initial paid
        cursor.execute("SELECT COALESCE(SUM(discounted_total), 0) AS initial_paid FROM cart_payments WHERE cart_id = ?", (cart_id,))
        initial_paid = float(cursor.fetchone()["initial_paid"])

        # Decide on new status
        if total_refunded >= initial_paid:
            new_status = 'refunded'
        elif total_refunded > 0:
            new_status = 'partial_refund'
        else:
            new_status = None  # Leave as is

        # Only update if we have a new status
        if new_status:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE cart SET cart_status = ?, cart_charge_updated = ? WHERE cart_id = ?", (new_status, now, cart_id))

        conn.commit()
        return {
            "success": True,
            "refunded": amount,
            "total_refunded": total_refunded,
            "initial_paid": initial_paid,
            "new_status": new_status
        }

    except Exception as e:
        print("Error processing refund:", e)
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            conn.close()

def update_vat_for_product(id, is_on):
    try:
        conn, cursor = get_database_connection()
        cursor.execute("UPDATE products SET vatable = ? WHERE product_id = ?",
                       (is_on, id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating vat: {e}")
        return False
    finally:
        conn.close()

def delete_viva_terminal(terminal_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute("DELETE FROM viva_setting WHERE id = ?", (terminal_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting viva terminal: {e}")
        return False
    finally:
        conn.close()

def update_order_type(cart_id, new_type):
    try:
        conn, cursor = get_database_connection()
        
        # 1. Update order type and dining tables
        cursor.execute("DELETE FROM cart_dining_tables WHERE cart_id = ?", (cart_id,))
        cursor.execute("UPDATE cart SET order_type = ? WHERE cart_id = ?", (new_type, cart_id))

        if new_type == 'dine':
            table_number = random.randint(1, 10)
            table_cover = random.randint(1, 10)
            cursor.execute("""
                INSERT INTO cart_dining_tables (cart_id, table_number, table_cover)
                VALUES (?, ?, ?)
                """, (cart_id, table_number, table_cover))
        
        # 2. Calculate VAT with options support
        vat_rate = json_utils.get_vat_rate()  # Returns 0.2 for 20%
        if vat_rate > 0:
            # Get all cart items with options
            cursor.execute("""
                SELECT 
                    ci.price, ci.quantity, ci.product_discount_type, 
                    ci.product_discount, ci.vatable, ci.options,
                    c.cart_discount_type, c.cart_discount
                FROM cart_item ci
                JOIN cart c ON ci.cart_id = c.cart_id
                WHERE ci.cart_id = ?""", (cart_id,))
            items = cursor.fetchall()
            
            cart_total = 0
            vatable_total = 0
            
            for item in items:
                base_price, base_qty, item_disc_type, item_disc, base_vatable, options_str, _, _ = item
                options = helpers.parse_options(options_str)
                
                # Calculate base item
                base_total = base_price * base_qty
                base_vat_amount = base_total if (new_type == 'dine' or base_vatable) else 0
                
                # Calculate all options
                options_total = 0
                options_vat_amount = 0
                for opt in options:
                    opt_total = opt['price'] * opt['quantity']
                    options_total += opt_total
                    if new_type == 'dine' or opt['vatable']:
                        options_vat_amount += opt_total
                
                # Combined total before discounts
                combined_total = base_total + options_total
                combined_vatable = base_vat_amount + options_vat_amount
                
                # Apply item-level discount proportionally
                if item_disc > 0:
                    combined_total = helpers.calculate_cart_discounts(item_disc, item_disc_type, combined_total)
                    if combined_total > 0:
                        discount_ratio = combined_total / (combined_total + item_disc)
                        combined_vatable *= discount_ratio
                
                # Add to totals
                cart_total += combined_total
                vatable_total += combined_vatable
            
            # Apply cart discount proportionally
            if items and items[0][7] > 0:  # cart_discount > 0
                cart_disc_type = items[0][6]
                cart_disc = items[0][7]
                cart_total = helpers.calculate_cart_discounts(cart_disc, cart_disc_type, cart_total)
                if cart_total > 0:
                    vatable_total *= (cart_total / (cart_total + cart_disc))
            
            # Determine VAT base and update
            vat_base = cart_total if new_type == 'dine' else vatable_total
            vat_amount = round(vat_base * vat_rate, 2)
            cursor.execute("UPDATE cart SET vat_amount = ? WHERE cart_id = ?", (vat_amount, cart_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error in update_order_type: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def create_delivery_rules_table():
    try:
        conn, cursor = get_database_connection()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS delivery_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_group INTEGER,              -- optional: groups related rules together
                rule_type TEXT NOT NULL,         -- 'base', 'per_mile', 'discount_amount', 'discount_percent'
                base_price REAL,                 -- for 'base' rule
                x_amount REAL,                   -- used as price per chunk or discount value
                y_mile REAL,                     -- distance chunk size for 'per_mile' (e.g., per 2 miles)
                min_order_total REAL,           -- threshold for applying discount
                discount_value REAL,            -- discount amount or percentage
                max_distance REAL,              -- max distance this rule applies to (optional)
                active INTEGER DEFAULT 1        -- 1 = active, 0 = inactive
            );
        ''')
        conn.commit()
        conn.close()
        return jsonify({"message": "Delivery rules table created successfully"}), 200
    except sqlite3.Error as e:
        return jsonify({"error": f"Error creating delivery rules table: {str(e)}"}), 500
    
def get_delivery_rules():
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT * FROM delivery_rules ORDER BY id ASC")
        rules = cursor.fetchall()
        
        # Convert to list of dictionaries
        if rules:
            rules = [dict(zip([desc[0] for desc in cursor.description], row)) for row in rules]
            return rules
        else:
            return []
    except sqlite3.Error as e:
        print(f"Error fetching delivery rules: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_active_delivery_rules():
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT * FROM delivery_rules WHERE active = 1")
        rows = cursor.fetchall()

        if not rows:
            return []

        col_names = [desc[0] for desc in cursor.description]
        rules = []
        for row in rows:
            rule = dict(zip(col_names, row))

            # Ensure numeric fields are not None and have default values
            rule['base_price'] = float(rule['base_price'] or 0)
            rule['x_amount'] = float(rule['x_amount'] or 0)
            rule['y_mile'] = float(rule['y_mile'] or 1)  # prevent division by zero
            rule['min_order_total'] = float(rule['min_order_total'] or 0)
            rule['discount_value'] = float(rule['discount_value'] or 0)
            rule['max_distance'] = float(rule['max_distance']) if rule['max_distance'] is not None else None

            rules.append(rule)

        return rules

    except Exception as e:
        print(f"Error fetching delivery rules: {e}")
        return []

def add_delivery_rule(rule):
    try:
        conn, cursor = get_database_connection()
        rule_group = rule.get('rule_group', 0)
        max_distance = rule.get('max_distance', 0)
        base_price = rule.get('base_price', 0)
        x_amount = rule.get('x_amount', 0)
        y_mile = rule.get('y_mile', 0)
        min_order_total = rule.get('min_order_total', 0)
        discount_value = rule.get('discount_value', 0)
        max_distance = rule.get('max_distance', 0)
        cursor.execute('''
            INSERT INTO delivery_rules (rule_group, rule_type, base_price, x_amount, y_mile, min_order_total, discount_value, max_distance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (rule_group, rule['rule_type'], base_price, x_amount, y_mile, min_order_total, discount_value, max_distance))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error adding delivery rule: {e}")
        return False
    finally:
        if conn:
            conn.close()

def delete_delivery_rule(rule_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute("DELETE FROM delivery_rules WHERE id = ?", (rule_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting delivery rule: {e}")
        return False
    finally:
        if conn:
            conn.close()

def toggle_delivery_rule_status(rule_id, active):
    """Toggle the active status of a delivery rule"""
    try:
        conn, cursor = get_database_connection()
        cursor.execute("UPDATE delivery_rules SET active = ? WHERE id = ?", (active, rule_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error toggling delivery rule status: {e}")
        return False
    finally:
        if conn:
            conn.close()

# new option groups management functions

def save_option_group(data):
    """Save a new option group to the database"""
    try:
        group_name = data.get('group_name', '').strip()
        group_description = data.get('group_description', '').strip()
        options = data.get('options', [])
        conn, cursor = get_database_connection()
        # Insert group
        cursor.execute(
            "INSERT INTO option_groups (group_name, group_description) VALUES (?, ?)",
            (group_name, group_description)
        )
        group_id = cursor.lastrowid

        # Insert group items
        for opt in options:
            option_id = int(opt['option_id'])
            option_item_max = int(opt.get('option_item_max', 1))
            option_order = int(opt.get('option_order', 0))

            cursor.execute("""
                INSERT INTO option_group_items (group_id, option_id, option_item_max, option_order)
                VALUES (?, ?, ?, ?)
            """, (group_id, option_id, option_item_max, option_order))

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error saving option group: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_option_groups():
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT group_id, group_name, group_description FROM option_groups ORDER BY group_id DESC")
        groups = [
            {
                "group_id": row[0],
                "group_name": row[1],
                "group_description": row[2] or ""
            }
            for row in cursor.fetchall()
        ]
        return groups
    except sqlite3.Error as e:
        print(f"Error fetching option groups: {e}")
        return []
    finally:
        if conn:
            conn.close()

def delete_options_group(group_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute("DELETE FROM option_group_items WHERE group_id = ?", (group_id,))
        cursor.execute("DELETE FROM option_groups WHERE group_id = ?", (group_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting option group: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_options_group_details(group_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT group_name, group_description FROM option_groups WHERE group_id = ?", (group_id,))
        group = cursor.fetchone()
        if not group:
            return jsonify({"success": False, "message": "Group not found"}), 404

        # Get group's option items
        cursor.execute("""
            SELECT ogi.option_id, o.option_name, o.option_type, ogi.option_item_max, ogi.option_order
            FROM option_group_items ogi
            JOIN options o ON ogi.option_id = o.option_id
            WHERE ogi.group_id = ?
            ORDER BY ogi.option_order ASC
        """, (group_id,))
        options = [
            {
                "option_id": row[0],
                "option_name": row[1],
                "option_type": row[2],
                "option_item_max": row[3],
                "option_order": row[4]
            }
            for row in cursor.fetchall()
        ]

        return jsonify({
            "success": True,
            "group_id": group_id,
            "group_name": group[0],
            "group_description": group[1],
            "options": options
        })
    except Exception as e:
        print("Error loading group details:", e)
        return jsonify({"success": False, "message": "Server error"}), 500
    finally:
        if conn:
            conn.close()

def bulk_apply_save_group_options(data):
    try:
        group_id = data.get('group_id')
        product_ids = data.get('product_ids', [])
        options = data.get('options', [])

        if not group_id or not product_ids or not options:
            return jsonify({"success": False, "message": "Missing data"}), 400

        conn, cursor = get_database_connection()

        for product_id in product_ids:
            # Clear existing options for the product
            cursor.execute("DELETE FROM product_options WHERE product_id = ?", (product_id,))

            for opt in options:
                option_id = int(opt['option_id'])
                option_item_max = int(opt['option_item_max'])
                option_order = int(opt['option_order'])

                cursor.execute("""
                    INSERT INTO product_options (product_id, option_id, option_item_max, option_order)
                    VALUES (?, ?, ?, ?)
                """, (product_id, option_id, option_item_max, option_order))

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error applying group to products: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_options_data(option_ids, menu_index, product_id):
    price_column = 'option_item_in_price' if menu_index == 0 else 'option_item_out_price'
    conn, cursor = get_database_connection()

    option_groups = []

    for opt_id in option_ids:
        # Fetch group details including product-specific order
        cursor.execute("""
            SELECT 
                o.option_id,
                o.option_name,
                o.option_order,
                o.option_type,
                po.option_item_max,
                po.option_order
            FROM options o
            LEFT JOIN product_options po ON o.option_id = po.option_id AND po.product_id = ?
            WHERE o.option_id = ?
        """, (product_id, opt_id))
        row = cursor.fetchone()

        if not row:
            continue

        cursor.execute(f"""
            SELECT 
                oi.option_item_id,
                oi.option_item_name,
                g.{price_column} AS price,
                g.vatable,
                g.option_item_colour
            FROM option_item_groups g
            JOIN option_items oi ON oi.option_item_id = g.option_item_id
            WHERE g.option_id = ?
            AND g.is_hidden = 0
            ORDER BY g.option_item_group_order, oi.option_item_name ASC
        """, (opt_id,))
        item_rows = cursor.fetchall()

        items = []
        for row_item in item_rows:
            items.append({
                'option_item_id': row_item[0],
                'option_item_name': row_item[1],
                'price': row_item[2],
                'vatable': row_item[3],
                'option_item_colour': row_item[4]
            })

        option_groups.append({
            'option_id': row[0],
            'option_name': row[1],
            'option_order': row[2],
            'option_type': row[3],
            'option_item_max': row[4],
            'order_field': row[5],
            'items': items
        })

    # NO SORTING — return in exact order given
    return option_groups

def get_all_options():
    try:
        conn, cursor = get_database_connection()        
        cursor.execute('''SELECT
            option_id, option_name
        FROM
            options
        ORDER BY
            option_order ASC''')
        options = cursor.fetchall()
        if options:
            options_list = [{'option_id': row[0], 'option_name': row[1]} for row in options]
            return options_list
        else:
            return []
    except Exception as e:
        return [{'error': str(e)}]
    
def update_option_items(data):
    try:
        conn, cursor = get_database_connection()
        items = data.get("items", [])
        option_id = data.get("option_id")

        for item in items:
            cursor.execute(
                """
                UPDATE option_item_groups
                SET option_item_in_price = ?, option_item_out_price = ?, vatable = ?
                WHERE option_id = ? AND option_item_id = ?
                """,
                (
                    item["in_price"],
                    item["out_price"],
                    item["vatable"],
                    option_id,
                    item["option_item_id"]
                )
            )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error updating option items: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def add_caller_id(caller_id, line, time_stamp):
    try:
        conn, cursor = get_database_connection()        
        cursor.execute("""
                INSERT INTO caller_log (caller_id, line, timestamp)
                VALUES (?, ?, ?)
            """, (caller_id, line, time_stamp))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error saving option group: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_address_by_caller_id(phone_number):
    try:
        conn, cursor = get_database_connection()

        query = """
            SELECT 
                a.address_id, a.address, a.postcode, a.distance,
                c.customer_id, c.customer_name, c.customer_telephone
            FROM customers c
            LEFT JOIN customer_addresses a ON c.customer_id = a.customer_id
            WHERE c.customer_telephone = ?
        """
        cursor.execute(query, (phone_number,))
        rows = cursor.fetchall()

        # Convert to list of dicts using cursor.description
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]

        return results

    except sqlite3.Error as e:
        print(f"Error getting caller data: {e}")
        return []

    finally:
        if conn:
            conn.close()

def get_customer_name_by_number(phone_number):
    try:
        conn, cursor = get_database_connection()

        query = """
            SELECT customer_name
            FROM customers
            WHERE customer_telephone = ?
            LIMIT 1
        """
        cursor.execute(query, (phone_number,))
        row = cursor.fetchone()

        if row:
            return row[0]  # customer_name
        return None

    except sqlite3.Error as e:
        print(f"Error getting customer name: {e}")
        return None

    finally:
        if conn:
            conn.close()

def update_products_order_colour(data):
    if not data or 'products' not in data or 'category_id' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    category_id = data['category_id']
    products = data['products']  # List of dicts: [{product_id, color}, ...]

    conn = None
    try:
        conn, cursor = get_database_connection()

        # Begin transaction explicitly
        conn.execute('BEGIN')

        for order_index, product in enumerate(products):
            product_id = int(product['product_id'])
            color = product.get('color', '') or None  # Treat empty string as NULL

            cursor.execute(
                '''
                UPDATE products
                SET product_order = ?, product_colour = ?
                WHERE product_id = ? AND category_id = ?
                ''',
                (order_index, color, product_id, category_id)
            )

        conn.commit()
        return jsonify({'success': True}), 200

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        print(f"SQLite error: {e}")
        return jsonify({'error': 'Database error occurred'}), 500

    finally:
        if conn:
            conn.close()

def update_options_order_colour(data):
    option_id = data.get('option_id')
    options = data.get('options', [])

    if not option_id or not isinstance(options, list):
        return jsonify({'error': 'Invalid input'}), 400

    try:
        conn, cursor = get_database_connection()

        for order_index, item in enumerate(options):
            option_item_id = item.get('option_item_id')
            color = item.get('color', '')

            cursor.execute("""
                UPDATE option_item_groups
                SET option_item_group_order = ?, option_item_colour = ?
                WHERE option_id = ? AND option_item_id = ?
            """, (order_index, color, option_id, option_item_id))

        conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        print('Error:', e)
        return jsonify({'error': 'Failed to update options'}), 500

    finally:
        if conn:
            conn.close()

def add_excluded_product(data):
    try:
        product_ids = data.get('product_ids', [])
        
        if not product_ids:
            return jsonify({'success': False, 'message': 'No product IDs provided', 'count': 0})
        conn, cursor = get_database_connection()
 
        values = [(pid,) for pid in product_ids]
        
        # Use INSERT OR IGNORE to avoid duplicate errors
        cursor.executemany(
            "INSERT OR IGNORE INTO excluded_kitchen_products (product_id) VALUES (?)",
            values
        )
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully excluded {count} products',
            'count': count
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return jsonify({
            'success': False,
            'message': f'Error excluding products: {str(e)}',
            'count': 0
        }), 500
    finally:
        if conn:
            conn.close()

def remove_excluded_product(product_id):
    try:
        conn, cursor = get_database_connection()
        cursor.execute(
            "DELETE FROM excluded_kitchen_products WHERE product_id = ?",
            (product_id,)
        )
        conn.commit()
        conn.close()
        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Product not found in exclusions'}), 404
        return jsonify({'success': True, 'message': 'Product removed from exclusions'})
    except sqlite3.Error as e:
        print(f"Error removing excluded product: {e}")
        return jsonify({'success': False, 'message': 'Error removing excluded product'}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'success': False, 'message': 'Unexpected error occurred'}), 500
    finally:
        if conn:
            conn.close()

def remove_all_excluded_products():
    try:
        conn, cursor = get_database_connection()
        cursor.execute("DELETE FROM excluded_kitchen_products")
        conn.commit()
        return jsonify({'success': True, 'message': 'All products removed from exclusions'})
    except sqlite3.Error as e:
        print(f"Error removing all excluded products: {e}")
        return jsonify({'success': False, 'message': 'Error removing all excluded products'}), 500
    finally:
        if conn:
            conn.close()

def get_menus():
    conn = None
    try:
        conn, cursor = get_database_connection()
        cursor.execute("SELECT id, name, slug, menu_colour FROM menus ORDER BY sort, name")
        rows = cursor.fetchall()
        return [
            {"id": r[0], "name": r[1], "slug": r[2], "menu_colour": r[3]}
            for r in rows
        ]
    except sqlite3.Error as e:
        print(f"Error fetching menus: {e}")
        return []
    finally:
        if conn:
            conn.close()

def attach_menu_slugs_to_categories(categories):
    """
    Adds 'menu_slugs' to each category (e.g., ['lunch','dinner']).
    Safe if menus/menu_categories are empty: leaves 'menu_slugs' as [].
    """
    conn = None
    try:
        if not categories:
            return categories

        # ensure the field and build lookup
        by_id = {}
        for c in categories:
            c["menu_slugs"] = []
            cid = c.get("category_id")
            if cid is not None:
                by_id[cid] = c

        if not by_id:
            return categories

        conn, cursor = get_database_connection()
        cursor.execute("""
            SELECT mc.category_id, m.slug
            FROM menu_categories mc
            JOIN menus m ON m.id = mc.menu_id
            ORDER BY mc.sort, m.sort, m.name
        """)
        for cid, mslug in cursor.fetchall():
            cat = by_id.get(cid)
            if cat is not None:
                cat["menu_slugs"].append(mslug)
    
        return categories
    except sqlite3.Error as e:
        print(f"Error attaching menu slugs: {e}")
        return categories
    finally:
        if conn:
            conn.close()

def create_menu(data):
    name = (data.get('name') or '').strip()
    slug = (data.get('slug') or '').strip().lower().replace(' ', '-')
    menu_colour = (data.get('menu_colour') or None)

    if not name or not slug:
        return jsonify(error="name and slug are required"), 400

    conn, cur = get_database_connection()
    try:
        # enforce unique slug
        cur.execute("SELECT 1 FROM menus WHERE slug = ?", (slug,))
        if cur.fetchone():
            return jsonify(error="slug already exists"), 400

        cur.execute(
            "INSERT INTO menus (name, slug, menu_colour) VALUES (?, ?, ?)",
            (name, slug, menu_colour)
        )
        conn.commit()
        new_id = cur.lastrowid
        return jsonify(menu={"id": new_id, "name": name, "slug": slug, "menu_colour": menu_colour}), 200
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify(error=str(e)), 500
    finally:
        conn.close()

def update_menu(menu_id, data):
    name = (data.get('name') or '').strip()
    slug = (data.get('slug') or '').strip().lower().replace(' ', '-')
    menu_colour = (data.get('menu_colour') or None)

    if not name or not slug:
        return jsonify(error="name and slug are required"), 400

    conn, cur = get_database_connection()
    try:
        # fetch current slug
        cur.execute("SELECT slug FROM menus WHERE id = ?", (menu_id,))
        row = cur.fetchone()
        if not row:
            return jsonify(error="menu not found"), 404
        old_slug = row[0]

        # ensure slug unique (excluding self)
        cur.execute("SELECT 1 FROM menus WHERE slug = ? AND id != ?", (slug, menu_id))
        if cur.fetchone():
            return jsonify(error="slug already exists"), 400

        cur.execute("""
            UPDATE menus
               SET name = ?, slug = ?, menu_colour = ?
             WHERE id = ?
        """, (name, slug, menu_colour, menu_id))
        conn.commit()

        payload = {
            "menu": {"id": menu_id, "name": name, "slug": slug, "menu_colour": menu_colour}
        }
        if old_slug != slug:
            payload["slug_changed"] = {"old_slug": old_slug, "new_slug": slug}

        return jsonify(payload)
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify(error=str(e)), 500
    finally:
        conn.close()

def delete_menu(menu_id):
    conn, cur = get_database_connection()
    try:
        # Remove assignments first (works with or without FK cascade)
        cur.execute("DELETE FROM menu_categories WHERE menu_id = ?", (menu_id,))
        # Now delete the menu
        cur.execute("DELETE FROM menus WHERE id = ?", (menu_id,))
        if cur.rowcount == 0:
            conn.rollback()
            return jsonify(error="menu not found"), 404

        conn.commit()
        return jsonify(ok=True)
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify(error=str(e)), 500
    finally:
        conn.close()

def attach_categories_to_menu(menu_id, data):
    cat_ids = data.get('category_ids') or []
    if not isinstance(cat_ids, list) or not cat_ids:
        return jsonify(error="category_ids required"), 400

    conn, cur = get_database_connection()
    try:
        # ensure menu exists
        cur.execute("SELECT 1 FROM menus WHERE id = ?", (menu_id,))
        if not cur.fetchone():
            return jsonify(error="menu not found"), 404

        # start from next sort
        cur.execute("SELECT COALESCE(MAX(sort), -1) FROM menu_categories WHERE menu_id = ?", (menu_id,))
        next_sort = (cur.fetchone()[0] or -1) + 1

        attached = 0
        skipped = 0
        for cid in cat_ids:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO menu_categories (menu_id, category_id, sort)
                    VALUES (?, ?, ?)
                """, (menu_id, cid, next_sort))
                # rowcount is 1 if inserted, 0 if ignored (duplicate)
                if cur.rowcount == 1:
                    attached += 1
                    next_sort += 1
                else:
                    skipped += 1
            except sqlite3.IntegrityError:
                # foreign key fail or similar → treat as skipped
                skipped += 1

        conn.commit()

        # Optional: total assigned now (for UI badges if you want)
        cur.execute("SELECT COUNT(*) FROM menu_categories WHERE menu_id = ?", (menu_id,))
        total_now = cur.fetchone()[0]

        return jsonify(ok=True, attached=attached, skipped=skipped, total_assigned=total_now), 200
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify(error=str(e)), 500
    finally:
        conn.close()

def detach_categories_from_menu(menu_id, data):
    ids = data.get('category_ids') or []
    if not isinstance(ids, list) or not ids:
        return jsonify(error="category_ids required"), 400

    # ensure ints
    try:
        ids = [int(x) for x in ids]
    except (ValueError, TypeError):
        return jsonify(error="category_ids must be integers"), 400

    conn, cur = get_database_connection()
    try:
        # menu must exist
        cur.execute("SELECT 1 FROM menus WHERE id = ?", (menu_id,))
        if not cur.fetchone():
            return jsonify(error="menu not found"), 404

        # delete links
        qmarks = ",".join("?" for _ in ids)
        cur.execute(
            f"DELETE FROM menu_categories WHERE menu_id = ? AND category_id IN ({qmarks})",
            (menu_id, *ids)
        )
        removed = cur.rowcount or 0
        conn.commit()
        return jsonify(ok=True, removed=removed), 200
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify(error=str(e)), 500
    finally:
        conn.close()

def get_category_print_groups():
    """
    Get category_id -> print_group mapping for sorting items on receipts.
    Returns dict: {category_id: print_group}
    """
    try:
        conn, cursor = get_database_connection()
        cursor.execute('SELECT category_id, COALESCE(print_group, 1) FROM category')
        groups = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return groups
    except Exception as e:
        print(f"Error getting print groups: {e}")
        return {}
