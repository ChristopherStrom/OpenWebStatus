import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import random
import string
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your secret key

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../backend/uptime.db')

# Ensure the 'default' and 'default/logs' folders exist
def ensure_default_folders():
    default_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../default')
    log_folder = os.path.join(default_folder, 'logs')

    # Create the folders if they don't exist
    if not os.path.exists(default_folder):
        os.makedirs(default_folder)
        logging.info(f"Created default folder: {default_folder}")

    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
        logging.info(f"Created logs folder: {log_folder}")

    return log_folder

# Set up logging
log_folder = ensure_default_folders()  # Ensure the folder is created
log_file = os.path.join(log_folder, 'app.log')

logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Function to create database and uptime/user tables if they don't exist
def init_db():
    try:
        # Ensure the backend folder exists, create if it doesn't
        backend_folder = os.path.dirname(DATABASE)
        if not os.path.exists(backend_folder):
            os.makedirs(backend_folder)
            logging.info(f"Created backend folder: {backend_folder}")

        # Connect to the database and create tables
        conn = sqlite3.connect(DATABASE)
        logging.info(f"Connected to the database at: {DATABASE}")
        
        cursor = conn.cursor()

        # Create the uptime table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uptime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                status TEXT
            )
        ''')

        # Create the users table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password TEXT
            )
        ''')

        conn.commit()
        conn.close()
        logging.info('Database and tables initialized successfully.')
    except Exception as e:
        logging.error(f"Error during database initialization: {e}")

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

# Fetch uptime data
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
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    data = get_daily_uptime()
    return render_template('index.html', data=data)

if __name__ == '__main__':
    # Ensure the default and logs folder exist
    ensure_default_folders()
    
    # Initialize the database and seed admin user if necessary
    init_db()
    seed_admin_user()
    app.run(port=8080)
