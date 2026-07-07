#!/bin/bash
# MavadoClaw Setup Script
# Sets up the development environment

set -e

echo "============================================"
echo "  MavadoClaw Worker Setup"
echo "============================================"

# Check prerequisites
echo ""
echo "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || { echo "Docker required but not installed. Aborting."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || COMPOSE_CMD="docker compose" || COMPOSE_CMD="docker-compose"
command -v python3 >/dev/null 2>&1 || { echo "Python 3 required but not installed. Aborting."; exit 1; }
command -v node >/dev/null 2>&1 || echo "Warning: Node.js not found (needed for Cloudflare Worker)"

echo "Prerequisites OK"

# Create .env if not exists
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env from template..."
    cp .env.example .env
    echo ".env created. Edit it to add your API keys (all optional)."
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Clone OmniRoute if not present
if [ ! -d "omniroute" ]; then
    echo ""
    echo "Cloning OmniRoute..."
    git clone --depth 1 https://github.com/diegosoapw/OmniRoute.git omniroute
fi

# Clone 9Router if not present
if [ ! -d "9router" ]; then
    echo ""
    echo "Cloning 9Router..."
    git clone --depth 1 https://github.com/decoulua/9router.git 9router
fi

# Build Docker images
echo ""
echo "Building Docker images..."
${COMPOSE_CMD:-docker-compose} -f docker-compose.local.yml build

echo ""
echo "============================================"
echo "  Setup Complete!"
echo ""
echo "  To start all services:"
echo "    ./supervisor.sh start"
echo ""
echo "  Or with Docker Compose:"
echo "    docker-compose -f docker-compose.local.yml up -d"
echo ""
echo "  Services:"
echo "    MavadoClaw  - http://localhost:8080"
echo "    OmniRoute   - http://localhost:3000"
echo "    9Router     - http://localhost:8081"
echo "    OpenHands   - http://localhost:3001"
echo ""
echo "  Cloudflare Worker:"
echo "    cd cloudflare-worker && npm install && npx wrangler deploy"
echo ""
echo "  HuggingFace Space:"
echo "    Push to GitHub, connect to HF Spaces"
echo "============================================"
