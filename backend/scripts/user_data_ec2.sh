#!/bin/bash
# ==============================================================================
# AWS EC2 User Data Startup Script — Task-2 Backend Server
# Target Instance: t3.micro (Amazon Linux 2023 / Ubuntu 22.04)
# Configures Python 3.11, virtualenv, dependencies & systemd Uvicorn service
# ==============================================================================

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/null) 2>&1

echo "[1/6] Installing OS system dependencies..."
if command -v dnf &> /dev/null; then
    dnf update -y
    dnf install -y python3.11 python3.11-pip git gcc python3.11-devel
    alias python_cmd='python3.11'
elif command -v apt-get &> /dev/null; then
    apt-get update -y
    apt-get install -y python3.11 python3.11-venv python3.11-dev git build-essential
    alias python_cmd='python3.11'
else
    yum install -y python3 git gcc python3-devel
    alias python_cmd='python3'
fi

echo "[2/6] Preparing Application Directory..."
APP_DIR="/opt/hh-goa-rag"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -f "$APP_DIR/requirements.txt" ]; then
    echo "Waiting for application files sync..."
    git clone https://github.com/apurvv28/HHGoa-RAGInGoa.git "$APP_DIR" || true
fi

echo "[3/6] Setting up Python Virtual Environment..."
python3.11 -m venv "$APP_DIR/.venv" || python3 -m venv "$APP_DIR/.venv"
source "$APP_DIR/.venv/bin/activate"

pip install --upgrade pip setuptools wheel
if [ -f "$APP_DIR/Task-2/requirements.txt" ]; then
    pip install -r "$APP_DIR/Task-2/requirements.txt"
elif [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r "$APP_DIR/requirements.txt"
else
    pip install fastapi uvicorn pydantic pydantic-settings httpx sentence-transformers qdrant-client sarvamai
fi

echo "[4/6] Creating Systemd Service for FastAPI Uvicorn Backend..."
cat << 'EOF' > /etc/systemd/system/task2-backend.service
[Unit]
Description=HH Goa Task-2 Voice RAG Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hh-goa-rag/Task-2
ExecStart=/opt/hh-goa-rag/.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=/opt/hh-goa-rag/Task-2

[Install]
WantedBy=multi-user.target
EOF

echo "[5/6] Enabling and starting task2-backend service..."
systemctl daemon-reload
systemctl enable task2-backend
systemctl restart task2-backend || true

echo "[6/6] Verifying local health check endpoint..."
sleep 5
curl -s http://localhost:8000/health || echo "Health check pending..."

echo "EC2 User Data script executed successfully!"
