# MavadoClaw Worker

> **Autonomous AI Virtual Company** - CEO/Orchestrator running 24/7 with zero human intervention

[![CI](https://github.com/complianceguardaireports-wq/MavadoClaw-Worker/actions/workflows/ci.yml/badge.svg)](https://github.com/complianceguardaireports-wq/MavadoClaw-Worker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE EDGE LAYER                     │
│  Workers AI (80+ models) │ Vectorize │ D1 │ R2 │ AI Gateway │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 HUGGING FACE SPACES LAYER                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │OmniRoute │  │ 9Router  │  │OpenHands │  │ MavadoClaw│   │
│  │ :3000    │  │ :8081    │  │ :3001    │  │ :8080    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    LIGHTNING.AI LAYER                         │
│  GPU Studios (A100/H100) │ LitServe │ Model Fine-tuning     │
└─────────────────────────────────────────────────────────────┘
```

## Services

| Service | Port | Tech | Role |
|---------|------|------|------|
| **MavadoClaw** | 8080 | Python FastAPI | CEO/Orchestrator |
| **OmniRoute** | 3000 | Node.js | Primary AI Gateway |
| **9Router** | 8081 | Node.js | Backup Router |
| **OpenHands** | 3001 | Docker | Coding Agent |

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone and setup
git clone https://github.com/complianceguardaireports-wq/MavadoClaw-Worker.git
cd MavadoClaw-Worker
bash scripts/setup.sh

# Start all services
docker-compose -f docker-compose.local.yml up -d

# Check health
curl http://localhost:8080/health
```

### Option 2: Supervisor (Local)

```bash
bash scripts/setup.sh
./supervisor.sh start
./supervisor.sh status
```

## Free API Stack

All LLM inference runs locally via OmniRoute + 9Router. **Zero API keys required.**

Optional free tiers for enhanced capabilities:

| Provider | Free Tier | Purpose |
|----------|-----------|---------|
| Google AI Studio | 15 RPM unlimited | LLM fallback |
| Groq | 14,400 req/day | Ultra-fast inference |
| DeepSeek | 5M tokens | Coding tasks |
| OpenRouter | $1 credit | 100+ models |
| Cloudflare Workers AI | 10K neurons/day | Edge inference |
| HuggingFace ZeroGPU | 5 min/day A100 | Burst compute |
| Lightning.ai | 15 credits/mo | GPU fine-tuning |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/chat` | POST | Chat completion |
| `/api/task` | POST | Execute task |
| `/api/deploy` | POST | Deploy project |
| `/api/agents` | GET | List agents |
| `/api/status` | GET | System status |
| `/` | GET | API documentation |

## Cloudflare Edge

Deploy the edge worker for global low-latency inference:

```bash
cd cloudflare-worker
npm install
npx wrangler deploy
```

## HuggingFace Spaces

Deploy as a web-accessible Space:

1. Push to GitHub
2. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
3. Connect your repository
4. Select Docker SDK
5. Space will auto-deploy

## Project Structure

```
MavadoClaw-Worker/
├── app.py                          # FastAPI entry point
├── Dockerfile                      # Multi-stage build
├── docker-compose.local.yml        # Local dev compose
├── supervisor.sh                   # Process manager
├── pandastack.toml                 # PandaStack config
├── config.json.template            # Configuration template
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables
├── plugins/
│   ├── ai_infrastructure.py        # Unified OmniRoute + 9Router
│   ├── omniroute_plugin/           # Primary AI gateway client
│   ├── ninerouter_plugin/          # Backup router + failover
│   ├── openhands_team/             # Coding agent delegation
│   ├── cloudflare_edge/            # Cloudflare Workers AI
│   ├── hf_spaces/                  # HuggingFace integration
│   └── lightning_ai/               # Lightning.ai integration
├── cloudflare-worker/
│   ├── wrangler.toml               # Cloudflare config
│   └── src/index.js                # Edge worker code
├── hf-space/
│   ├── Dockerfile                  # HF Space build
│   ├── app.py                      # Gradio interface
│   └── requirements.txt            # HF dependencies
├── scripts/
│   ├── setup.sh                    # Development setup
│   └── deploy.sh                   # Multi-platform deploy
├── tests/
│   └── test_all.py                 # Comprehensive tests
└── .github/workflows/
    └── ci.yml                      # CI/CD pipeline
```

## Configuration

Edit `config.json.template` or set environment variables in `.env`:

```bash
cp .env.example .env
# Edit .env with your optional API keys
```

## Usage Commands

```
dev: <task>              # Spawn OpenHands for coding
route: <model> <prompt>  # Direct OmniRoute call
status                   # Company health report
deploy <project>         # Deploy to production
```

## License

MIT - Build your own autonomous AI company!
