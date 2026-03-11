#!/bin/bash
# ════════════════════════════════════════════════════
#  XFeat Vision Lab — Azure App Service Startup Script
#  Startup command in Azure: bash startup.sh
#  NOTE: pip install is handled by Azure Oryx at deploy
#        time. This script only handles XFeat download
#        and starts Gunicorn.
# ════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
XFEAT_DIR="$BACKEND_DIR/accelerated_features"

echo "=== XFeat Vision Lab — Startup ==="
echo "Backend dir: $BACKEND_DIR"

# 1. Download XFeat via curl (git not available on Azure App Service)
if [ ! -d "$XFEAT_DIR" ]; then
    echo "[1/2] Downloading XFeat from GitHub..."
    curl -sL https://github.com/verlab/accelerated_features/archive/refs/heads/main.zip \
         -o /tmp/xfeat.zip
    unzip -q /tmp/xfeat.zip -d /tmp/
    mv /tmp/accelerated_features-main "$XFEAT_DIR"
    rm -f /tmp/xfeat.zip
    echo "[1/2] XFeat downloaded OK"
else
    echo "[1/2] XFeat already present. Skipping."
fi

# 2. Create runtime dirs
mkdir -p "$BACKEND_DIR/uploads" "$BACKEND_DIR/outputs"

# 3. Install FFmpeg for browser-compatible H.264 video encoding
if ! command -v ffmpeg &> /dev/null; then
    echo "[2.5/3] Installing FFmpeg..."
    apt-get update -qq && apt-get install -y -qq ffmpeg
    echo "[2.5/3] FFmpeg installed OK"
else
    echo "[2.5/3] FFmpeg already installed. Skipping."
fi

# 4. Start Gunicorn (packages already installed by Azure Oryx)
echo "[2/2] Starting Gunicorn on port 8000..."
cd "$BACKEND_DIR"
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 1 \
    --timeout 600 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    app:app
