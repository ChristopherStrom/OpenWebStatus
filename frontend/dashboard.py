import os
import logging
import sqlite3
import hashlib
import random
import string
import time
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../backend/uptime.db')

# Ensure the 'default' and 'default/logs' folders exist
def ensure_default_folders():
    default_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../default')
    log_folder = os.path.join(default_folder, 'logs')

    os.makedirs(default_folder, exist_ok=True)
    os.makedirs(log_folder, exist_ok=True)
    logging.info(f"Default and logs folders ensured at: {default_folder}, {log_folder}")

    return log_folder

log_folder = ensure_default_folders()  # Ensure the folder is created
log_file = os.path.join(log_folder, 'app.log')

logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,  # Ensure DEBUG level is set for detailed logging
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Fetch all sites from the database
def get_all_sites():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sites")
            sites = cursor.fetchall()
        return sites
    except Exception as e:
        logging.error(f"Error fetching sites: {e}")
        return []

# Fetch site data for displaying uptime/downtime in the dashboard
def get_site_data():
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, purpose, url FROM sites")
            sites = cursor.fetchall()

            site_data = []
            for site in sites:
                site_id, name, purpose, url = site
                # Get uptime data for the past 90 days
                cursor.execute("""
                    SELECT date(down_at) FROM downtime
                    WHERE site_id = ? AND down_at >= date('now', '-90 days')
                    ORDER BY down_at ASC
                """, (site_id,))
                downtime_dates = [row[0] for row in cursor.fetchall()]

                # Construct a list of days with 'up' or 'down' status for the last 90 days
                days_status = []
                for day_offset in range(89, -1, -1):  # Start from 89 days ago to today
                    day = time.strftime('%Y-%m-%d', time.gmtime(time.time() - day_offset * 86400))
                    days_status.append({'status': 'downtime' if day in downtime_dates else 'uptime', 'date': day, 'site_id': site_id})

                # Calculate uptime percentage
                total_days = len(days_status)
                up_days = len([day for day in days_status if day['status'] == 'uptime'])
                uptime_percentage = (up_days / total_days) * 100 if total_days > 0 else 0

                # Split the list into weekly chunks
                weeks_status = [days_status[i:i + 7] for i in range(0, len(days_status), 7)]

                site_data.append((site_id, name, purpose, url, weeks_status, round(uptime_percentage, 2)))

        return site_data
    except Exception as e:
        logging.error(f"Error fetching site data: {e}")
        return []

# Function to generate a random password
def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

# Function to hash a password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)

        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
                user = cursor.fetchone()

            if user:
                session['logged_in'] = True
                return redirect(url_for('index'))
            else:
                return "Invalid username or password", 403
        except Exception as e:
            logging.error(f"Error during login: {e}")
            return "Login failed", 500

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Home page (dashboard)
@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    # Get site data to display in the dashboard
    data = get_site_data()
    return render_template('index.html', data=data)

# Settings page to add, manage, and edit sites
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        purpose = request.form['purpose']
        url = request.form['url']
        frequency = int(request.form['frequency'])
        enabled = 1 if 'enabled' in request.form else 0

        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO sites (name, purpose, url, frequency, enabled) VALUES (?, ?, ?, ?, ?)",
                               (name, purpose, url, frequency, enabled))
                conn.commit()
                logging.info(f"Added new site: {name}")
        except Exception as e:
            logging.error(f"Error adding site: {e}")
        return redirect(url_for('settings'))

    sites = get_all_sites()
    return render_template('settings.html', sites=sites)

# Route to edit a site
@app.route('/edit_site/<int:site_id>', methods=['GET', 'POST'])
def edit_site(site_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        purpose = request.form['purpose']
        url = request.form['url']
        frequency = int(request.form['frequency'])
        enabled = 1 if 'enabled' in request.form else 0

        try:
            with sqlite3.connect(DATABASE) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sites SET name = ?, purpose = ?, url = ?, frequency = ?, enabled = ?
                    WHERE id = ?
                """, (name, purpose, url, frequency, enabled, site_id))
                conn.commit()
                logging.info(f"Updated site with id: {site_id}")
        except Exception as e:
            logging.error(f"Error updating site with id {site_id}: {e}")
        return redirect(url_for('settings'))

    # Fetch site data for editing
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sites WHERE id = ?", (site_id,))
            site = cursor.fetchone()
    except Exception as e:
        logging.error(f"Error fetching site with id {site_id} for editing: {e}")
        return redirect(url_for('settings'))

    return render_template('edit_site.html', site=site)

# Route to display downtime details page for a specific site and date
@app.route('/downtime/<int:site_id>/<date>')
def downtime(site_id, date):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    try:
        # Fetch site information for display
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sites WHERE id = ?", (site_id,))
            site = cursor.fetchone()
        
        if not site:
            return "Site not found", 404
        
        site_name = site[0]
    except Exception as e:
        logging.error(f"Error fetching site with id {site_id} for downtime page: {e}")
        return "Error retrieving site data", 500

    # Render downtime.html and pass the site details and date
    return render_template('downtime.html', site_id=site_id, date=date, site_name=site_name)

# Ensure the default and logs folder exist
ensure_default_folders()

# Check if the database exists
if not os.path.exists(DATABASE):
    logging.error("Database does not exist. Application will not run.")
    exit(1)

# Start the Flask app
if __name__ == '__main__':
    app.run()
