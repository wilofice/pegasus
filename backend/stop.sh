#!/bin/bash

PID_FILE="running_processes.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "PID file '$PID_FILE' not found. No processes to stop."
    exit 1
fi

echo "Stopping processes listed in $PID_FILE..."

# Read PIDs from the file, one per line
while IFS= read -r PID; do
    if [ -n "$PID" ]; then # Check if PID is not empty
        echo "Attempting to kill PID: $PID"
        # Use 'kill' command. SIGTERM (default) is graceful.
        # Use 'kill -9' for forceful kill if SIGTERM doesn't work.
        kill "$PID"
        # Check if the kill command was successful
        if [ $? -eq 0 ]; then
            echo "Successfully sent termination signal to PID $PID."
        else
            echo "Failed to send termination signal to PID $PID. It might already be stopped or not exist."
        fi
    fi
done < "$PID_FILE"

# Give a moment for processes to terminate
sleep 2

# Verify if processes are truly gone and clean up PID file
echo "Verifying processes and cleaning up PID file..."
CLEAN_PIDS=""
while IFS= read -r PID; do
    if [ -n "$PID" ]; then
        # Check if the process with this PID is still running
        if ps -p "$PID" > /dev/null; then
            echo "Warning: Process with PID $PID is still running. You might need to kill -9."
            CLEAN_PIDS+="$PID\n" # Keep this PID for a potential next try
        else
            echo "PID $PID is no longer running."
        fi
    fi
done < "$PID_FILE"

# Overwrite PID file with only the PIDs that are still running (if any)
if [ -n "$CLEAN_PIDS" ]; then
    echo -e "$CLEAN_PIDS" > "$PID_FILE"
    echo "Updated $PID_FILE with remaining running PIDs."
else
    rm -f "$PID_FILE"
    echo "All processes stopped. Removed $PID_FILE."
fi

echo "Stop script finished."