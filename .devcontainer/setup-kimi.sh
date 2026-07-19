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

# Install localtunnel for public URL
npm install -g localtunnel

# Create keep-alive and server start script
cat > /workspaces/pentaract/start-kimi.sh << 'SCRIPT'
#!/bin/bash
# Start kimi-code server with localtunnel

# Kill any existing kimi-server process
pkill -f "kimi server" 2>/dev/null || true

echo "Starting Kimi Code server on port 10000..."
kimi server run --port 10000 --host --insecure-no-tls --log-level info \
    --allow-remote-terminals --allow-remote-shutdown 2>&1 &

# Wait for server to start
sleep 5

# Create localtunnel for public access
echo "Creating localtunnel for public access..."
lt --port 10000 --subdomain kimi-code-$(echo $RANDOM | md5sum | head -c 8) 2>&1 &

echo ""
echo "=========================================="
echo "  Kimi Code Server is running!"
echo "=========================================="
echo ""
echo "To connect from your kimi CLI:"
echo "  kimi config set server_url https://YOUR-LT-URL.loca.lt"
echo "  kimi config set server_password VNE1wpc7gqGD1THY-Np6WRPYdU5LlOrk3ICvxsy_N58"
echo ""
echo "NOTE: Localtunnel URL changes on each restart."
echo "Check the Codespace logs for the current URL."
SCRIPT

chmod +x /workspaces/pentaract/start-kimi.sh

# Start kimi-code immediately
bash /workspaces/pentaract/start-kimi.sh

echo ""
echo "Setup complete! Kimi Code is running."
