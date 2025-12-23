from escpos.printer import Win32Raw, Dummy
from datetime import datetime
from pos import json_utils
from pos import database as posdb
import database
import textwrap
import traceback, re, json
import helpers
from decimal import Decimal, ROUND_CEILING

pound_on = posdb.get_setting("pound_sign")
if pound_on is None:
    posdb.set_setting("pound_sign", 0)
    pound_on = 0
pound_sign = '£' if int(pound_on) else ''

def ceil_penny(val):
    return Decimal(val).quantize(Decimal('0.01'), rounding=ROUND_CEILING)


# duplcated in helpers.py
def calculate_cart_discounts(discount_amount, discount_type, amount_to_discount):
    # used for items and total price
    if amount_to_discount == 0:
        return amount_to_discount

    # Check discount type
    if discount_type == 'fixed':
        discounted_price = amount_to_discount - discount_amount
    elif discount_type == 'percentage':
        discount_percentage = (discount_amount / 100)
        discount_value = amount_to_discount * discount_percentage
        discounted_price = amount_to_discount - discount_value
    else:
        discounted_price = amount_to_discount

    return max(discounted_price, 0)

def format_wrapped_line(quantity, product, price, width, price_width=7):
    """
    Returns a string with wrapped quantity/product lines and right-aligned price on the first line.
    """
    left_width = width - price_width
    product_full = f"{quantity}x {product}"
    wrapped_lines = textwrap.wrap(product_full, width=left_width)

    result = ""
    for i, line in enumerate(wrapped_lines):
        if i == 0:
            price_str = f"{pound_sign}{price:.2f}".rjust(price_width)
            result += line.ljust(left_width) + price_str + "\n"
        else:
            result += line + "\n"
    return result

def print_block(printer, items, prefix, spacing=1):
    """
    Prints a list of items with a specified prefix and spacing between lines.
    Adds extra spacing for the last item.
    """
    for i, item in enumerate(items):
        end = "\n\n" if i == len(items) - 1 else "\n"
        printer.text(f"{prefix} {item}{end}")

# helper function to adjust column width for prices
def adjusted_width(column_width, value_str):
    """Adjust column width based on string length of a value."""
    return column_width - len(value_str)

# helper for online receipt
def format_online_receipt(order, column_width):
    items = re.sub(r'(?<!~)<br>', '\n +', order['items'])
    items = re.sub(r'~<br>', '\n\n', items)
    
    formatted_lines = []
    for line in items.split('\n'):
        # Determine indentation
        indent = ''
        if line.startswith('    '):
            indent = '    '
            line = line[4:]
        
        price_match = re.match(r'^(.*?) - (.*)$', line)
        if price_match:
            item_name = price_match.group(1)
            price = price_match.group(2)
            
            price_with_symbol = f"{pound_sign}{price}"
            price_space = len(price_with_symbol) + 1  # +1 for at least one space before price
            
            name_width = column_width - price_space
            
            wrapped_lines = textwrap.wrap(item_name, width=name_width)
            
            for i in range(len(wrapped_lines) - 1):
                formatted_lines.append(f"{indent}{wrapped_lines[i]}")
            
            last_line = wrapped_lines[-1]
            spaces_needed = column_width - len(indent) - len(last_line) - len(price_with_symbol)
            formatted_lines.append(f"{indent}{last_line}{' ' * spaces_needed}{price_with_symbol}")
        else:
            formatted_lines.append(f"{indent}{line}")
    
    items = '\n'.join(formatted_lines)

    items = re.sub(r'~', '\n', items)
    
    return items

