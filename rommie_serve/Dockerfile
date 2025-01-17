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

# Create a new user 'roomie' with a home directory and add to sudoers
RUN useradd -m -s /bin/bash roomie && \
    echo "roomie ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set the working directory to 'roomie's home
WORKDIR /home/roomie

# Copy the repository into the container's 'roomie' home directory
COPY . /home/roomie/SignalWire_python_AI_examples/roomie_serve

# Change ownership of the copied files to 'roomie'
RUN chown -R roomie:roomie /home/roomie/SignalWire_python_AI_examples

# Switch to 'roomie' to run subsequent commands
USER roomie

# Navigate to the roomie_serve directory
WORKDIR /home/roomie/SignalWire_python_AI_examples/roomie_serve

# Convert line endings of the install script to Unix format and make it executable
RUN sudo dos2unix install-roomie-serve.sh && chmod +x install-roomie-serve.sh
COPY .env /home/roomie/SignalWire_python_AI_examples/roomie_serve/
RUN sudo dos2unix /home/roomie/SignalWire_python_AI_examples/roomie_serve/.env
# Execute the install script
RUN ./install-roomie-serve.sh

# Ensure the main Python script is executable
RUN sudo chmod +x app.py

# Copy the .env file into the roomie_serve directory
COPY .env /home/roomie/SignalWire_python_AI_examples/roomie_serve/
# RUN sudo source /etc/environment

# Create a symbolic link for ngrok in /usr/local/bin
# RUN sudo ln -s /home/roomie/SignalWire_python_AI_examples/roomie_serve/venv/bin/ngrok /usr/local/bin/ngrok
RUN mkdir -p /home/roomie/.config/ngrok && chmod -R 755 /home/roomie/.config/ngrok


# Expose the application port
EXPOSE 5000

# Define the entrypoint to activate the virtual environment and start the app
ENTRYPOINT ["/bin/bash", "-c", "source venv/bin/activate && exec python3 app.py"]
