import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import Processor

from app.core.config import settings


def setup_logging() -> None:
    """
    Setup structured logging with structlog
    """
    timestamper = structlog.processors.TimeStamper(fmt="ISO")
    
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        timestamper,
    ]

    if settings.LOG_FORMAT == "json":
        # JSON formatting for production
        structlog.configure(
            processors=shared_processors
            + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
    else:
        # Console formatting for development
        structlog.configure(
            processors=shared_processors
            + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(),
            foreign_pre_chain=shared_processors,
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # Set specific loggers
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.error").handlers = [handler]
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance
    """
    return structlog.get_logger(name)


class LoggingMiddleware:
    """
    Middleware for logging HTTP requests and responses
    """
    def __init__(self, app):
        self.app = app
        self.logger = get_logger("http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = None
        status_code = 500
        
        async def send_wrapper(message):
            nonlocal status_code, start_time
            if message["type"] == "http.response.start":
                status_code = message["status"]
                start_time = message.get("start_time")
            await send(message)

        try:
            request_info = {
                "method": scope["method"],
                "path": scope["path"],
                "query_string": scope.get("query_string", b"").decode(),
                "client": scope.get("client"),
                "user_agent": dict(scope.get("headers", [])).get(b"user-agent", b"").decode(),
            }
            
            self.logger.info("Request started", **request_info)
            
            await self.app(scope, receive, send_wrapper)
            
            self.logger.info(
                "Request completed",
                status_code=status_code,
                **request_info
            )
            
        except Exception as e:
            self.logger.error(
                "Request failed",
                error=str(e),
                error_type=type(e).__name__,
                **request_info
            )
            raise


def log_user_action(
    user_id: int,
    action: str,
    resource: str = None,
    details: Dict[str, Any] = None,
    ip_address: str = None,
    user_agent: str = None,
):
    """
    Log user actions for audit trail
    """
    logger = get_logger("audit")
    logger.info(
        "User action",
        user_id=user_id,
        action=action,
        resource=resource,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_security_event(
    event_type: str,
    details: Dict[str, Any] = None,
    user_id: int = None,
    ip_address: str = None,
    severity: str = "INFO",
):
    """
    Log security events
    """
    logger = get_logger("security")
    log_func = getattr(logger, severity.lower(), logger.info)
    log_func(
        "Security event",
        event_type=event_type,
        details=details,
        user_id=user_id,
        ip_address=ip_address,
    )