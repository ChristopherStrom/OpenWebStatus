
# Gunicorn Setup for OpenWebStatus

This guide explains how to configure Gunicorn to run both the backend API and the frontend dashboard for OpenWebStatus on a server using Gunicorn.

## Project Structure:
```
OpenWebStatus/
│
├── api.py                  # API for uptime checks
├── dashboard.py            # Dashboard for visualizing uptime
├── requirements.txt        # Required Python dependencies
├── GUNICORN_SETUP.md       # This setup guide
└── ...
```

## Prerequisites:

Ensure Python, Gunicorn, and Flask are installed on your server.
The `api.py` file runs the backend, and `dashboard.py` handles the frontend.

```bash
pip install gunicorn flask requests
```

## 1. Running the Backend API with Gunicorn

To run the backend API on port 8081, follow these steps:

### a. Create a Gunicorn service file for the API:

```bash
sudo nano /etc/systemd/system/gunicorn-api.service
```

Add the following content, replacing the paths with your project details:

```ini
[Unit]
Description=Gunicorn API for OpenWebStatus (status.domain.com)
After=network.target

[Service]
User=yourusername
Group=www-data
WorkingDirectory=/path/to/OpenWebStatus
ExecStart=/path/to/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8081 api:app

[Install]
WantedBy=multi-user.target
```

### b. Start and enable the service:

```bash
sudo systemctl start gunicorn-api
sudo systemctl enable gunicorn-api
```

This will start the backend API on port 8081 and automatically run it at boot.


## 2. Running the Frontend Dashboard with Gunicorn

Now, configure the dashboard to run on port 8080.

### a. Create a Gunicorn service file for the dashboard:

```bash
sudo nano /etc/systemd/system/gunicorn-dashboard.service
```

Add the following content:

```ini
[Unit]
Description=Gunicorn Dashboard for OpenWebStatus (status.domain.com)
After=network.target

[Service]
User=yourusername
Group=www-data
WorkingDirectory=/path/to/OpenWebStatus
ExecStart=/path/to/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8080 dashboard:app

[Install]
WantedBy=multi-user.target
```

### b. Start and enable the service:

```bash
sudo systemctl start gunicorn-dashboard
sudo systemctl enable gunicorn-dashboard
```

## 3. Nginx Configuration

If you are using Nginx as a reverse proxy, create the following Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/status.domain.com
```

Add this content to proxy the requests to the correct Gunicorn services:

```nginx
server {
    listen 80;
    server_name status.domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    error_log /var/log/nginx/status_error.log;
    access_log /var/log/nginx/status_access.log;
}
```

Enable the new site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/status/etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Now you have:
- The backend API running on port `8081`.
- The frontend dashboard running on port `8080`.
- Nginx routing traffic to the appropriate Gunicorn instances.