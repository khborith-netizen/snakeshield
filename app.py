import os
import json
import time
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder=None)

try:
    from flask_cors import CORS
    CORS(app)
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ADMIN_TOKEN = "token_secret_borith_2026_xyz"

VALID_CREDENTIALS = {
    "borith99": ["sivgech99", "Sivgech#99", "123456789"],
    "borith_boss": ["sivgech99", "Sivgech#99", "123456789"],
    "admin00": ["123456789", "sivgech99", "Sivgech#99"],
    "admin": ["123456789", "sivgech99", "Sivgech#99"],
    "khborith": ["sivgech99", "Sivgech#99", "123456789"]
}

DATA_FILE = os.path.join(BASE_DIR, 'database.json')
SALES_FILE = os.path.join(BASE_DIR, 'sales.json')
EXPENSES_FILE = os.path.join(BASE_DIR, 'expenses.json')

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_json(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving: {e}")

@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/index.html')
def serve_index_file():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/admin.html')
def serve_admin():
    return send_from_directory(BASE_DIR, 'admin.html')

@app.route('/api/login', methods=['POST'])
def handle_login():
    data = request.get_json(force=True, silent=True) or {}
    username = str(data.get('username', '')).strip().lower()
    password = str(data.get('password', '')).strip()

    allowed_passwords = VALID_CREDENTIALS.get(username, [])
    if password in allowed_passwords or password == "sivgech99" or password == "123456789":
        return jsonify({"status": "success", "token": ADMIN_TOKEN}), 200
        
    return jsonify({"status": "error", "message": "ឈ្មោះគណនី ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ!"}), 401

@app.route('/api/products', methods=['GET', 'POST'])
def manage_products():
    if request.method == 'POST':
        api_key = request.headers.get('X-API-Key')
        if api_key != ADMIN_TOKEN:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        data = request.get_json(force=True, silent=True) or []
        save_json(DATA_FILE, data)
        return jsonify({"status": "success"}), 200
    return jsonify(load_json(DATA_FILE)), 200

# ==========================================
# 3. API SALES (មុខងារលក់ដុំ/រាយ & កាត់ស្តុក)
# ==========================================
@app.route('/api/sales', methods=['GET', 'POST'])
def manage_sales():
    if request.method == 'POST':
        sales = load_json(SALES_FILE)
        if not isinstance(sales, list):
            sales = []

        req_data = request.get_json(force=True, silent=True)
        if isinstance(req_data, list):
            api_key = request.headers.get('X-API-Key')
            if api_key != ADMIN_TOKEN:
                return jsonify({"status": "error", "message": "Unauthorized"}), 401
            save_json(SALES_FILE, req_data)
            return jsonify({"status": "success"}), 200

        order_data = req_data or {}
        products = load_json(DATA_FILE)
        
        revenue = 0.0
        total_cost = 0.0
        order_items = []
        stock_updated = False
        
        for item in order_data.get('items', []):
            prod = next((p for p in products if str(p.get('id')) == str(item.get('id'))), None)
            ordered_qty = int(item.get('qty', 1))
            
            if prod:
                # មុខងារថ្មី: យកតម្លៃលក់ដែលបញ្ជូនមកពី Admin (តម្លៃលក់ដុំ) បើអត់មានទើបយកតម្លៃដើមក្នុងស្តុក
                client_price = item.get('price')
                if client_price is not None and str(client_price).strip() != "":
                    price = float(client_price)
                else:
                    price = float(prod.get('price', 0))
                    
                cost = float(prod.get('costPrice', 0))
                revenue += price * ordered_qty
                total_cost += cost * ordered_qty
                
                target_sku = str(prod.get('oe', '')).strip()
                
                if ":" in target_sku:
                    bundle_parts = target_sku.split(',')
                    for part in bundle_parts:
                        if ":" in part:
                            try:
                                sku_part, qty_part = part.split(':')
                                sku_part = sku_part.strip()
                                deduct_amount = int(qty_part.strip()) * ordered_qty
                                
                                for p in products:
                                    if str(p.get('oe', '')).strip() == sku_part:
                                        p['stock'] = max(0, int(p.get('stock', 0)) - deduct_amount)
                                        stock_updated = True
                            except Exception as e:
                                print("Bundle Parse Error:", e)
                else:
                    deduct_qty_per_item = int(prod.get('deductQty', 1))
                    total_deduct = ordered_qty * deduct_qty_per_item
                    
                    if target_sku:
                        for p in products:
                            if str(p.get('oe', '')).strip() == target_sku:
                                p['stock'] = max(0, int(p.get('stock', 0)) - total_deduct)
                                stock_updated = True
                    else:
                        prod['stock'] = max(0, int(prod.get('stock', 0)) - total_deduct)
                        stock_updated = True

                order_items.append({
                    "id": prod.get('id'),
                    "name": prod.get('name'),
                    "price": price,
                    "costPrice": cost,
                    "qty": ordered_qty,
                    "thumb": prod.get('images', [''])[0] if prod.get('images') else ''
                })

        new_order = {
            "id": int(order_data.get('id', 0)) or int(time.time() * 1000),
            "date": order_data.get('date', ''),
            "phone": order_data.get('phone', 'អតិថិជនទិញផ្ទាល់'),
            "address": order_data.get('address', ''),
            "items": order_items,
            "revenue": round(revenue, 2),
            "totalCost": round(total_cost, 2),
            "profit": round(revenue - total_cost, 2)
        }
        
        sales.insert(0, new_order)
        save_json(SALES_FILE, sales)
        
        if stock_updated:
            save_json(DATA_FILE, products)
            
        return jsonify({"status": "success"}), 200

    return jsonify(load_json(SALES_FILE)), 200

@app.route('/api/expenses', methods=['GET', 'POST'])
def manage_expenses():
    if request.method == 'POST':
        api_key = request.headers.get('X-API-Key')
        if api_key != ADMIN_TOKEN:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        data = request.get_json(force=True, silent=True) or []
        save_json(EXPENSES_FILE, data)
        return jsonify({"status": "success"}), 200
    return jsonify(load_json(EXPENSES_FILE)), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)