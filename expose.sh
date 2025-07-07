#!/bin/bash

# Configuration
BACKEND_PORT=8000

echo "🚀 Starting Cloudflare Tunnel to your local service on port $BACKEND_PORT"

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "🔍 cloudflared not found. Installing..."

    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        wget -O cloudflared.tgz https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.tgz
        tar -xvzf cloudflared.tgz
        sudo mv cloudflared /usr/local/bin/
        rm cloudflared.tgz
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install cloudflared || {
            echo "🍎 Please install Homebrew first: https://brew.sh/"
            exit 1
        }
    else
        echo "❌ Unsupported OS: $OSTYPE"
        exit 1
    fi
fi

echo "✅ cloudflared is installed."

# Start the tunnel
echo "🌐 Starting tunnel..."
cloudflared tunnel --url http://localhost:$BACKEND_PORT
