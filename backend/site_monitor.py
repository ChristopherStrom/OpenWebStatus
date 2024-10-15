import os
import time
import requests
import sqlite3
import logging
import hashlib
import random
import string

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uptime.db')
log_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../default/logs')
log_file = os.path.join(log_folder, 'monitor.log')

# Ensure logging is set up
os.makedirs(log_folder, exist_ok=True)

logging.basicConfig(
    filename=log_file,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def generate_random_password(length=10):
    """Generate a random password."""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for _ in range(length))

def hash_password(password):
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def seed_admin_user():
    """Seed the admin user if no users exist and create/overwrite default password file."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Check if any users exist
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]

        if count == 0:
            # Generate and hash a random password
            random_password = generate_random_password()
            hashed_password = hash_password(random_password)

            # Insert the default admin user
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_password))
            conn.commit()

            # Define the path for the default password file
            default_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../default')
            os.makedirs(default_folder, exist_ok=True)
            
            password_file_path = os.path.join(default_folder, 'default_password.txt')

            # Overwrite the password file
            with open(password_file_path, 'w') as f:
                f.write(f"Default admin password: {random_password}")

            logging.info('Admin user created and default password saved.')
        else:
            logging.info('Admin user already exists, skipping password creation.')

        conn.close()
    except Exception as e:
        logging.error(f"Error during admin user seeding: {e}")
        raise

def check_db_tables():
    """Ensure required tables exist in the database."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                password TEXT
            )
        ''')

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downtime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER,
                down_at TEXT
            )
        ''')

        conn.commit()
        conn.close()
        logging.info('Database and tables initialized successfully.')
    except sqlite3.Error as e:
        logging.error(f"SQLite error during table creation: {e}")
        raise
    except Exception as e:
        logging.error(f"Error during database initialization: {e}")
        raise

def insert_default_site():
    """Insert google.com as the default site if not already present."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Check if the default google.com site exists
        cursor.execute("SELECT COUNT(*) FROM sites WHERE url = 'https://www.google.com'")
        count = cursor.fetchone()[0]

        if count == 0:
            logging.info("Inserting default site: google.com")
            # Insert default site with a 5-minute check frequency
            cursor.execute(
                "INSERT INTO sites (name, purpose, url, frequency, enabled) VALUES (?, ?, ?, ?, ?)",
                ('Google', 'Default site monitoring', 'https://www.google.com', 300, 1)
            )
            conn.commit()
            logging.info("Default site google.com inserted.")
        else:
            logging.info("Default site google.com already exists, skipping insertion.")

        conn.close()
    except Exception as e:
        logging.error(f"Error inserting default site: {e}")
        raise

def monitor_sites():
    """Monitor the sites in the database and log downtime."""
    while True:
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT id, url, frequency FROM sites WHERE enabled=1")
            sites = cursor.fetchall()

            for site_id, url, frequency in sites:
                check_site_status(site_id, url, frequency)

            conn.close()
            time.sleep(10)  # Recheck every 10 seconds for new sites
        except Exception as e:
            logging.error(f"Error in site monitoring: {e}")

def check_site_status(site_id, url, frequency):
    """Check the status of a site and log downtime if needed."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            log_downtime(site_id)
    except requests.RequestException:
        log_downtime(site_id)

    time.sleep(frequency)

def log_downtime(site_id):
    """Log when a site goes down."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO downtime (site_id, down_at) VALUES (?, ?)", (site_id, time.strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        logging.info(f"Logged downtime for site ID: {site_id}")
    except Exception as e:
        logging.error(f"Error logging downtime for site ID {site_id}: {e}")

if __name__ == '__main__':
    logging.info("Starting site monitoring...")

    try:
        # Ensure tables are created and the admin user is seeded with a default password
        check_db_tables()
        seed_admin_user()

        # Insert default google.com site for tracking
        insert_default_site()

    except Exception as e:
        logging.error(f"Failed during DB initialization or site insertion: {e}")
        exit(1)

    # Start the site monitoring process
    monitor_sites()