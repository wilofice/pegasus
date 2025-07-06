# Vertex AI Agent Engine Setup Guide

This guide shows how to configure Pegasus to use Google Vertex AI Agent Engine for advanced session management and conversation tracking.

## Prerequisites

1. **Google Cloud Project**: You need a GCP project with billing enabled
2. **Vertex AI API**: Enable the Vertex AI API in your project
3. **Authentication**: Set up Google Cloud authentication
4. **Agent Engine Instance**: Create a Vertex AI Agent Engine instance

## Step 1: Enable APIs and Set Up Authentication

### Enable Required APIs
```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable vertexai.googleapis.com
```

### Set Up Authentication
Choose one of these authentication methods:

#### Option A: Service Account (Recommended for Production)
```bash
# Create a service account
gcloud iam service-accounts create pegasus-vertex-ai \
    --description="Service account for Pegasus Vertex AI integration" \
    --display-name="Pegasus Vertex AI"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:pegasus-vertex-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Download the service account key
gcloud iam service-accounts keys create ~/pegasus-vertex-ai-key.json \
    --iam-account=pegasus-vertex-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### Option B: User Account (For Development)
```bash
gcloud auth login
gcloud auth application-default login
```

## Step 2: Create Agent Engine Instance

### Using Python SDK
```python
import vertexai
from vertexai import agent_engines

# Initialize Vertex AI
vertexai.init(project="YOUR_PROJECT_ID", location="us-central1")

# Create an agent engine instance
agent_engine = agent_engines.create()
print(f"Agent Engine ID: {agent_engine.name.split('/')[-1]}")
```

### Using gcloud CLI
```bash
# Create the agent engine (replace YOUR_PROJECT_ID and us-central1 as needed)
gcloud alpha vertex-ai reasoning-engines create \
    --region=us-central1 \
    --project=YOUR_PROJECT_ID
```

## Step 3: Configure Pegasus

### Environment Variables
Add these to your `.env` file:

```bash
# LLM Provider
LLM_PROVIDER=vertex_ai

# Vertex AI Configuration
VERTEX_AI_PROJECT_ID=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_AGENT_ENGINE_ID=your-agent-engine-id
VERTEX_AI_MODEL=gemini-2.0-flash
VERTEX_AI_TIMEOUT=60.0
VERTEX_AI_TEMPERATURE=0.7
VERTEX_AI_MAX_TOKENS=2048
VERTEX_AI_TOP_K=40
VERTEX_AI_TOP_P=0.95

# Authentication (if using service account)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
```

### Alternative: Python Configuration
```python
from core.config import settings

# Update settings programmatically
settings.llm_provider = "vertex_ai"
settings.vertex_ai_project_id = "your-gcp-project-id"
settings.vertex_ai_location = "us-central1"
settings.vertex_ai_agent_engine_id = "your-agent-engine-id"
```

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 5: Test the Configuration

### Basic Health Check
```python
from services.llm_client import get_llm_client

client = get_llm_client()
health = await client.health_check()
print(health)
```

### Test Session Management
```python
from services.llm_client import get_llm_client

client = get_llm_client()

# Create a session
session_id = await client.create_session("user123")
print(f"Created session: {session_id}")

# Use session for chat
response = await client.chat_with_session(
    messages=[{"role": "user", "content": "Hello!"}],
    session_id=session_id,
    user_id="user123"
)
print(f"Response: {response}")

# List user sessions
sessions = await client.list_sessions("user123")
print(f"User sessions: {sessions}")
```

## Features

### Session Management
- **Create Sessions**: Automatic session creation per user
- **Persistent Conversations**: Session state maintains conversation history
- **Multi-User Support**: Isolated sessions per user ID
- **Session Cleanup**: Programmatic session deletion

### Event Tracking
- **Conversation Events**: All user and assistant messages tracked
- **Metadata Support**: Custom metadata per event
- **Event History**: Retrieve full conversation history
- **Timestamping**: Precise event timing

### Dual Mode Operation
- **Session Mode**: For applications requiring conversation persistence
- **Stateless Mode**: For one-off queries without session overhead
- **Automatic Fallback**: Graceful degradation if session operations fail

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `VERTEX_AI_PROJECT_ID` | None | Your GCP project ID (required) |
| `VERTEX_AI_LOCATION` | `us-central1` | GCP region for Vertex AI |
| `VERTEX_AI_AGENT_ENGINE_ID` | None | Agent Engine instance ID (required) |
| `VERTEX_AI_MODEL` | `gemini-2.0-flash` | Model for content generation |
| `VERTEX_AI_TIMEOUT` | `60.0` | Request timeout in seconds |
| `VERTEX_AI_TEMPERATURE` | `0.7` | Generation temperature (0.0-1.0) |
| `VERTEX_AI_MAX_TOKENS` | `2048` | Maximum tokens in response |
| `VERTEX_AI_TOP_K` | `40` | Top-K sampling parameter |
| `VERTEX_AI_TOP_P` | `0.95` | Top-P sampling parameter |

## Troubleshooting

### Authentication Issues
```bash
# Check current authentication
gcloud auth list

# Re-authenticate if needed
gcloud auth application-default login
```

### Permission Issues
Ensure your account/service account has these roles:
- `roles/aiplatform.user`
- `roles/ml.developer` (if using custom models)

### Agent Engine Not Found
Verify your Agent Engine ID:
```bash
gcloud alpha vertex-ai reasoning-engines list \
    --region=us-central1 \
    --project=YOUR_PROJECT_ID
```

### Network/Firewall Issues
Ensure these domains are accessible:
- `*.googleapis.com`
- `*-aiplatform.googleapis.com`

## Cost Considerations

- **Session Storage**: Sessions are billed based on storage duration
- **API Calls**: Each generation request is billed per token
- **Event Storage**: Event tracking incurs minimal storage costs

## Security Best Practices

1. **Service Accounts**: Use dedicated service accounts with minimal permissions
2. **Key Rotation**: Regularly rotate service account keys
3. **Network Security**: Use VPC service controls if available
4. **Audit Logging**: Enable Cloud Audit Logs for API calls
5. **Data Residency**: Choose appropriate regions for data sovereignty

## Migration from Other Providers

### From OpenAI
1. Update `LLM_PROVIDER=vertex_ai`
2. Remove OpenAI-specific settings
3. Add Vertex AI configuration
4. Test session functionality

### From Google Generative AI
1. Update `LLM_PROVIDER=vertex_ai`
2. Keep existing Google authentication
3. Add Agent Engine configuration
4. Enjoy enhanced session management

## Support

For issues specific to:
- **Vertex AI**: Check [Google Cloud Status](https://status.cloud.google.com/)
- **Pegasus Integration**: Check application logs
- **Authentication**: Verify IAM permissions and credentials