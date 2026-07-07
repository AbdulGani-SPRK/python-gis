# Hostinger VPS Deployment Guide
# Property Consultant GIS Service

## Overview

This guide deploys the FastAPI GIS service natively on Ubuntu 24.04 LTS without Docker,
using **GitHub as the source of truth** — push from your local machine, pull on the VPS.

- **App runtime**: Python 3.12 + uvicorn (systemd-managed)
- **Database**: PostgreSQL + PostGIS (already installed on VPS)
- **n8n**: Already running in Docker on the same VPS (port 5678)
- **Exposed at**: `http://<vps-ip>:8000` (raw HTTP, no Nginx)

---

## Prerequisites Checklist

- [ ] PostgreSQL is running on the VPS: `sudo systemctl status postgresql`
- [ ] PostGIS is enabled in `realestate_db`:
  ```sql
  -- Inside psql:
  \c realestate_db
  SELECT PostGIS_Version();
  ```
- [ ] OSM pg dump has been restored:
  ```bash
  psql -U postgres -d realestate_db < your_dump.sql
  ```
- [ ] You know the PostgreSQL `postgres` user password
- [ ] n8n Docker container is running: `docker ps | grep n8n`
- [ ] You have a GitHub account and the repo is created (public or private)

---

## Part A — Local Machine: Push to GitHub

Do these steps **once on your Windows machine** before touching the VPS.

### Step 1 — Initialize Git (if not already done)

Open PowerShell in the project folder:

```powershell
cd "C:\Users\yuvra\OneDrive\Desktop\Study\Projects\Property consultant Agent\python-gis"

git init
git add .
git commit -m "Initial commit: Property Consultant GIS Service"
```

> **Note**: `.env` is already in `.gitignore` — your secrets will NOT be pushed to GitHub.

### Step 2 — Create a GitHub repo and push

