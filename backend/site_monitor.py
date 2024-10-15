import os
import time
import requests
import sqlite3
import logging

# Define paths for database and logs
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uptime.db')
log_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../default/logs')
log_file = os.path.join(log_folder, 'monitor.log')

# Ensure logging folder and file are set up
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
    logging.info(f"Created log folder: {log_folder}")

logging.basicConfig(filename=log_file, level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def check_db_tables():
    """Ensure required tables exist in the database."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Create the 'sites' table if it does not exist
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

        # Create the 'downtime' table if it does not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downtime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER,
                down_at TEXT
            )
        ''')

        conn.commit()
        conn.close()
        logging.info("Database tables checked and created if needed.")
    
    except sqlite3.Error as e:
        logging.error(f"SQLite error during table creation: {e}")
        raise

def monitor_sites():
    """Monitor the sites in the database and log downtime."""
    while True:
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            # Select enabled sites to monitor
            cursor.execute("SELECT id, url, frequency FROM sites WHERE enabled=1")
            sites = cursor.fetchall()

            # Monitor each site
            for site_id, url, frequency in sites:
                check_site_status(site_id, url, frequency)

            conn.close()
            logging.info("Site monitoring cycle completed.")
            time.sleep(10)  # Recheck every 10 seconds for new sites
        
        except sqlite3.Error as e:
            logging.error(f"SQLite error in site monitoring: {e}")
            time.sleep(10)  # Retry after delay in case of SQLite issues

        except Exception as e:
            logging.error(f"Unexpected error in site monitoring: {e}")
            time.sleep(10)  # Retry after delay

def check_site_status(site_id, url, frequency):
    """Check the status of a site and log downtime if needed."""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            log_downtime(site_id)
        else:
            logging.info(f"Site {url} (ID: {site_id}) is up.")

    except requests.RequestException:
        log_downtime(site_id)

    time.sleep(frequency)

def log_downtime(site_id):
    """Log when a site goes down."""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Insert downtime entry
        cursor.execute("INSERT INTO downtime (site_id, down_at) VALUES (?, ?)", 
                       (site_id, time.strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        logging.warning(f"Site with ID {site_id} is down. Downtime logged.")
    
    except sqlite3.Error as e:
        logging.error(f"SQLite error while logging downtime for site {site_id}: {e}")

if __name__ == '__main__':
    logging.info("Starting site monitoring service...")
    
    try:
        # Ensure tables are set up
        check_db_tables()
        logging.info("Database and tables initialized.")

        # Begin site monitoring
        monitor_sites()

    except Exception as e:
        logging.error(f"Fatal error occurred in site monitoring service: {e}")
