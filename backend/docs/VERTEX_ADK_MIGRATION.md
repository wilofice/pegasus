# Vertex AI Agent Development Kit (ADK) Migration Guide

## Overview

The Pegasus backend has been evolved to support Google's Vertex AI Agent Development Kit (ADK) for advanced session management and agent orchestration. This provides more robust conversation handling, better session persistence, and enhanced agent capabilities.

## What's New

### ✨ **Vertex ADK Integration**
- **Advanced Session Management**: Built-in session persistence with Vertex AI Agent Engine
- **Agent Orchestration**: Custom Pegasus agent with specialized tools and instructions
- **Tool Integration**: Extensible framework for adding Pegasus-specific capabilities
- **Enhanced Context**: Better conversation context handling across sessions
- **Robust Error Handling**: Fallback mechanisms and comprehensive error recovery

### 🔧 **Technical Improvements**
- **ADK Agent**: Custom agent with Pegasus-specific instructions and tools
- **Session Service**: Integrated VertexAiSessionService for automatic session management
- **Event Streaming**: Real-time agent response processing
- **Health Monitoring**: Comprehensive health checks for ADK components

## Migration Path

### **Option 1: Switch to ADK (Recommended)**
```bash
# Update environment variable
echo "LLM_PROVIDER=vertex_adk" >> backend/.env
```

### **Option 2: Keep Current Implementation**
```bash
# Keep existing configuration 
echo "LLM_PROVIDER=vertex_ai" >> backend/.env
```

## Configuration

### **New ADK Client Settings**
All existing Vertex AI settings are reused:

```env
# LLM Provider (NEW: Use vertex_adk for ADK)
LLM_PROVIDER=vertex_adk

# Vertex AI Configuration (Same as before)
VERTEX_AI_PROJECT_ID=gen-lang-client-0319023828
VERTEX_AI_LOCATION=europe-west4
VERTEX_AI_AGENT_ENGINE_ID=3290583215235923968
VERTEX_AI_MODEL=gemini-2.5-flash
VERTEX_AI_TIMEOUT=60.0
VERTEX_AI_TEMPERATURE=0.7
VERTEX_AI_MAX_TOKENS=2048
VERTEX_AI_TOP_K=40
VERTEX_AI_TOP_P=0.95
VERTEX_AI_USER_ID=pegasus_user

# Authentication (Same as before)
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### **Dependencies**
The ADK dependencies are already installed:
```bash
google-cloud-aiplatform[adk,agent_engine]>=1.42.0
google-adk>=1.5.0
```

## Key Differences

### **Session Management**
| Feature | Current (vertex_ai) | New (vertex_adk) |
|---------|-------------------|------------------|
| Session Creation | Manual API calls | ADK VertexAiSessionService |
| Session Persistence | Custom retry logic | Built-in ADK handling |
| Event Management | Manual event formatting | ADK event streaming |
| Error Recovery | Basic fallbacks | Comprehensive ADK error handling |

### **Agent Capabilities**
| Feature | Current | New ADK |
|---------|---------|----------|
| Instructions | System prompts | Custom Pegasus agent with tools |
| Context Handling | Message-based | Session-based with state |
| Tool Integration | None | Extensible tool framework |
| Response Processing | Direct API responses | Agent orchestration |

## Testing the Migration

### **1. Test ADK Client Functionality**
```python
# Test basic ADK client creation
from services.llm.vertex_adk_client import VertexADKClient

client = VertexADKClient()
health = await client.health_check()
print(f"ADK Health: {health}")
```

### **2. Test Factory Integration**
```python
# Test factory switching
from services.llm.factory import LLMClientFactory

# Current implementation
vertex_client = LLMClientFactory.create_client("vertex_ai")

# New ADK implementation  
adk_client = LLMClientFactory.create_client("vertex_adk")
```

### **3. Test Session Management**
```python
# Create session and test conversation
client = VertexADKClient()
session_id = await client.create_session("test_user")
response = await client.chat_with_session(
    messages=[{"role": "user", "content": "Hello!"}],
    session_id=session_id,
    user_id="test_user"
)
print(f"Response: {response}")
```

## Benefits of ADK Migration

### **🚀 Enhanced Performance**
- **Optimized Session Handling**: ADK provides native session optimization
- **Reduced Latency**: Built-in connection pooling and caching
- **Better Scaling**: Automatic load balancing for high-volume requests

### **🔒 Improved Reliability**
- **Robust Error Handling**: ADK includes comprehensive error recovery
- **Session Persistence**: Built-in session state management
- **Health Monitoring**: Automatic health checks and service monitoring

### **⚡ Advanced Features**
- **Tool Integration**: Framework for adding custom Pegasus tools
- **Agent Orchestration**: Multi-step reasoning and planning capabilities
- **Context Awareness**: Enhanced conversation context across sessions
- **State Management**: Persistent conversation state and memory

### **🛠 Better Maintainability**
- **Standardized API**: ADK provides consistent interface patterns
- **Future-Proof**: Built on Google's official agent framework
- **Documentation**: Comprehensive ADK documentation and examples
- **Community Support**: Active ADK community and updates

## Rollback Plan

If issues arise, you can easily rollback:

```bash
# Rollback to current implementation
echo "LLM_PROVIDER=vertex_ai" >> backend/.env

# Restart the backend
# The system will automatically use the current Vertex AI client
```

## Current Status

### ✅ **Completed**
- [x] ADK dependencies installed
- [x] VertexADKClient implementation complete
- [x] Factory integration complete
- [x] Session management implemented
- [x] Health checks implemented
- [x] Error handling and fallbacks
- [x] Backward compatibility maintained

### 🔄 **Testing Phase**
- [ ] Production testing with authentication
- [ ] Performance comparison testing
- [ ] Session persistence validation
- [ ] Tool integration testing

### 📋 **Next Steps**
1. **Switch to ADK**: Update `LLM_PROVIDER=vertex_adk` in production
2. **Monitor Performance**: Compare ADK vs current implementation
3. **Validate Sessions**: Ensure session persistence works correctly
4. **Add Custom Tools**: Extend Pegasus agent with domain-specific tools

## Support

The ADK implementation maintains full backward compatibility. The original `vertex_client.py` remains available as `LLM_PROVIDER=vertex_ai`.

For issues or questions:
1. Check ADK health status: `GET /health` endpoint
2. Review logs for ADK-specific error messages
3. Test session functionality with dedicated endpoints
4. Fallback to original implementation if needed

---

**Ready to migrate to Vertex ADK for enhanced session management and agent capabilities!** 🚀