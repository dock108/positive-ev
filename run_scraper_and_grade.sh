#!/bin/bash

# Set environment variables for cron
export PATH="$PATH:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export HOME="/Users/mikefucs"

# Set DISPLAY for GUI applications (needed for Chrome)
export DISPLAY=:0

# Load user profile to get environment variables
[ -f "$HOME/.zshrc" ] && source "$HOME/.zshrc"
[ -f "$HOME/.bash_profile" ] && source "$HOME/.bash_profile"

# Set the working directory
cd /Users/mikefucs/Desktop/positive-ev

# Load environment variables from .env file
[ -f ".env" ] && export $(grep -v '^#' .env | xargs)

# Activate virtual environment
source venv/bin/activate

# Log start time
echo "Started run at $(date)" >> /Users/mikefucs/Desktop/positive-ev/logs/cron_log.txt

# Run the scraper with Python from virtual environment
python src/scraper.py

# Run the grade calculator after scraper completes
python src/grade_calculator.py

# Log completion time
echo "Completed run at $(date)" >> /Users/mikefucs/Desktop/positive-ev/logs/cron_log.txt
