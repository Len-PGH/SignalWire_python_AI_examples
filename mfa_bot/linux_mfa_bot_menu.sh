#!/usr/bin/env bash
# ============================================================================
# Bash Script: Build 'mfa-bot-image' and Manage Containers on Debian
#
# 1) Create new container from 'mfa-bot-image'
# 2) Start existing container (multi-try)
# 3) List & stop a running container
# 4) Exit
#
# Checks if Docker is installed; if not, offers to install Docker using
# 'apt-get install docker.io' (Debian-specific). Adjust as needed for other distros.
# ============================================================================

# Config: Wait time (seconds) & max tries
WAIT_TIME=5
MAX_TRIES=4

# ----------------------------------------------------------------------------
# 0. Check if Docker is installed, else prompt to install (Debian-specific)
# ----------------------------------------------------------------------------
check_and_install_docker() {
  if ! command -v docker &>/dev/null; then
    echo "Docker is not installed on this system."
    read -rp "Would you like to install Docker now? [y/N]: " installChoice
    if [[ "$installChoice" =~ ^[Yy]$ ]]; then
      echo "Attempting to install Docker (Debian example)..."
      sudo apt-get update
      sudo apt-get install -y docker.io

      # Check if Docker is installed now
      if ! command -v docker &>/dev/null; then
        echo "Docker installation failed or is not in PATH."
        exit 1
      else
        echo "Docker installed successfully."
      fi
    else
      echo "Docker is required to run this script. Exiting..."
      exit 1
    fi
  else
    echo "Docker is already installed."
  fi
}

# ----------------------------------------------------------------------------
# 1. Build Docker Image (mfa-bot-image)
# ----------------------------------------------------------------------------
build_image() {
  echo
  echo "============================================"
  echo "Building Docker image 'mfa-bot-image'..."
  echo "============================================"
  if ! docker build -t "mfa-bot-image" .; then
    echo "Docker build failed. Check your Dockerfile and try again."
    read -rp "Press Enter to continue..."
    exit 1
  fi
}

# ----------------------------------------------------------------------------
# 2. Main Menu
# ----------------------------------------------------------------------------
main_menu() {
  while true; do
    echo
    echo "============================================"
    echo "               Main Menu"
    echo "============================================"
    echo "1) Create a new container"
    echo "2) Start an existing container"
    echo "3) List and stop a running container"
    echo "4) Exit"
    echo "============================================"

    read -rp "Enter your choice (1, 2, 3, or 4): " choice
    case "$choice" in
      1) create_new_container ;;
      2) start_existing_container ;;
      3) stop_running_container ;;
      4) 
         echo
         echo "============================================"
         echo " Operation Completed - Exiting"
         echo "============================================"
         read -rp "Press Enter to continue..."
         exit 0
         ;;
      *)
         echo
         echo "Invalid choice. Please enter 1, 2, 3, or 4."
         ;;
    esac
  done
}

# ----------------------------------------------------------------------------
# Option 1: Create a New Container from 'mfa-bot-image'
# ----------------------------------------------------------------------------
create_new_container() {
  echo
  echo "============================================"
  echo "     Create a New Container"
  echo "============================================"
  read -rp "Name for new container (default: mfa-bot-container): " containerName
  if [ -z "$containerName" ]; then
    containerName="mfa-bot-container"
  fi

  echo "Checking if '$containerName' already exists..."
  if docker ps -a --format '{{.Names}}' | grep -wq "$containerName"; then
    echo "A container named '$containerName' already exists."
    echo "Pick another name or remove the existing container."
    read -rp "Press Enter to continue..."
    return
  fi

  echo
  echo "Creating container '$containerName' from 'mfa-bot-image' with Bash..."
  docker run -it --name "$containerName" "mfa-bot-image" bash
}

