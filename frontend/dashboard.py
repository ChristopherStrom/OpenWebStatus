import os
import logging
import threading
import time
import requests
import sqlite3
import random
import string
import hashlib
import sys
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

# Set up logging
log_folder = ensure_default_folders()
log_file = os.path.join(log_folder, 'app.log')

logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

import sys

def init_db():
    logging.info("Starting database initialization...")
    try:
        backend_folder = os.path.dirname(DATABASE)
        if not os.path.exists(backend_folder):
            os.makedirs(backend_folder)
            logging.info(f"Created backend folder: {backend_folder}")

        # Check if the database file exists before connecting
        db_exists = os.path.exists(DATABASE)
        logging.info(f"Database path: {DATABASE}")
        conn = sqlite3.connect(DATABASE)
        
        # Log the creation of the database if it didn't exist before
        if not db_exists:
            logging.info(f"Created new database at: {DATABASE}")
        else:
            logging.info(f"Using existing database at: {DATABASE}")

        cursor = conn.cursor()

        # Log before attempting to create each table
        logging.info("Attempting to create 'uptime' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uptime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                status TEXT
            )
        ''')
        logging.info("'uptime' table created or already exists.")

        logging.info("Attempting to create 'users' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password TEXT
            )
        ''')
        logging.info("'users' table created or already exists.")

        logging.info("Attempting to create 'sites' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                purpose TEXT,
                url TEXT,
                frequency INTEGER,
                enabled INTEGER
            )
        ''')
        logging.info("'sites' table created or already exists.")

        logging.info("Attempting to create 'downtime' table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downtime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER,
                down_at TEXT
            )
        ''')
        logging.info("'downtime' table created or already exists.")

        # Commit the changes
        logging.info("Committing changes...")
        conn.commit()
        logging.info("Tables created successfully and changes committed.")
        
        # Close the connection
        conn.close()
        logging.info("Database connection closed.")
    
    except sqlite3.Error as e:
        logging.error(f"SQLite error occurred during database initialization: {e}")
        sys.exit(1)  # Exit the program on failure

    except Exception as e:
        logging.error(f"Error during database initialization: {e}")
        sys.exit(1)  # Exit the program on failure

# Function to generate a random password
def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

# Function to hash a password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to seed database with an admin user if no users exist
def seed_admin_user():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Check if any users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        if count == 0:
            # Generate a random password
            random_password = generate_random_password()

            # Hash the password
            hashed_password = hash_password(random_password)

            # Insert the default admin user
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_password))
            conn.commit()

            # Define the path for the default password file
            default_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../default')
            password_file_path = os.path.join(default_folder, 'default_password.txt')

            # Save the password to the file
            with open(password_file_path, 'w') as f:
                f.write(f"Default admin password: {random_password}")

            logging.info('Admin user created and password saved.')
        conn.close()
    except Exception as e:
        logging.error(f"Error during admin user seeding: {e}")

def monitor_sites():
    while True:
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            # Check if the 'sites' table exists before querying it
            cursor.execute('''
                SELECT name FROM sqlite_master WHERE type='table' AND name='sites';
            ''')
            table_exists = cursor.fetchone()

            if not table_exists:
                logging.error("Table 'sites' does not exist. Exiting site monitoring.")
                conn.close()
                logging.info("App is stopping due to missing 'sites' table.")
                return  # Stop monitoring if table doesn't exist

            # Query for enabled sites and start monitoring them
            cursor.execute("SELECT id, url, frequency FROM sites WHERE enabled=1")
            sites = cursor.fetchall()

            for site_id, url, frequency in sites:
                threading.Thread(target=check_site_status, args=(site_id, url, frequency)).start()

            conn.close()
            time.sleep(10)  # Recheck every 10 seconds for new sites

        except sqlite3.Error as e:
            logging.error(f"SQLite error occurred in site monitoring: {e}")
            time.sleep(10)  # Delay before retrying
        except Exception as e:
            logging.error(f"Error in site monitoring: {e}")
            time.sleep(10)  # Delay before retrying

# Check the status of each site and log downtime if needed
def check_site_status(site_id, url, frequency):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            log_downtime(site_id)
    except requests.RequestException:
        log_downtime(site_id)

    time.sleep(frequency)

# Log downtime if site is down
def log_downtime(site_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO downtime (site_id, down_at) VALUES (?, ?)", (site_id, time.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

# Start the site monitoring task in a background thread
threading.Thread(target=monitor_sites, daemon=True).start()

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

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    data = get_daily_uptime()
    return render_template('index.html', data=data)

@app.route('/settings')
def settings():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('settings.html')

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

if __name__ == '__main__':
    # Ensure the default and logs folder exist
    ensure_default_folders()

    # Initialize the database and seed admin user if necessary
    try:
        init_db()  # Ensure database and tables are properly created
        seed_admin_user()  # Seed admin if necessary

        # Only start monitoring after DB initialization is confirmed
        logging.info("Starting site monitoring after DB check is complete.")
        threading.Thread(target=monitor_sites, daemon=True).start()

        # Start Flask app
        app.run(port=8080)

    except Exception as e:
        logging.error(f"Failed to initialize application: {e}")
        logging.info("App is stopping due to initialization failure.")
        sys.exit(1)  # Exit if initialization fails
