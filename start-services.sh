#!/bin/bash
# Simple script to start Kimi + cloudflared tunnel on codespace
# This script outputs the tunnel URL at the end

set +e

echo "=== start-services.sh ==="

# Kill existing processes
pkill -f "kimi" 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true
sleep 2

# --- Find the right kimi binary ---
# The codespace has kimi v1.49.0 (Python) which doesn't have 'server' command
# We need @moonshot-ai/kimi-code v0.x which has 'kimi server run'

KIMI_BIN=""
KIMI_TYPE=""

# Check all possible locations
for candidate in /home/codespace/.python/current/bin/kimi /usr/local/bin/kimi /home/codespace/.local/bin/kimi /usr/bin/kimi; do
    if [ -x "$candidate" ]; then
        VER=$("$candidate" --version 2>/dev/null | head -1)
        echo "Found kimi at $candidate (version: $VER)"
    fi
done

# Check npm global install
NPM_KIMI=""
if command -v npx &>/dev/null; then
    echo "npx available, can use @moonshot-ai/kimi-code"
fi
if command -v node &>/dev/null; then
    NPM_GLOBAL=$(npm root -g 2>/dev/null)
    if [ -f "$NPM_GLOBAL/@moonshot-ai/kimi-code/index.js" ] || [ -f "$NPM_GLOBAL/@moonshot-ai/kimi-code/cli.js" ]; then
        echo "Found npm kimi-code at $NPM_GLOBAL/@moonshot-ai/kimi-code"
    fi
fi

# Strategy: Use npx to run the right kimi version
# This avoids PATH conflicts and ensures we get v0.21.0 which has 'server run'
echo ""
echo "--- Configuring Kimi password ---"
npx -y @moonshot-ai/kimi-code@0.21.0 config set server_password "VNE1wpc7gqGD1THY-Np6WRPYdU5LlOrk3ICvxsy_N58" 2>/dev/null || true

echo "--- Starting Kimi Code Server (via npx @moonshot-ai/kimi-code@0.21.0) ---"
nohup npx -y @moonshot-ai/kimi-code@0.21.0 server run \
    --port 10000 --host --insecure-no-tls --log-level info \
    --allow-remote-terminals --allow-remote-shutdown \
    > /tmp/kimi-startup.log 2>&1 &
KIMI_PID=$!
echo "Kimi PID: $KIMI_PID"
sleep 10

# Check if Kimi is running
if curl -s -o /dev/null -w "" http://localhost:10000/ 2>/dev/null; then
    echo "Kimi: UP"
else
    echo "Kimi: FAILED (port 10000 not responding)"
    cat /tmp/kimi-startup.log 2>/dev/null | tail -10
    echo ""
    echo "--- Trying alternative: kimi directly with --help ---"
    kimi --help 2>&1 | head -30 || true
fi

# Install cloudflared if not present
CF_PATH="/home/codespace/cloudflared"
if [ ! -f "$CF_PATH" ]; then
    echo "Installing cloudflared..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O "$CF_PATH" 2>&1
    if [ $? -ne 0 ]; then
        echo "cloudflared download failed, trying apt..."
        sudo apt-get install -y cloudflared 2>/dev/null || true
        if command -v cloudflared &>/dev/null; then
            CF_PATH="cloudflared"
        fi
    else
        chmod +x "$CF_PATH"
    fi
fi

echo "cloudflared: $(command -v cloudflared || echo $CF_PATH)"

# Start cloudflared tunnel
echo "Starting cloudflared tunnel..."
nohup "$CF_PATH" tunnel --url http://localhost:10000 > /tmp/tunnel2.log 2>&1 &
CF_PID=$!
echo "cloudflared PID: $CF_PID"

# Wait for URL
echo "Waiting for tunnel URL..."
for i in $(seq 1 20); do
    URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/tunnel2.log 2>/dev/null | tail -1)
    if [ -n "$URL" ]; then
        echo "Tunnel URL: $URL"
        echo "=== start-services.sh DONE ==="
        exit 0
    fi
    sleep 3
done

echo "Tunnel URL: (timeout - showing log)"
cat /tmp/tunnel2.log 2>/dev/null | tail -10
echo "=== start-services.sh FAILED ==="
exit 1
