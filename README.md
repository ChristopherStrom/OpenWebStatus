
#OpenWebStatus

OpenWebStatus is an open-source website monitoring tool that checks the availability of a given URL and port every minute. 
It logs uptime and downtime, then visualizes daily uptime percentages in a calendar-like view, inspired by the GitHub contribution calendar.

This project is licensed under the GNU General Public License v3 (GPLv3), ensuring that it remains free and open for modification and distribution.

#Features:
- Periodic checks of website availability (every 1 minute).
- Logs uptime percentage by day.
- GitHub-style calendar visualization of uptime.
- RESTful API for adding/removing URLs and retrieving uptime stats.
- Lightweight and easy to deploy on existing servers.
- Supports monitoring multiple URLs and ports.

#License:
OpenWebStatus is licensed under the GNU General Public License v3 (GPLv3). This guarantees the freedom to use, modify, 
and distribute the software while maintaining the same freedoms for others.

#Setup Instructions:
1. Clone the repository:
   git clone https://github.com/ChristopherStrom/OpenWebStatus.git

2. Install dependencies:
   pip install -r requirements.txt

3. Run the backend API (Gunicorn setup recommended):
   gunicorn --workers 3 --bind 127.0.0.1:8081 wsgi:app

4. Start the frontend dashboard:
   python dashboard.py

#Contributing:
Contributions are welcome! Please submit pull requests or create issues for any bugs or new features.

#License:
This project is licensed under the GNU GPL v3 - see the LICENSE file for details.

