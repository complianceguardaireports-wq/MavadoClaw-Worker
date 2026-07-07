#!/bin/bash
# MavadoClaw Deploy Script
# Deploys to Cloudflare Workers, HuggingFace Spaces, and Lightning.ai

set -e

echo "============================================"
echo "  MavadoClaw Deployment"
echo "============================================"

deploy_cloudflare() {
    echo ""
    echo "--- Deploying to Cloudflare Workers ---"
    cd cloudflare-worker

    if [ ! -f "wrangler.toml" ]; then
        echo "Error: wrangler.toml not found"
        return 1
    fi

    command -v wrangler >/dev/null 2>&1 || npm install -g wrangler

    if [ -n "$CLOUDFLARE_API_TOKEN" ]; then
        wrangler deploy
        echo "Cloudflare Worker deployed!"
    else
        echo "CLOUDFLARE_API_TOKEN not set. Run:"
        echo "  export CLOUDFLARE_API_TOKEN=your-token"
        echo "  ./scripts/deploy.sh cloudflare"
    fi
    cd ..
}

deploy_huggingface() {
    echo ""
    echo "--- Deploying to HuggingFace Spaces ---"

    if [ -n "$HF_TOKEN" ] && [ -n "$HF_SPACE_NAME" ]; then
        pip install huggingface_hub
        huggingface-cli login --token $HF_TOKEN

        echo "Pushing to HuggingFace Space: $HF_SPACE_NAME"
        huggingface-cli upload $HF_SPACE_NAME . --repo-type space
        echo "HuggingFace Space deployed!"
    else
        echo "HF_TOKEN and HF_SPACE_NAME not set. Run:"
        echo "  export HF_TOKEN=your-token"
        echo "  export HF_SPACE_NAME=your-space-name"
        echo "  ./scripts/deploy.sh huggingface"
    fi
}

deploy_lightning() {
    echo ""
    echo "--- Lightning.ai Deployment ---"
    echo "To deploy to Lightning.ai:"
    echo "1. Go to https://lightning.ai"
    echo "2. Create a new AI Studio"
    echo "3. Upload this project"
    echo "4. Or use: pip install lightning && lightning run app app.py"
}

case "${1:-all}" in
    cloudflare|cf)
        deploy_cloudflare
        ;;
    huggingface|hf)
        deploy_huggingface
        ;;
    lightning|lightning)
        deploy_lightning
        ;;
    all)
        deploy_cloudflare
        deploy_huggingface
        deploy_lightning
        ;;
    *)
        echo "Usage: $0 {cloudflare|huggingface|lightning|all}"
        exit 1
        ;;
esac

echo ""
echo "============================================"
echo "  Deployment Complete!"
echo "============================================"