def print_escpos_receipt(customer, items, status, tendered=None, change=None):
    try:
        print_settings = json_utils.get_multiple_pos_settings("receipt_printer_settings", "escpos_printer_settings")

        receipt_settings = print_settings.get("receipt_printer_settings", [])
        escpos_settings = print_settings.get("escpos_printer_settings", [])

        receipt = receipt_settings[0] if receipt_settings else {}
        escpos = escpos_settings[0] if escpos_settings else {}
        
        division_hint = json_utils.get_division_hint()

        header_text = receipt.get('header_text', "")
        footer_text = receipt.get('footer_text', "")

        """
        settings defaults 
        48 for font a 1,1
        48 for font a 1,2 (largest)
        32 for font b 2,1
        64 for font b 1,1 (smallest)
        """
        column_width = escpos.get("width", 48)
        font = escpos.get("font_style", "a")
        custom_size = True
        font_width = escpos.get("font_size_width", 1)
        font_height = escpos.get("font_size_height", 1)

        # Initialize printer
        printer = Win32Raw()
        # printer = Dummy()  # for testing
        printer.open()
        
        # arguments for kitchen receipt
        customer_dict = customer
        item_dict = items

        data = items[0].get_json()
        cart_data = data.get('cart_data')
        item_list = data.get('items')
        customer = customer.get_json()
        
        # Extract variables
        cart_id = customer['cart_id']
        cart_discount = float(cart_data.get('cart_discount', 0) or 0)
        cart_discount_type = cart_data.get('cart_discount_type')  # 'fixed' or 'percentage'
        cart_service_charge = float(cart_data.get('cart_service_charge', 0) or 0)
        cart_note = cart_data.get('overall_note', "")
        employee_name = customer['employee_name']
        duplicate_text = " - DUPLICATE" if status != "completed" else ""
        
        # Customer info
        customer_info = f"{customer['customer_name']}"
        if customer['customer_telephone'] != "00000":
            customer_info += f"\n{customer['customer_telephone']}"
        
        if customer['order_type'] in ['dine', 'delivery']:
            customer_info += (
                ("\nTABLE: " + str(customer['table_number']) + "   COVERS: " + str(customer['table_cover']) 
                if customer['order_type'] == "dine" else "") +
                (("\n" + customer['address']) if customer['order_type'] == "delivery" and customer['address'] else "") +
                (("\n" + customer['postcode']) if customer['order_type'] == "delivery" and customer['postcode'] else "")
            )
        
        charge_updated = datetime.strptime(customer['charge_updated'], '%Y-%m-%d %H:%M:%S')

        printer.set(font=font, align='left', width=font_width, height=font_height, bold=False, custom_size=custom_size)
        
        # --- PRINT RECEIPT ---
        
        # Header (centered)
        if status == "completed" or status == "reprint":
            printer.set(align='center')
            printer.text(f"{header_text}\n")
            printer.text("." * column_width + "\n")
        
        # Order info
        printer.set(align='center', bold=True, font='b', height=2, width=2, custom_size=True)
        printer.text(f"{customer['order_type'].upper()}\n")
        printer.text("." * column_width + "\n\n")
        printer.set(font=font, width=font_width, height=font_height, bold=False, custom_size=custom_size)
        printer.text(f"#{cart_id}{duplicate_text}\n")
        printer.text(f"{charge_updated.strftime('%a %d %b %I:%M%p')}\n")
        printer.text(f"SERVED BY: {employee_name}\n")
        printer.text("." * column_width + "\n")
        
        # Customer info
        printer.text(f"{customer_info}\n")
        printer.text("." * column_width + "\n\n")
        printer.set(align='left', bold=False)
        # Items
        total_price = 0.0                 # subtotal after per-item discounts
        discountable_subtotal = 0.0       # only items where cpn == 1/True
        total_items = 0
        total_item_discount = 0.0

        for item in item_list:
            product = item.get('product_name')
            quantity = int(item.get('quantity') or 0)
            base_price = float(item.get('price') or 0.0)
            product_note = item.get('product_note', '')
            item_discount_amount = float(item.get('product_discount', 0) or 0)
            item_discount_type = item.get('product_discount_type')
            options_data = item.get('options', "")

            # Base price x quantity
            item_total_price = base_price * quantity

            # Options
            option_lines = []
            if options_data:
                options = [option.split('|') for option in options_data.split(', ')]
                for option in options:
                    option_name = option[1]
                    try:
                        option_price = float(option[2])
                        option_qty = int(option[4])
                    except (IndexError, ValueError):
                        option_price = 0.0
                        option_qty = 1

                    total_option_price = option_price * option_qty * quantity
                    item_total_price += total_option_price

                    qty_str = f"{option_qty}x " if option_qty > 1 else ""
                    price_str = f" ({total_option_price:.2f})" if option_price > 0 else ""
                    option_lines.append(f"{qty_str}{option_name}{price_str}")

            # Per-item discount
            if item_discount_amount > 0:
                discounted_price = calculate_cart_discounts(item_discount_amount, item_discount_type, item_total_price)
                item_level_discount = item_total_price - discounted_price
                total_item_discount += item_level_discount
            else:
                discounted_price = item_total_price
                item_level_discount = 0.0

            # Print product line
            product_display = f"{product}*" if item_level_discount > 0 else product
            printer.textln(format_wrapped_line(quantity, product_display, discounted_price, column_width, price_width=7))

            # Print options
            if option_lines:
                print_block(printer, option_lines, "  +", spacing=2)

            # Print notes
            if product_note:
                notes = product_note.split("|")
                print_block(printer, notes, "  -", spacing=2)

            total_items += quantity
            total_price += discounted_price

            # Track discountable subtotal (cpn truthy)
            if item.get('cpn') in (1, '1', True):
                discountable_subtotal += discounted_price
        
        # Notes section
        if cart_note:
            printer.text("." * column_width + "\n")
            printer.text(f"{cart_note}\n")
        
        # Item count
        printer.text("." * column_width + "\n")
        printer.set(align='center', bold=True)
        printer.text(f"{total_items} ITEMS\n")
        printer.set(align='left', bold=False)
        
        # --- Totals ---
        sub_total = total_price

        # Cart-level discount ONLY on discountable_subtotal
        applied_discount = 0.0
        if cart_discount > 0:
            if cart_discount_type == "fixed":
                applied_discount = min(cart_discount, discountable_subtotal)
            elif cart_discount_type == "percentage":
                applied_discount = (discountable_subtotal * cart_discount) / 100.0

        # Subtotal after cart-level discount
        display_total_after_discount = max(0.0, sub_total - applied_discount)

        # Service AFTER discount
        if customer['order_type'] == "dine":
            service_amount = (display_total_after_discount * cart_service_charge) / 100.0
            service_label = "SERVICE CHARGE"
        else:
            service_amount = cart_service_charge
            service_label = "DELIVERY CHARGE"
        
        grand_total = round(display_total_after_discount + service_amount, 2)

        # Print totals
        printer.text("." * column_width + "\n")
        sub_total_width = adjusted_width(column_width, f"{pound_sign}{sub_total:.2f}")
        printer.text(f"SUBTOTAL:".ljust(sub_total_width) + f"{pound_sign}{sub_total:.2f}\n")

        if applied_discount > 0:
            discount_label = f"DISCOUNT ({cart_discount:.0f}%)" if cart_discount_type == 'percentage' else "DISCOUNT:"
            discount_width = adjusted_width(column_width, f"-{pound_sign}{applied_discount:.2f}")
            printer.text(discount_label.ljust(discount_width) + f"-{pound_sign}{applied_discount:.2f}\n")

        if service_amount > 0:
            service_width = adjusted_width(column_width, f"{pound_sign}{service_amount:.2f}")
            printer.text(f"{service_label}:".ljust(service_width) + f"{pound_sign}{service_amount:.2f}\n")
        
        printer.text("=" * column_width + "\n")
        printer.set(bold=True)
        grand_total_width = adjusted_width(column_width, f"{pound_sign}{grand_total:.2f}")
        printer.text(f"TOTAL:".ljust(grand_total_width) + f"{pound_sign}{grand_total:.2f}\n")
        printer.set(bold=False)
        
        # Payment info
        if status == "completed" or status == "reprint":
            printer.text("." * column_width + "\n")
            amount_tendered = posdb.get_payment_info(cart_id)
            for method, amount in amount_tendered:
                amount_width = adjusted_width(column_width, f"{pound_sign}{amount:.2f}")
                printer.text(f"{method.upper()}:".ljust(amount_width) + f"{pound_sign}{float(amount):.2f}\n")
            if tendered is not None and change is not None:
                tendered_width = adjusted_width(column_width, f"{pound_sign}{float(tendered):.2f}")
                change_width = adjusted_width(column_width, f"{pound_sign}{abs(change):.2f}")
                printer.text(f"TENDERED:".ljust(tendered_width) + f"{pound_sign}{float(tendered):.2f}\n")
                printer.text(f"CHANGE:".ljust(change_width) + f"{pound_sign}{abs(change):.2f}\n")
                helpers.open_drawer()
            printer.text("." * column_width + "\n")
        else:
            printer.set(align='center', bold=True)
            printer.text("No payment received\n\n")
            # division hint
            table_cover = customer.get('table_cover', 0)
            if (
                customer.get('order_type') == "dine"
                and division_hint
                and str(table_cover).isdigit()
                and (cover := int(table_cover)) > 2
            ):
                G = Decimal(str(grand_total))
                per = ceil_penny(G / Decimal(cover))

                lines = [f"{pound_sign}{G:.2f} / {cover} = {pound_sign}{per:.2f}"]
                for m in range(2, min(cover, 4) + 1):  # 2 up to cover, capped at 5
                    group_amt = ceil_penny(G * Decimal(m) / Decimal(cover))
                    lines.append(f"{pound_sign}{per:.2f} * {m} = {pound_sign}{group_amt:.2f}")

                printer.text("Division hint:\n")
                for line in lines:
                    printer.text(line + "\n")
                printer.text("\n\n")
        # Footer
        if status == "completed" or status == "reprint":
            printer.set(align='center')
            printer.text(f"{footer_text}\n")
        printer.set(align='center', font='b', width=1, height=1, bold=True, custom_size=custom_size)
        printer.text(f"Printed: {datetime.now().strftime('%d/%m/%y %I:%M%p')}\n")
        
        # Add space and cut
        printer.text("\n\n")
        printer.cut()
        printer.close()

        if receipt.get('kitchen_print') and status == "completed":
            print_kitchen_receipt(customer_dict, item_dict)
            
        return "printed"
    except Exception as e:
        print(f"Error printing receipt: {e}")
        traceback.print_exc()
        return "error"