# ----------------------------------------------------------------------------
# Option 2: Start an Existing Container (List all, multi-try)
# ----------------------------------------------------------------------------
start_existing_container() {
  echo
  echo "============================================"
  echo "  Start an Existing Container (All)"
  echo "============================================"

  echo "Retrieving all containers (running or stopped)..."
  mapfile -t allContainers < <(docker ps -a --format '{{.Names}}')

  if [ "${#allContainers[@]}" -eq 0 ]; then
    echo "No containers exist on this system."
    read -rp "Press Enter to continue..."
    return
  fi

  # Display the containers
  local i=1
  for cName in "${allContainers[@]}"; do
    echo "$i. $cName"
    ((i++))
  done

  local max="${#allContainers[@]}"
  echo
  read -rp "Enter the number of the container to start: " selection

  # Validate numeric input
  if ! [[ "$selection" =~ ^[0-9]+$ ]]; then
    echo
    echo "Invalid selection. Must be a number between 1 and $max."
    read -rp "Press Enter to continue..."
    return
  fi

  if (( selection < 1 || selection > max )); then
    echo
    echo "Invalid selection. Must be between 1 and $max."
    read -rp "Press Enter to continue..."
    return
  fi

  local chosenIndex=$(( selection - 1 ))
  local chosen="${allContainers[$chosenIndex]}"

  echo
  echo "Checking if container '$chosen' is running..."
  if docker ps --format '{{.Names}}' | grep -wq "$chosen"; then
    echo "'$chosen' is already running."
    open_container_bash "$chosen"
    return
  fi

  echo "'$chosen' is not running. Using multi-try logic..."

  local tries=1
  while (( tries <= MAX_TRIES )); do
    echo
    echo "Try #$tries: Starting '$chosen'..."
    if docker start "$chosen" >start_out.txt 2>start_err.txt; then
      echo "Container '$chosen' started successfully."
      cat start_out.txt
      rm -f start_out.txt start_err.txt
      post_start_wait "$chosen"
      return
    else
      echo "Failed to start '$chosen' on try #$tries."
      cat start_err.txt
      rm -f start_out.txt start_err.txt
      ((tries++))
      if (( tries > MAX_TRIES )); then
        echo
        echo "Tried $MAX_TRIES times but cannot start '$chosen'."
        read -rp "Press Enter to continue..."
        return
      fi
      echo "Wait $WAIT_TIME seconds..."
      sleep "$WAIT_TIME"
    fi
  done
}

# After starting the container, wait a bit and confirm it's running, then attach
post_start_wait() {
  local containerName="$1"
  echo
  echo "Waiting $WAIT_TIME seconds for '$containerName' to be ready..."
  sleep "$WAIT_TIME"

  echo "Checking if '$containerName' is now running..."
  if ! docker ps --format '{{.Names}}' | grep -wq "$containerName"; then
    echo "Container '$containerName' not found as running after attempts."
    read -rp "Press Enter to continue..."
    return
  fi

  open_container_bash "$containerName"
}

# Attach Bash to a running container
open_container_bash() {
  local cName="$1"
  echo
  echo "Opening Bash shell in '$cName'..."
  docker exec -it "$cName" bash
  echo "Returned from Bash in '$cName'."
  read -rp "Press Enter to continue..."
}

# ----------------------------------------------------------------------------
# Option 3: List & Stop a Running Container
# ----------------------------------------------------------------------------
stop_running_container() {
  echo
  echo "============================================"
  echo "  List & Stop a Running Container"
  echo "============================================"

  echo "Retrieving currently running containers..."
  mapfile -t runningContainers < <(docker ps --format '{{.Names}}')

  if [ "${#runningContainers[@]}" -eq 0 ]; then
    echo "No running containers found."
    read -rp "Press Enter to continue..."
    return
  fi

  # Display running containers
  local i=1
  for rName in "${runningContainers[@]}"; do
    echo "$i. $rName"
    ((i++))
  done

  local max="${#runningContainers[@]}"
  echo
  read -rp "Enter the number of the running container to stop: " sPick

  # Validate numeric input
  if ! [[ "$sPick" =~ ^[0-9]+$ ]]; then
    echo
    echo "Invalid selection. Must be between 1 and $max."
    read -rp "Press Enter to continue..."
    return
  fi

  if (( sPick < 1 || sPick > max )); then
    echo
    echo "Invalid selection. Must be between 1 and $max."
    read -rp "Press Enter to continue..."
    return
  fi

  local stopIndex=$(( sPick - 1 ))
  local stopName="${runningContainers[$stopIndex]}"

  echo "Attempting to stop '$stopName'..."
  if docker stop "$stopName" >stop_out.txt 2>stop_err.txt; then
    echo "Container '$stopName' stopped successfully."
    cat stop_out.txt
    rm -f stop_out.txt stop_err.txt
  else
    echo "Failed to stop '$stopName'."
    cat stop_err.txt
    rm -f stop_out.txt stop_err.txt
  fi

  read -rp "Press Enter to continue..."
}

# ----------------------------------------------------------------------------
# Main Execution
# ----------------------------------------------------------------------------

# (1) Check if Docker is installed; if not, offer to install with "apt-get install docker.io"
check_and_install_docker

# (2) Build Docker image 'mfa-bot-image'
build_image

# (3) Main menu loop
main_menu
