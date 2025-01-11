# Use Debian 12 as the base image
FROM debian:12

# Set environment variables to non-interactive to avoid prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package lists and install necessary system packages
RUN apt-get update && \
    apt-get install -y \
        git \
        python3 \
        sudo \
        dos2unix \
        nano \
        python3-venv \
        python3-pip \
        curl \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev \
        ca-certificates \
        bash \
    && rm -rf /var/lib/apt/lists/*

# Create a new user 'mfauser' with a home directory and add to sudoers
RUN useradd -m -s /bin/bash mfauser && \
    echo "mfauser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set the working directory to 'mfauser's home
WORKDIR /home/mfauser

# Copy the entire repository into the container's 'mfauser' home directory
COPY . /home/mfauser/SignalWire_python_AI_examples/MFA-Bot

# Change ownership of the copied files to 'mfauser'
RUN chown -R mfauser:mfauser /home/mfauser/SignalWire_python_AI_examples

# Switch to 'mfauser' to run subsequent commands
USER mfauser

# Navigate to the MFA-Bot directory
WORKDIR /home/mfauser/SignalWire_python_AI_examples/MFA-Bot

# Convert line endings of the install script to Unix format
RUN dos2unix install-mfa-bot-v1.sh

# Make the install script executable
RUN chmod +x install-mfa-bot-v1.sh

# Execute the install script
RUN ./install-mfa-bot-v1.sh

# Ensure the main Python script is executable
RUN chmod +x app.py

# Copy the .env file into the MFA-Bot directory
COPY .env /home/mfauser/SignalWire_python_AI_examples/MFA-Bot/.env

# Define the entrypoint using JSON array syntax for better signal handling
ENTRYPOINT ["/bin/bash", "-c", "source venv/bin/activate && exec python3 app.py"]
