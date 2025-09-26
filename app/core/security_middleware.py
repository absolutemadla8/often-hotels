import time
from typing import Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.logging import get_logger, log_security_event

logger = get_logger("security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy - relaxed for API documentation
        if request.url.path in ["/docs", "/redoc"]:
            # More permissive CSP for documentation pages
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' https: data: https://fonts.gstatic.com; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
        else:
            # Stricter CSP for regular pages
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https: data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS header (only for HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware
    For production, use Redis-based rate limiting
    """
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: Dict[str, Dict] = {}
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean up old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            log_security_event(
                "rate_limit_exceeded",
                details={"ip": client_ip, "path": request.url.path},
                ip_address=client_ip,
                severity="WARNING"
            )
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Record request
        self._record_request(client_ip, current_time)
        
        response = await call_next(request)
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address, considering proxy headers"""
        if forwarded_for := request.headers.get("X-Forwarded-For"):
            return forwarded_for.split(",")[0].strip()
        if real_ip := request.headers.get("X-Real-IP"):
            return real_ip
        return request.client.host if request.client else "unknown"
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove entries older than the rate limit period"""
        cutoff_time = current_time - self.period
        for client_ip in list(self.clients.keys()):
            client_data = self.clients[client_ip]
            client_data["requests"] = [
                req_time for req_time in client_data["requests"]
                if req_time > cutoff_time
            ]
            if not client_data["requests"]:
                del self.clients[client_ip]
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited"""
        if client_ip not in self.clients:
            return False
        
        client_data = self.clients[client_ip]
        cutoff_time = current_time - self.period
        recent_requests = [
            req_time for req_time in client_data["requests"]
            if req_time > cutoff_time
        ]
        
        return len(recent_requests) >= self.calls
    
    def _record_request(self, client_ip: str, current_time: float):
        """Record a request from the client"""
        if client_ip not in self.clients:
            self.clients[client_ip] = {"requests": []}
        
        self.clients[client_ip]["requests"].append(current_time)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced request logging with security event detection
    """
    
    SUSPICIOUS_PATTERNS = [
        "/admin", "/.env", "/config", "/backup", "/wp-admin",
        "script>", "javascript:", "eval(", "base64",
        "../", "..\\", "/etc/passwd", "/etc/shadow"
    ]
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # Check for suspicious patterns
        self._check_suspicious_request(request, client_ip)
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log request details
        logger.info(
            "HTTP request processed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            process_time=process_time,
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent", ""),
        )
        
        # Log slow requests
        if process_time > 5.0:
            logger.warning(
                "Slow request detected",
                method=request.method,
                path=request.url.path,
                process_time=process_time,
                client_ip=client_ip,
            )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        if forwarded_for := request.headers.get("X-Forwarded-For"):
            return forwarded_for.split(",")[0].strip()
        if real_ip := request.headers.get("X-Real-IP"):
            return real_ip
        return request.client.host if request.client else "unknown"
    
    def _check_suspicious_request(self, request: Request, client_ip: str):
        """Check for suspicious request patterns"""
        url_path = request.url.path.lower()
        query_string = str(request.url.query).lower()
        
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in url_path or pattern in query_string:
                log_security_event(
                    "suspicious_request",
                    details={
                        "pattern": pattern,
                        "path": url_path,
                        "query": query_string,
                        "method": request.method,
                    },
                    ip_address=client_ip,
                    severity="WARNING"
                )
                break


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """
    Validate Host header to prevent Host Header Injection attacks
    """
    
    def __init__(self, app, allowed_hosts: list = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1", "0.0.0.0"]
    
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").lower()
        
        # Extract hostname without port
        hostname = host.split(":")[0] if ":" in host else host
        
        if hostname not in self.allowed_hosts:
            log_security_event(
                "invalid_host_header",
                details={"host": host, "path": request.url.path},
                ip_address=request.client.host if request.client else None,
                severity="WARNING"
            )
            
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid host header"
            )
        
        return await call_next(request)