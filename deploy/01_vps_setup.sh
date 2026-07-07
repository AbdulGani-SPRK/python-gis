#!/usr/bin/env bash
# =============================================================================
# 01_vps_setup.sh — System-level setup for Property Consultant GIS Service
# Ubuntu 24.04 LTS
#
# Run this ONCE as root (or with sudo) on the VPS.
# PostgreSQL + PostGIS are already installed, so this script ONLY installs:
#   - Python 3.12 + venv + pip
#   - GDAL system libraries (required by geopandas / GeoAlchemy2)
#   - Build tools (gcc, g++, libpq-dev)
#   - Creates the 'realestate' system user and /opt/real-estate-ai directory
# =============================================================================

set -euo pipefail

echo "======================================================"
echo " Property Consultant GIS — VPS Setup (Ubuntu 24.04)"
echo "======================================================"

# ── 1. Update apt ─────────────────────────────────────────────────────────────
echo ""
echo "[1/5] Updating package lists..."
apt-get update -y

# ── 2. Install system dependencies ────────────────────────────────────────────
echo ""
echo "[2/5] Installing Python 3.12, GDAL, build tools, and libpq..."
apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    gcc \
    g++ \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    curl \
    git

# Clean up apt cache
apt-get clean
rm -rf /var/lib/apt/lists/*

# ── 3. Verify GDAL installation ───────────────────────────────────────────────
echo ""
echo "[3/5] Verifying GDAL..."
gdal-config --version && echo "  ✓ GDAL OK: $(gdal-config --version)"

# ── 4. Create dedicated system user ───────────────────────────────────────────
echo ""
echo "[4/5] Creating system user 'realestate'..."
if id "realestate" &>/dev/null; then
    echo "  -> User 'realestate' already exists, skipping."
else
    useradd --system --no-create-home --shell /usr/sbin/nologin realestate
    echo "  ✓ User 'realestate' created."
fi

# ── 5. Create app directory ───────────────────────────────────────────────────
echo ""
echo "[5/5] Creating app directory /opt/realestate-gis..."
mkdir -p /opt/realestate-gis
chown realestate:realestate /opt/realestate-gis
chmod 755 /opt/realestate-gis
echo "  ✓ Directory ready."

echo ""
echo "======================================================"
echo " System setup complete!"
echo " Next step: run  sudo bash deploy/02_deploy_app.sh"
echo "======================================================"
