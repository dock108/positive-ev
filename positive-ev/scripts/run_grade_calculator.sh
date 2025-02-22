#!/bin/bash

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project root directory
cd "${DIR}/.."

# Activate virtual environment (adjust path if needed)
source venv/bin/activate

# Set environment variables
export FLASK_APP=run.py
export FLASK_ENV=production
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Run the grade calculator
python app/scripts/run_grade_calculator.py

# Deactivate virtual environment
deactivate 