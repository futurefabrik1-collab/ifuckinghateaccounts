#!/bin/bash
# Startup script for Railway deployment

echo "=================================================="
echo "I FUCKING HATE ACCOUNTS - Starting Application"
echo "=================================================="

# Initialize database and create admin on first run
echo "Initializing application..."
python init_app.py

# Start the application with gunicorn
# Using gevent async workers for better concurrency
# 8 workers with 100 connections each = ~800 concurrent connections
echo "Starting web server with async workers..."
exec gunicorn --bind 0.0.0.0:${PORT:-5001} \
  --workers 8 \
  --worker-class gevent \
  --worker-connections 100 \
  --timeout 300 \
  --access-logfile - \
  --error-logfile - \
  web.app:app
