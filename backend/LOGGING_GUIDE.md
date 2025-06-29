# Request/Response Logging System

## Overview

The Pegasus backend now includes a comprehensive request/response logging middleware that automatically logs all HTTP requests and responses to daily log files.

## Features

- ✅ **Daily Log Files**: Each day gets its own log file (`requests_YYYY-MM-DD.log`)
- ✅ **Structured JSON Logging**: All logs are in JSON format for easy parsing
- ✅ **Request Details**: Method, URL, headers, body, client IP, timestamp
- ✅ **Response Details**: Status code, headers, body, response time
- ✅ **Security**: Sensitive headers (Authorization, Cookie) are redacted
- ✅ **Performance**: Configurable body size limits and exclusions
- ✅ **Binary Handling**: Smart handling of file uploads and binary content
- ✅ **Log Management**: Built-in tools for compression, cleanup, and analysis

## Configuration

### Environment Variables (.env)

```bash
# Enable/disable logging
ENABLE_REQUEST_LOGGING=true

# Log directory (relative to backend root)
LOG_DIRECTORY=./logs

# Maximum body size to log (in bytes)
LOG_MAX_BODY_SIZE=10000

# Whether to log binary content details
LOG_BINARY_CONTENT=false

# Paths to exclude from logging (comma-separated)
LOG_EXCLUDED_PATHS=/health,/docs,/redoc,/openapi.json,/favicon.ico

# HTTP methods to exclude from logging (comma-separated)
LOG_EXCLUDED_METHODS=
```

### Default Excluded Paths

The following paths are excluded by default to reduce noise:
- `/health` - Health check endpoint
- `/docs` - OpenAPI documentation
- `/redoc` - ReDoc documentation  
- `/openapi.json` - OpenAPI schema
- `/favicon.ico` - Browser favicon requests

## Log File Structure

### Location
Log files are stored in the `./logs/` directory by default:
```
logs/
├── requests_2024-01-15.log
├── requests_2024-01-16.log
├── requests_2024-01-17.log.gz  # Compressed old files
└── ...
```

### Log Entry Format

Each log entry is a JSON object on a single line:

#### Request Entry
```json
{
  "request_id": "a1b2c3d4",
  "type": "REQUEST",
  "method": "POST",
  "url": "http://localhost:9000/api/audio/upload",
  "path": "/api/audio/upload",
  "query_params": {"user_id": "test123"},
  "headers": {
    "content-type": "multipart/form-data",
    "authorization": "<REDACTED>",
    "user-agent": "Mozilla/5.0..."
  },
  "client_ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "body_size": 2048,
  "body": {"key": "value"},
  "timestamp": "2024-01-15T10:30:00.123456Z"
}
```

#### Response Entry
```json
{
  "request_id": "a1b2c3d4",
  "type": "RESPONSE",
  "status_code": 200,
  "headers": {
    "content-type": "application/json",
    "content-length": "156"
  },
  "body_size": 156,
  "body": {"id": "uuid", "status": "success"},
  "duration_ms": 245.67,
  "timestamp": "2024-01-15T10:30:00.369123Z"
}
```

### Special Body Handling

- **Large Bodies**: Bodies larger than `LOG_MAX_BODY_SIZE` show as `<LARGE_BODY: X bytes>`
- **Binary Content**: File uploads show as `<BINARY_CONTENT: mime/type>`
- **Streaming**: Streaming responses show as `<STREAMING_RESPONSE>`
- **JSON**: Valid JSON is parsed and stored as objects
- **Text**: Non-JSON text is stored as strings (truncated if too long)

## Log Management

### Manual Commands

```bash
# List all log files
python3 scripts/log_manager.py list

# Show statistics
python3 scripts/log_manager.py stats

# Compress files older than 7 days
python3 scripts/log_manager.py compress --days 7

# Delete files older than 30 days  
python3 scripts/log_manager.py delete --days 30

# Analyze specific date
python3 scripts/log_manager.py analyze 2024-01-15

# Search logs for specific terms
python3 scripts/log_manager.py search 2024-01-15 "audio/upload"
python3 scripts/log_manager.py search 2024-01-15 "error" --type response
```

### Automated Cleanup

