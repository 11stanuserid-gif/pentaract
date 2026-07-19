#!/bin/bash
set -e

export PATH="$HOME/.local/bin:$PATH"

echo "=== Hermes Agent Starting ==="
echo "Version: $(hermes --version 2>/dev/null || echo 'unknown')"

# Configure model if API key is provided
if [ -n "$HERMES_API_KEY" ]; then
    echo "Configuring model provider..."
    hermes config set provider "${HERMES_PROVIDER:-openrouter}" 2>/dev/null || true
    hermes config set api_key "$HERMES_API_KEY" 2>/dev/null || true
    hermes config set model "${HERMES_MODEL:-openai/gpt-4o-mini}" 2>/dev/null || true
fi

# Start Hermes in gateway mode if TELEGRAM_BOT_TOKEN is set
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Starting Telegram gateway..."
    hermes gateway start --token "$TELEGRAM_BOT_TOKEN" &
    GATEWAY_PID=$!
fi

# Keep container running
echo "Hermes Agent is running."
echo "Use 'hermes' CLI for interactive mode."
echo "Use 'hermes gateway' for messaging platform access."

# If gateway was started, wait for it
if [ -n "$GATEWAY_PID" ]; then
    wait $GATEWAY_PID
else
    # Keep alive
    while true; do
        sleep 3600
    done
fi
