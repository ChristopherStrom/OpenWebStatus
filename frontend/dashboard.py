from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
import random
import string
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace this with your secret key

DATABASE = '../backend/uptime.db'

# Function to create database and uptime/user tables if they don't exist
def init_db():
    conn = sqlite3.connect(DATABASE)
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

# Function to generate a random password
def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

# Function to hash a password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to seed database with an admin user if no users exist
def seed_admin_user():
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
        if not os.path.exists(default_folder):
            os.makedirs(default_folder)

        password_file_path = os.path.join(default_folder, 'default_password.txt')

        # Save the password to the file
        with open(password_file_path, 'w') as f:
            f.write(f"Default admin password: {random_password}")

    conn.close()

# Function to fetch uptime data
def get_daily_uptime():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, status FROM uptime")
    results = cursor.fetchall()
    conn.close()
    return results

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Hash the entered password
        hashed_password = hash_password(password)

        # Check if the user exists in the database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_password))
        user = cursor.fetchone()
        conn.close()

        if user:
            # Successful login
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return "Invalid username or password", 403

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Main dashboard route
@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    data = get_daily_uptime()
    return render_template('index.html', data=data)

if __name__ == '__main__':
    # Initialize the database and seed admin user if necessary
    init_db()
    seed_admin_user()
    app.run(port=8080)
