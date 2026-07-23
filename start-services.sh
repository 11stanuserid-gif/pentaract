#!/bin/bash
# Simple script to start Kimi + cloudflared tunnel on codespace
# This script outputs the tunnel URL at the end

set +e

echo "=== start-services.sh ==="

# Kill existing processes
pkill -f "kimi server" 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true
sleep 2

# Check if kimi binary exists
KIMI_PATH=""
if command -v kimi &>/dev/null; then
    KIMI_PATH=$(command -v kimi)
elif [ -f /home/codespace/.local/bin/kimi ]; then
    KIMI_PATH="/home/codespace/.local/bin/kimi"
elif [ -f /usr/local/bin/kimi ]; then
    KIMI_PATH="/usr/local/bin/kimi"
fi

echo "Kimi binary: ${KIMI_PATH:-not found}"

if [ -n "$KIMI_PATH" ]; then
    # Start Kimi server
    echo "Starting Kimi on port 10000..."
    nohup "$KIMI_PATH" server run --port 10000 --host --insecure-no-tls --allow-remote-terminals --allow-remote-shutdown > /tmp/kimi-startup.log 2>&1 &
    sleep 8

    # Check if Kimi is running
    if curl -s -o /dev/null -w "" http://localhost:10000/ 2>/dev/null; then
        echo "Kimi: UP"
    else
        echo "Kimi: FAILED (port 10000 not responding)"
        cat /tmp/kimi-startup.log 2>/dev/null | tail -10
    fi
else
    echo "Kimi: SKIPPED (binary not available)"
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
