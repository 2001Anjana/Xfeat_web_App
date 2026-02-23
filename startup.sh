#!/bin/bash
# ════════════════════════════════════════════════════
#  XFeat Vision Lab — Azure App Service Startup Script
#  Startup command: bash startup.sh
# ════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
XFEAT_DIR="$BACKEND_DIR/accelerated_features"

echo "=== XFeat Vision Lab — Startup ==="
echo "Script dir: $SCRIPT_DIR"
echo "Backend dir: $BACKEND_DIR"

# 1. Clone XFeat if not already present
if [ ! -d "$XFEAT_DIR" ]; then
    echo "[1/3] Cloning XFeat repository..."
    git clone --depth 1 https://github.com/verlab/accelerated_features.git "$XFEAT_DIR"
    echo "[1/3] XFeat cloned OK"
else
    echo "[1/3] XFeat already present. Skipping clone."
fi

# 2. Install Python dependencies
echo "[2/3] Installing dependencies..."
pip install --quiet --no-cache-dir -r "$BACKEND_DIR/requirements.txt"
echo "[2/3] Dependencies installed"

# 3. Create uploads and outputs dirs if needed
mkdir -p "$BACKEND_DIR/uploads" "$BACKEND_DIR/outputs"

# 4. Start Gunicorn (1 worker to fit within B1 RAM)
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
