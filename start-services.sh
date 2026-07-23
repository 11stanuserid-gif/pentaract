#!/bin/bash
# Script to start Kimi Code Server + cloudflared tunnel on codespace
set +e

echo "=== start-services.sh ==="

# Kill existing processes
pkill -f "kimi" 2>/dev/null || true
pkill -f cloudflared 2>/dev/null || true
sleep 2

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

# Step 1: Start cloudflared first to get a tunnel URL
# It's OK if nothing is on port 10000 yet - cloudflared will show 502
echo "Starting cloudflared tunnel (phase 1)..."
nohup "$CF_PATH" tunnel --url http://localhost:10000 > /tmp/tunnel2.log 2>&1 &
CF_PID=$!
echo "cloudflared PID: $CF_PID"

# Wait for tunnel URL
TUNNEL_URL=""
echo "Waiting for tunnel URL..."
for i in $(seq 1 30); do
    TUNNEL_URL=$(grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/tunnel2.log 2>/dev/null | tail -1)
    if [ -n "$TUNNEL_URL" ]; then
        echo "Got tunnel URL: $TUNNEL_URL"
        break
    fi
    sleep 2
done

if [ -z "$TUNNEL_URL" ]; then
    echo "Tunnel URL: (timeout)"
    cat /tmp/tunnel2.log 2>/dev/null | tail -10
    exit 1
fi

# Step 2: Start Kimi Code Server with the tunnel URL as allowed host
echo ""
echo "--- Configuring Kimi password ---"
npx -y @moonshot-ai/kimi-code@0.21.0 config set server_password "VNE1wpc7gqGD1THY-Np6WRPYdU5LlOrk3ICvxsy_N58" 2>/dev/null || true

# Extract just the hostname from the tunnel URL
TUNNEL_HOST=$(echo "$TUNNEL_URL" | sed 's|https://||')
echo "--- Starting Kimi Code Server with allowed-host: $TUNNEL_HOST ---"
nohup npx -y @moonshot-ai/kimi-code@0.21.0 server run \
    --port 10000 --host --insecure-no-tls --log-level info \
    --allow-remote-terminals --allow-remote-shutdown \
    --allowed-host "$TUNNEL_HOST" \
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
fi

echo ""
echo "Tunnel URL: $TUNNEL_URL"
echo "Kimi PID: $KIMI_PID"
echo "=== start-services.sh DONE ==="
