"""Request/Response logging middleware for FastAPI."""
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.config import settings


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests and responses to daily log files."""
    
    def __init__(self, app: ASGIApp, log_dir: str = "./logs"):
        super().__init__(app)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self._setup_logger()
    
    def _setup_logger(self):
        """Set up the daily rotating logger."""
        # Create a logger specifically for request/response logging
        self.logger = logging.getLogger("request_response_logger")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # We'll add handlers dynamically per day
        self.logger.propagate = False
    
    def _get_daily_logger(self) -> logging.Logger:
        """Get or create a logger for today's date."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"requests_{today}.log"
        
        # Check if we need to create a new handler for today
        handler_name = f"daily_handler_{today}"
        existing_handler = None
        
        for handler in self.logger.handlers:
            if hasattr(handler, 'baseFilename') and handler_name in str(handler.baseFilename):
                existing_handler = handler
                break
        
        if not existing_handler:
            # Remove old handlers (from previous days)
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
                handler.close()
            
            # Create new handler for today
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # Add handler to logger
            self.logger.addHandler(file_handler)
        
        return self.logger
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log request/response details."""
        # Generate unique request ID
        request_id = str(uuid4())[:8]
        start_time = time.time()
        
        # Log request
        await self._log_request(request, request_id)
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        await self._log_response(response, request_id, duration)
        
        return response
    
    async def _log_request(self, request: Request, request_id: str):
        """Log incoming request details."""
        logger = self._get_daily_logger()
        
        # Extract request information
        request_data = {
            "request_id": request_id,
            "type": "REQUEST",
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": self._sanitize_headers(dict(request.headers)),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Try to capture request body (with size limit)
        try:
            body = await self._get_request_body(request)
            if body:
                request_data["body_size"] = len(body)
                if len(body) < 10000:  # Only log body if less than 10KB
                    try:
                        # Try to parse as JSON
                        request_data["body"] = json.loads(body)
                    except json.JSONDecodeError:
                        # If not JSON, log as string (truncated if too long)
                        request_data["body"] = body[:1000] + "..." if len(body) > 1000 else body
                else:
                    request_data["body"] = f"<LARGE_BODY: {len(body)} bytes>"
        except Exception as e:
            request_data["body_error"] = str(e)
        
        # Log the request
        logger.info(json.dumps(request_data, ensure_ascii=False, default=str))
    
    async def _log_response(self, response: Response, request_id: str, duration: float):
        """Log outgoing response details."""
        logger = self._get_daily_logger()
        
        # Extract response information
        response_data = {
            "request_id": request_id,
            "type": "RESPONSE", 
            "status_code": response.status_code,
            "headers": self._sanitize_headers(dict(response.headers)),
            "duration_ms": round(duration * 1000, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Try to capture response body
        try:
            body = await self._get_response_body(response)
            if body:
                response_data["body_size"] = len(body)
                if len(body) < 10000:  # Only log body if less than 10KB
                    try:
                        # Try to parse as JSON
                        response_data["body"] = json.loads(body)
                    except json.JSONDecodeError:
                        # If not JSON, log as string (truncated if too long)
                        response_data["body"] = body[:1000] + "..." if len(body) > 1000 else body
                else:
                    response_data["body"] = f"<LARGE_BODY: {len(body)} bytes>"
            else:
                response_data["body"] = json.loads(response)
        except Exception as e:
            response_data["body_error"] = str(e)
        
        # Log the response
        logger.info(json.dumps(response_data, ensure_ascii=False, default=str))
    
    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Safely extract request body."""
        try:
            # Check if request has body
            if request.method in ["GET", "HEAD", "OPTIONS"]:
                return None
            
            # Check content type
            content_type = request.headers.get("content-type", "")
            
            # Skip binary content
            if any(t in content_type.lower() for t in ["image/", "video/", "audio/", "application/octet-stream"]):
                return f"<BINARY_CONTENT: {content_type}>"
            
            # Get body
            body = await request.body()
            if body:
                return body.decode('utf-8', errors='replace')
            return None
            
        except Exception:
            return None
    
    async def _get_response_body(self, response: Response) -> Optional[str]:
        """Safely extract response body."""
        try:
            # For error responses (4xx, 5xx), try harder to get the body
            is_error = response.status_code >= 400
            
            # Skip streaming responses (unless it's an error)
            if isinstance(response, StreamingResponse) and not is_error:
                return "<STREAMING_RESPONSE>"
            
            # Check content type
            content_type = response.headers.get("content-type", "")
            
            # Skip binary content (unless it's an error)
            if not is_error and any(t in content_type.lower() for t in ["image/", "video/", "audio/", "application/octet-stream"]):
                return f"<BINARY_CONTENT: {content_type}>"
            
            # For FastAPI responses, try to get the actual content
            if hasattr(response, 'body') and response.body:
                if isinstance(response.body, bytes):
                    return response.body.decode('utf-8', errors='replace')
                else:
                    return str(response.body)
            
            # For streaming responses with errors, try to read the content
            if isinstance(response, StreamingResponse) and is_error:
                return "<ERROR_STREAMING_RESPONSE>"
            
            return None
            
        except Exception as e:
            return f"<BODY_READ_ERROR: {str(e)}>"
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive information from headers."""
        sensitive_headers = {
            "authorization", "cookie", "x-api-key", "x-auth-token", 
            "authentication", "proxy-authorization"
        }
        
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in sensitive_headers:
                sanitized[key] = "<REDACTED>"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


class RequestLoggingConfig:
    """Configuration for request logging middleware."""
    
    def __init__(
        self,
        log_dir: str = "./logs",
        max_body_size: int = 10000,
        log_binary_content: bool = False,
        excluded_paths: Optional[list] = None,
        excluded_methods: Optional[list] = None
    ):
        self.log_dir = log_dir
        self.max_body_size = max_body_size
        self.log_binary_content = log_binary_content
        self.excluded_paths = excluded_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.excluded_methods = excluded_methods or []


class SelectiveLoggingMiddleware(RequestResponseLoggingMiddleware):
    """Enhanced logging middleware with selective logging capabilities."""
    
    def __init__(self, app: ASGIApp, config: RequestLoggingConfig = None):
        self.config = config or RequestLoggingConfig()
        super().__init__(app, self.config.log_dir)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with selective logging."""
        # Check if this request should be logged
        if self._should_skip_logging(request):
            return await call_next(request)
        
        # Use parent's dispatch method for logging
        return await super().dispatch(request, call_next)
    
    def _should_skip_logging(self, request: Request) -> bool:
        """Determine if this request should be skipped from logging."""
        # Skip excluded paths
        if request.url.path in self.config.excluded_paths:
            return True
        
        # Skip excluded methods
        if request.method in self.config.excluded_methods:
            return True
        
        # Skip health checks and static files
        if request.url.path.startswith(("/health", "/static", "/favicon")):
            return True
        
        return False