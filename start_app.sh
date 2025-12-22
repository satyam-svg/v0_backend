#!/bin/bash

# Set working directory to script location
cd "$(dirname "$0")"

# Create logs directory if it doesn't exist
mkdir -p logs

# Timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/app_${TIMESTAMP}.log"

# Install requirements
echo "Installing requirements..."
pip3 install -r requirements.txt >> "$LOG_FILE" 2>&1

# Check if any Flask process is already running
if pgrep -f "python3 app.py" > /dev/null; then
    echo "Stopping existing Flask application..."
    pkill -f "python3 app.py"
    sleep 2
fi

# Start the Flask application in the background
echo "Starting Flask application..."
nohup python3 app.py >> "$LOG_FILE" 2>&1 &

# Save the PID to a file
echo $! > app.pid

echo "Application started! Check logs at $LOG_FILE"
echo "PID: $(cat app.pid)" 