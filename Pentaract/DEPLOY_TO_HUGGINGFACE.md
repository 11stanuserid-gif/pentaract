# Pentaract — Hugging Face Spaces + Neon Deploy Guide (Free, No CC)

## Part A: Free PostgreSQL on Neon

1. Open https://neon.tech/
2. Sign up with **GitHub** (no CC needed)
3. Create a new project → name `pentaract`
4. Copy the connection string:
   ```
   postgres://user:pass@ep-xxx.us-east-2.aws.neon.tech/pentaract?sslmode=require
   ```

## Part B: Deploy Pentaract on Hugging Face Spaces

1. Open https://huggingface.co/
2. Sign up with **GitHub** (no CC needed)
3. Click your profile → **New Space**
4. Configure:
   - **Space Name:** `pentaract`
   - **License:** MIT
   - **Space SDK:** **Docker**
   - **Docker Template:** **Blank**
5. Create Space

## Part C: Upload Dockerfile

In the Space, create a file `Dockerfile` with:

```dockerfile
FROM thedominux/pentaract:latest

ENV PORT=7860

EXPOSE 7860

ENTRYPOINT ["/pentaract"]
```

Or use CLI to push (recommended):
```bash
# Install huggingface-cli
pip install huggingface_hub

# Login (get token from https://huggingface.co/settings/tokens)
huggingface-cli login

# Clone the space
git clone https://huggingface.co/spaces/YOUR_USERNAME/pentaract
cd pentaract

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM thedominux/pentaract:latest
ENV PORT=7860
EXPOSE 7860
ENTRYPOINT ["/pentaract"]
EOF

# Push
git add .
git commit -m "Initial deploy"
git push
```

## Part D: Set Secrets (Environment Variables)

In Space Settings → **Repository Secrets**, add:

| Key | Value |
|---|---|
| `SUPERUSER_EMAIL` | your-email@gmail.com |
| `SUPERUSER_PASS` | your-strong-password |
| `SECRET_KEY` | your-long-random-secret |
| `TELEGRAM_API_BASE_URL` | https://api.telegram.org |
| `WORKERS` | 4 |
| `CHANNEL_CAPACITY` | 32 |
| `ACCESS_TOKEN_EXPIRE_IN_SECS` | 1800 |
| `REFRESH_TOKEN_EXPIRE_IN_DAYS` | 14 |
| `DATABASE_USER` | (from Neon part A) |
| `DATABASE_PASSWORD` | (from Neon part A) |
| `DATABASE_NAME` | pentaract |
| `DATABASE_HOST` | (from Neon part A, the hostname) |
| `DATABASE_PORT` | 5432 |
| `DATABASE_SSLMODE` | require |

## Part E: Keep it 24/7 (Prevent Spin-Down)

Hugging Face Spaces spin down after 48 hours of inactivity.

**Fix:** Use a free uptime monitor:

1. Open https://uptimerobot.com/ (no CC, signup free)
2. Add monitor → HTTP → your Space URL
3. Set check interval: **5 minutes**
4. Save

This will ping your app every 5 minutes, keeping it alive 24/7.

---

**Done!** Your Pentaract is now live on Hugging Face Spaces!
