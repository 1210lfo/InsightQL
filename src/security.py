"""
Security module for InsightQL
Centralizes security utilities and best practices.
"""

import logging
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# Error Sanitization - Don't expose raw errors to users
# =============================================================================

# Patterns that should NEVER be exposed to users
SENSITIVE_PATTERNS = [
    r"password[=:]\s*\S+",
    r"api[_-]?key[=:]\s*\S+",
    r"token[=:]\s*\S+",
    r"secret[=:]\s*\S+",
    r"postgresql://[^\s]+",
    r"supabase\.co/[^\s]+",
    r"SUPABASE_[A-Z_]+",
    r"GITHUB_TOKEN",
    r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",  # JWT tokens
]

USER_FRIENDLY_ERRORS = {
    "connection refused": "No se pudo conectar a la base de datos. Por favor intenta de nuevo.",
    "timeout": "La consulta tardó demasiado. Intenta con filtros más específicos.",
    "rate limit": "Demasiadas consultas. Por favor espera unos segundos.",
    "permission denied": "No tienes permisos para realizar esta operación.",
    "invalid api key": "Error de configuración del servidor. Contacta al administrador.",
    "quota exceeded": "Se alcanzó el límite de uso. Intenta más tarde.",
    "no data": "No se encontraron datos con los filtros especificados.",
}


def sanitize_error(error: Exception | str) -> str:
    """
    Sanitize error messages to avoid exposing sensitive information.
    
    Args:
        error: The error to sanitize
        
    Returns:
        A user-friendly error message
    """
    error_str = str(error).lower()
    
    # Check for known error patterns
    for pattern, friendly_msg in USER_FRIENDLY_ERRORS.items():
        if pattern in error_str:
            logger.error(f"Original error (sanitized for user): {error}")
            return friendly_msg
    
    # Check for sensitive information
    original_str = str(error)
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, original_str, re.IGNORECASE):
            logger.error(f"Sensitive data in error (hidden from user): {error}")
            return "Ocurrió un error interno. Por favor intenta de nuevo."
    
    # Generic error - still log the original
    logger.error(f"Error: {error}")
    
    # Return a sanitized version (remove paths, stack traces)
    if "Traceback" in original_str or "File \"" in original_str:
        return "Ocurrió un error procesando tu consulta. Intenta de nuevo."
    
    # Allow short, non-sensitive errors through
    if len(original_str) < 100 and not any(
        s in original_str.lower() for s in ["key", "token", "password", "secret"]
    ):
        return f"Error: {original_str}"
    
    return "Ocurrió un error. Por favor intenta de nuevo."


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, identifier: str = "default") -> bool:
        """
        Check if a request is allowed under the rate limit.
        
        Args:
            identifier: Unique identifier for rate limiting (e.g., session_id)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]
        
        # Check limit
        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        # Record request
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str = "default") -> int:
        """Get remaining requests in the current window."""
        now = time.time()
        window_start = now - self.window_seconds
        
        current_requests = len([
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ])
        
        return max(0, self.max_requests - current_requests)


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        from src.config import get_config
        config = get_config()
        _rate_limiter = RateLimiter(
            max_requests=config.agent.max_requests_per_minute,
            window_seconds=60
        )
    return _rate_limiter


def rate_limit(func: Callable) -> Callable:
    """Decorator to apply rate limiting to a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        limiter = get_rate_limiter()
        if not limiter.is_allowed():
            raise RateLimitError("Demasiadas consultas. Por favor espera unos segundos.")
        return func(*args, **kwargs)
    return wrapper


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    pass


# =============================================================================
# Input Validation
# =============================================================================

# Blocked patterns for prompt injection prevention
BLOCKED_PATTERNS = [
    r"ignore\s+(previous|all)\s+instructions",
    r"system\s*:\s*",
    r"<\s*script\s*>",
    r"javascript\s*:",
    r"data\s*:.*base64",
    r";\s*drop\s+table",
    r"--\s*$",
    r"union\s+select",
    r"or\s+1\s*=\s*1",
]


def validate_user_input(query: str) -> tuple[bool, str]:
    """
    Validate user input for security issues.
    
    Args:
        query: The user's query string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "La consulta no puede estar vacía."
    
    if len(query) > 2000:
        return False, "La consulta es demasiado larga. Máximo 2000 caracteres."
    
    # Check for blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Blocked pattern detected in query: {pattern}")
            return False, "La consulta contiene patrones no permitidos."
    
    return True, ""


def sanitize_parameters(params: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize parameters before sending to database.
    
    Args:
        params: Dictionary of parameters
        
    Returns:
        Sanitized parameters
    """
    sanitized = {}
    
    for key, value in params.items():
        if value is None:
            continue
            
        if isinstance(value, str):
            # Remove null bytes
            value = value.replace("\x00", "")
            # Limit string length
            value = value[:500]
            # Basic SQL injection prevention (RPC functions use parameterized queries)
            value = value.replace("'", "''")
            
        sanitized[key] = value
    
    return sanitized


# =============================================================================
# Audit Logging
# =============================================================================

def audit_log(
    action: str,
    details: dict[str, Any] | None = None,
    user_id: str = "anonymous",
    severity: str = "INFO"
) -> None:
    """
    Log an auditable action for security monitoring.
    
    Args:
        action: Description of the action
        details: Additional details about the action
        user_id: Identifier for the user (session-based for Streamlit)
        severity: Log severity level
    """
    audit_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "user_id": user_id,
        "details": details or {},
    }
    
    log_func = {
        "DEBUG": logger.debug,
        "INFO": logger.info,
        "WARNING": logger.warning,
        "ERROR": logger.error,
        "CRITICAL": logger.critical,
    }.get(severity.upper(), logger.info)
    
    log_func(f"AUDIT: {audit_entry}")


# =============================================================================
# Environment Validation
# =============================================================================

def validate_environment() -> list[str]:
    """
    Validate that required environment variables are set.
    
    Returns:
        List of warnings/errors about the environment
    """
    import os
    
    issues = []
    
    required_vars = [
        ("SUPABASE_URL", "Database URL"),
        ("SUPABASE_SERVICE_ROLE_KEY", "Database access key"),
        ("GITHUB_TOKEN", "LLM API access"),
    ]
    
    for var, description in required_vars:
        value = os.getenv(var, "")
        if not value:
            issues.append(f"❌ {var} no configurado ({description})")
        elif var.endswith("_KEY") or var.endswith("_TOKEN"):
            # Check for placeholder values
            if "xxx" in value.lower() or "your_" in value.lower():
                issues.append(f"⚠️ {var} parece tener un valor placeholder")
    
    # Check for development mode indicators
    if os.getenv("DEBUG", "").lower() == "true":
        issues.append("⚠️ DEBUG mode está habilitado - deshabilitar en producción")
    
    return issues
