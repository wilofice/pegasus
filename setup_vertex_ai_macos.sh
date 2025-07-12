#!/bin/bash

# This script automates the setup of Google Vertex AI Agent Engine ID
# and updates the backend/.env file for macOS.

# Function to prompt for user input
prompt_for_input() {
    read -p "$1: " input
    echo "$input"
}

# Install gcloud CLI if not already installed
if ! command -v gcloud &> /dev/null
then
    echo "gcloud CLI not found. Installing..."
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null
    then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    echo "Installing google-cloud-sdk via Homebrew..."
    brew install google-cloud-sdk
    echo "gcloud CLI installed."
else
    echo "gcloud CLI is already installed."
fi

# Authenticate gcloud CLI (this command is interactive)
echo "Initializing gcloud CLI. This will open a browser for login and configuration."
gcloud init
gcloud auth application-default login --impersonate-service-account pegasus@gen-lang-client-0319023828.iam.gserviceaccount.com