#!/bin/bash

# I FUCKING HATE ACCOUNTS - App Launcher
# Launches the Receipt Checker web application

# Navigate to app directory
cd "/Users/markburnett/DevPro/Receipt Checker"

# Activate virtual environment
source venv/bin/activate

# Check if server is already running
if lsof -ti:5001 > /dev/null 2>&1; then
    echo "App is already running on http://127.0.0.1:5001"
    echo "Opening in browser..."
    open http://127.0.0.1:5001
else
    echo "Starting I FUCKING HATE ACCOUNTS..."
    echo ""
    
    # Start the Flask app
    python3 web/app.py &
    
    # Wait for server to start
    sleep 3
    
    # Open in default browser
    open http://127.0.0.1:5001
    
    echo ""
    echo "✅ App is running!"
    echo "🌐 URL: http://127.0.0.1:5001"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo ""
    
    # Keep script running so you can see logs
    wait
fi
