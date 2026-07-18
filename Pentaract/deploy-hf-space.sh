#!/bin/bash
# Pentaract - Hugging Face Spaces Deploy Script
# No credit card needed. Free tier: 2 vCPU, 16GB RAM

set -e

echo "=========================================="
echo "  Pentaract - Hugging Face Spaces Deploy"
echo "=========================================="
echo ""

# ─── Step 1: Check prerequisites ───
echo "[1/5] Checking prerequisites..."

if ! command -v git &> /dev/null; then
    echo "ERROR: git is required. Install it first."
    exit 1
fi

if ! command -v huggingface-cli &> /dev/null; then
    echo "Installing huggingface_hub..."
    pip install huggingface_hub -q
fi

echo "  OK - git and huggingface-cli available"
echo ""

# ─── Step 2: Login to Hugging Face ───
echo "[2/5] Login to Hugging Face"
echo "  Go to https://huggingface.co/settings/tokens"
echo "  Create a token with 'write' access"
echo ""
read -sp "  Paste your HF token (input hidden): " HF_TOKEN
echo ""
huggingface-cli login --token "$HF_TOKEN"
echo "  Login successful!"
echo ""

# ─── Step 3: Ask user details ───
echo "[3/5] Configuration"
read -p "  Your Hugging Face username: " HF_USER
read -p "  Space name (default: pentaract): " SPACE_NAME
SPACE_NAME=${SPACE_NAME:-pentaract}

echo ""
echo "  Creating Space '$SPACE_NAME' for user '$HF_USER'..."

# Create the space via API
curl -s -X POST "https://huggingface.co/api/spaces" \
  -H "Authorization: Bearer $HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"$SPACE_NAME\",
    \"organization\": null,
    \"sdk\": \"docker\",
    \"type\": \"space\"
  }" > /dev/null

echo "  Space created!"
echo ""

# ─── Step 4: Clone and prepare Space ───
echo "[4/5] Preparing deployment files..."

rm -rf "/tmp/$SPACE_NAME" 2>/dev/null
git clone "https://huggingface.co/spaces/$HF_USER/$SPACE_NAME" "/tmp/$SPACE_NAME"
cd "/tmp/$SPACE_NAME"

# Dockerfile for Spaces
cat > Dockerfile << 'DOCKEREOF'
FROM thedominux/pentaract:latest

ENV PORT=7860
EXPOSE 7860

ENTRYPOINT ["/pentaract"]
DOCKEREOF

# Generate .env for local reference
cat > .env.example << 'ENVEOF'
# ─── Pentaract Environment Variables ───
PORT=7860
WORKERS=4
CHANNEL_CAPACITY=32

# Admin account
SUPERUSER_EMAIL=your-email@example.com
SUPERUSER_PASS=your-strong-password

# Security
ACCESS_TOKEN_EXPIRE_IN_SECS=1800
REFRESH_TOKEN_EXPIRE_IN_DAYS=14
SECRET_KEY=openssl rand -hex 32 (GENERATE THIS)

# Telegram
TELEGRAM_API_BASE_URL=https://api.telegram.org

# PostgreSQL (use Neon free tier - neon.tech)
DATABASE_USER=pentaract
DATABASE_PASSWORD=your-db-password
DATABASE_NAME=pentaract
DATABASE_HOST=ep-xxx.us-east-2.aws.neon.tech
DATABASE_PORT=5432
DATABASE_SSLMODE=require
ENVEOF

# README
cat > README.md << 'READMEEOF'
---
title: Pentaract
emoji: 📁
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Pentaract - Cloud Storage on Telegram

Deployed on Hugging Face Spaces Free Tier.

## Setup

Set these Secrets in Space Settings → Repository Secrets:

| Secret Key | Description |
|---|---|
| SUPERUSER_EMAIL | Admin email |
| SUPERUSER_PASS | Admin password |
| SECRET_KEY | Random hex string (run: openssl rand -hex 32) |
| TELEGRAM_API_BASE_URL | https://api.telegram.org |
| DATABASE_USER | PostgreSQL user (from Neon) |
| DATABASE_PASSWORD | PostgreSQL password (from Neon) |
| DATABASE_NAME | Database name |
| DATABASE_HOST | PostgreSQL host (from Neon) |
| DATABASE_PORT | 5432 |
| DATABASE_SSLMODE | require |
READMEEOF

git add .
git commit -m "Initial deploy: Pentaract"

echo ""

# ─── Step 5: Push and deploy ───
echo "[5/5] Deploying to Hugging Face Spaces..."
git push

echo ""
echo "=========================================="
echo "  DEPLOY COMPLETE!"
echo "=========================================="
echo ""
echo "  App URL: https://$HF_USER-$SPACE_NAME.hf.space"
echo ""
echo "  IMPORTANT: Set Secrets in Space Settings:"
echo "  https://huggingface.co/spaces/$HF_USER/$SPACE_NAME/settings"
echo ""
echo "  Required Secrets (from Neon free PostgreSQL):"
echo "  1. Go to https://neon.tech → Sign up with GitHub (no CC)"
echo "  2. Create project → copy connection string"
echo "  3. Set these in HF Spaces Secrets:"
echo "     - SUPERUSER_EMAIL"
echo "     - SUPERUSER_PASS"
echo "     - SECRET_KEY (run: openssl rand -hex 32)"
echo "     - DATABASE_USER"
echo "     - DATABASE_PASSWORD"
echo "     - DATABASE_NAME"
echo "     - DATABASE_HOST"
echo "     - DATABASE_PORT=5432"
echo "     - DATABASE_SSLMODE=require"
echo ""
echo "  4. Set up UptimeRobot (free, no CC) to keep it 24/7:"
echo "     https://uptimerobot.com → Add monitor → your Space URL"
echo ""
echo "=========================================="
