import os
import logging
import sqlite3
import hashlib
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key
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

# Fetch site data for displaying uptime/downtime in dashboard
def get_site_data():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, (
                SELECT group_concat(
                    CASE
                        WHEN EXISTS (SELECT 1 FROM downtime WHERE downtime.site_id = sites.id AND date(downtime.down_at) = day) THEN 'down'
                        ELSE 'up'
                    END, ','
                )
                FROM (
                    SELECT date('now', '-' || (365 - rowid) || ' days') AS day
                    FROM sqlite_sequence WHERE rowid <= 365
                )
            ) AS status FROM sites
        """)
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        logging.error(f"Error fetching site data: {e}")
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

# Home page (dashboard)
@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    # Get site data to display in the dashboard
    data = get_site_data()
    return render_template('index.html', data=data)

# Settings page to add and manage sites
@app.route('/settings')
def settings():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('settings.html')

# Add a new site
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
        logging.info(f"Added new site: {name}")
    except Exception as e:
        logging.error(f"Error adding site: {e}")
    return redirect(url_for('settings'))

if __name__ == '__main__':
    # Ensure the default and logs folder exist
    ensure_default_folders()

    # Initialize the database and seed admin user if necessary
    seed_admin_user()

    # Start the Flask app
    app.run(port=8080)
