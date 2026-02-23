#!/bin/bash
# ════════════════════════════════════════════════════
#  XFeat Vision Lab — Azure App Service Startup Script
#  Startup command in Azure: bash startup.sh
# ════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
XFEAT_DIR="$BACKEND_DIR/accelerated_features"

echo "=== XFeat Vision Lab — Startup ==="
echo "Backend dir: $BACKEND_DIR"

# 1. Download XFeat via curl (git not available on Azure App Service)
if [ ! -d "$XFEAT_DIR" ]; then
    echo "[1/3] Downloading XFeat from GitHub..."
    curl -sL https://github.com/verlab/accelerated_features/archive/refs/heads/main.zip \
         -o /tmp/xfeat.zip
    unzip -q /tmp/xfeat.zip -d /tmp/
    mv /tmp/accelerated_features-main "$XFEAT_DIR"
    rm -f /tmp/xfeat.zip
    echo "[1/3] XFeat downloaded OK"
else
    echo "[1/3] XFeat already present. Skipping."
fi

# 2. Install Python dependencies
echo "[2/3] Installing dependencies..."
pip install --quiet --no-cache-dir -r "$BACKEND_DIR/requirements.txt"
echo "[2/3] Dependencies installed"

# 3. Create runtime dirs
mkdir -p "$BACKEND_DIR/uploads" "$BACKEND_DIR/outputs"

# 4. Start Gunicorn
echo "[3/3] Starting Gunicorn on port 8000..."
cd "$BACKEND_DIR"
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --timeout 600 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    app:app