Consider setting up a cron job for automatic cleanup:

```bash
# Add to crontab (crontab -e)
# Compress logs older than 7 days (daily at 2 AM)
0 2 * * * cd /path/to/backend && python3 scripts/log_manager.py compress --days 7

# Delete logs older than 90 days (weekly)
0 3 * * 0 cd /path/to/backend && python3 scripts/log_manager.py delete --days 90
```

## Testing

### Test the Logging System
```bash
# Start the backend server
python3 main.py

# In another terminal, run the test
python3 test_logging.py
```

The test will:
1. ✅ Check if the server is running
2. ✅ Make various types of requests
3. ✅ Verify log files are created
4. ✅ Analyze log content
5. ✅ Show statistics

### Manual Testing
```bash
# Make a test request
curl -X GET "http://localhost:9000/api/audio/" \
  -H "Authorization: Bearer test-token" \
  -H "User-Agent: Test-Client/1.0"

# Check today's log file
cat logs/requests_$(date +%Y-%m-%d).log | jq .
```

## Security Considerations

### Sensitive Data Protection

The middleware automatically redacts sensitive headers:
- `Authorization`
- `Cookie` 
- `X-API-Key`
- `X-Auth-Token`
- `Authentication`
- `Proxy-Authorization`

### Binary Content Handling

File uploads and binary content are not logged in full to prevent:
- Log file bloat
- Potential security issues
- Performance problems

Instead, you'll see:
```json
{
  "body": "<BINARY_CONTENT: audio/mp4>",
  "body_size": 2048576
}
```

### Privacy Compliance

For GDPR/privacy compliance:
1. **Exclude sensitive endpoints** via `LOG_EXCLUDED_PATHS`
2. **Limit body logging** with `LOG_MAX_BODY_SIZE`
3. **Regular cleanup** of old logs
4. **Access control** on log directory

## Performance Impact

### Minimal Overhead
- Async processing doesn't block requests
- Body reading is limited by size threshold
- Excluded paths skip logging entirely
- JSON serialization is optimized

### Recommendations
- Keep `LOG_MAX_BODY_SIZE` reasonable (10KB default)
- Exclude high-frequency endpoints if needed
- Compress old logs regularly
- Monitor log directory disk usage

## Troubleshooting

### Common Issues

**Logs not being created:**
```bash
# Check if logging is enabled
grep ENABLE_REQUEST_LOGGING .env

# Check directory permissions
ls -la logs/

# Check server logs for errors
python3 main.py 2>&1 | grep -i log
```

**Large log files:**
```bash
# Check file sizes
python3 scripts/log_manager.py stats

# Reduce body size limit
echo "LOG_MAX_BODY_SIZE=1000" >> .env

# Add more exclusions
echo "LOG_EXCLUDED_PATHS=/health,/metrics,/favicon.ico" >> .env
```

**Performance issues:**
```bash
# Disable logging temporarily
echo "ENABLE_REQUEST_LOGGING=false" >> .env

# Exclude high-traffic endpoints
echo "LOG_EXCLUDED_PATHS=/health,/api/audio/status" >> .env
```

### Log Analysis Examples

```bash
# Find all error responses
grep '"status_code": [45][0-9][0-9]' logs/requests_2024-01-15.log

# Count requests by method
grep '"type": "REQUEST"' logs/requests_2024-01-15.log | jq -r '.method' | sort | uniq -c

# Find slow requests (>1000ms)
grep '"duration_ms"' logs/requests_2024-01-15.log | jq 'select(.duration_ms > 1000)'

# Track specific user activity
grep '"user_id": "test123"' logs/requests_2024-01-15.log | jq .
```

## Integration with Monitoring

### ELK Stack Integration
```bash
# Send logs to Elasticsearch
filebeat -e -c filebeat.yml

# Logstash configuration for JSON parsing
input {
  file {
    path => "/path/to/logs/requests_*.log"
    start_position => "beginning"
    codec => "json"
  }
}
```

### Grafana Dashboard
Create dashboards tracking:
- Request rate over time
- Response time percentiles  
- Error rate by endpoint
- Status code distribution

The logging system provides comprehensive visibility into your API usage while maintaining performance and security!