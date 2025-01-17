#!/bin/bash

# ===============================
# Install Script for Debian-based Systems
# ===============================

echo "Starting installation for Debian-based systems..."

# Clean up environment variables and source .env once
if [ -f ".env" ]; then
    sed -i 's/\r//' .env
    set -a
    source .env
else
    echo "Error: .env file not found. Please create it first."
    exit 1
fi

# Check required variables
if [ -z "$NGROK_AUTH_TOKEN" ] || [ -z "$NGROK_DOMAIN" ]; then
    echo "Error: NGROK_AUTH_TOKEN or NGROK_DOMAIN is not set in .env"
    exit 1
fi

# Step 1: Update System and Install Prerequisites
echo "Updating package lists and installing system dependencies..."
sudo apt-get update -y && sudo apt-get dist-upgrade -y
sudo apt-get install -y python3 python3-pip python3-venv curl build-essential libssl-dev libffi-dev python3-dev

# Step 2: Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 installation failed. Please install it manually."
    exit 1
fi
echo "Python 3 found: $(python3 --version)"

# Step 3: Check for pip3
if ! command -v pip3 &> /dev/null; then
    echo "pip3 not found. Installing pip3..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    if sudo python3 get-pip.py; then
        rm get-pip.py
    else
        echo "Failed to install pip3. Exiting."
        exit 1
    fi
fi

# Step 4: Create Virtual Environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created successfully."
fi

source .env
# Step 5: Install ngrok
if ! command -v ngrok &> /dev/null; then
    echo "Installing ngrok..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
        sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
        sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt-get update -y && sudo apt-get install ngrok -y
fi
echo "ngrok version: $(ngrok --version)"

# Configure ngrok
if [ ! -f "/home/roomie/.config/ngrok/ngrok.yml" ]; then
    mkdir -p /home/roomie/.config/ngrok
    touch /home/roomie/.config/ngrok/ngrok.yml
fi
sudo ln -sf /home/roomie/SignalWire_python_AI_examples/roomie_serve/venv/bin/ngrok /usr/local/bin/ngrok
ngrok config add-authtoken "$NGROK_AUTH_TOKEN"
ngrok config upgrade
# Start ngrok and expose the application
echo "Starting ngrok with domain: $NGROK_DOMAIN"
ngrok http --url="$NGROK_DOMAIN" 5000 &
echo "ngrok tunnel started. You can access your app via $NGROK_DOMAIN."

# Step 6: Activate Virtual Environment and Install Dependencies
source venv/bin/activate
cat <<EOF > requirements.txt
flask
requests
python-dotenv
signalwire
signalwire_swaig
pyngrok
EOF
pip install --upgrade pip
pip install -r requirements.txt

# Step 7: Verify Flask Installation
if ! pip list | grep Flask &> /dev/null; then
    echo "Error: Flask failed to install."
    exit 1
fi

# Step 8: Final Instructions
echo "Installation complete!"
echo "Activate your virtual environment with:"
echo "source venv/bin/activate"
echo "Run your Flask app with:"
echo "python3 app.py"
