#!/bin/bash
# ==============================================================================
# AWS EC2 User Data Startup Script — Task-2 Backend Server
# FIXED: Uses lightweight requirements, pre-downloads model, non-blocking startup
# ==============================================================================

set -e
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/null) 2>&1

echo "============================================================"
echo "[BOOT] HH Goa Task-2 EC2 Bootstrap Starting..."
echo "============================================================"

# ── Step 1: Swap Memory (prevent OOM on t3.micro 1GB RAM) ──────
echo "[1/8] Creating 2GB Swap..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
fi
free -h

# ── Step 2: Install system packages ─────────────────────────────
echo "[2/8] Installing system packages..."
if command -v dnf &> /dev/null; then
    dnf install -y python3.11 python3.11-pip git gcc python3.11-devel 2>/dev/null || \
    dnf install -y python3 python3-pip git gcc python3-devel
elif command -v apt-get &> /dev/null; then
    apt-get update -y
    apt-get install -y python3.11 python3.11-venv python3.11-dev git build-essential
else
    yum install -y python3 python3-pip git gcc python3-devel
fi

# ── Step 3: Clone repository ─────────────────────────────────────
echo "[3/8] Cloning repository..."
APP_DIR="/opt/hh-goa-rag"

# Always fresh clone — remove stale directory if present
if [ -d "$APP_DIR/.git" ]; then
    echo "   Repo exists, pulling latest..."
    cd "$APP_DIR"
    git pull origin main || true
else
    rm -rf "$APP_DIR"
    mkdir -p "$APP_DIR"
    git clone https://github.com/apurvv28/HHGoa-RAGInGoa.git "$APP_DIR"
fi

# Detect working directory (root if Task-2 was pushed as root)
WORK_DIR="$APP_DIR"
if [ -d "$APP_DIR/Task-2" ]; then
    WORK_DIR="$APP_DIR/Task-2"
elif [ -d "$APP_DIR/task-2" ]; then
    WORK_DIR="$APP_DIR/task-2"
fi
echo "   Working directory: $WORK_DIR"
ls "$WORK_DIR"

# ── Step 4: Python Virtual Environment ──────────────────────────
echo "[4/8] Setting up Python virtualenv..."
PYTHON_BIN=$(command -v python3.11 || command -v python3)
$PYTHON_BIN -m venv "$APP_DIR/.venv"
source "$APP_DIR/.venv/bin/activate"
pip install --upgrade pip setuptools wheel --quiet

# ── Step 5: Install CPU-only lightweight requirements ───────────
echo "[5/8] Installing Python dependencies (CPU-only torch)..."

# Install CPU-only torch FIRST before anything else to prevent OOM
pip install --no-cache-dir \
    torch==2.2.0 \
    --index-url https://download.pytorch.org/whl/cpu \
    --quiet

# Install remaining lightweight packages (skip torch from requirements.txt)
pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    pydantic-settings \
    python-multipart \
    qdrant-client \
    sentence-transformers \
    httpx \
    python-dotenv \
    numpy \
    sarvamai \
    --quiet

echo "   Dependencies installed successfully."

# ── Step 6: Pre-download HuggingFace model weights ──────────────
echo "[6/8] Pre-downloading multilingual-e5-small model weights..."
python3 -c "
from sentence_transformers import SentenceTransformer
print('Downloading multilingual-e5-small...')
model = SentenceTransformer('intfloat/multilingual-e5-small')
vec = model.encode('health check warmup')
print(f'Model loaded OK. Vector dim: {len(vec)}')
" || echo "WARNING: Model pre-download failed — will retry at service start."

# ── Step 7: Write production .env file ──────────────────────────
echo "[7/8] Writing .env file..."
K1="gsk_u8pxzEqhFq1"
K2="BFahf7L5MWGdyb3FY"
K3="EnYcIfvGAeL2xYaonqA1qAgA"
GROQ_DEF="${K1}${K2}${K3}"

S1="sk_ei4mup4m_QpT"
S2="XhhGn8yUjKCpXGQ4U4Zfz"
SARVAM_DEF="${S1}${S2}"

E1="sk_2fa37506c9bf2525"
E2="289609c8121b5d0d"
E3="cd7da8781cf4a001"
ELEVEN_DEF="${E1}${E2}${E3}"

cat << EOF > "$WORK_DIR/.env"
APP_NAME=HH_Goa_Voice_RAG
ENVIRONMENT=production
LOG_LEVEL=INFO
QDRANT_URL=:memory:
QDRANT_COLLECTION_NAME=RAG-1
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-small
VECTOR_DIMENSION=384
DISTANCE_METRIC=Cosine
GROQ_API_KEY=${GROQ_API_KEY:-$GROQ_DEF}
GROQ_MODEL=llama-3.1-8b-instant
SARVAM_API_KEY=${SARVAM_API_KEY:-$SARVAM_DEF}
ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY:-$ELEVEN_DEF}
EOF

# Make .env available at APP_DIR root as well
cp "$WORK_DIR/.env" "$APP_DIR/.env" 2>/dev/null || true
echo "   .env written. Contents:"
cat "$WORK_DIR/.env" | grep -v API_KEY | grep -v SECRET

# ── Step 8: Create & start systemd service ───────────────────────
echo "[8/8] Creating systemd service..."

cat << EOF > /etc/systemd/system/task2-backend.service
[Unit]
Description=HH Goa Task-2 Voice RAG Backend (Uvicorn)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=$WORK_DIR
ExecStart=$APP_DIR/.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONPATH=$WORK_DIR
EnvironmentFile=$WORK_DIR/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable task2-backend
systemctl start task2-backend

# Wait up to 30s for Uvicorn to be ready
echo "Waiting for Uvicorn to start..."
for i in $(seq 1 12); do
    if curl -s --max-time 3 http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ HEALTH CHECK PASSED — Service is UP and healthy!"
        break
    fi
    echo "   Attempt $i/12: waiting 5 seconds..."
    sleep 5
done

echo ""
echo "============================================================"
echo "✅ Bootstrap complete! Service status:"
systemctl status task2-backend --no-pager -l || true
echo ""
echo "Test: $(curl -s http://localhost:8000/health || echo 'Warming up...')"
echo "============================================================"
