# Alfred Agent Platform - Cross-Platform Setup

This guide helps you set up Alfred Agent Platform across different development environments.

## Quick Start

### 1. Clone and Configure

```bash
git clone <your-repo-url>
cd alfred-agent-platform-v2
cp .env.example .env
# Edit .env with your API keys and settings
```

### 2. Choose Your Platform

#### Windows/Linux with NVIDIA GPU (Recommended for Performance)
```bash
./scripts/start-gpu.sh
```
**Features:**
- ⚡ GPU-accelerated local LLM inference (RTX 3080 Ti, etc.)
- 🚀 Fastest local model responses
- 💡 Best for development with heavy LLM usage

#### Mac (Apple Silicon M1/M2/M3)
```bash
./scripts/start-mac.sh
```
**Features:**
- 🍎 Optimized for Apple Silicon
- 💾 Utilizes 64GB RAM efficiently
- 🔄 CPU inference with multi-core optimization

#### Development/Testing (Any Platform)
```bash
docker-compose up -d
```
**Features:**
- 🛠️ Basic setup for testing
- ⚙️ CPU-only inference
- 📦 Minimal resource usage

## Platform-Specific Optimizations

### Windows/Linux + NVIDIA GPU
- **GPU Memory**: ~8-10GB VRAM used for llama3:8b
- **Performance**: ~10x faster inference than CPU
- **Requirements**: NVIDIA Container Toolkit installed

### Mac M1/M2/M3
- **Memory**: Up to 16GB allocated for LLM service
- **Performance**: Optimized CPU inference with parallel processing
- **Architecture**: Native ARM64 Docker images

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ALFRED_OPENAI_API_KEY` | OpenAI API key for GPT models | Yes |
| `ALFRED_ANTHROPIC_API_KEY` | Anthropic API key (optional) | No |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `ALFRED_DEBUG` | Enable debug logging | No |

## Services Overview

| Service | Port | Description |
|---------|------|-------------|
| UI Chat | 8502 | Streamlit chat interface |
| Agent Core | 8011 | Main API with model routing |
| Ollama | 11434 | Local LLM service |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache and sessions |

## Troubleshooting

### GPU Issues (Windows/Linux)
```bash
# Check GPU availability
nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Mac Performance
```bash
# Check available memory
sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024) " GB"}'

# Monitor Docker resource usage
docker stats
```

### Service Health
```bash
# Check all service status
docker ps

# View logs for specific service
docker logs <service-name>
```

## Development Workflow

1. **Edit code** in your preferred editor
2. **Test locally** with your platform-specific setup
3. **Commit changes** to git
4. **Pull on other machine** and test with different platform setup
5. **Ensure cross-platform compatibility**

## Model Capabilities

### Local Models (GPU-accelerated)
- **llama3:8b**: Fast, capable local inference
- **Performance**: Best on GPU systems

### Cloud Models (API-based)
- **GPT-3.5-turbo**: Fast, cost-effective
- **GPT-4**: Most capable, higher cost
- **Performance**: Consistent across all platforms