1. Go to [github.com/new](https://github.com/new) and create a new **private** repository (e.g. `real-estate-ai`).
2. Push your code:

```powershell
git remote add origin https://github.com/<YOUR_USERNAME>/real-estate-ai.git
git branch -M main
git push -u origin main
```

Confirm the code is visible on GitHub before continuing.

---

## Part B — VPS: Initial Server Setup

SSH into your VPS:

```bash
ssh root@<vps-ip>
```

### Step 3 — Run the system setup script (once only)

This installs Python 3.12, GDAL, gcc, libpq, and creates the `realestate` system user.

```bash
# Install git if not present
apt-get install -y git

# Clone the repo into /opt/real-estate-ai
git clone https://github.com/<YOUR_USERNAME>/real-estate-ai.git /opt/real-estate-ai

# Run system setup
chmod +x /opt/real-estate-ai/deploy/01_vps_setup.sh
sudo bash /opt/real-estate-ai/deploy/01_vps_setup.sh
```

### Step 4 — Edit the deployment script with your credentials

```bash
nano /opt/real-estate-ai/deploy/02_deploy_app.sh
```

Set these values at the top of the script:

```bash
REPO_URL="https://github.com/<YOUR_USERNAME>/real-estate-ai.git"
BRANCH="main"

DB_PASSWORD="your_actual_postgres_password"
GEMINI_API_KEY="your_actual_gemini_api_key"
```

Save and exit: `Ctrl+O` → `Enter` → `Ctrl+X`

### Step 5 — Run the deployment script

```bash
chmod +x /opt/real-estate-ai/deploy/02_deploy_app.sh
sudo bash /opt/real-estate-ai/deploy/02_deploy_app.sh
```

This script will:
1. `git pull` the latest code from GitHub
2. Set up the Python virtual environment
3. Install all `requirements.txt` dependencies (including GDAL bindings)
4. Write the production `.env` file (secrets stay on the server, never in Git)
5. Run `alembic upgrade head` to apply DB migrations
6. Install and start the `realestate-gis` systemd service

### Step 6 — Open port 8000 in the firewall

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

Also open port 8000 in your **Hostinger VPS firewall panel** (VPS → Firewall in the Hostinger dashboard).

### Step 7 — Verify

```bash
# Check service status
systemctl status realestate-gis

# Test locally on the VPS
curl http://localhost:8000/docs
```

The API should now be reachable at:

```
http://<your-vps-ip>:8000/docs   ← Swagger UI
http://<your-vps-ip>:8000/redoc  ← ReDoc
```

---

## Updating the App (Ongoing Workflow)

Every time you make code changes, the workflow is:

**Local machine:**
```powershell
git add .
git commit -m "describe your changes"
git push origin main
```

**VPS:**
```bash
sudo bash /opt/real-estate-ai/deploy/02_deploy_app.sh
```

The script does `git pull` + reinstalls deps + restarts the service. It is **idempotent** — safe to re-run at any time.

---

## Private Repo — Authentication on VPS

If your GitHub repo is **private**, you need to authenticate on the VPS. The two easiest options:

### Option A: GitHub Personal Access Token (simplest)

1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Tokens (classic)
2. Generate a token with `repo` scope
3. On the VPS, clone using the token in the URL:

```bash
git clone https://<YOUR_TOKEN>@github.com/<YOUR_USERNAME>/real-estate-ai.git /opt/real-estate-ai
```

Or store credentials so you don't have to repeat it:

```bash
git config --global credential.helper store
# Then do a git pull — it will ask once, and store the credentials
```

### Option B: SSH Deploy Key

```bash
# On the VPS, generate a key (no passphrase)
ssh-keygen -t ed25519 -C "vps-deploy" -f ~/.ssh/github_deploy -N ""

# Print the public key
cat ~/.ssh/github_deploy.pub
```

Go to your GitHub repo → Settings → Deploy keys → Add deploy key → paste the public key (read-only is fine).

```bash
# Configure git to use this key
echo -e "Host github.com\n  IdentityFile ~/.ssh/github_deploy\n  StrictHostKeyChecking no" >> ~/.ssh/config

# Now use SSH URL when cloning
git clone git@github.com:<YOUR_USERNAME>/real-estate-ai.git /opt/real-estate-ai
```

---

## Common Operations

### Restart the service
```bash
sudo systemctl restart realestate-gis
```

### View live logs
```bash
journalctl -u realestate-gis -f
```

### View last 100 lines of logs
```bash
journalctl -u realestate-gis -n 100 --no-pager
```

### Run Alembic migrations manually
```bash
cd /opt/real-estate-ai
sudo -u realestate .venv/bin/alembic upgrade head
sudo -u realestate .venv/bin/alembic current
```

### Check the production .env
```bash
sudo cat /opt/real-estate-ai/.env
```

---

## Troubleshooting

| Problem | Command to investigate |
|---|---|
| Service won't start | `journalctl -u realestate-gis -n 50 --no-pager` |
| Can't connect to PostgreSQL | `psql -U postgres -d realestate_db -c "SELECT 1"` |
| GDAL import error | `/opt/real-estate-ai/.venv/bin/python -c "import osgeo.gdal; print('OK')"` |
| Port 8000 not reachable | `sudo ufw status` + check Hostinger firewall panel |
| `git pull` auth failure | See "Private Repo — Authentication" section above |
| Alembic migration fails | Check `DATABASE_URL` in `.env` and that `realestate_db` exists |
| n8n webhooks not working | `curl http://localhost:5678` to verify n8n is accessible from the VPS |

---

## Production `.env` Reference

The deployment script writes this automatically. Secrets are **never committed to Git**.

```env
APP_NAME="Real Estate Property Consultant GIS Service"
APP_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+psycopg://postgres:<password>@localhost:5432/realestate_db

SQL_ECHO=false
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT_SECONDS=30

DEFAULT_SEARCH_PAGE_SIZE=20
MAX_SEARCH_PAGE_SIZE=100
DEFAULT_NEARBY_RADIUS_M=3000
MAX_NEARBY_RADIUS_M=25000

N8N_WEBHOOK_BASE_URL=http://localhost:5678/webhook
GEMINI_API_KEY=<your-key>
```
