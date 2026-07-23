#!/bin/bash
# Simple script to start Kimi + cloudflared tunnel on codespace
# This script outputs the tunnel URL at the end

set -e

# Kill existing processes
pkill -f "kimi server" 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true
sleep 2

# Start Kimi server
echo "Starting Kimi on port 10000..."
nohup kimi server run --port 10000 --host --insecure-no-tls --allow-remote-terminals --allow-remote-shutdown > /tmp/kimi-startup.log 2>&1 &
sleep 8

# Check if Kimi is running
if curl -s -o /dev/null -w "" http://localhost:10000/ 2>/dev/null; then
    echo "Kimi: UP"
else
    echo "Kimi: FAILED"
    exit 1
fi

# Install cloudflared if not present
if [ ! -f /home/codespace/cloudflared ]; then
    echo "Installing cloudflared..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /home/codespace/cloudflared
    chmod +x /home/codespace/cloudflared
fi

# Start cloudflared tunnel
echo "Starting cloudflared tunnel..."
nohup /home/codespace/cloudflared tunnel --url http://localhost:10000 > /tmp/tunnel2.log 2>&1 &

# Wait for URL
echo "Waiting for tunnel URL..."
for i in $(seq 1 15); do
    URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/tunnel2.log 2>/dev/null | tail -1)
    if [ -n "$URL" ]; then
        echo "Tunnel URL: $URL"
        exit 0
    fi
    sleep 3
done

echo "Tunnel URL: (timeout)"
exit 1
