import os
import json
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configuration
ADMIN_PANEL_PASSWORD = os.getenv("ADMIN_PANEL_PASSWORD", "admin123")
ADMIN_FILE = "admins.txt"
STATS_FILE = "bot_stats.json"

# Global variables
admin_ids = []
stats = {
    "total_conversions": 0,
    "successful_conversions": 0,
    "failed_conversions": 0,
    "last_conversion": None,
    "bot_uptime": time.time(),
    "active_users": []
}
stats_lock = threading.Lock()
app = Flask(__name__)
app.secret_key = os.urandom(24)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["5 per minute"]
)

def load_admins():
    """Load admin IDs from file"""
    global admin_ids
    try:
        if os.path.exists(ADMIN_FILE):
            with open(ADMIN_FILE, 'r') as f:
                admin_ids = [int(line.strip()) for line in f if line.strip().isdigit()]
    except Exception as e:
        print(f"Error loading admins: {str(e)}")

def save_admins():
    """Save admin IDs to file"""
    try:
        with open(ADMIN_FILE, 'w') as f:
            for admin_id in admin_ids:
                f.write(f"{admin_id}\n")
    except Exception as e:
        print(f"Error saving admins: {str(e)}")

def load_stats():
    """Load bot statistics from file"""
    global stats
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r') as f:
                saved_stats = json.load(f)
                # Only update existing keys to avoid losing in-memory data
                for key in stats.keys():
                    if key in saved_stats:
                        stats[key] = saved_stats[key]
                
                # Convert active_users from list back to set
                if isinstance(stats.get("active_users"), list):
                    stats["active_users"] = set(stats["active_users"])
    except Exception as e:
        print(f"Error loading stats: {str(e)}")

def save_stats():
    """Save bot statistics to file"""
    try:
        with stats_lock:
            # Convert set to list for JSON serialization
            active_users = list(stats["active_users"])
            stats_to_save = {**stats, "active_users": active_users}
            
            with open(STATS_FILE, 'w') as f:
                json.dump(stats_to_save, f, indent=2)
    except Exception as e:
        print(f"Error saving stats: {str(e)}")

def get_uptime():
    """Get formatted bot uptime"""
    uptime_seconds = time.time() - stats["bot_uptime"]
    return str(timedelta(seconds=int(uptime_seconds))).split('.')[0]

def get_hourly_activity():
    """Generate hourly activity data for the chart"""
    now = datetime.now()
    hours = []
    counts = []
    
    # Generate last 24 hours
    for i in range(23, -1, -1):
        hour = now - timedelta(hours=i)
        hours.append(hour.strftime("%H:00"))
        # Count conversions in this hour (simplified for demo)
        counts.append(min(5, stats["total_conversions"] // 24))  # Demo data
    
    return hours, counts

@app.before_request
def before_request():
    """Load data before each request"""
    load_admins()
    load_stats()
    
    # Ensure active_users is a set
    if not isinstance(stats["active_users"], set):
        stats["active_users"] = set(stats["active_users"])

# Flask Admin Panel Routes
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PANEL_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Get hourly activity data
    hourly_labels, hourly_data = get_hourly_activity()
    
    return render_template(
        'dashboard.html',
        stats=stats,
        admins=admin_ids,
        uptime=get_uptime(),
        current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        hourly_labels=json.dumps(hourly_labels),
        hourly_data=json.dumps(hourly_data)
    )

@app.route('/add_admin', methods=['POST'])
def add_admin():
    if not session.get('logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        admin_id = int(request.form.get('admin_id'))
        if admin_id in admin_ids:
            return jsonify({"success": False, "error": "Admin already exists"}), 400
        
        admin_ids.append(admin_id)
        save_admins()
        return jsonify({"success": True, "message": f"Admin {admin_id} added successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/remove_admin', methods=['POST'])
def remove_admin():
    if not session.get('logged_in'):
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        admin_id = int(request.form.get('admin_id'))
        if admin_id not in admin_ids:
            return jsonify({"success": False, "error": "Admin not found"}), 404
        
        admin_ids.remove(admin_id)
        save_admins()
        return jsonify({"success": True, "message": f"Admin {admin_id} removed successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/stats')
def get_stats():
    """API endpoint for worker to update stats"""
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify({
        "total_conversions": stats["total_conversions"],
        "successful_conversions": stats["successful_conversions"],
        "failed_conversions": stats["failed_conversions"],
        "last_conversion": stats["last_conversion"],
        "active_users": len(stats["active_users"])
    })

if __name__ == '__main__':
    # Load initial data
    load_admins()
    load_stats()
    
    # Start the Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
