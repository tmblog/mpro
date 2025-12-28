import sys

if sys.stdout is None:
    sys.stdout = open('app.log', 'a', encoding='utf-8', errors='replace')
if sys.stderr is None:
    sys.stderr = open('error.log', 'a', encoding='utf-8', errors='replace')
import os, sys
import errno
import atexit
from pathlib import Path
import psutil
if getattr(sys, 'frozen', False):
    os.environ['ESCPOS_CAPABILITIES_FILE'] = os.path.join(sys._MEIPASS, 'escpos', "capabilities.json")

from flask import Flask, render_template, render_template_string, request, jsonify, redirect, url_for, send_file
from flask_cors import CORS, cross_origin
import database, requests, json, secrets, config, helpers, webview, threading, sys, time, data_directory, wmi, urllib.parse, subprocess
from logging_utils import logger, log_error, logs_folder
from pos import pos_bp
from pos import database as posdb
from datetime import datetime
from os import path
from waitress import serve
from concurrent.futures import ThreadPoolExecutor, as_completed
from print_helpers_escpos import print_online_receipt, print_online_total
from teya_sdk_api import kill_teya_sdk

if getattr(sys, 'frozen', False):
    import pyi_splash

app = Flask(__name__)
cors = CORS(app)
# app.secret_key = secrets.token_urlsafe(32)
app.secret_key = '7NBy-MyjIzC3qzjoinS0yc_UFQkKtDOS3ZqjpR86-ao'

# Register the "pos" blueprint
app.register_blueprint(pos_bp)

data_dir = data_directory.get_data_directory()
# app.config['PERMANENT_SESSION_LIFETIME']
# print(app.config)
flask_app_running = False
printed_order_ids = []

json_file_path = os.path.join(data_dir, 'printed_order_ids.json')

try:
    if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
        with open(json_file_path, "r") as json_file:
            printed_order_ids = json.load(json_file)
    else:
        printed_order_ids = []
except json.JSONDecodeError as e:
    print(f"Error loading JSON file: {e}")
    printed_order_ids = []

if not os.path.exists(json_file_path):
    with open(json_file_path, "w") as json_file:
        json.dump([], json_file)

urlSecret = config.SECRET_KEY
urlUsername = config.USERNAME_SIM
import updater
# @app.context_processor
# def inject_data():
#     open = helpers.fetch_open_status()
#     print("I printed", open)
#     return dict(api_data=open)

@app.errorhandler(500)  # 500 is the HTTP status code for internal server error
def server_error(e):
    return render_template('offline.html'), 500

@app.template_filter('format_datetime')
def format_datetime(value):
    if not value:
        return ''
    try:
        dt = datetime.strptime(value, '%d-%m-%Y %H:%M')
        return dt.strftime('%a %d-%m-%Y @ %H:%M')
    except ValueError:
        return value

@app.route('/')
def home():
    return render_template('pos_index.html')

@app.route('/system')
def system():
    c = wmi.WMI()
    hostname = c.Win32_ComputerSystem()[0].Name
    os_info = c.Win32_OperatingSystem()[0].Caption
    processor_info = c.Win32_Processor()[0].Name
    system_type = c.Win32_ComputerSystem()[0].SystemType
    username = c.Win32_ComputerSystem()[0].UserName
    timezone = c.Win32_TimeZone()[0].Caption
    locale = c.Win32_OperatingSystem()[0].Locale
    total_physical_memory = int(c.Win32_ComputerSystem()[0].TotalPhysicalMemory)
    ram_info = f"{total_physical_memory / (1024 ** 3):.2f} GB"

    disk_info = []
    for disk in c.Win32_LogicalDisk():
        if disk.DriveType == 3:  # Only include fixed disks
            disk_size_gb = int(disk.Size) / (1024 ** 3)
            disk_free_gb = int(disk.FreeSpace) / (1024 ** 3)
            disk_info.append(f"{disk.DeviceID}: {disk_size_gb:.2f} GB total, {disk_free_gb:.2f} GB free")
    
    local_ip = helpers.get_local_ip()

    if local_ip:
        local_ip = local_ip
    else:
        local_ip = "failed to retrieve local ip"

    back_link = helpers.generate_back_link()

    return render_template('system.html', hostname=hostname, os_info=os_info,
                           processor_info=processor_info, system_type=system_type,
                           username=username, timezone=timezone, locale=locale,
                           ram_info=ram_info, disk_info=disk_info, local_ip=local_ip, back_link=back_link)

@app.route('/orders')
def online_orders():
    database.create_tables()
    if not database.any_url_exists():
        return render_template('home.html')
    else:
        #helpers.refresh_token()  # Get a list of tokens
        return render_template('orders.html')