def print_kitchen_receipt(customer, items):
    print_settings = json_utils.get_multiple_pos_settings("receipt_printer_settings", "escpos_printer_settings")

    receipt_settings = print_settings.get("receipt_printer_settings", [])
    escpos_settings = print_settings.get("escpos_printer_settings", [])

    receipt = receipt_settings[0] if receipt_settings else {}
    escpos = escpos_settings[0] if escpos_settings else {}

    column_width = escpos.get("width", 48)
    font = escpos.get("font_style", "a")
    custom_size = True
    font_width = escpos.get("font_size_width", 1)
    font_height = escpos.get("font_size_height", 1)

    kitchen_printer = posdb.get_setting('kitchen_printer')
    if kitchen_printer is None:
        posdb.set_setting('kitchen_printer', '')
        kitchen_printer = ''
    if kitchen_printer:
        printer = Win32Raw(kitchen_printer)
    else:
        printer = Win32Raw()

    printer.open()

    data = items[0].get_json()
    cart_data = data.get('cart_data')
    item_list = data.get('items')
    customer = customer.get_json()

    # Filter kitchen-excluded products
    excluded_ids = posdb.get_excluded_kitchen_product_ids()
    item_list = [item for item in item_list if item['product_id'] not in excluded_ids]

    if not item_list:
        print("[INFO] No kitchen items to print.")
        return

    cart_id = customer['cart_id']
    cart_note = cart_data['overall_note']
    customer_info = f"{customer['customer_name']}"
    if customer['customer_telephone'] != "00000":
        customer_info += f"\n{customer['customer_telephone']}"
    
    if customer['order_type'] in ['dine', 'delivery']:
        customer_info += (
            ("\nTABLE: " + str(customer['table_number']) + "   COVERS: " + str(customer['table_cover']) 
             if customer['order_type'] == "dine" else "") +
            (("\n" + customer['address']) if customer['order_type'] == "delivery" and customer['address'] else "") +
            (("\n" + customer['postcode']) if customer['order_type'] == "delivery" and customer['postcode'] else "")
        )
    
    charge_updated = datetime.strptime(customer['charge_updated'], '%Y-%m-%d %H:%M:%S')

    printer.set(font=font, align='center', width=font_width, height=font_height, bold=False, custom_size=custom_size)
    printer.text("KITCHEN COPY\n")
    printer.text("." * column_width + "\n\n")
    # --- PRINT RECEIPT ---
    # Order info
    printer.set(align='center', bold=True, font='b', height=2, width=2, custom_size=True)
    printer.text(f"{customer['order_type'].upper()}\n")
    printer.text("." * column_width + "\n\n")
    printer.set(font=font, align='center', width=font_width, height=font_height, bold=False, custom_size=custom_size)
    printer.text(f"#{cart_id}\n")
    printer.text(f"{charge_updated.strftime('%a %d %b %I:%M%p')}\n")
    printer.text("." * column_width + "\n")
    
    # Customer info
    printer.text(f"{customer_info}\n")
    printer.text("." * column_width + "\n\n")
    printer.set(font=font, align='left', width=font_width, height=font_height, bold=False, custom_size=custom_size)
    # Items list
    total_price = 0
    total_items = 0
    total_item_discount = 0

    for item in item_list:
        product = item.get('product_name')
        quantity = item.get('quantity')
        base_price = item.get('price')
        product_note = item.get('product_note', '')
        item_discount_amount = item.get('product_discount', 0)
        item_discount_type = item.get('product_discount_type')
        options_data = item.get('options', "")

        # Base price x quantity
        item_total_price = base_price * quantity

        # --- Handle options ---
        option_lines = []
        if options_data:
            options = [option.split('|') for option in options_data.split(', ')]
            for option in options:
                option_name = option[1]
                try:
                    option_price = float(option[2])
                    option_qty = int(option[4])
                except (IndexError, ValueError):
                    option_price = 0
                    option_qty = 1

                total_option_price = option_price * option_qty * quantity
                item_total_price += total_option_price

                qty_str = f"{option_qty}x " if option_qty > 1 else ""
                price_str = f" ({total_option_price:.2f})" if option_price > 0 else ""
                option_lines.append(f"{qty_str}{option_name}{price_str}")

        # --- Apply discount ---
        if item_discount_amount > 0:
            discounted_price = calculate_cart_discounts(item_discount_amount, item_discount_type, item_total_price)
            item_level_discount = item_total_price - discounted_price
            total_item_discount += item_level_discount
        else:
            discounted_price = item_total_price
            item_level_discount = 0

        # Print product line
        product_display = f"{product}*" if item_level_discount > 0 else product
        printer.textln(format_wrapped_line(quantity, product_display, discounted_price, column_width, price_width=7))

        # Print options
        if option_lines:
            print_block(printer, option_lines, "  +", spacing=2)

        # Print notes
        if product_note:
            notes = product_note.split("|")
            print_block(printer, notes, "  -", spacing=2)

        total_items += quantity
        total_price += discounted_price

    
    # Notes section
    if cart_note:
        printer.text("." * column_width + "\n")
        printer.text(f"{cart_note}\n")
    
    # Item count
    printer.text("." * column_width + "\n")
    printer.set(align='center', bold=True)
    printer.text(f"{total_items} ITEMS\n")
    printer.set(align='left', bold=False)
    printer.text("." * column_width + "\n")

    printer.set(align='center', font='b', width=1, height=1, bold=True, custom_size=custom_size)
    printer.text(f"Printed: {datetime.now().strftime('%d/%m/%y %I:%M%p')}\n")
    
    # Add space and cut
    printer.text("\n\n")
    printer.cut()
    printer.close()
        
    return "printed"

