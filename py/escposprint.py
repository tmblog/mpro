from escpos.printer import Win32Raw, Dummy
from datetime import datetime
from pos import json_utils
from pos import database as posdb
import database
import textwrap
import traceback, re, json
import helpers
from decimal import Decimal, ROUND_CEILING

show_options_price = True  # From settings later

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

def format_mods_for_print(product_note, column_width, price_width=7):
    """
    Parse and format modifiers for receipt printing.
    New format: modifier_id|name|price|qty, modifier_id|name|price|qty, ...
    Legacy format: name|name|name
    
    Returns list of formatted lines with prices right-aligned.
    """
    if not product_note:
        return []
    
    formatted = []
    
    # Split by comma for new format
    for mod_str in product_note.split(', '):
        mod_str = mod_str.strip()
        if not mod_str:
            continue
            
        parts = mod_str.split('|')
        
        if len(parts) >= 4:
            # New format: modifier_id|name|price|qty
            name = parts[1]
            try:
                price = float(parts[2])
            except (ValueError, IndexError):
                price = 0
            try:
                qty = int(parts[3])
            except (ValueError, IndexError):
                qty = 1
            
            # Build display string
            qty_str = f"{qty}x " if qty > 1 else ""
            left_part = f"  - {qty_str}{name}"
            
            if price != 0:
                # Format price with sign
                if price > 0:
                    price_str = f"+{pound_sign}{price:.2f}"
                else:
                    price_str = f"-{pound_sign}{abs(price):.2f}"
                
                # Calculate padding for right alignment
                left_width = column_width - len(price_str)
                line = left_part.ljust(left_width) + price_str
            else:
                line = left_part
            
            formatted.append(line)
            
        elif len(parts) == 1:
            # Legacy format: just the name (split by pipe gave us individual names)
            # This handles old "spicy|no onions|well done" format
            formatted.append(f"  - {parts[0]}")
        else:
            # Partial format - try to use what we have
            name = parts[1] if len(parts) > 1 else parts[0]
            formatted.append(f"  - {name}")
    
    # If nothing parsed from comma split, try legacy pipe split
    if not formatted and '|' in product_note and ',' not in product_note:
        # Pure legacy format: name|name|name
        for name in product_note.split('|'):
            if name.strip():
                formatted.append(f"  - {name.strip()}")
    
    return formatted

def format_mods_for_kitchen(product_note):
    """
    Parse modifiers for kitchen receipt - NO prices shown.
    """
    if not product_note:
        return []
    
    formatted = []
    
    for mod_str in product_note.split(', '):
        mod_str = mod_str.strip()
        if not mod_str:
            continue
            
        parts = mod_str.split('|')
        
        if len(parts) >= 4:
            # New format: modifier_id|name|price|qty
            name = parts[1]
            try:
                qty = int(parts[3])
            except (ValueError, IndexError):
                qty = 1
            
            qty_str = f"{qty}x " if qty > 1 else ""
            formatted.append(f"  - {qty_str}{name}")
            
        elif len(parts) == 1 and parts[0].strip():
            formatted.append(f"  - {parts[0].strip()}")
    
    # Legacy fallback
    if not formatted and '|' in product_note and ',' not in product_note:
        for name in product_note.split('|'):
            if name.strip():
                formatted.append(f"  - {name.strip()}")
    
    return formatted

def format_option_line(option_name, price, qty, item_qty, show_price=True):
    """Format option line with inline price."""
    prefix = "  + "
    qty_str = f"{qty}x " if qty > 1 else ""
    
    if show_price and price != 0:
        line_total = price * qty * item_qty
        sign = "+" if line_total >= 0 else "-"
        price_str = f" ({sign}{pound_sign}{abs(line_total):.2f})"
    else:
        price_str = ""
    
    return f"{prefix}{qty_str}{option_name}{price_str}"

def format_mod_line(mod_name, price, qty, item_qty):
    """Format modifier line with inline price."""
    prefix = "  - "
    qty_str = f"{qty}x " if qty > 1 else ""
    
    if price != 0:
        line_total = price * qty * item_qty
        sign = "+" if line_total >= 0 else "-"
        price_str = f" ({sign}{pound_sign}{abs(line_total):.2f})"
    else:
        price_str = ""
    
    return f"{prefix}{qty_str}{mod_name}{price_str}"

