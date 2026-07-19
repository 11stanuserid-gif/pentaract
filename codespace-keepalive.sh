#!/bin/bash
# Codespace Keep-Alive Script
# Runs on Render to keep GitHub Codespace active 24/7

CODESPACE_URL="https://turbo-space-enigma-vpv5g6vp6pjxcwg6x.github.dev"
GITHUB_TOKEN="${GITHUB_TOKEN:?Set GITHUB_TOKEN env var}"

echo "Starting Codespace Keep-Alive..."
echo "Target: $CODESPACE_URL"
echo "Interval: Every 5 minutes"

# Function to check codespace status
check_status() {
    STATUS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user/codespaces/turbo-space-enigma-vpv5g6vp6pjxcwg6x | jq -r '.state')
    echo "Status: $STATUS"
    return $([ "$STATUS" = "Available" ] && echo 0 || echo 1)
}

# Function to wake up codespace if sleeping
wake_codespace() {
    curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user/codespaces/turbo-space-enigma-vpv5g6vp6pjxcwg6x/start
}

# Function to send keep-alive request
send_keepalive() {
    # Try to access the codespace web interface
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$CODESPACE_URL" 2>/dev/null)
    echo "Keep-alive sent - HTTP: $HTTP_CODE"
}

# Main loop
while true; do
    echo "[$(date)] Running keep-alive check..."
    
    # Check if codespace is available
    if ! check_status; then
        echo "Codespace not available, attempting to wake..."
        wake_codespace
        sleep 10
    fi
    
    # Send keep-alive
    send_keepalive
    
    echo "Next check in 5 minutes..."
    sleep 300
done