def print_online_receipt(order):
    try:
        print_settings = json_utils.get_multiple_pos_settings("receipt_printer_settings", "escpos_printer_settings")

        receipt_settings = print_settings.get("receipt_printer_settings", [])
        escpos_settings = print_settings.get("escpos_printer_settings", [])

        receipt = receipt_settings[0] if receipt_settings else {}
        escpos = escpos_settings[0] if escpos_settings else {}

        header_text = receipt.get('header_text', "")
        footer_text = receipt.get('footer_text', "")
        online_header_on = receipt.get('online_header', False)
        online_footer_on = receipt.get('online_footer', False)

        column_width = escpos.get("width", 48)
        font = escpos.get("font_style", "a")
        custom_size = True
        font_width = escpos.get("font_size_width", 1)
        font_height = escpos.get("font_size_height", 1)

        # Initialize printer
        printer = Win32Raw()
        printer.open()

        printer.set(font=font, align='center', width=font_width, height=font_height, bold=True, custom_size=custom_size)
        if online_header_on and header_text:
            printer.text(f"{header_text}\n")
            printer.text("." * column_width + "\n")
        printer.set(font='b', width=2, height=2, custom_size=True)

        delivery_type = (order.get("delivery_collection") or "").strip().lower()

        if delivery_type == "collection":
            printer.text("COLLECTION\n")
            printer.text("." * column_width + "\n")
        elif delivery_type == "delivery":
            printer.text("DELIVERY\n")
            printer.text("." * column_width + "\n\n")
        else:
            printer.text("DINE\n")
            printer.text("." * column_width + "\n\n")


        printer.set(font=font, align='center', width=font_width, height=font_height, bold=False, custom_size=custom_size)
        printer.text(f"#{order["order_id"]}\n")
        printer.text(f"{order["delivery_collection"].upper()}\n")
        printer.text("." * column_width + "\n")

        printer.set(align='left', bold=False)

        order_time = datetime.strptime(order['order_time'], '%Y-%m-%d %H:%M:%S')
        order_for_time = datetime.strptime(order['order_for_time'], '%Y-%m-%d %H:%M:%S')

        printer.text(f"{order_time.strftime("%a %d %b")}\n")
        printer.text(f"Placed:".ljust(column_width - 7) + f"{order_time.strftime("%I:%M%p")}\n")
        printer.text(f"Due:".ljust(column_width - 7) + f"{order_for_time.strftime("%I:%M")}\n")
        printer.text("." * column_width + "\n")

        printer.set(align='center')
        printer.text(f"{order['customer_name']}\n\n")
        printer.text(f"{order['customer_tel']}\n\n")
        if order['delivery_collection'] == "Delivery":
            printer.text(f"{order['delAdd'].replace('<br>', '\n')}\n")
        printer.text("." * column_width + "\n")

        printer.set(align='left')

        formatted_items = format_online_receipt(order, column_width)
        printer.text(formatted_items + '\n')
        printer.text("." * column_width + "\n")
        
        if order['order_note']:
            printer.text(f"Note: {order['order_note']}\n")
            printer.text("." * column_width + "\n")

        printer.set(align='center', bold=True)
        printer.text(f"{order['CNT']} ITEMS\n")
        printer.text("." * column_width + "\n")

        printer.set(align='left', bold=False)      
        delivery_value = order.get('delivery_value')
        if delivery_value and delivery_value != 'undefined' and delivery_value.replace('.', '', 1).isdigit():
            if float(delivery_value) > 0:
                delivery_width = adjusted_width(column_width, f"{pound_sign}{delivery_value}")
                printer.text(f"Delivery:".ljust(delivery_width) + f"{pound_sign}{delivery_value}\n")

        if float(order['discount_value']) > 0:
            discount_width = adjusted_width(column_width, f"-{pound_sign}{order['discount_value']}")
            printer.text(f"Discount:".ljust(discount_width) + f"-{pound_sign}{order['discount_value']}\n")

        printer.set(bold=True)
        total_width = adjusted_width(column_width, f"{pound_sign}{order['order_total']}")
        printer.text(f"Total {order['payment_method'].upper()}:".ljust(total_width) + f"{pound_sign}{order['order_total']}\n")

        printer.set(bold=False)
        printer.text("." * column_width + "\n")
        if online_footer_on and footer_text:
            printer.set(align='center')
            printer.text(f"{footer_text}\n")
            printer.text("." * column_width + "\n")
        printer.set(align='center', font='b', width=1, height=1, bold=True, custom_size=custom_size)
        printer.text(f"Printed: {datetime.now().strftime('%d/%m/%y %I:%M%p')}\n")
        printer.text("\n\n")
        printer.cut()
        printer.close()
        if receipt.get('kitchen_print'):
            print_online_kitchen_receipt(order)
        return "printed"
    except Exception as e:
        print(f"Error printing online receipt: {e}")
        traceback.print_exc()
        return "error"
    
