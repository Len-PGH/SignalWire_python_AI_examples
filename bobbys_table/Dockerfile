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

# Create a new user 'bobby' with a home directory and add to sudoers
RUN useradd -m -s /bin/bash bobby && \
    echo "bobby ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set the working directory to 'bobby's home
WORKDIR /home/bobby

# Copy the entire repository into the container's 'bobby' home directory
COPY . /home/bobby/SignalWire_python_AI_examples/bobbys_table

# Change ownership of the copied files to 'bobby'
RUN chown -R bobby:bobby /home/bobby/SignalWire_python_AI_examples

# Switch to 'bobby' to run subsequent commands
USER bobby

# Navigate to the bobbys_table directory
WORKDIR /home/bobby/SignalWire_python_AI_examples/bobbys_table

# Convert line endings of the install script to Unix format
RUN dos2unix install_bobbys_table.sh

# Make the install script executable
RUN chmod +x install_bobbys_table.sh

# Execute the install script
ADD install_bobbys_table.sh /home/bobby/SignalWire_python_AI_examples/bobbys_table/

# Ensure the main Python script is executable
RUN chmod +x app.py

# Copy the .env file into the bobbys_table directory

COPY .env /home/bobby/SignalWire_python_AI_examples/bobbys_table/
# RUN sudo ln -s /home/bobby/SignalWire_python_AI_examples/bobbys_table/venv/bin/ngrok /usr/local/bin/ngrok

# Define the entrypoint using JSON array syntax for better signal handling
ENTRYPOINT ["/bin/bash", "-c", "source /home/bobby/SignalWire_python_AI_examples/bobbys_table/install_bobbys_table.sh && source venv/bin/activate && exec python3 app.py"]
