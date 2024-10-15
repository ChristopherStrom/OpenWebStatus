from flask import Flask, jsonify
import requests
from datetime import datetime
import sqlite3

app = Flask(__name__)

DATABASE = 'uptime.db'

# Initialize the SQLite database
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS uptime (
                        id INTEGER PRIMARY KEY,
                        url TEXT,
                        port INTEGER,
                        timestamp DATETIME,
                        status TEXT)''')
    conn.commit()
    conn.close()

# Check URL and port
def check_website(url, port):
    try:
        response = requests.get(f'http://{url}:{port}', timeout=5)
        return response.status_code == 200
    except Exception as e:
        return False

# Record the uptime result in the database
def record_result(url, port, status):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO uptime (url, port, timestamp, status) VALUES (?, ?, ?, ?)",
                   (url, port, datetime.now(), status))
    conn.commit()
    conn.close()

@app.route('/check/<url>/<int:port>', methods=['GET'])
def check(url, port):
    is_up = check_website(url, port)
    status = 'up' if is_up else 'down'
    record_result(url, port, status)
    return jsonify({'url': url, 'port': port, 'status': status})

if __name__ == '__main__':
    init_db()
    app.run(port=8081)