#for first login and adding new urls
@app.route('/token')
def token():
    url = request.args.get('url')
    
    fullUrl = "https://"+url+"/app/v1/login.php"

    data = {
        'secret': urlSecret,
        'username': urlUsername
    }

    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(fullUrl, json=data, headers=headers)
       
        if response.status_code == 200:
            result = response.json()  # Parse JSON response
            jwt = result.get('jwt')    # Get jwt from parsed response
            
            if jwt:
                database.create_tables()  # Create the table if it doesn't exist
                database.insert_token(url, jwt)
                return jsonify({'success': True, 'message': 'URL added successfully'})
            else:
                result_message = 'JWT not found in the response'
        else:
            result = {'message': f'POST request failed with status code: {response.status_code}'}
            result_message = result['message']
            logger.info("Initial Token request")
            log_error(f'POST request failed with status code: {response.status_code}')
            
    except requests.exceptions.RequestException as e:
        result = {'message': f'Error: {str(e)}'}
        result_message = result['message']
        logger.info("Initial Token last exception")
        log_error(f'Error: {str(e)}')
    
    return jsonify({'message': result_message})

@app.route('/get_orders', methods=['POST'])
def get_orders():
    urls = database.get_tokens()
    if not urls:
        logger.info("No URLs available in the database")
        return jsonify({'message': 'No URLs available in the database'})

    results = []
    if len(urls) == 1:
        url, token = urls[0]
        results = fetch_orders(url, token, printed_order_ids)
    else:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_orders, url, token, printed_order_ids) for url, token in urls]
            for future in as_completed(futures):
                results.extend(future.result())

    if results:
        # Filter and sort orders
        results = sorted(
            (r for r in results if r.get('order_time')),
            key=lambda x: x['order_time'],
            reverse=True
        )
        with open(json_file_path, "w") as json_file:
            json.dump(printed_order_ids, json_file)
    else:
        helpers.delete_all_print_files()
        helpers.clear_print_id_file()

    return jsonify(results)

def process_order(order, printed_order_ids):
    """
    Processes a single order: generates a PDF if it hasn't been printed yet,
    and adds the order ID to the list of printed orders.
    
    :param order: The order data to process
    :param printed_order_ids: The list of order IDs that have already been printed
    :return: Processed order with 'url' added
    """
    order_id = order.get('order_id')
    if order_id and order_id not in printed_order_ids:
        if posdb.get_setting('print_type') == "native":
            print_online_receipt(order)
        else:
            helpers.generate_pdf(order)
        printed_order_ids.append(order_id)
    return order

def fetch_orders(url, token, printed_order_ids):
    headers_template = {'Content-Type': 'application/json'}

    while True:
        headers = {**headers_template, 'Authorization': f'Bearer {token}'}
        full_url = f"https://{url}/app/v1/orders.php"

        try:
            response = requests.post(full_url, json={}, headers=headers)
            response.raise_for_status()
            orders = response.json()

            filtered_orders = []
            for order in orders:
                order['url'] = url
                processed_order = process_order(order, printed_order_ids)
                filtered_orders.append(processed_order)

            return filtered_orders

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:  # Unauthorized error
                token_info = helpers.refresh_token()
                if token_info:
                    token = token_info[1]
                    logger.info(f"Token refreshed. Retrying...")
                    continue  # Retry with new token
                else:
                    logger.error("Token refresh failed.")
                    return [{'error': 'Token refresh failed'}]
            else:
                logger.error(f"HTTP error for {url}: {str(e)}")
                return [{'error': f'HTTP error: {str(e)}'}]

        except Exception as e:
            logger.error(f"Exception for {url}: {str(e)}")
            return [{'error': f'Error: {str(e)}'}]

@app.route('/refresh_token', methods=['GET'])
def refresh_token_route():
    token = helpers.refresh_token()  # Call the refresh_token function here
    #print(token)
    if token:
        return jsonify({'token': token})
    else:
        logger.info("Unable to refresh token")
        return jsonify({'error': 'Unable to refresh token'})

