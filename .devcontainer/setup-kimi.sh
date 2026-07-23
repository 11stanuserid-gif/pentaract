#!/bin/bash
# Kimi Code setup for GitHub Codespace
# Runs automatically when Codespace starts

set -e

echo "=========================================="
echo "  Setting up Kimi Code Server..."
echo "=========================================="

# Install kimi-code globally
npm install -g @moonshot-ai/kimi-code@0.21.0

# Configure server password
kimi config set server_password "VNE1wpc7gqGD1THY-Np6WRPYdU5LlOrk3ICvxsy_N58"

# Install cloudflared for reliable tunnel
echo "Installing cloudflared..."
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /home/codespace/cloudflared
chmod +x /home/codespace/cloudflared

# Create keep-alive and server start script
cat > /workspaces/pentaract/start-kimi.sh << 'SCRIPT'
#!/bin/bash
# Start kimi-code server with public tunnel

# Kill any existing kimi-server process
pkill -f "kimi server" 2>/dev/null || true

echo "Starting Kimi Code server on port 10000..."
kimi server run --port 10000 --host --insecure-no-tls --log-level info \
    --allow-remote-terminals --allow-remote-shutdown 2>&1 &

# Wait for server to start
sleep 5

# Kill any old cloudflared
pkill -f cloudflared 2>/dev/null || true
sleep 1

# Start cloudflared tunnel for reliable public access
echo "Creating cloudflared tunnel for public access..."
nohup /home/codespace/cloudflared tunnel --url http://localhost:10000 > /tmp/tunnel2.log 2>&1 &

echo ""
echo "=========================================="
echo "  Kimi Code Server is running!"
echo "=========================================="
echo ""
echo "Tunnel URL will appear in /tmp/tunnel2.log"
echo "Run: grep -oP 'https://[a-z0-9-]+\.trycloudflare\.com' /tmp/tunnel2.log | tail -1"
echo ""
echo "To connect from your kimi CLI:"
echo "  kimi config set server_url TUNNEL_URL"
echo "  kimi config set server_password VNE1wpc7gqGD1THY-Np6WRPYdU5LlOrk3ICvxsy_N58"
echo ""
SCRIPT

chmod +x /workspaces/pentaract/start-kimi.sh

# Start services immediately
bash /workspaces/pentaract/start-kimi.sh

echo ""
echo "Setup complete! Kimi Code is running."
