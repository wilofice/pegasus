#!/bin/bash

# This script automates the setup of Google Vertex AI Agent Engine ID
# and updates the backend/.env file for Ubuntu.

# Function to prompt for user input
prompt_for_input() {
    read -p "$1: " input
    echo "$input"
}

# Install gcloud CLI if not already installed
if ! command -v gcloud &> /dev/null
then
    echo "gcloud CLI not found. Installing..."
    sudo apt-get update
    sudo apt-get install apt-transport-https ca-certificates gnupg curl -y
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
    sudo apt-get update
    sudo apt-get install google-cloud-sdk -y
    echo "gcloud CLI installed."
else
    echo "gcloud CLI is already installed."
fi

# Authenticate gcloud CLI (this command is interactive)
echo "Initializing gcloud CLI. This will open a browser for login and configuration."
gcloud init

# Get the project ID from the current gcloud config
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "No project is configured. Please run 'gcloud init' again and select a project."
    exit 1
fi
echo "Using project: $PROJECT_ID"

LOCATION="us-central1" # Default location as per documentation

echo "Enabling required Google Cloud APIs..."
gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID
gcloud services enable vertexai.googleapis.com --project=$PROJECT_ID
gcloud services enable storage.googleapis.com --project=$PROJECT_ID

# Create a unique bucket name for staging
STAGING_BUCKET="gs://${PROJECT_ID}-vertex-ai-staging"
echo -e "\nA staging bucket is required for Vertex AI to store temporary files."
echo "The script will use the following bucket: $STAGING_BUCKET"
echo "Checking if the bucket exists..."

if gsutil ls "$STAGING_BUCKET" &>/dev/null; then
    echo "Staging bucket already exists."
else
    echo "Staging bucket not found. Creating it now..."
    gsutil mb -p "$PROJECT_ID" -l "$LOCATION" "$STAGING_BUCKET"
    if [ $? -eq 0 ]; then
        echo "Bucket created successfully."
    else
        echo "Failed to create bucket. Please check your permissions or create it manually in the Google Cloud Console."
        exit 1
    fi
fi

# Install google-cloud-aiplatform Python package
echo "Installing google-cloud-aiplatform Python package..."
pip install "google-cloud-aiplatform[all]==1.71.1" "langchain-google-vertexai"


# Python script to create the agent engine
LOCATION="us-central1"

AGENT_ENGINE_ID=$(PROJECT_ID="$PROJECT_ID" LOCATION="$LOCATION" python -c '
import os
import sys
import vertexai
from vertexai.preview import reasoning_engines
from langchain_google_vertexai import VertexAI

try:
    project_id = os.environ["PROJECT_ID"]
    location = os.environ["LOCATION"]
    vertexai.init(project=project_id, location=location)
    model = VertexAI(model_name="gemini-1.5-pro-001")
    agent = reasoning_engines.LangchainAgent(
        model=model,
        tools=[],
    )
    reasoning_engine = reasoning_engines.ReasoningEngine.create(
        agent,
        requirements=[
            "google-cloud-aiplatform[langchain,agent_engines]"
        ]
    )
    print(reasoning_engine.name.split("/")[-1])
except Exception as e:
    print(f"Error creating reasoning engine: {e}", file=sys.stderr)
    exit(1)
')

if [[ -z "$AGENT_ENGINE_ID" ]]; then
    echo "Failed to create Agent Engine ID. Please check the output above for errors."
    exit 1
fi

echo "Vertex AI Agent Engine created successfully."
echo "Agent Engine ID: $AGENT_ENGINE_ID"
)

AGENT_ENGINE_OUTPUT=$(python -c "$PYTHON_SCRIPT" 2>&1)
AGENT_ENGINE_ID=$(echo "$AGENT_ENGINE_OUTPUT" | grep -oP 'AGENT_ENGINE_ID_OUTPUT:\K[^ ]+')

if [ -z "$AGENT_ENGINE_ID" ]; then
    echo "Failed to extract Agent Engine ID. Please check the output above for errors."
    echo "Agent Engine creation output: $AGENT_ENGINE_OUTPUT"
    exit 1
fi

echo "Extracted Agent Engine ID: $AGENT_ENGINE_ID"

SCRIPT_DIR="$(dirname "$0")"
ENV_FILE="$SCRIPT_DIR/backend/.env"
ENV_EXAMPLE_FILE="$SCRIPT_DIR/backend/.env.example"

echo "Updating or creating $ENV_FILE..."

# Check if .env file exists, if not, create it from .env.example
if [ ! -f "$ENV_FILE" ]; then
    echo "backend/.env not found. Creating from backend/.env.example"
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
fi

# Update or add Vertex AI configuration
sed -i '/# Vertex AI Configuration/d' "$ENV_FILE"
sed -i '/LLM_PROVIDER=vertex_ai/d' "$ENV_FILE"
sed -i '/VERTEX_AI_PROJECT_ID=/d' "$ENV_FILE"
sed -i '/VERTEX_AI_LOCATION=/d' "$ENV_FILE"
sed -i '/VERTEX_AI_AGENT_ENGINE_ID=/d' "$ENV_FILE"
sed -i '/VERTEX_AI_MODEL=/d' "$ENV_FILE"
sed -i '/VERTEX_AI_TIMEOUT=/d' "$ENV_FILE"
sed -i '/VERTEX_AI_TEMPERATURE=/d' "$ENV_FILE"
sed -i '/VERTEX_AI_MAX_TOKENS=/d' "$ENV_FILE"
sed -i '/VERTEX_AI_TOP_K=/d' "$ENV_FILE"
sed -i '/VERTEX_AI_TOP_P=/d' "$ENV_FILE"
sed -i '/GOOGLE_APPLICATION_CREDENTIALS=/d' "$ENV_FILE"

cat << EOF >> "$ENV_FILE"

# LLM Provider
LLM_PROVIDER=vertex_ai

# Vertex AI Configuration
VERTEX_AI_PROJECT_ID=$PROJECT_ID
VERTEX_AI_LOCATION=$LOCATION
VERTEX_AI_AGENT_ENGINE_ID=$AGENT_ENGINE_ID
VERTEX_AI_MODEL=gemini-2.0-flash
VERTEX_AI_TIMEOUT=60.0
VERTEX_AI_TEMPERATURE=0.7
VERTEX_AI_MAX_TOKENS=2048
VERTEX_AI_TOP_K=40
VERTEX_AI_TOP_P=0.95

# Authentication (if using service account)
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
EOF

echo "Successfully updated $ENV_FILE with Vertex AI configuration."
echo "Please review the $ENV_FILE file and uncomment/update GOOGLE_APPLICATION_CREDENTIALS if using a service account."