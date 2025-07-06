# LLM Configuration Guide

The Pegasus backend now supports multiple LLM providers. You can choose between local (Ollama) and cloud-based (Google Generative AI/Gemini) models.

## Supported Providers

1. **Ollama** (Default) - Local LLM using Ollama
2. **Google Generative AI** - Google's Gemini models
3. **OpenAI** - Legacy support for OpenAI API

## Configuration

### Provider Selection

Set the `LLM_PROVIDER` environment variable to choose your provider:

```bash
# Use Ollama (default if not set)
export LLM_PROVIDER=ollama

# Use Google Generative AI (Gemini)
export LLM_PROVIDER=google_generative_ai
# or
export LLM_PROVIDER=gemini

# Use OpenAI (legacy)
export LLM_PROVIDER=openai
```

### Provider-Specific Configuration

#### Ollama Configuration

```bash
# Ollama base URL (default: http://localhost:11434)
export OLLAMA_BASE_URL=http://localhost:11434

# Ollama model to use (default: llama2)
export OLLAMA_MODEL=llama2

# Request timeout in seconds (default: 60)
export OLLAMA_TIMEOUT=60
```

Available models depend on what you have pulled in Ollama. Common options:
- `llama2`
- `mistral`
- `codellama`
- `vicuna`

#### Google Generative AI Configuration

```bash
# API Key (required)
export GOOGLE_GENERATIVE_AI_API_KEY=your-api-key-here
# or
export GEMINI_API_KEY=your-api-key-here

# Model to use (default: gemini-pro)
export GOOGLE_GENERATIVE_AI_MODEL=gemini-pro

# Request timeout in seconds (default: 30)
export LLM_TIMEOUT=30
```

Available models:
- `gemini-pro` - Text generation
- `gemini-pro-vision` - Multimodal (if needed in future)

#### OpenAI Configuration (Legacy)

```bash
# API Key (required)
export OPENAI_API_KEY=your-api-key-here
# or
export LLM_API_KEY=your-api-key-here

# API base URL (default: https://api.openai.com/v1)
export OPENAI_API_URL=https://api.openai.com/v1

# Model to use (default: gpt-3.5-turbo)
export OPENAI_MODEL=gpt-3.5-turbo

# Request timeout in seconds (default: 30)
export LLM_TIMEOUT=30
```

## Usage Examples

### Basic Usage

```python
from services.llm_client import get_llm_client

# Get the configured LLM client
client = get_llm_client()

# Generate text
response = await client.generate("Explain quantum computing in simple terms")

# Chat completion
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
]
response = await client.chat(messages)
```

### Dynamic Provider Selection

```python
from services.llm_client import LLMClientFactory

# Create a specific client
ollama_client = LLMClientFactory.create_client("ollama")
gemini_client = LLMClientFactory.create_client("google_generative_ai")

# Use different providers for different tasks
local_response = await ollama_client.generate("Quick local task")
cloud_response = await gemini_client.generate("Complex cloud task")
```

### Health Checks

```python
# Check if the LLM service is healthy
health = await client.health_check()
print(f"Provider: {health.get('provider')}")
print(f"Healthy: {health.get('healthy')}")
print(f"Model Available: {health.get('model_available')}")
```

## Choosing Between Providers

### When to use Ollama:
- Privacy is important (all processing is local)
- You have sufficient local compute resources
- You want to avoid API costs
- Low latency is critical
- You need offline capability

### When to use Google Generative AI:
- You need state-of-the-art model performance
- You don't have powerful local hardware
- You need to handle high concurrent load
- You want minimal setup and maintenance
- You need consistent performance

## Environment File Example

Create a `.env` file in your backend directory:

```bash
# Choose your LLM provider
LLM_PROVIDER=ollama

# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_TIMEOUT=60

# Google Generative AI configuration (if using)
# GOOGLE_GENERATIVE_AI_API_KEY=your-api-key
# GOOGLE_GENERATIVE_AI_MODEL=gemini-pro

# OpenAI configuration (if using)
# OPENAI_API_KEY=your-api-key
# OPENAI_MODEL=gpt-3.5-turbo
```

## Troubleshooting

### Ollama Issues
- Ensure Ollama is running: `ollama serve`
- Check if model is available: `ollama list`
- Pull model if needed: `ollama pull llama2`

### Google Generative AI Issues
- Verify API key is correct
- Check API quotas and limits
- Ensure network connectivity

### General Issues
- Check environment variables are set correctly
- Look at backend logs for detailed error messages
- Use health check endpoint to diagnose issues