def parse_modifiers(product_note):
    """
    Parse modifier string into list of dicts.
    Handles both new format (modifier_id|name|price|qty) and legacy format (name|name|name).
    """
    mods = []
    if not product_note:
        return mods
    
    # Try new comma-separated format first
    if ', ' in product_note or (product_note.count('|') >= 3):
        for mod_str in product_note.split(', '):
            mod_str = mod_str.strip()
            if not mod_str:
                continue
            parts = mod_str.split('|')
            if len(parts) >= 4:
                try:
                    mods.append({
                        'name': parts[1],
                        'price': float(parts[2]) if parts[2] else 0,
                        'qty': int(parts[3]) if parts[3] else 1
                    })
                except (ValueError, IndexError):
                    # Fallback - just use as name
                    mods.append({'name': mod_str, 'price': 0, 'qty': 1})
            elif len(parts) == 1 and parts[0]:
                mods.append({'name': parts[0], 'price': 0, 'qty': 1})
    else:
        # Legacy pipe-separated format: name|name|name
        for name in product_note.split('|'):
            name = name.strip()
            if name:
                mods.append({'name': name, 'price': 0, 'qty': 1})
    
    return mods

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

        column_width = escpos.get("width", 48)
        font = escpos.get("font_style", "a")
        custom_size = True
        font_width = escpos.get("font_size_width", 1)
        font_height = escpos.get("font_size_height", 1)

        # Initialize printer
        printer = Win32Raw()
        printer.open()
        
        # Arguments for kitchen receipt
        customer_dict = customer
        item_dict = items

        data = items[0].get_json()
        cart_data = data.get('cart_data')
        item_list = data.get('items')
        customer = customer.get_json()
        
        # Extract variables
        cart_id = customer['cart_id']
        cart_discount = float(cart_data.get('cart_discount', 0) or 0)
        cart_discount_type = cart_data.get('cart_discount_type')
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
                ("\nTABLE: " + str(customer.get('table_display') or customer.get('table_number', '')) + 
                 "   GUESTS: " + str(customer.get('total_covers') or customer.get('table_cover', ''))
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
            if header_text:
                header_lines = header_text.split('\n')
                # First line (store name) - bigger
                printer.set(align='center', bold=True, width=2, height=2, custom_size=True)
                printer.text(f"{header_lines[0]}\n")

                # Small gap - print empty line at smaller height
                printer.set(height=1, width=1, custom_size=True)
                printer.text("\n")
                # Rest of header - normal size
                if len(header_lines) > 1:
                    printer.set(align='center', bold=False, width=font_width, height=font_height, custom_size=custom_size)
                    printer.text('\n'.join(header_lines[1:]) + "\n")
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
        
        # ============================================
        # ITEMS - Sorted by print_group with separators
        # ============================================
        
        # Get print groups and sort items
        # ============================================
        # ITEMS - Sorted by print_group with separators
        # ============================================
        
        # Get print groups and sort items
        print_groups = posdb.get_category_print_groups()
        item_list_sorted = sorted(item_list, key=lambda x: (
            print_groups.get(x.get('category_id'), 1),
            x.get('category_order', 999),
            x.get('product_name', '')
        ))
        
        total_price = 0.0
        discountable_subtotal = 0.0
        total_items = 0
        total_item_discount = 0.0
        last_group = None

        for item in item_list_sorted:
            # --- Print group separator ---
            current_group = print_groups.get(item.get('category_id'), 1)
            
            if last_group == 0 and current_group > 0:
                printer.text("_" * column_width + "\n\n")
            elif last_group == 1 and current_group == 2:
                printer.text("_" * column_width + "\n\n")
            
            last_group = current_group
            # --- End separator logic ---
            
            product = item.get('product_name')
            quantity = int(item.get('quantity') or 0)
            base_price = float(item.get('price') or 0.0)
            product_note = item.get('product_note', '')
            item_discount_amount = float(item.get('product_discount', 0) or 0)
            item_discount_type = item.get('product_discount_type')
            options_data = item.get('options', "")

            # Base price x quantity
            item_total_price = base_price * quantity

            # --- Parse and calculate options ---
            option_lines = []
            if options_data:
                options = [option.split('|') for option in options_data.split(', ')]
                for option in options:
                    option_name = option[1] if len(option) > 1 else ''
                    try:
                        option_price = float(option[2]) if len(option) > 2 else 0
                        option_qty = int(option[4]) if len(option) > 4 else 1
                    except (IndexError, ValueError):
                        option_price = 0
                        option_qty = 1

                    total_option_price = option_price * option_qty * quantity
                    item_total_price += total_option_price

                    # Format option line with right-aligned price
                    if option_name:
                        option_lines.append(
                            format_option_line(option_name, option_price, option_qty, quantity, show_options_price)
                        )

            # --- Parse and calculate modifiers ---
            mod_lines = []
            mods = parse_modifiers(product_note)
            for mod in mods:
                mod_total = mod['price'] * mod['qty'] * quantity
                item_total_price += mod_total

                # Format modifier line with inline price
                mod_lines.append(
                    format_mod_line(mod['name'], mod['price'], mod['qty'], quantity)
                )

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
            printer.text(format_wrapped_line(quantity, product_display, discounted_price, column_width, price_width=7))

            # Print options
            for line in option_lines:
                printer.text(f"{line}\n")

            # Print modifiers
            for line in mod_lines:
                printer.text(f"{line}\n")
            
            # Add spacing after options/mods
            if option_lines or mod_lines:
                printer.text("\n")

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
            service_label = f"SERVICE ({cart_service_charge:.0f}%)"
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
            # Division hint
            table_cover = customer.get('total_covers') or customer.get('table_cover', 0)
            if (
                customer.get('order_type') == "dine"
                and division_hint
                and str(table_cover).isdigit()
                and (cover := int(table_cover)) > 2
            ):
                G = Decimal(str(grand_total))
                per = ceil_penny(G / Decimal(cover))

                lines = [f"{pound_sign}{G:.2f} / {cover} = {pound_sign}{per:.2f}"]
                for m in range(2, min(cover, 4) + 1):
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
            ("\nTABLE: " + str(customer.get('table_display') or customer.get('table_number', '')) + 
            "   GUESTS: " + str(customer.get('total_covers') or customer.get('table_cover', ''))
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

        # --- Parse options (no prices on kitchen) ---
        option_lines = []
        if options_data:
            options = [option.split('|') for option in options_data.split(', ')]
            for option in options:
                option_name = option[1] if len(option) > 1 else ''
                try:
                    option_price = float(option[2]) if len(option) > 2 else 0
                    option_qty = int(option[4]) if len(option) > 4 else 1
                except (IndexError, ValueError):
                    option_price = 0
                    option_qty = 1

                total_option_price = option_price * option_qty * quantity
                item_total_price += total_option_price

                # Kitchen: no prices, just name with qty
                if option_name:
                    qty_str = f"{option_qty}x " if option_qty > 1 else ""
                    option_lines.append(f"  + {qty_str}{option_name}")

        # --- Parse modifiers (no prices on kitchen) ---
        mod_lines = []
        mods = parse_modifiers(product_note)
        for mod in mods:
            mod_total = mod['price'] * mod['qty'] * quantity
            item_total_price += mod_total
            
            # Kitchen: no prices, just name with qty
            qty_str = f"{mod['qty']}x " if mod['qty'] > 1 else ""
            mod_lines.append(f"  - {qty_str}{mod['name']}")

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
        printer.text(format_wrapped_line(quantity, product_display, discounted_price, column_width, price_width=7))

        # Print options
        for line in option_lines:
            printer.text(f"{line}\n")

        # Print modifiers
        for line in mod_lines:
            printer.text(f"{line}\n")
        
        # Add spacing after options/mods
        if option_lines or mod_lines:
            printer.text("\n")

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
    
def get_database_connection():
    """Import here to avoid circular imports"""
    from pos import database as posdb
    return posdb.get_database_connection()

def mark_section_printed(items_to_mark):
    """Update printed quantities for items after successful print"""
    conn, cursor = get_database_connection()
    for item in items_to_mark:
        cursor.execute(
            f"UPDATE cart_item SET {item['column']} = ? WHERE cart_item_id = ?",
            (item['new_printed_qty'], item['cart_item_id'])
        )
    conn.commit()
    conn.close()

def print_section_receipt(customer, items, section='kitchen', mode='normal'):
    """
    Unified print function for kitchen or bar.
    Now includes print_group sorting and separators.
    
    section: 'kitchen' or 'bar'
    mode: 'normal', 'new_only', or 'reprint'
    
    Returns: 'printed', 'no_items', 'disabled', or 'error'
    """
    
    # Check if this section is enabled
    section_enabled = posdb.get_setting_bool(f'{section}_print', default=False)
    section_printer = posdb.get_setting_str(f'{section}_printer', default='')
    
    if not section_enabled:
        print(f"[INFO] {section.title()} printing is disabled.")
        return "disabled"
    
    if not section_printer:
        print(f"[INFO] No {section} printer configured.")
        return "disabled"

    # Get print settings
    print_settings = json_utils.get_multiple_pos_settings("escpos_printer_settings")
    escpos_settings = print_settings.get("escpos_printer_settings", [])
    escpos = escpos_settings[0] if escpos_settings else {}

    column_width = escpos.get("width", 48)
    font = escpos.get("font_style", "a")
    custom_size = True
    font_width = escpos.get("font_size_width", 1)
    font_height = escpos.get("font_size_height", 1)

    data = items[0].get_json()
    cart_data = data.get('cart_data')
    item_list = data.get('items')
    customer_data = customer.get_json()

    # Filter items based on section
    excluded_ids = posdb.get_excluded_kitchen_product_ids()
    
    if section == 'kitchen':
        section_items = [item for item in item_list if item['product_id'] not in excluded_ids]
        section_label = "KITCHEN"
    else:
        section_items = [item for item in item_list if item['product_id'] in excluded_ids]
        section_label = "BAR"

    printed_qty_column = f'{section}_printed_qty'

    # Build print list based on mode
    items_to_print = []
    items_to_mark = []

    for item in section_items:
        current_qty = int(item.get('quantity', 0))
        printed_qty = int(item.get(printed_qty_column, 0))
        unprinted_qty = current_qty - printed_qty

        if mode == 'new_only':
            if unprinted_qty > 0:
                print_item = item.copy()
                print_item['print_quantity'] = unprinted_qty
                items_to_print.append(print_item)
                items_to_mark.append({
                    'cart_item_id': item['cart_item_id'],
                    'new_printed_qty': current_qty,
                    'column': printed_qty_column
                })
        elif mode == 'reprint':
            print_item = item.copy()
            print_item['print_quantity'] = current_qty
            items_to_print.append(print_item)
        else:  # normal
            print_item = item.copy()
            print_item['print_quantity'] = current_qty
            items_to_print.append(print_item)
            items_to_mark.append({
                'cart_item_id': item['cart_item_id'],
                'new_printed_qty': current_qty,
                'column': printed_qty_column
            })

    has_previous_prints = any(int(item.get(printed_qty_column, 0)) > 0 for item in section_items)
    if not items_to_print:
        print(f"[INFO] No {section} items to print.")
        return "no_items"

    # ============================================
    # Sort by print_group
    # ============================================
    print_groups = posdb.get_category_print_groups()
    items_to_print_sorted = sorted(items_to_print, key=lambda x: (
        print_groups.get(x.get('category_id'), 1),
        x.get('category_order', 999),
        x.get('product_name', '')
    ))

    # Build customer info
    cart_id = customer_data['cart_id']
    cart_note = cart_data.get('overall_note', '')
    customer_info = f"{customer_data['customer_name']}"
    if customer_data['customer_telephone'] != "00000":
        customer_info += f"\n{customer_data['customer_telephone']}"
    
    if customer_data['order_type'] in ['dine', 'delivery']:
        customer_info += (
            ("\nTABLE: " + str(customer_data.get('table_display') or customer_data.get('table_number', '')) + 
             "   GUESTS: " + str(customer_data.get('total_covers') or customer_data.get('table_cover', ''))
             if customer_data['order_type'] == "dine" else "") +
            (("\n" + customer_data['address']) if customer_data['order_type'] == "delivery" and customer_data.get('address') else "") +
            (("\n" + customer_data['postcode']) if customer_data['order_type'] == "delivery" and customer_data.get('postcode') else "")
        )
    
    charge_updated = datetime.strptime(customer_data['charge_updated'], '%Y-%m-%d %H:%M:%S')

    try:
        if section_printer:
            printer = Win32Raw(section_printer)
        else:
            printer = Win32Raw()

        printer.set(font=font, align='center', width=font_width, height=font_height, bold=False, custom_size=custom_size)
        
        if mode == 'reprint':
            printer.text(f"** {section_label} REPRINT **\n")
        elif mode == 'new_only' and has_previous_prints:
            printer.text(f"** {section_label} ADDITION **\n")
        else:
            printer.text(f"{section_label} COPY\n")
        
        printer.text("." * column_width + "\n\n")
        
        printer.set(align='center', bold=True, font='b', height=2, width=2, custom_size=True)
        printer.text(f"{customer_data['order_type'].upper()}\n")
        printer.text("." * column_width + "\n\n")
        
        printer.set(font=font, align='center', width=font_width, height=font_height, bold=False, custom_size=custom_size)
        printer.text(f"#{cart_id}\n")
        printer.text(f"{charge_updated.strftime('%a %d %b %I:%M%p')}\n")
        printer.text("." * column_width + "\n")
        
        printer.text(f"{customer_info}\n")
        printer.text("." * column_width + "\n\n")
        
        printer.set(font=font, align='left', width=font_width, height=font_height, bold=False, custom_size=custom_size)
        
        # ============================================
        # Print items with separators
        # ============================================
        total_items = 0
        last_group = None

        for item in items_to_print_sorted:
            # --- Print group separator ---
            current_group = print_groups.get(item.get('category_id'), 1)
            
            if last_group == 0 and current_group > 0:
                printer.text("_" * column_width + "\n\n")
            elif last_group == 1 and current_group == 2:
                printer.text("_" * column_width + "\n\n")
            
            last_group = current_group
            # --- End separator logic ---

            product = item.get('product_name')
            quantity = item['print_quantity']
            product_note = item.get('product_note', '')
            options_data = item.get('options', "")

            # --- Parse options (no prices on section receipts) ---
            option_lines = []
            if options_data:
                options = [option.split('|') for option in options_data.split(', ')]
                for option in options:
                    option_name = option[1] if len(option) > 1 else ''
                    try:
                        option_qty = int(option[4]) if len(option) > 4 else 1
                    except (IndexError, ValueError):
                        option_qty = 1

                    if option_name:
                        qty_str = f"{option_qty}x " if option_qty > 1 else ""
                        option_lines.append(f"  + {qty_str}{option_name}")

            # --- Parse modifiers (no prices on section receipts) ---
            mod_lines = []
            mods = parse_modifiers(product_note)
            for mod in mods:
                qty_str = f"{mod['qty']}x " if mod['qty'] > 1 else ""
                mod_lines.append(f"  - {qty_str}{mod['name']}")

            # Print product line (no price on section receipts)
            printer.text(f"{quantity}x {product}\n")

            # Print options
            for line in option_lines:
                printer.text(f"{line}\n")

            # Print modifiers
            for line in mod_lines:
                printer.text(f"{line}\n")
            
            # Add spacing
            if option_lines or mod_lines:
                printer.text("\n")

            total_items += quantity
        
        if cart_note:
            printer.text("." * column_width + "\n")
            printer.text(f"{cart_note}\n")
        
        printer.text("." * column_width + "\n")
        printer.set(align='center', bold=True)
        printer.text(f"{total_items} ITEMS\n")
        printer.set(align='left', bold=False)
        printer.text("." * column_width + "\n")

        printer.set(align='center', font='b', width=1, height=1, bold=True, custom_size=custom_size)
        printer.text(f"Printed: {datetime.now().strftime('%d/%m/%y %I:%M%p')}\n")
        
        printer.text("\n\n")
        printer.cut()
        printer.close()

        if items_to_mark:
            mark_section_printed(items_to_mark)
            
        return "printed"
    
    except Exception as e:
        print(f"Error printing {section} receipt: {e}")
        traceback.print_exc()
        return "error"

def send_to_sections(customer, items, sections=None, mode='new_only'):
    """
    Send order to kitchen and/or bar.
    
    sections: ['kitchen'], ['bar'], ['kitchen', 'bar'], or None for both
    mode: 'normal', 'new_only', 'reprint'
    
    Returns dict of results per section
    """
    if sections is None:
        sections = ['kitchen', 'bar']
    
    results = {}
    for section in sections:
        results[section] = print_section_receipt(customer, items, section=section, mode=mode)
    
    return results
