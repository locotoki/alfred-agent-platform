#!/bin/bash
# Start Alfred Platform with GPU support (Windows/Linux with NVIDIA)

echo "🚀 Starting Alfred Platform with GPU acceleration..."
echo "Platform: $(uname -s)"

# Check if NVIDIA GPU is available
if command -v nvidia-smi &> /dev/null; then
    echo "✅ NVIDIA GPU detected"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "⚠️  No NVIDIA GPU detected - falling back to CPU mode"
    docker-compose up -d
    exit 0
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Start with GPU configuration
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d

echo "🎉 Alfred Platform started with GPU acceleration!"
echo "📊 UI Chat: http://localhost:8502"
echo "🔧 Agent Core: http://localhost:8011"
echo "🤖 Ollama API: http://localhost:11434"