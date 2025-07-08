#!/bin/bash

# Configuration
TUNNEL_NAME="pegasus-backend"
BACKEND_PORT=8000
CONFIG_FILE=".cloudflared/config.yml"

# --- Installation ---
if ! command -v cloudflared &> /dev/null; then
    echo "🔍 cloudflared not found. Installing..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        wget -q -O cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
        chmod +x cloudflared
        sudo mv cloudflared /usr/local/bin/
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew is not installed. Please install it from https://brew.sh/"
            exit 1
        fi
        brew install cloudflared
    else
        echo "❌ Unsupported OS for automatic installation: $OSTYPE"
        exit 1
    fi
    echo "✅ cloudflared installed."
fi

# --- Authentication & Tunnel Creation ---
if [ ! -f ~/.cloudflared/cert.pem ]; then
    echo "⚠️ You need to authenticate with Cloudflare."
    echo "Please run 'cloudflared tunnel login' and follow the instructions."
    exit 1
fi

if ! cloudflared tunnel list | grep -q $TUNNEL_NAME; then
    echo "🚀 Creating tunnel '$TUNNEL_NAME'..."
    cloudflared tunnel create $TUNNEL_NAME
fi

# --- Configuration ---
mkdir -p .cloudflared
if [ ! -f "$CONFIG_FILE" ]; then
    echo "📝 Creating config file for tunnel '$TUNNEL_NAME'..."
    cat <<EOF > $CONFIG_FILE
tunnel: $TUNNEL_NAME
credentials-file: /home/mica/.cloudflared/$(cloudflared tunnel list | grep $TUNNEL_NAME | awk '{print $1}').json

ingress:
  - hostname: $TUNNEL_NAME.yourdomain.com # <-- IMPORTANT: Change this to your domain
    service: http://localhost:$BACKEND_PORT
  - service: http_status:404
EOF
    echo "✅ Config file created at $CONFIG_FILE"
    echo "🛑 IMPORTANT: Please edit the hostname in $CONFIG_FILE to your domain."
    exit 0
fi

# --- Start Tunnel ---
echo "🌐 Starting tunnel '$TUNNEL_NAME'..."
cloudflared tunnel --config $CONFIG_FILE run