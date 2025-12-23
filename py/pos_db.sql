CREATE TABLE attendance (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                clock_in DATETIME DEFAULT CURRENT_TIMESTAMP,
                clock_out DATETIME NULL, -- Nullable
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
CREATE TABLE caller_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caller_id TEXT NOT NULL,
                line INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
CREATE TABLE "card_terminals" (
                tid TEXT PRIMARY KEY,
                terminal_location TEXT
            , selected TEXT DEFAULT 0)
CREATE TABLE "cart" (
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
                "in_use"	INTEGER DEFAULT 0, vat_amount DECIMAL(10,2) DEFAULT 0, sync_status TEXT DEFAULT 'pending', address_id INTEGER,
                PRIMARY KEY("cart_id" AUTOINCREMENT)
            )
CREATE TABLE "cart_dining_tables" (
                order_table_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id INTEGER,
                table_number TEXT,
                table_cover INTEGER
            )
CREATE TABLE "cart_item" (
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
CREATE TABLE "cart_payments" (
                "cart_payments_id"	INTEGER,
                "cart_id"	INTEGER,
                "payment_method"	TEXT,
                "discounted_total"	DECIMAL(10, 2),
                PRIMARY KEY("cart_payments_id" AUTOINCREMENT),
                FOREIGN KEY("cart_id") REFERENCES "cart"("cart_id")
            )
CREATE TABLE "category" (
                "category_id"	INTEGER,
                "category_name"	TEXT,
                "category_order"	INTEGER DEFAULT 0,
                "category_colour"	TEXT,
                "category_text_colour"	TEXT,
                "is_hidden"	INTEGER DEFAULT 0,
                PRIMARY KEY("category_id" AUTOINCREMENT)
            )
CREATE TABLE "customer_addresses" (
                address_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT,
                address TEXT,
                postcode TEXT, distance REAL DEFAULT 0,
                FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
            )
CREATE TABLE "customers" (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                customer_telephone TEXT
            )
CREATE TABLE delivery_rules (
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
CREATE TABLE "dining_tables" (
                table_id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_number TEXT,
                table_occupied INTEGER DEFAULT 0
            )
CREATE TABLE discount_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount REAL
            )
CREATE TABLE employees (
                employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pin INTEGER UNIQUE,
                name TEXT,
                hourly_rate REAL DEFAULT 0,
                role INTEGER, 
                app_theme TEXT DEFAULT 'light'
                )
CREATE TABLE excluded_kitchen_products (
                product_id INTEGER PRIMARY KEY REFERENCES products(product_id)
            )
CREATE TABLE gallery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                image_order INTEGER DEFAULT 1,
                duration INTEGER DEFAULT 7,
                active INTEGER DEFAULT 1
            )
CREATE TABLE kitchen_orders (
                order_id INT,
                item_id INT,
                kitchen_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (order_id, item_id),
                FOREIGN KEY (order_id) REFERENCES cart(cart_id),
                FOREIGN KEY (item_id) REFERENCES cart_item(cart_item_id)
            )
CREATE TABLE menu_categories (
                menu_id     INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                sort        INTEGER DEFAULT 0 CHECK(sort >= 0),
                PRIMARY KEY (menu_id, category_id),
                FOREIGN KEY (menu_id)     REFERENCES menus(id)      ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES category(category_id) ON DELETE CASCADE
            )
CREATE TABLE menus (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            sort INTEGER DEFAULT 0 CHECK(sort >= 0),
            menu_colour TEXT
            )
CREATE TABLE option_group_items (
                group_id INTEGER,
                option_id INTEGER,
                option_item_max INTEGER DEFAULT 1,
                option_order INTEGER DEFAULT 0,
                FOREIGN KEY (group_id) REFERENCES option_groups(group_id),
                FOREIGN KEY (option_id) REFERENCES options(option_id)
            )
CREATE TABLE option_groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                group_description TEXT
            )
CREATE TABLE "option_item_groups" (
                "option_id" INTEGER,
                "option_item_id" INTEGER,
                "option_item_in_price" REAL DEFAULT 0,
                "option_item_out_price" REAL DEFAULT 0,
                "is_hidden" INTEGER DEFAULT 0,
                "vatable" INTEGER DEFAULT 0, option_item_group_order INT DEFAULT 0, option_item_colour TEXT DEFAULT '',
                PRIMARY KEY("option_id", "option_item_id"),
                FOREIGN KEY("option_id") REFERENCES "options"("option_id") ON DELETE CASCADE,
                FOREIGN KEY("option_item_id") REFERENCES "option_items"("option_item_id") ON DELETE CASCADE
            )
CREATE TABLE "option_items" (
                "option_item_id" INTEGER PRIMARY KEY AUTOINCREMENT,
                "option_item_name" TEXT,
                "vatable" INTEGER DEFAULT 0
            )
CREATE TABLE "options" (
                "option_id"	INTEGER,
                "option_name"	TEXT,
                "option_order" INTEGER DEFAULT 0,
                "option_type"	TEXT,
                "required"	INTEGER DEFAULT 0,
                "is_hidden"	INTEGER DEFAULT 0,
                PRIMARY KEY("option_id" AUTOINCREMENT)
            )
CREATE TABLE "product_modifiers" (
                modifier_id INTEGER PRIMARY KEY AUTOINCREMENT,
                modifier_name TEXT
            )
CREATE TABLE "product_options" (
                "product_id" INTEGER,
                "option_id" INTEGER,
                "is_hidden" INTEGER DEFAULT 0,
                "option_item_max" INTEGER DEFAULT 1, option_order INTEGER DEFAULT 0,
                FOREIGN KEY("option_id") REFERENCES "options"("option_id"),
                FOREIGN KEY("product_id") REFERENCES "products"("product_id")
            )
CREATE TABLE "products" (
                "product_id"	INTEGER,
                "category_id"	INTEGER,
                "product_name"	TEXT,
                "in_price"	REAL,
                "out_price"	REAL,
                "cpn"	INTEGER,
                "is_favourite"	INTEGER DEFAULT 0,
                "is_hidden"	INTEGER DEFAULT 0,
                "vatable"	INTEGER DEFAULT 0,
                "barcode"	TEXT, product_colour TEXT DEFAULT '', product_order INT DEFAULT 0, track_inventory INT DEFAULT 0, stock_quantity INT DEFAULT 0, low_stock_threshold INT DEFAULT 5,
                FOREIGN KEY("category_id") REFERENCES "category"("category_id"),
                PRIMARY KEY("product_id" AUTOINCREMENT)
            )
CREATE TABLE refunds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cart_id INTEGER,
                payment_type TEXT,
                amount DECIMAL(10, 2),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
