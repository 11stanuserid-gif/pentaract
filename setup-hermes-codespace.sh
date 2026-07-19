#!/bin/bash
# Hermes Agent Setup Script for GitHub Codespace
# Run this in your codespace terminal

set -e

echo "🔧 Installing Hermes Agent in Codespace..."
echo "============================================"

# Step 1: Install system dependencies
echo ""
echo "📦 Step 1: Installing system dependencies..."
sudo apt-get update && sudo apt-get install -y \
    curl \
    git \
    ripgrep \
    ffmpeg \
    2>/dev/null || true

# Step 2: Install Node.js if not present
echo ""
echo "📦 Step 2: Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null
    sudo apt-get install -y nodejs 2>/dev/null
fi
echo "Node.js: $(node --version 2>/dev/null || echo 'not found')"

# Step 3: Install uv (Python package manager)
echo ""
echo "📦 Step 3: Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null
export PATH="$HOME/.local/bin:$PATH"

# Step 4: Install Hermes Agent
echo ""
echo "📦 Step 4: Installing Hermes Agent..."
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Step 5: Source bashrc
echo ""
echo "🔄 Step 5: Reloading shell..."
source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null || true

# Step 6: Configure Hermes
echo ""
echo "⚙️ Step 6: Configuring Hermes Agent..."

# Set provider to zenmux (free models)
hermes config set provider custom 2>/dev/null || true
hermes config set api_base "https://api.zenmux.ai/v1" 2>/dev/null || true
hermes config set api_key "sk-mg-v1-1f269a8a7f1c9636abb7b2e4624513ad3b3ab57ef6545c0fde5d9060747b33a8" 2>/dev/null || true
hermes config set model "moonshotai/kimi-k3-free" 2>/dev/null || true

# Step 7: Test
echo ""
echo "🧪 Step 7: Testing Hermes Agent..."
hermes --version 2>/dev/null || echo "Hermes installed but version check failed"

echo ""
echo "============================================"
echo "✅ Hermes Agent Installation Complete!"
echo "============================================"
echo ""
echo "🎯 Commands:"
echo "  hermes              # Start chatting"
echo "  hermes model        # Change model"
echo "  hermes config       # View config"
echo "  hermes gateway      # Start Telegram gateway"
echo ""
echo "📱 Telegram Setup:"
echo "  hermes gateway setup"
echo "  hermes gateway start"
echo ""
echo "🔗 Connect to Telegram bot:"
echo "  Token: 8963452565:AAEaraSY0lpwkJ6Z1_0EGyENY7-MM-B3qy0"
echo ""
