from flask import Flask, render_template
import sqlite3
import os

app = Flask(__name__)

DATABASE = 'uptime.db'

# Function to create database and uptime table if it doesn't exist
def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uptime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

# Function to seed database with sample data if no records exist
def seed_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM uptime")
    count = cursor.fetchone()[0]
    if count == 0:
        # Insert sample data
        cursor.execute("INSERT INTO uptime (timestamp, status) VALUES ('2024-10-14 10:00:00', 'up')")
        cursor.execute("INSERT INTO uptime (timestamp, status) VALUES ('2024-10-14 11:00:00', 'down')")
        cursor.execute("INSERT INTO uptime (timestamp, status) VALUES ('2024-10-14 12:00:00', 'up')")
        conn.commit()
    conn.close()

# Fetch uptime data from the database
def get_daily_uptime():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, status FROM uptime")
    results = cursor.fetchall()
    conn.close()
    return results

@app.route('/')
def index():
    data = get_daily_uptime()
    return render_template('index.html', data=data)

if __name__ == '__main__':
    # Initialize the database and seed if necessary
    init_db()
    seed_db()
    app.run(port=8080)
