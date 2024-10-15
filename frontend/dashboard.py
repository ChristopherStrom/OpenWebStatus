import os
import logging
import sqlite3
import random
import string
import hashlib
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your secret key
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../backend/uptime.db')

# Ensure the 'default' and 'default/logs' folders exist
def ensure_default_folders():
    default_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../default')
    log_folder = os.path.join(default_folder, 'logs')

    if not os.path.exists(default_folder):
        os.makedirs(default_folder)
        logging.info(f"Created default folder: {default_folder}")

    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
        logging.info(f"Created logs folder: {log_folder}")

    return log_folder

log_folder = ensure_default_folders()  # Ensure the folder is created
log_file = os.path.join(log_folder, 'app.log')

logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,  # Ensure DEBUG level is set for detailed logging
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Function to hash a password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Fetch uptime data for display on the index page
def get_daily_uptime():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, status FROM uptime")
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logging.error(f"Error fetching uptime data: {e}")
        return []

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = hash_password(password)

        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
            user = cursor.fetchone()
            conn.close()

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

# Index route (displays uptime data)
@app.route('/')
def index():
    data = get_daily_uptime()
    return render_template('index.html', data=data)

# Settings route
@app.route('/settings')
def settings():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('settings.html')

# Add site route (handles adding a new site)
@app.route('/add_site', methods=['POST'])
def add_site():
    name = request.form['name']
    purpose = request.form['purpose']
    url = request.form['url']
    frequency = int(request.form['frequency'])
    enabled = 1 if 'enabled' in request.form else 0

    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sites (name, purpose, url, frequency, enabled) VALUES (?, ?, ?, ?, ?)",
                       (name, purpose, url, frequency, enabled))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error adding site: {e}")
    return redirect(url_for('settings'))

# Run the Flask app
if __name__ == '__main__':
    logging.info("Starting the web application...")
    app.run(port=8080)
