#!/bin/bash
# Startup script for Railway deployment

echo "=================================================="
echo "I FUCKING HATE ACCOUNTS - Starting Application"
echo "=================================================="

# Initialize database and create admin on first run
echo "Initializing application..."
python init_app.py

# Start the application with gunicorn
echo "Starting web server..."
exec gunicorn --bind 0.0.0.0:${PORT:-5001} --workers 4 --timeout 120 --access-logfile - --error-logfile - web.app:app
