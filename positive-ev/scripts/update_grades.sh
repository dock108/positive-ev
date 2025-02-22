#!/bin/bash

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment (adjust path as needed)
source "${DIR}/../venv/bin/activate"

# Change to the application directory
cd "${DIR}/.."

# Set the FLASK_APP environment variable
export FLASK_APP=run.py

# Run the grade calculator script
python -c "from app.scripts.grade_calculator import calculate_grades; calculate_grades()"

# Deactivate virtual environment
deactivate 