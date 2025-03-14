#!/bin/bash

# Change to the project directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting pipeline at $(date)"

# Run the scraper
echo "Running scraper..."
python src/scraper.py
scraper_exit=$?

# Run the grade calculator
echo "Running grade calculator..."
python src/grade_calculator.py
calculator_exit=$?

# Check if both ran successfully
if [ $scraper_exit -eq 0 ] && [ $calculator_exit -eq 0 ]; then
    echo "Pipeline completed successfully at $(date)"
    exit 0
else
    echo "Pipeline failed at $(date)"
    exit 1
fi 