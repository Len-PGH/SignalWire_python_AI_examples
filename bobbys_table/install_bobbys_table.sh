#!/bin/bash

# ===============================
# Install Script for Debian-based Systems
# ===============================

echo "Starting installation for Debian-based systems..."

# Step 1: Update System and Install Prerequisites
echo "Updating package lists and installing system dependencies..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv curl build-essential libssl-dev libffi-dev python3-dev

# Step 2: Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 installation failed. Please install it manually."
    exit 1
fi
echo "Python 3 found: $(python3 --version)"

# Step 3: Check for pip3 and Install Manually if Missing
if ! command -v pip3 &> /dev/null; then
    echo "pip3 not found. Installing pip3..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    if sudo python3 get-pip.py; then
        echo "pip3 successfully installed."
        rm get-pip.py
    else
        echo "Failed to install pip3. Exiting."
        exit 1
    fi
else
    echo "pip3 found: $(pip3 --version)"
fi

# Step 4: Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating a Python virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created successfully."
fi

# Step 5: Activate Virtual Environment
echo "Activating virtual environment..."
source venv/bin/activate

# Step 6: Install Python Dependencies
echo "Installing Python dependencies..."
cat <<EOF > requirements.txt
flask
requests
python-dotenv
signalwire
signalwire_swaig
EOF

pip3 install --upgrade pip
pip3 install -r requirements.txt

echo "Dependencies installed successfully."

# Step 7: Verify Installation of Required Libraries
echo "Verifying Flask installation..."
if ! pip3 list | grep Flask &> /dev/null; then
    echo "Error: Flask failed to install."
    exit 1
fi
echo "Flask installation verified."

# Step 8: Optional ngrok Installation
if ! command -v ngrok &> /dev/null; then
    echo "ngrok not found. Installing ngrok..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
        sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
        sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt-get update && sudo apt-get install ngrok -y
    echo "ngrok installed successfully."
else
    echo "ngrok found: $(ngrok --version)"
fi

# Step 9: Environment Variable Setup
echo "Creating .env file..."
cat <<EOF > .env
SIGNALWIRE_PROJECT_ID=your_project_id
SIGNALWIRE_TOKEN=your_auth_token
SIGNALWIRE_SPACE=your_space_name
FROM_NUMBER=your_from_number
NGROK_AUTH_TOKEN=your_ngrok_auth_token
NGROK_DOMAIN=your_ngrok_domain
NGROK_PATH=/usr/bin/ngrok
HTTP_USERNAME=admin
HTTP_PASSWORD=password
DEBUG_WEBOOK_URL=http://localhost:5000
EOF

echo "Environment variables written to .env file. Update with your credentials."

# Step 10: Final Instructions
echo "Installation complete!"
echo "Activate your virtual environment with:"
echo "source venv/bin/activate"
echo "Run your Flask app with:"
echo "python3 app.py"
