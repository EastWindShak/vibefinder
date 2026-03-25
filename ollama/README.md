# VibeFinder Ollama

Standalone Ollama container for VibeFinder AI recommendations.

## Quick Start

```bash
# Create the network first (if not exists)
docker network create vibefinder-network

# Start Ollama
docker-compose up -d

# Pull the llama3.1 model (first time setup)
docker-compose --profile setup up ollama-pull

# Or manually pull a model
docker exec vibefinder-ollama ollama pull llama3.1
```

## GPU Support (Enabled by Default)

NVIDIA CUDA GPU acceleration is **enabled by default** for optimal performance.

### Requirements

- NVIDIA GPU with CUDA support
- NVIDIA drivers installed (version 525+ recommended)
- nvidia-container-toolkit installed

### Install nvidia-container-toolkit (if not installed)

**Windows (WSL2):**
```bash
# In WSL2 Ubuntu
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

**Linux:**
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Disable GPU (CPU-only mode)

If you don't have an NVIDIA GPU, remove or comment out the `deploy` section in `docker-compose.yml`:

```yaml
# deploy:
#   resources:
#     reservations:
#       devices:
#         - driver: nvidia
#           count: all
#           capabilities: [gpu]
#     limits:
#       memory: 16G
```

### Memory Configuration

Default: 16GB RAM limit (suitable for llama3.1 8B model)

Adjust in `docker-compose.yml`:
```yaml
limits:
  memory: 16G  # Change to 32G for larger models
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| OLLAMA_HOST | 0.0.0.0 | Host to bind to |
| OLLAMA_KEEP_ALIVE | 24h | How long to keep models loaded |
| OLLAMA_NUM_PARALLEL | 2 | Max parallel requests |
| NVIDIA_VISIBLE_DEVICES | all | GPUs visible to container |
| Memory limit | 16GB | RAM limit for llama3.1 8B |

## API Endpoints

- **Base URL**: http://localhost:11434
- **Generate**: POST /api/generate
- **Chat**: POST /api/chat
- **List Models**: GET /api/tags
- **Pull Model**: POST /api/pull

## Useful Commands

```bash
# Check running models
docker exec vibefinder-ollama ollama list

# Pull a model
docker exec vibefinder-ollama ollama pull llama3

# Run a quick test
docker exec vibefinder-ollama ollama run llama3 "Hello, world!"

# Check Ollama version
docker exec vibefinder-ollama ollama --version

# View logs
docker-compose logs -f ollama

# Restart Ollama
docker-compose restart ollama
```

## Available Models

Popular models for music recommendations:

```bash
# Recommended for VibeFinder (default)
docker exec vibefinder-ollama ollama pull llama3.1

# Alternatives
docker exec vibefinder-ollama ollama pull llama3.1:70b  # Larger, more capable (needs ~48GB VRAM)
docker exec vibefinder-ollama ollama pull qwen2.5:14b   # Great multilingual support
docker exec vibefinder-ollama ollama pull mistral       # Fast alternative
docker exec vibefinder-ollama ollama pull mixtral       # Good for complex tasks
```

## Data Persistence

Models are stored in a Docker volume named `vibefinder-ollama-data`.

To see volume location:
```bash
docker volume inspect vibefinder-ollama-data
```

## Troubleshooting

### Out of memory
Reduce the model size or increase Docker memory limits.

### Slow responses
- Enable GPU support
- Use a smaller model
- Increase `OLLAMA_NUM_PARALLEL`

### Model not found
```bash
docker exec vibefinder-ollama ollama pull llama3.1
```
