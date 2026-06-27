from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
import os
from datetime import datetime
import urllib.parse

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Database file path
DB_FILE = 'database/data.json'
AUDIT_FILE = 'database/audit_log.json'

def load_data():
    """Load data from JSON file"""
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"items": [], "last_id": 0}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {"items": [], "last_id": 0}

def save_data(data):
    """Save data to JSON file"""
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving data: {e}")
        return False

def load_audit_log():
    """Load audit log from JSON file"""
    try:
        if os.path.exists(AUDIT_FILE):
            with open(AUDIT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"audits": [], "last_id": 0}
    except Exception as e:
        print(f"Error loading audit log: {e}")
        return {"audits": [], "last_id": 0}

def save_audit_log(data):
    """Save audit log to JSON file"""
    try:
        os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
        with open(AUDIT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving audit log: {e}")
        return False

def get_next_audit_id(data):
    """Get next available audit ID"""
    data['last_id'] = data.get('last_id', 0) + 1
    return data['last_id']

def get_next_id(data):
    """Get next available ID"""
    data['last_id'] = data.get('last_id', 0) + 1
    return data['last_id']

def calculate_priority(sales_count, stock, min_stock):
    """Calculate priority based on sales and stock"""
    if sales_count > 30:
        return "tinggi"
    elif sales_count > 15:
        return "sedang"
    else:
        return "rendah"

def check_stock_warning(items):
    """Check items that are below minimum stock"""
    warnings = []
    for item in items:
        if item['stock'] <= item['min_stock']:
            warnings.append({
                'id': item['id'],
                'name': item['name'],
                'stock': item['stock'],
                'min_stock': item['min_stock'],
                'unit': item.get('unit', 'pcs'),
                'message': f"Stok {item['name']} tersisa {item['stock']} {item.get('unit', 'pcs')} (min: {item['min_stock']} {item.get('unit', 'pcs')})"
            })
    return warnings

# Register custom template filters
@app.template_filter('sum')
def sum_filter(sequence, attribute=None):
    """Custom filter to sum values in a list"""
    if not sequence:
        return 0
    if attribute:
        return sum(item.get(attribute, 0) for item in sequence)
    return sum(sequence)

@app.template_filter('selectattr')
def selectattr_filter(sequence, attribute, value):
    """Custom filter to select items by attribute value"""
    if not sequence:
        return []
    return [item for item in sequence if item.get(attribute) == value]

@app.route('/')
def index():
    """Home page - display all items"""
    data = load_data()
    items = data.get('items', [])
    
    # Update priority for each item
    for item in items:
        item['priority'] = calculate_priority(
            item.get('sales_count', 0),
            item['stock'],
            item['min_stock']
        )
    
    # Check stock warnings
    warnings = check_stock_warning(items)
    
    # Get combo items info
    for item in items:
        if item.get('is_combo', False) and item.get('combo_items'):
            combo_names = []
            for combo_id in item['combo_items']:
                for i in items:
                    if i['id'] == combo_id:
                        combo_names.append(i['name'])
                        break
            item['combo_names'] = ', '.join(combo_names) if combo_names else '-'
        else:
            item['combo_names'] = '-'
    
    save_data(data)  # Save updated priorities
    
    # Calculate statistics for template
    total_items = len(items)
    total_stock = sum(item['stock'] for item in items)
    high_priority_count = len([item for item in items if item['priority'] == 'tinggi'])
    warning_count = len(warnings)
    
    # Get recent audits
    audit_data = load_audit_log()
    recent_audits = audit_data.get('audits', [])[-5:]  # Last 5 audits
    
    return render_template('index.html', 
                         items=items, 
                         warnings=warnings,
                         total_items=total_items,
                         total_stock=total_stock,
                         high_priority_count=high_priority_count,
                         warning_count=warning_count,
                         recent_audits=recent_audits)

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    """Add new item"""
    if request.method == 'POST':
        data = load_data()
        
        # Get form data
        name = request.form.get('name')
        category = request.form.get('category')
        stock = int(request.form.get('stock', 0))
        min_stock = int(request.form.get('min_stock', 0))
        unit = request.form.get('unit', 'pcs')
        price = float(request.form.get('price', 0))
        sales_count = int(request.form.get('sales_count', 0))
        is_combo = request.form.get('is_combo') == 'on'
        combo_items = request.form.getlist('combo_items')
        combo_items = [int(x) for x in combo_items if x]
        
        # Create new item
        new_item = {
            'id': get_next_id(data),
            'name': name,
            'category': category,
            'stock': stock,
            'min_stock': min_stock,
            'unit': unit,
            'price': price,
            'sales_count': sales_count,
            'priority': calculate_priority(sales_count, stock, min_stock),
            'is_combo': is_combo,
            'combo_items': combo_items
        }
        
        data['items'].append(new_item)
        
        if save_data(data):
            flash('Barang berhasil ditambahkan!', 'success')
        else:
            flash('Gagal menambahkan barang!', 'error')
        
        return redirect(url_for('index'))
    
    # GET request - show form
    data = load_data()
    items = data.get('items', [])
    return render_template('add_item.html', items=items)

@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    """Edit existing item"""
    data = load_data()
    items = data.get('items', [])
    
    # Find item by ID
    item_index = None
    item = None
    for i, it in enumerate(items):
        if it['id'] == item_id:
            item_index = i
            item = it
            break
    
    if not item:
        flash('Barang tidak ditemukan!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Update item data
        item['name'] = request.form.get('name')
        item['category'] = request.form.get('category')
        item['stock'] = int(request.form.get('stock', 0))
        item['min_stock'] = int(request.form.get('min_stock', 0))
        item['unit'] = request.form.get('unit', 'pcs')
        item['price'] = float(request.form.get('price', 0))
        item['sales_count'] = int(request.form.get('sales_count', 0))
        item['is_combo'] = request.form.get('is_combo') == 'on'
        item['combo_items'] = [int(x) for x in request.form.getlist('combo_items') if x]
        item['priority'] = calculate_priority(item['sales_count'], item['stock'], item['min_stock'])
        
        # Update the item in the list
        items[item_index] = item
        data['items'] = items
        
        if save_data(data):
            flash('Barang berhasil diupdate!', 'success')
        else:
            flash('Gagal mengupdate barang!', 'error')
        
        return redirect(url_for('index'))
    
    # GET request - show form
    return render_template('edit_item.html', item=item, items=items)

@app.route('/delete/<int:item_id>')
def delete_item(item_id):
    """Delete item"""
    data = load_data()
    items = data.get('items', [])
    
    # Remove item
    items = [it for it in items if it['id'] != item_id]
    data['items'] = items
    
    if save_data(data):
        flash('Barang berhasil dihapus!', 'success')
    else:
        flash('Gagal menghapus barang!', 'error')
    
    return redirect(url_for('index'))

@app.route('/audit', methods=['GET', 'POST'])
def audit():
    """Audit page - input actual stock and outgoing items"""
    data = load_data()
    items = data.get('items', [])
    audit_data = load_audit_log()
    audits = audit_data.get('audits', [])
    
    if request.method == 'POST':
        # Get audit data
        audit_items = []
        total_discrepancy = 0
        discrepancies = []
        
        for item in items:
            item_id = item['id']
            actual_stock_key = f'actual_stock_{item_id}'
            outgoing_key = f'outgoing_{item_id}'
            
            actual_stock = request.form.get(actual_stock_key)
            outgoing = request.form.get(outgoing_key)
            
            if actual_stock:
                actual_stock = int(actual_stock)
                outgoing = int(outgoing) if outgoing else 0
                
                # Calculate expected stock (system stock - outgoing)
                expected_stock = item['stock'] - outgoing
                
                # Check discrepancy
                is_discrepancy = actual_stock != expected_stock
                discrepancy_value = actual_stock - expected_stock
                
                if is_discrepancy:
                    total_discrepancy += 1
                    discrepancies.append({
                        'item_id': item_id,
                        'item_name': item['name'],
                        'system_stock': item['stock'],
                        'outgoing': outgoing,
                        'expected_stock': expected_stock,
                        'actual_stock': actual_stock,
                        'discrepancy': discrepancy_value
                    })
                
                audit_items.append({
                    'item_id': item_id,
                    'item_name': item['name'],
                    'system_stock': item['stock'],
                    'outgoing': outgoing,
                    'expected_stock': expected_stock,
                    'actual_stock': actual_stock,
                    'is_discrepancy': is_discrepancy,
                    'discrepancy_value': discrepancy_value
                })
        
        # Save audit record
        audit_record = {
            'id': get_next_audit_id(audit_data),
            'timestamp': datetime.now().isoformat(),
            'auditor': request.form.get('auditor', 'Unknown'),
            'notes': request.form.get('notes', ''),
            'items': audit_items,
            'total_items': len(audit_items),
            'total_discrepancies': total_discrepancy,
            'discrepancies': discrepancies,
            'status': 'warning' if total_discrepancy > 0 else 'ok'
        }
        
        audit_data['audits'].append(audit_record)
        save_audit_log(audit_data)
        
        # Update system stock if no discrepancies
        if total_discrepancy == 0:
            for item in items:
                outgoing_key = f'outgoing_{item["id"]}'
                outgoing = int(request.form.get(outgoing_key, 0))
                if outgoing > 0:
                    item['stock'] = item['stock'] - outgoing
                    item['priority'] = calculate_priority(
                        item.get('sales_count', 0),
                        item['stock'],
                        item['min_stock']
                    )
            save_data(data)
            flash('Audit selesai! Semua data sesuai dan stok telah diperbarui.', 'success')
        else:
            flash(f'Audit selesai! Ditemukan {total_discrepancy} ketidaksesuaian data. Silakan periksa detailnya.', 'warning')
        
        return redirect(url_for('audit_result', audit_id=audit_record['id']))
    
    # GET request - show audit form
    return render_template('audit.html', items=items)

@app.route('/audit/result/<int:audit_id>')
def audit_result(audit_id):
    """Show audit result"""
    audit_data = load_audit_log()
    audit_record = None
    
    for audit in audit_data.get('audits', []):
        if audit['id'] == audit_id:
            audit_record = audit
            break
    
    if not audit_record:
        flash('Audit tidak ditemukan!', 'error')
        return redirect(url_for('index'))
    
    return render_template('audit_result.html', audit=audit_record)

@app.route('/audit/history')
def audit_history():
    """Show audit history"""
    audit_data = load_audit_log()
    audits = audit_data.get('audits', [])
    audits.reverse()  # Show latest first
    
    return render_template('audit_history.html', audits=audits)

@app.route('/report')
def report():
    """Generate and show report"""
    data = load_data()
    items = data.get('items', [])
    
    # Update priorities
    for item in items:
        item['priority'] = calculate_priority(
            item.get('sales_count', 0),
            item['stock'],
            item['min_stock']
        )
    
    # Group by priority
    high_priority = [it for it in items if it['priority'] == 'tinggi']
    medium_priority = [it for it in items if it['priority'] == 'sedang']
    low_priority = [it for it in items if it['priority'] == 'rendah']
    
    # Total statistics
    total_items = len(items)
    total_stock = sum(it['stock'] for it in items)
    total_value = sum(it['stock'] * it['price'] for it in items)
    
    return render_template('report.html', 
                         items=items,
                         high_priority=high_priority,
                         medium_priority=medium_priority,
                         low_priority=low_priority,
                         total_items=total_items,
                         total_stock=total_stock,
                         total_value=total_value)

@app.route('/send_report')
def send_report():
    """Send report via WhatsApp"""
    data = load_data()
    items = data.get('items', [])
    
    # Update priorities for report
    for item in items:
        item['priority'] = calculate_priority(
            item.get('sales_count', 0),
            item['stock'],
            item['min_stock']
        )
    
    # Generate report message
    message = "📊 *LAPORAN STOK BARANG*\n"
    message += f"Tanggal: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
    message += "=" * 30 + "\n\n"
    
    # Group by priority
    high = [it for it in items if it['priority'] == 'tinggi']
    medium = [it for it in items if it['priority'] == 'sedang']
    low = [it for it in items if it['priority'] == 'rendah']
    
    if high:
        message += "🔴 *PRIORITAS TINGGI*\n"
        for it in high:
            message += f"• {it['name']}: {it['stock']} {it['unit']} (Terjual: {it.get('sales_count', 0)})\n"
        message += "\n"
    
    if medium:
        message += "🟡 *PRIORITAS SEDANG*\n"
        for it in medium:
            message += f"• {it['name']}: {it['stock']} {it['unit']} (Terjual: {it.get('sales_count', 0)})\n"
        message += "\n"
    
    if low:
        message += "🟢 *PRIORITAS RENDAH*\n"
        for it in low:
            message += f"• {it['name']}: {it['stock']} {it['unit']} (Terjual: {it.get('sales_count', 0)})\n"
        message += "\n"
    
    # Check stock warnings
    warnings = check_stock_warning(items)
    if warnings:
        message += "⚠️ *PERINGATAN STOK MINIMAL*\n"
        for w in warnings:
            message += f"• {w['message']}\n"
        message += "\n"
    
    message += "📈 *STATISTIK*\n"
    message += f"Total Item: {len(items)}\n"
    message += f"Total Stok: {sum(it['stock'] for it in items)}\n"
    message += f"Nilai Total: Rp {sum(it['stock'] * it['price'] for it in items):,}\n"
    message += "\n"
    message += "_Dikirim dari Aplikasi Manajemen Stok_"
    
    # Encode message for URL
    encoded_message = urllib.parse.quote(message)
    wa_url = f"https://wa.me/?text={encoded_message}"
    
    return redirect(wa_url)

@app.route('/api/items')
def api_items():
    """API endpoint to get all items"""
    data = load_data()
    return jsonify(data.get('items', []))

@app.route('/api/stock-warnings')
def api_stock_warnings():
    """API endpoint to get stock warnings"""
    data = load_data()
    items = data.get('items', [])
    warnings = check_stock_warning(items)
    return jsonify(warnings)

@app.route('/api/audit/history')
def api_audit_history():
    """API endpoint to get audit history"""
    audit_data = load_audit_log()
    return jsonify(audit_data.get('audits', []))

@app.route('/api/items/<int:item_id>')
def api_item_detail(item_id):
    """API endpoint to get item detail"""
    data = load_data()
    items = data.get('items', [])
    item = next((it for it in items if it['id'] == item_id), None)
    if item:
        return jsonify(item)
    return jsonify({'error': 'Item not found'}), 404

@app.route('/api/update-stock/<int:item_id>', methods=['POST'])
def api_update_stock(item_id):
    """API endpoint to update stock"""
    data = load_data()
    items = data.get('items', [])
    
    item = next((it for it in items if it['id'] == item_id), None)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    new_stock = request.json.get('stock')
    if new_stock is None:
        return jsonify({'error': 'Stock value required'}), 400
    
    try:
        new_stock = int(new_stock)
        if new_stock < 0:
            return jsonify({'error': 'Stock cannot be negative'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid stock value'}), 400
    
    item['stock'] = new_stock
    item['priority'] = calculate_priority(
        item.get('sales_count', 0),
        item['stock'],
        item['min_stock']
    )
    
    if save_data(data):
        return jsonify({'success': True, 'item': item})
    return jsonify({'error': 'Failed to update stock'}), 500

@app.route('/api/add-sales/<int:item_id>', methods=['POST'])
def api_add_sales(item_id):
    """API endpoint to add sales count"""
    data = load_data()
    items = data.get('items', [])
    
    item = next((it for it in items if it['id'] == item_id), None)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    quantity = request.json.get('quantity', 1)
    try:
        quantity = int(quantity)
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be positive'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid quantity value'}), 400
    
    if item['stock'] < quantity:
        return jsonify({'error': 'Insufficient stock'}), 400
    
    item['stock'] -= quantity
    item['sales_count'] = item.get('sales_count', 0) + quantity
    item['priority'] = calculate_priority(
        item['sales_count'],
        item['stock'],
        item['min_stock']
    )
    
    if save_data(data):
        return jsonify({'success': True, 'item': item})
    return jsonify({'error': 'Failed to update sales'}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Create database directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
    
    # Initialize empty database if it doesn't exist
    if not os.path.exists(DB_FILE):
        initial_data = {
            "items": [],
            "last_id": 0
        }
        save_data(initial_data)
    
    # Initialize empty audit log if it doesn't exist
    if not os.path.exists(AUDIT_FILE):
        initial_audit = {
            "audits": [],
            "last_id": 0
        }
        save_audit_log(initial_audit)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
