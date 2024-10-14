from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

DATABASE = 'uptime.db'

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
    app.run(port=8080)
