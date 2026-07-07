#!/usr/bin/env bash
# =============================================================================
# 02_deploy_app.sh — Application deployment for Property Consultant GIS Service
# Ubuntu 24.04 LTS
#
# Run this as root (or sudo) on the VPS from the project root directory.
# Re-run this script any time you want to update the deployment.
#
# PREREQUISITES:
#   1. 01_vps_setup.sh has been run successfully.
#   2. PostgreSQL + PostGIS is already installed and running.
#   3. The database 'realestate_db' exists with PostGIS enabled.
#   4. Fill in the variables below before running.
# =============================================================================

set -euo pipefail

# =============================================================================
# EDIT THESE BEFORE RUNNING
# =============================================================================
APP_DIR="/opt/real-estate-ai/python-gis"
REPO_URL="https://github.com/AbdulGani-SPRK/python-gis.git"  # GitHub repo URL
BRANCH="main"                       # Branch to deploy

DB_USER="postgres"
DB_PASSWORD=""                       # Leave empty if no password is set on postgres user.
                                     # Run: sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'yourpass';"
                                     # then set DB_PASSWORD="yourpass" here.
DB_NAME="realestate_db"
DB_HOST="localhost"
DB_PORT="5432"

GEMINI_API_KEY="your_gemini_api_key_here"  # <- Set your Gemini API key

# n8n is running in Docker on the same VPS — it publishes port 5678 to the host
N8N_WEBHOOK_BASE_URL="http://localhost:5678/webhook"

# The VPS public IP (used for informational output only)
VPS_IP=$(curl -s ifconfig.me || echo "<your-vps-ip>")
# =============================================================================

APP_USER="realestate"
VENV="$APP_DIR/.venv"
SERVICE_NAME="realestate-gis"

echo "======================================================"
echo " Property Consultant GIS — App Deployment"
echo "======================================================"

# ── 1. Deploy source code via Git ────────────────────────────────────────────
echo ""
echo "[1/6] Deploying source code to $APP_DIR from GitHub..."

if [ -z "$REPO_URL" ]; then
    echo "  ERROR: REPO_URL is not set. Edit this script and add your GitHub repo URL."
    exit 1
fi

if [ -d "$APP_DIR/.git" ]; then
    echo "  -> Repo already cloned. Pulling latest from '$BRANCH'..."
    git -C "$APP_DIR" fetch origin
    git -C "$APP_DIR" reset --hard origin/$BRANCH
    git -C "$APP_DIR" clean -fd
else
    echo "  -> Cloning $REPO_URL into $APP_DIR..."
    # /opt/real-estate-ai already exists on the VPS as a parent folder.
    # We clone into the python-gis subdirectory.
    mkdir -p /opt/real-estate-ai
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ── 2. Create / update Python virtual environment ─────────────────────────────
echo ""
echo "[2/6] Setting up Python virtual environment..."

if [ ! -d "$VENV" ]; then
    python3.12 -m venv "$VENV"
    echo "  -> Virtual environment created."
else
    echo "  -> Virtual environment already exists."
fi

# Install / upgrade pip and dependencies
"$VENV/bin/pip" install --upgrade pip --quiet
"$VENV/bin/pip" install --no-cache-dir -r "$APP_DIR/requirements.txt"
echo "  ✓ Dependencies installed."

# ── 3. Write production .env ──────────────────────────────────────────────────
echo ""
echo "[3/6] Writing production .env file..."

# Build DATABASE_URL — omit password if not set
if [ -n "$DB_PASSWORD" ]; then
    DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
else
    DATABASE_URL="postgresql+psycopg://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

cat > "$APP_DIR/.env" <<EOF
APP_NAME="Real Estate Property Consultant GIS Service"
APP_VERSION=0.1.0
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1

# PostgreSQL + PostGIS (native on VPS)
DATABASE_URL=${DATABASE_URL}

SQL_ECHO=false
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT_SECONDS=30

DEFAULT_SEARCH_PAGE_SIZE=20
MAX_SEARCH_PAGE_SIZE=100
DEFAULT_NEARBY_RADIUS_M=3000
MAX_NEARBY_RADIUS_M=25000

N8N_WEBHOOK_BASE_URL=${N8N_WEBHOOK_BASE_URL}
GEMINI_API_KEY=${GEMINI_API_KEY}
EOF

chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
echo "  ✓ .env written (permissions: 600)."

# ── 4. Run Alembic migrations ─────────────────────────────────────────────────
echo ""
echo "[4/6] Running Alembic database migrations..."
cd "$APP_DIR"
sudo -u "$APP_USER" "$VENV/bin/alembic" upgrade head
echo "  ✓ Migrations applied."

# ── 5. Install / reload systemd service ──────────────────────────────────────
echo ""
echo "[5/6] Installing systemd service '$SERVICE_NAME'..."

# Copy the service file
cp "$APP_DIR/deploy/realestate-gis.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo "  ✓ Service '$SERVICE_NAME' is enabled and started."

# ── 6. Health check ───────────────────────────────────────────────────────────
echo ""
echo "[6/6] Waiting for service to start..."
sleep 3

STATUS=$(systemctl is-active "$SERVICE_NAME" || true)
if [ "$STATUS" = "active" ]; then
    echo "  ✓ Service is running!"
else
    echo "  WARNING: Service status is '$STATUS'."
    echo "  Check logs with: journalctl -u $SERVICE_NAME -n 50 --no-pager"
fi

echo ""
echo "======================================================"
echo " Deployment complete!"
echo " API is available at: http://${VPS_IP}:8000"
echo " Swagger docs:        http://${VPS_IP}:8000/docs"
echo ""
echo " Useful commands:"
echo "   systemctl status $SERVICE_NAME"
echo "   journalctl -u $SERVICE_NAME -f"
echo "   systemctl restart $SERVICE_NAME"
echo "======================================================"