def print_online_kitchen_receipt(order):
    try:
        print_settings = json_utils.get_multiple_pos_settings("escpos_printer_settings")
        escpos_settings = print_settings.get("escpos_printer_settings", [])
        escpos = escpos_settings[0] if escpos_settings else {}

        column_width = escpos.get("width", 48)
        font = escpos.get("font_style", "a")
        custom_size = True
        font_width = escpos.get("font_size_width", 1)
        font_height = escpos.get("font_size_height", 1)

        # Initialize printer
        kitchen_printer = posdb.get_setting('kitchen_printer')
        if kitchen_printer is None:
            posdb.set_setting('kitchen_printer', '')
            kitchen_printer = ''
        if kitchen_printer:
            printer = Win32Raw(kitchen_printer)
        else:
            printer = Win32Raw()
        printer.open()        

        printer.set(font=font, align='center', width=font_width, height=font_height, bold=True, custom_size=custom_size)
        printer.text(f"KITCHEN COPY\n")
        printer.text("." * column_width + "\n\n")
        printer.set(font='b', width=2, height=2, custom_size=True)
        delivery_type = (order.get("delivery_collection") or "").strip().lower()

        if delivery_type == "collection":
            printer.text("COLLECTION\n")
            printer.text("." * column_width + "\n")
        elif delivery_type == "delivery":
            printer.text("DELIVERY\n")
            printer.text("." * column_width + "\n\n")
        else:
            printer.text("DINE\n")
            printer.text("." * column_width + "\n\n")

        printer.set(font=font, align='center', width=font_width, height=font_height, bold=False, custom_size=custom_size)
        printer.text(f"#{order["order_id"]}\n")
        printer.text(f"{order["delivery_collection"].upper()}\n")
        printer.text("." * column_width + "\n")

        printer.set(align='left', bold=False)

        order_time = datetime.strptime(order['order_time'], '%Y-%m-%d %H:%M:%S')
        order_for_time = datetime.strptime(order['order_for_time'], '%Y-%m-%d %H:%M:%S')

        printer.text(f"{order_time.strftime("%a %d %b")}\n")
        printer.text(f"Placed:".ljust(column_width - 7) + f"{order_time.strftime("%I:%M%p")}\n")
        printer.text(f"Due:".ljust(column_width - 7) + f"{order_for_time.strftime("%I:%M")}\n")
        printer.text("." * column_width + "\n")

        printer.set(align='center')
        printer.text(f"{order['customer_name']}\n\n")
        printer.text(f"{order['customer_tel']}\n\n")
        
        if order['delivery_collection'] == "Delivery":
            printer.text(f"{order['delAdd'].replace('<br>', '\n')}\n")
        
        printer.text("." * column_width + "\n")
        formatted_items = format_online_receipt(order, column_width)
        printer.set(align='left')
        printer.text(formatted_items + '\n')
        printer.text("." * column_width + "\n")
        
        if order['order_note']:
            printer.text(f"Note: {order['order_note']}\n")
            printer.text("." * column_width + "\n")
        printer.set(align='center', bold=True)
        printer.text(f"{order['CNT']} ITEMS\n")
        printer.text("." * column_width + "\n")
        printer.set(align='center', font='b', width=1, height=1, bold=True, custom_size=custom_size)
        printer.text(f"Printed: {datetime.now().strftime('%d/%m/%y %I:%M%p')}\n")
        printer.text("\n\n")
        printer.cut()
        printer.close()
        return "printed"
    except Exception as e:
        print(f"Error printing online kitchen receipt: {e}")
        traceback.print_exc()
        return "error"
    
