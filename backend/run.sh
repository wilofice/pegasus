#!/bin/bash

# Define a file to store PIDs
PID_FILE="running_processes.pid"

# --- Start start_worker.py ---
echo "Starting start_worker.py..."
python start_worker.py &
WORKER_PID=$! # Get the PID of the last background process
echo "start_worker.py started with PID: $WORKER_PID"
echo "$WORKER_PID" > "$PID_FILE" # Store PID in the file

# --- Start main.py ---
echo "Starting main.py..."
python main.py &
MAIN_PID=$! # Get the PID of the last background process
echo "main.py started with PID: $MAIN_PID"
echo "$MAIN_PID" >> "$PID_FILE" # Append PID to the file

echo "All processes started. PIDs stored in $PID_FILE"
echo "You can now safely close this terminal if desired."
echo "To stop them, run the 'stop_processes.sh' script."