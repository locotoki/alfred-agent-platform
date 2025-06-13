#!/bin/bash
# Start Alfred Platform optimized for Mac (Apple Silicon)

echo "🍎 Starting Alfred Platform for Mac (Apple Silicon)..."
echo "Platform: $(uname -s) $(uname -m)"

# Check if running on Apple Silicon
if [[ "$(uname -m)" == "arm64" ]]; then
    echo "✅ Apple Silicon detected"
    echo "💾 Available RAM: $(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024) " GB"}')"
else
    echo "ℹ️  Running on Intel Mac"
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Start with Mac configuration
docker-compose -f docker-compose.yml -f docker-compose.mac.yml up -d

echo "🎉 Alfred Platform started for Mac!"
echo "📊 UI Chat: http://localhost:8502"
echo "🔧 Agent Core: http://localhost:8011"
echo "🤖 Ollama API: http://localhost:11434"
echo ""
echo "💡 Tip: Mac will use CPU inference. For faster responses, consider using cloud GPT models."