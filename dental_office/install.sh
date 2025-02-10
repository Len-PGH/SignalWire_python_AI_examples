#!/bin/bash
# install.sh: Setup environment, install dependencies, and initialize the database

set -e

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "python3 could not be found. Please install Python 3."
    exit 1
fi

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install Flask
pip install --upgrade pip
pip install Flask

# Initialize the database if it doesn't exist
if [ ! -f "calendar.db" ]; then
    echo "Initializing database..."
    python -c "from app import init_db; init_db()"
fi

echo "Installation complete. To run the application, execute: python app.py"
