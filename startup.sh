#!/bin/bash
# ════════════════════════════════════════════════════
#  XFeat Vision Lab — Azure App Service Startup Script
#  Azure runs this once on each container start.
#  Set this as the startup command in Azure portal:
#    bash startup.sh
# ════════════════════════════════════════════════════

set -e

BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"
XFEAT_DIR="$BACKEND_DIR/accelerated_features"

echo "=== XFeat Vision Lab — Startup ==="

# 1. Clone XFeat if not already present
if [ ! -d "$XFEAT_DIR" ]; then
    echo "[1/3] Cloning XFeat repository..."
    git clone https://github.com/verlab/accelerated_features.git "$XFEAT_DIR"
    echo "[1/3] XFeat cloned OK"
else
    echo "[1/3] XFeat repo already present. Skipping."
fi

# 2. Install Python dependencies
echo "[2/3] Installing Python dependencies..."
pip install --quiet -r "$BACKEND_DIR/requirements.txt"
echo "[2/3] Dependencies installed OK"

# 3. Start Flask app with Gunicorn (production WSGI server)
echo "[3/3] Starting Flask backend on port 8000..."
cd "$BACKEND_DIR"
gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 300 app:app
