#!/bin/bash
# Central script to run all cron jobs for the betting chatbot

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

# Set up log directory
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Log file
LOG_FILE="$LOG_DIR/cron_jobs.log"

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting cron jobs..."

# Refresh betting data
log "Running refresh_data.py..."
python3 "$SCRIPT_DIR/refresh_data.py"
if [ $? -eq 0 ]; then
    log "refresh_data.py completed successfully"
else
    log "ERROR: refresh_data.py failed"
fi

# Enforce timeouts
log "Running enforce_timeouts.py..."
python3 "$SCRIPT_DIR/enforce_timeouts.py"
if [ $? -eq 0 ]; then
    log "enforce_timeouts.py completed successfully"
else
    log "ERROR: enforce_timeouts.py failed"
fi

log "All cron jobs completed"

# Example crontab entries:
#
# # Refresh betting data every hour
# 0 * * * * /path/to/betting-chatbot/scripts/cron_jobs.sh
#
# # Or run individual scripts:
# # Refresh betting data every hour
# 0 * * * * /path/to/betting-chatbot/scripts/refresh_data.py
# # Enforce timeouts every 15 minutes
# */15 * * * * /path/to/betting-chatbot/scripts/enforce_timeouts.py
