# Pentaract — Back4app Deploy Guide (Free, No CC)

## Step 1: Sign up on Back4app
1. Open https://www.back4app.com/
2. Click **Sign Up** → **Continue with GitHub**
3. No credit card needed

## Step 2: Create a New App
1. Dashboard → **Create new app**
2. Choose **Docker** as the container type
3. App name: `pentaract` (or anything)
4. Choose **Free** plan

## Step 3: Configure Docker Image
- Image repository: `thedominux/pentaract`
- Tag: `latest`
- Port: `8000`

## Step 4: Add PostgreSQL Database
1. Back4app provides built-in PostgreSQL
2. Go to your app → **Database**
3. Create a new PostgreSQL database (free tier)
4. Note down the credentials (host, port, user, password, database name)

## Step 5: Set Environment Variables
In your app → **Environment Variables**, add:

```
PORT=8000
WORKERS=4
CHANNEL_CAPACITY=32
SUPERUSER_EMAIL=your-email@gmail.com
SUPERUSER_PASS=your-strong-password-here
ACCESS_TOKEN_EXPIRE_IN_SECS=1800
REFRESH_TOKEN_EXPIRE_IN_DAYS=14
SECRET_KEY=your-long-random-secret-key-here
TELEGRAM_API_BASE_URL=https://api.telegram.org

DATABASE_USER=pentaract
DATABASE_PASSWORD=your-db-password-from-step4
DATABASE_NAME=pentaract
DATABASE_HOST=your-db-host-from-step4
DATABASE_PORT=5432
```

## Step 6: Deploy
1. Click **Deploy**
2. Wait for build & deploy (2-5 minutes)
3. You'll get a URL like `https://pentaract.back4app.io`

## Step 7: Keep it 24/7 Alive
Back4app free tier stays always-on. No spin-down.

---

**Done!** Your Pentaract is now live 24/7 for free!
