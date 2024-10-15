import os
import time
import requests
import sqlite3
import logging

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uptime.db')

log_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../default/logs')
log_file = os.path.join(log_folder, 'monitor.log')

# Ensure logging is set up
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def check_db_tables():
    """Ensure required tables exist in the database."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

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
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO downtime (site_id, down_at) VALUES (?, ?)", (site_id, time.strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    logging.info("Starting site monitoring...")
    check_db_tables()
    monitor_sites()
