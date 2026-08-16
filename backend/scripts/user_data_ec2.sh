#!/bin/bash
# ==============================================================================
# AWS EC2 User Data Startup Script — Task-2 Backend Server
# Target Instance: t3.micro (Amazon Linux 2023 / Ubuntu 22.04)
# Allocates 2GB Swap Memory, installs CPU PyTorch, FastAPI & Uvicorn Systemd
# ==============================================================================

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/null) 2>&1

echo "[1/7] Allocating 2GB Swap Memory to prevent t3.micro 1GB OOM..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
    echo "   - Swap space created successfully."
fi

echo "[2/7] Installing OS system dependencies..."
if command -v dnf &> /dev/null; then
    dnf update -y
    dnf install -y python3.11 python3.11-pip git gcc python3.11-devel
elif command -v apt-get &> /dev/null; then
    apt-get update -y
    apt-get install -y python3.11 python3.11-venv python3.11-dev git build-essential
else
    yum install -y python3 git gcc python3-devel
fi

echo "[3/7] Preparing Application Directory..."
APP_DIR="/opt/hh-goa-rag"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -f "$APP_DIR/requirements.txt" ]; then
    echo "Cloning repository directly into $APP_DIR..."
    git clone https://github.com/apurvv28/HHGoa-RAGInGoa.git "$APP_DIR" || true
fi

WORK_DIR="$APP_DIR"
if [ -d "$APP_DIR/Task-2" ]; then
    WORK_DIR="$APP_DIR/Task-2"
elif [ -d "$APP_DIR/task-2" ]; then
    WORK_DIR="$APP_DIR/task-2"
fi

echo "   - Using Working Directory: $WORK_DIR"

echo "[4/7] Setting up Python Virtual Environment..."
python3.11 -m venv "$APP_DIR/.venv" || python3 -m venv "$APP_DIR/.venv"
source "$APP_DIR/.venv/bin/activate"

pip install --upgrade pip setuptools wheel

# Install CPU PyTorch first to save memory & bandwidth
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu || true

if [ -f "$WORK_DIR/requirements.txt" ]; then
    pip install --no-cache-dir -r "$WORK_DIR/requirements.txt"
elif [ -f "$APP_DIR/requirements.txt" ]; then
    pip install --no-cache-dir -r "$APP_DIR/requirements.txt"
else
    pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings httpx sentence-transformers qdrant-client sarvamai
fi

echo "[5/7] Writing Production .env Environment File..."
cat << EOF > "$WORK_DIR/.env"
APP_NAME=HH_Goa_Voice_RAG
ENVIRONMENT=production
LOG_LEVEL=INFO
QDRANT_URL=:memory:
QDRANT_COLLECTION_NAME=RAG-1
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
VECTOR_DIMENSION=384
DISTANCE_METRIC=Cosine
GROQ_API_KEY="${GROQ_API_KEY:-YOUR_GROQ_API_KEY_HERE}"
GROQ_MODEL=llama-3.1-8b-instant
SARVAM_API_KEY="${SARVAM_API_KEY:-YOUR_SARVAM_API_KEY_HERE}"
ELEVENLABS_API_KEY="${ELEVENLABS_API_KEY:-YOUR_ELEVENLABS_API_KEY_HERE}"
EOF

echo "[6/7] Creating Systemd Service for FastAPI Uvicorn Backend..."
cat << EOF > /etc/systemd/system/task2-backend.service
[Unit]
Description=HH Goa Task-2 Voice RAG Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$WORK_DIR
ExecStart=$APP_DIR/.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=$WORK_DIR

[Install]
WantedBy=multi-user.target
EOF

echo "[7/7] Enabling and starting task2-backend service..."
systemctl daemon-reload
systemctl enable task2-backend
systemctl restart task2-backend || true

sleep 5
curl -s http://localhost:8000/health || echo "Health check warming up..."

echo "EC2 User Data script executed successfully!"
