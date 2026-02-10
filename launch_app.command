#!/bin/bash

# I FUCKING HATE ACCOUNTS - Desktop Launcher
# Double-click this file to launch the app

# Navigate to app directory
cd "/Users/markburnett/DevPro/Receipt Checker"

# Activate virtual environment
source venv/bin/activate

# Check if server is already running
if lsof -ti:5001 > /dev/null 2>&1; then
    echo "✅ App is already running!"
    echo "🌐 Opening http://127.0.0.1:5001 in browser..."
    echo ""
    open http://127.0.0.1:5001
    sleep 2
    exit 0
fi

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║        💰 I FUCKING HATE ACCOUNTS 💰                         ║"
echo "║        Because accounting fucking sucks!                     ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 Starting server..."
echo ""

# Start the Flask app in background
python3 web/app.py > /dev/null 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Check if server started successfully
if lsof -ti:5001 > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo "🌐 Opening http://127.0.0.1:5001 in browser..."
    echo ""
    
    # Open in default browser
    open http://127.0.0.1:5001
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ App is running on: http://127.0.0.1:5001"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "⚠️  KEEP THIS WINDOW OPEN while using the app"
    echo ""
    echo "To stop the server:"
    echo "  • Close this Terminal window, OR"
    echo "  • Press Ctrl+C"
    echo ""
    echo "Logs will appear below..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Show live logs
    tail -f /dev/null
else
    echo "❌ Failed to start server"
    echo "Please check the logs for errors"
    exit 1
fi
