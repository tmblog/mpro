# route from routes file responsible for adding to cart

@pos_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    item = request.get_json()
    return database.add_item_to_cart(item)

# function from database.py

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