@app.route('/update_order/<id>/<status>/<orderFor>/<siteUrl>', methods=['POST'])
def update_order(id, status, orderFor, siteUrl):

    url = urllib.parse.unquote(siteUrl)
    fullUrl = "https://"+url+"/app/v1/update.php"
    
    data = {
        "id": id,
        "status": status,
        "orderFor": orderFor
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(fullUrl, json=data, headers=headers)
        
        if response.status_code == 200:
            return jsonify({"message": "Order updated successfully"})
        else:
            return jsonify({"message": f"Failed to update order. Status code: {response.status_code}"})
    except requests.exceptions.RequestException as e:
        logger.info("Update orders exception")
        log_error(f'Error: {str(e)}')
        return jsonify({"message": f"Error: {str(e)}"})

@app.route('/acknowledge_cancel/<id>/<path:siteUrl>', methods=['POST'])
def acknowledge_cancel(id, siteUrl):
    url = urllib.parse.unquote(siteUrl)
    fullUrl = "https://"+url+"/stuart.php"
    
    data = {
        "id": id,
        "seen": True
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(fullUrl, json=data, headers=headers)
        
        if response.status_code == 200:
            return jsonify({"message": "Acknowledged successfully"})
        else:
            return jsonify({"message": f"Failed to acknowledge. Status code: {response.status_code}"})
    except requests.exceptions.RequestException as e:
        logger.info("Update orders exception")
        log_error(f'Error: {str(e)}')
        return jsonify({"message": f"Error: {str(e)}"})

@app.route('/manual_print', methods=['POST'])
def manuel_print():
    order_data = request.json
    if posdb.get_setting('print_type') == "native":
            print_online_receipt(order_data)
    else:
        helpers.generate_pdf(order_data)
    response_data = {"message": "Data received successfully"}
    return jsonify(response_data)

@app.route('/settings')
def settings():
    back_link = helpers.generate_back_link()
    return render_template('settings.html', back_link=back_link)

@app.route('/printer_settings')
def printer_settings():
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # settings_path = os.path.join(script_dir, 'printer_settings.json')
    settings_path = os.path.join(data_dir, 'printer_settings.json')
    
    with open(settings_path, 'r') as settings_file:
        printer_settings = json.load(settings_file)

    return render_template('printer-settings.html', printer_settings=printer_settings)

@app.route('/save_printer_settings', methods=['POST'])
def save_printer_settings():
    # Get form data
    paper_width = request.form.get('paper_width')
    line_height = float(request.form.get('line_height'))
    font_size = request.form.get('font_size')
    font_weight = request.form.get('font_weight')
    copies = request.form.get('copies')
    footer = request.form.get('footer_text')
    if footer is not None:
        footer = footer.replace("\r\n", "\n")
    header = request.form.get('header_text')
    if header is not None:
        header = header.replace("\r\n", "\n")
    kitchen_print = request.form.get('kitchen_print')
    reservation_print = request.form.get('reservation_print')

    # Construct settings dictionary
    settings = {
        "paper_width": paper_width,
        "paper_height": "auto",
        "margin_size": 0,
        "padding_size": 0,
        "line_height": float(line_height),
        "font_size": int(font_size),
        "font_weight": font_weight,
        "copies": int(copies),
        "footer_text": footer,
        "header_text": header,
        "kitchen_print": kitchen_print,
        "reservation_print": reservation_print
    }

    # Save settings to JSON file
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # settings_path = os.path.join(script_dir, 'printer_settings.json')
    settings_path = os.path.join(data_dir, 'printer_settings.json')
    
    with open(settings_path, 'w') as settings_file:
        json.dump(settings, settings_file, indent=4)

    return redirect(url_for('printer_settings'))

@app.route('/get_totals')
def get_totals():
    urls = database.get_tokens() or []   # Expecting [(url, token), ...]
    if not urls:
        return render_template('home.html')

    def call_one(url, token):
        # allow either raw host or full https URL in DB
        full_url = url if url.startswith('http') else f"https://{url}/app/v1/daily.php"
        if not url.startswith('http'):
            full_url = f"https://{url}/app/v1/daily.php"

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        try:
            r = requests.post(full_url, json={}, headers=headers, timeout=10)
            if r.ok:
                return {'url': url, 'ok': True, 'data': r.json(), 'status': r.status_code}
            else:
                # try to surface JSON error if provided
                try:
                    err = r.json()
                except Exception:
                    err = {'message': r.text}
                return {'url': url, 'ok': False, 'error': err, 'status': r.status_code}
        except requests.exceptions.RequestException as e:
            logger.info("Get totals exception")
            log_error(f'Error: {str(e)}')
            return {'url': url, 'ok': False, 'error': {'message': str(e)}, 'status': None}

    results = [call_one(u, t) for (u, t) in urls]

    back_link = helpers.generate_back_link()

    # If there’s exactly one URL and it succeeded, keep your existing template
    ok = [r for r in results if r['ok']]
    if len(results) == 1 and ok:
        return render_template('count.html',
                               result=ok[0]['data'],
                               url=ok[0]['url'],
                               back_link=back_link)

    # Otherwise render a multi-source page
    return render_template('count_multi.html', results=results, back_link=back_link)

@app.route("/print_total", methods=["POST"])
def print_total():
    data = request.get_json(silent=True) or {}

    payload = data.get("result") or data.get("results")
    if payload is None:
        return jsonify({"error": "Missing 'result' (or 'results') in request body"}), 400

    # If the client sent a JSON *string*, parse it
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            return jsonify({"error": "Invalid JSON in result(s)", "detail": str(e)}), 400

    # We expect a list of dict rows like your template iterates over
    if not isinstance(payload, (list, tuple)):
        return jsonify({"error": "result(s) must be a list"}), 400

    if posdb.get_setting('print_type') == "native":
        print_online_total(payload)          # pass parsed list
    else:
        # If your PDF helper expects a string, dump it; if it already handles lists, pass as-is
        helpers.generate_pdf(json.dumps(payload))

    return jsonify({"message": "Print request received"})

@app.route('/display_urls')
def display_urls():
    urls_data = database.get_urls()
    back_link = helpers.generate_back_link()
    return render_template('urls.html', urls_data=urls_data, back_link=back_link)

@app.route('/delete_url', methods=['DELETE'])
def delete_url():
    url_id = request.args.get('id')
    if url_id:
        database.delete_url(url_id)
        return jsonify({'success': True, 'message': 'URL deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'URL ID not provided'})

@app.route('/expired')
def expired():
    return render_template('expired.html')

@app.route('/completed')
def completed():
    return render_template('completed.html')

@app.route('/canceled')
def canceled():
    return render_template('canceled.html')

@app.route('/quick-assist')
def quick_assist():
    try:
        # Attempt to open Quick Assist using the ms-quick-assist protocol
        result = subprocess.run(['start', 'ms-quick-assist:'], shell=True, check=True, capture_output=True)
        return"Quick Assist launched successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to launch Quick Assist. Error code: {e.returncode} Error message: {e.stderr.decode().strip()}"
    except FileNotFoundError:
        return"Quick Assist is not installed or the ms-quick-assist protocol is not recognized."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@app.route("/logs")
def get_logs():
    return send_file(
        os.path.join(logs_folder, "app.log.txt"),
        as_attachment=True  # Forces the browser to download the file
    )

def run_flask_app():
    global flask_app_running
    if not flask_app_running:
        serve(app, host='0.0.0.0', port=5000, threads=6)
        flask_app_running = True

def on_closed():
    global flask_app_running
    flask_app_running = False
    threading.Thread(target=delayed_shutdown).start()

def delayed_shutdown():
    kill_teya_sdk(force=True, timeout=5.0)
    print("Closing server...")
    time.sleep(1)
    print("Server closed.")
    os._exit(0)

def check_single_instance():
    # Get appropriate application name
    app_name = os.path.splitext(os.path.basename(sys.executable if getattr(sys, 'frozen', False) else __file__))[0]
    lock_file = Path.home() / f".{app_name}.lock"
    
    # Check for existing lock
    if lock_file.exists():
        try:
            # Read PID from existing lock file
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process still exists
            if is_process_running(pid):
                print("Another instance is already running. Exiting.")
                sys.exit(1)
            else:
                # Stale lock from crashed instance
                lock_file.unlink()
        except (ValueError, PermissionError, OSError):
            # Invalid lock file contents or permissions
            lock_file.unlink()
    
    # Create new lock file
    try:
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
    except OSError as e:
        print(f"Failed to create lock file: {e}")
        sys.exit(1)
    
    # Register cleanup
    atexit.register(cleanup_lock, lock_file)

def is_process_running(pid):
    """Check if process exists (cross-platform)"""
    try:
        if os.name == 'nt':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(1, False, pid)  # PROCESS_QUERY_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)  # Doesn't actually kill, just checks
            return True
    except:
        return False

def cleanup_lock(lock_file):
    """Remove lock file, handling potential errors"""
    try:
        lock_file.unlink(missing_ok=True)
    except Exception as e:
        print(f"Warning: Failed to remove lock file: {e}")

if __name__ == '__main__':
    #app.run(debug=True)
    #app.run(host="0.0.0.0", port=5000, debug=True)
    # #for webview next
    check_single_instance()
    helpers.reservation_prints()
    helpers.start_sync_thread(config.LICENCE_BASE_URL)
    helpers.initialize_license_system(config.LICENCE_BASE_URL)
    threading.Thread(target=run_flask_app).start()
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
    webview.settings['ALLOW_DOWNLOADS'] = True
    window = webview.create_window("Alaan", "http://127.0.0.1:5000/pos", maximized=True, resizable=False)
    window.events.closing += on_closed
    if getattr(sys, 'frozen', False):
        pyi_splash.close()

    # Check if a second screen is available
    screens = webview.screens
    if len(screens) > 1:
        second_screen = screens[1] # Get second monitor
        second_window = webview.create_window("Second Screen", "http://127.0.0.1:5000/gallery",  resizable=False, screen=second_screen, fullscreen=True)
    webview.start()