def print_online_total(rows):
    """
    rows: list[dict] with keys CARD, CASH, CARDTOTAL, CASHTOTAL, DELIVERY (optional)
    Aggregates exactly like your Jinja template does.
    """
    today = datetime.today()

    total_card_orders = 0
    total_cash_orders = 0
    total_card_value  = 0.0
    total_cash_value  = 0.0
    total_delivery    = 0.0

    for item in rows:
        card      = int((item.get("CARD") or 0))
        cash      = int((item.get("CASH") or 0))
        cardtotal = float((item.get("CARDTOTAL") or 0))
        cashtotal = float((item.get("CASHTOTAL") or 0))
        delivery  = float((item.get("DELIVERY") or 0))

        total_card_orders += card
        total_cash_orders += cash
        total_card_value  += cardtotal
        total_cash_value  += cashtotal
        total_delivery    += delivery

    total_orders = total_card_orders + total_cash_orders
    total_value  = total_card_value  + total_cash_value

    # If you need the business URL for the header
    try:
        res = database.get_urls()
        business_url = res[0][1]  # adjust if your schema differs
    except Exception:
        business_url = None

    try:
        print_settings = json_utils.get_multiple_pos_settings("escpos_printer_settings")
        escpos_settings = print_settings.get("escpos_printer_settings", [])
        escpos = escpos_settings[0] if escpos_settings else {}

        column_width = escpos.get("width", 48)
        font = escpos.get("font_style", "a")
        custom_size = True
        font_width = escpos.get("font_size_width", 1)
        font_height = escpos.get("font_size_height", 1)

        # Initialize printer
        printer = Win32Raw()
        printer.open()

        printer.set(font=font, align='center', width=font_width, height=font_height, bold=True, custom_size=custom_size)
        printer.text(f"DAILY TOTALS\n")
        printer.text(f"{today.strftime('%d/%m/%Y')}\n")
        printer.text(f"{business_url}\n")
        printer.text("." * column_width + "\n")
        printer.set(align='left', bold=False)

        card_trans_width = adjusted_width(column_width, f"{total_card_orders}")
        printer.text(f"CARD TRANSACTIONS:".ljust(card_trans_width) + f"{total_card_orders}\n")
        card_amount_width = adjusted_width(column_width, f"{pound_sign}{total_card_value:.2f}")
        printer.text(f"CARD TOTAL:".ljust(card_amount_width) + f"{pound_sign}{total_card_value:.2f}\n")
        cash_trans_width = adjusted_width(column_width, f"{total_cash_orders}")
        printer.text(f"CASH TRANSACTIONS:".ljust(cash_trans_width) + f"{total_cash_orders}\n")
        cash_amount_width = adjusted_width(column_width, f"{pound_sign}{total_cash_value:.2f}")
        printer.text(f"CASH TOTAL:".ljust(cash_amount_width) + f"{pound_sign}{total_cash_value:.2f}\n")
        total_orders_width = adjusted_width(column_width, f"{total_orders}")
        printer.text(f"TOTAL TRANSACTIONS:".ljust(total_orders_width) + f"{total_orders}\n")
        total_value_width = adjusted_width(column_width, f"{pound_sign}{total_value:.2f}")
        printer.text(f"GRAND TOTAL:".ljust(total_value_width) + f"{pound_sign}{total_value:.2f}\n")
        printer.text("." * column_width + "\n")
        printer.set(align='center', font='b', width=1, height=1, bold=True, custom_size=custom_size)
        printer.text(f"Printed: {datetime.now().strftime('%d/%m/%y %I:%M%p')}\n")
        printer.text("\n\n")
        printer.cut()
        printer.close()
        
    except Exception as e:
        print(f"Error printing online total: {e}")
        traceback.print_exc()
        return "error"

