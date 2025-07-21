#!/bin/bash

# Define a file to store PIDs
PID_FILE="running_processes.pid"

# Path to your virtual environment's activate script
# Adjust this if your .venv is not directly in the current directory
VENV_ACTIVATE_SCRIPT="./.venv/bin/activate"

# Check if the virtual environment exists
if [ ! -f "$VENV_ACTIVATE_SCRIPT" ]; then
    echo "Error: Virtual environment not found at $VENV_ACTIVATE_SCRIPT."
    echo "Please ensure you have created and activated your virtual environment (e.g., 'python3 -m venv .venv' and 'source .venv/bin/activate')."
    exit 1
fi

# Source the virtual environment's activate script
# This modifies the current shell's PATH to use the venv's python
source "$VENV_ACTIVATE_SCRIPT"

# --- Start start_worker.py ---
echo "Starting start_worker.py..."
# Use 'python' directly as the venv's python is now in PATH
python start_worker.py &
WORKER_PID=$! # Get the PID of the last background process
echo "start_worker.py started with PID: $WORKER_PID"
echo "$WORKER_PID" > "$PID_FILE" # Store PID in the file (clears previous PIDs)

# --- Start main.py ---
echo "Starting main.py..."
# Use 'python' directly as the venv's python is now in PATH
python main.py &
MAIN_PID=$! # Get the PID of the last background process
echo "main.py started with PID: $MAIN_PID"
echo "$MAIN_PID" >> "$PID_FILE" # Append PID to the file

echo "All processes started using virtual environment. PIDs stored in $PID_FILE"
echo "You can now safely close this terminal if desired."
echo "To stop them, run the 'stop_processes.sh' script."

# IMPORTANT: Do NOT deactivate here. The processes need the environment to persist.
# The `deactivate` command is usually for interactive shell use.