def print_pos_totals(totals):
    gross_total = totals.get('grand_total', 0)
    net_total = gross_total - totals.get('total_refunds', 0)
    total_orders = totals.get('total_orders', 0)
    card_total = totals.get('card_payments_total', 0)
    card_count = totals.get('card_payments_count', 0)
    cash_total = totals.get('cash_payments_total', 0)
    cash_count = totals.get('cash_payments_count', 0)
    refund_total = totals.get('total_refunds', 0)
    refund_count = totals.get('refunded_orders_count', 0)
    takeaway_count = totals.get('takeaway_count', 0)
    waiting_count = totals.get('waiting_count', 0)
    delivery_count = totals.get('delivery_count', 0)
    dine_count = totals.get('dine_count', 0)
    vat_amount = totals.get('total_vat_amount', 0)
    processing_orders_count = totals.get('processing_orders_count', 0)
    processing_orders_total = totals.get('processing_orders_total', 0)
    start_date = datetime.strptime(totals['start_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    end_date = datetime.strptime(totals['end_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    printed_date = datetime.strptime(totals['printed_at'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%d/%m/%Y %H:%M')

    try:
        print_settings = json_utils.get_multiple_pos_settings("escpos_printer_settings")
        escpos_settings = print_settings.get("escpos_printer_settings", [])
        escpos = escpos_settings[0] if escpos_settings else {}

        column_width = escpos.get("width", 48)
        font = escpos.get("font_style", "a")
        custom_size = True
        font_width = escpos.get("font_size_width", 1)
        font_height = escpos.get("font_size_height", 1)

        # Initialize printer
        printer = Win32Raw()
        printer.open()

        printer.set(font=font, align='center', width=font_width, height=font_height, bold=True, custom_size=custom_size)
        printer.text(f"SALES TOTALS REPORT\n")
        printer.set(bold=False)
        printer.text(f"{start_date} to {end_date}\n")
        printer.set(bold=True)
        printer.text("." * column_width + "\n")
        printer.text(f"SUMMARY\n")
        printer.set(align='left', bold=False)
        gross_total_width = adjusted_width(column_width, f"{pound_sign}{gross_total:.2f}")
        printer.text(f"Gross Total:".ljust(gross_total_width) + f"{pound_sign}{gross_total:.2f}\n")
        refunds_width = adjusted_width(column_width, f"-{pound_sign}{refund_total:.2f}")
        printer.text(f"Refunds:".ljust(refunds_width) + f"-{pound_sign}{refund_total:.2f}\n")
        printer.text("." * column_width + "\n")
        net_total_width = adjusted_width(column_width, f"{pound_sign}{net_total:.2f}")
        printer.text(f"Net Total:".ljust(net_total_width) + f"{pound_sign}{net_total:.2f}\n")
        total_orders_width = adjusted_width(column_width, f"{total_orders}")
        printer.text(f"Total Orders:".ljust(total_orders_width) + f"{total_orders}\n")
        total_vat_width = adjusted_width(column_width, f"{pound_sign}{vat_amount:.2f}")
        printer.text(f"Total VAT:".ljust(total_vat_width) + f"{pound_sign}{vat_amount:.2f}\n")
        printer.text("." * column_width + "\n")
        printer.set(align='center', bold=True)
        printer.text(f"PAYMENT METHODS\n")
        printer.set(align='left', bold=False)
        card_count_total_width = adjusted_width(column_width, f"{pound_sign}{card_total:.2f} ({card_count})")
        printer.text(f"Card:".ljust(card_count_total_width) + f"{pound_sign}{card_total:.2f} ({card_count})\n")
        cash_count_total_width = adjusted_width(column_width, f"{pound_sign}{cash_total:.2f} ({cash_count})")
        printer.text(f"Cash:".ljust(cash_count_total_width) + f"{pound_sign}{cash_total:.2f} ({cash_count})\n")
        refund_count_total_width = adjusted_width(column_width, f"-{pound_sign}{refund_total:.2f} ({refund_count})")
        printer.text(f"Refunds:".ljust(refund_count_total_width) + f"-{pound_sign}{refund_total:.2f} ({refund_count})\n")
        printer.text("." * column_width + "\n")
        printer.set(align='center', bold=True)
        printer.text(f"ORDER TYPES\n")
        printer.set(align='left', bold=False)
        takeaway_count_width = adjusted_width(column_width, f"{takeaway_count}")
        printer.text(f"Takeaway:".ljust(takeaway_count_width) + f"{takeaway_count}\n")
        dine_count_width = adjusted_width(column_width, f"{dine_count}")
        printer.text(f"Dine In:".ljust(dine_count_width) + f"{dine_count}\n")
        delivery_count_width = adjusted_width(column_width, f"{delivery_count}")
        printer.text(f"Delivery:".ljust(delivery_count_width) + f"{delivery_count}\n")
        waiting_count_width = adjusted_width(column_width, f"{waiting_count}")
        printer.text(f"Waiting:".ljust(waiting_count_width) + f"{waiting_count}\n")

        if processing_orders_count > 0:
            printer.text("." * column_width + "\n")
            printer.text(f"UNACCOUNTED ORDERS\n")
            printer.set(align='left', bold=False)
            processing_orders_width = adjusted_width(column_width, f"{processing_orders_count}")
            printer.text(f"Count:".ljust(processing_orders_width) + f"{processing_orders_count}\n")
            processing_total_width = adjusted_width(column_width, f"{pound_sign}{processing_orders_total:.2f}")
            printer.text(f"Total Value:".ljust(processing_total_width) + f"{pound_sign}{processing_orders_total:.2f}\n")
        
        # footer
        printer.text("." * column_width + "\n")
        printer.set(align='center', font='b', width=1, height=1, bold=True, custom_size=custom_size)
        printer.text(f"Printed: {datetime.now().strftime('%d/%m/%y %I:%M%p')}\n")
        printer.text("Generated by Eggss POS System\n")
        printer.text("\n\n")
        printer.cut()
        printer.close()
        return "printed"
    except Exception as e:
        print(f"Error printing POS totals: {e}")
        traceback.print_exc()
        return "error"
