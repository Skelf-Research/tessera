"""
Structured logging for Tessera operations.
Provides secure, configurable logging with sensitive data protection.
"""

import logging
import logging.handlers
import json
import time
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ..utils.exceptions import TesseraError


class SecurityLogFormatter(logging.Formatter):
    """Custom formatter for security-sensitive logs."""

    def __init__(self):
        super().__init__()
        self.sensitive_fields = {
            'private_key', 'master_password', 'secret', 'password',
            'token', 'signature', 'proof_data', 'key_material'
        }

    def format(self, record):
        """Format log record with sensitive data protection."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            extra = self._sanitize_data(record.extra_data)
            log_data.update(extra)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or hash sensitive data from log entries."""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if key.lower() in self.sensitive_fields:
                if isinstance(value, (str, bytes)):
                    # Hash sensitive values for correlation while protecting data
                    hash_obj = hashlib.sha256(str(value).encode())
                    sanitized[f"{key}_hash"] = hash_obj.hexdigest()[:16]
                else:
                    sanitized[f"{key}_present"] = True
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value

        return sanitized


class TesseraLogger:
    """
    Main logger for Tessera operations.
    Provides structured logging with security considerations.
    """

    def __init__(self, name: str = "tessera", log_dir: str = None,
                 log_level: str = "INFO", max_bytes: int = 10*1024*1024,
                 backup_count: int = 5):
        """
        Initialize Tessera logger.

        Args:
            name: Logger name
            log_dir: Directory for log files (defaults to ~/.tessera/logs)
            log_level: Logging level
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Set up log directory
        if log_dir is None:
            log_dir = os.path.expanduser("~/.tessera/logs")

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.log_dir, 0o700)

        # Configure handlers
        self._setup_handlers(max_bytes, backup_count)

    def _setup_handlers(self, max_bytes: int, backup_count: int):
        """Set up file and console handlers."""
        # Clear existing handlers
        self.logger.handlers.clear()

        # File handler with rotation
        log_file = self.log_dir / f"{self.name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(SecurityLogFormatter())
        self.logger.addHandler(file_handler)

        # Console handler for development
        if os.getenv('CALLDNS_DEBUG'):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(SecurityLogFormatter())
            self.logger.addHandler(console_handler)

        # Set restrictive permissions on log files
        os.chmod(log_file, 0o600)

    def log(self, level: str, message: str, **kwargs):
        """Log a message with optional extra data."""
        log_method = getattr(self.logger, level.lower())

        # Create log record with extra data
        extra = {'extra_data': kwargs} if kwargs else {}
        log_method(message, extra=extra)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log('info', message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log('warning', message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log('error', message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log('debug', message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.log('critical', message, **kwargs)


class SecurityLogger(TesseraLogger):
    """
    Specialized logger for security events.
    Tracks authentication, authorization, and potential security issues.
    """

    def __init__(self, log_dir: str = None):
        super().__init__("tessera.security", log_dir)
        self.security_events = []
        self._setup_security_monitoring()

    def _setup_security_monitoring(self):
        """Set up security-specific monitoring."""
        # Additional handler for security alerts
        security_log_file = self.log_dir / "security.log"
        security_handler = logging.handlers.RotatingFileHandler(
            security_log_file, maxBytes=5*1024*1024, backupCount=10
        )
        security_handler.setFormatter(SecurityLogFormatter())
        self.logger.addHandler(security_handler)

        os.chmod(security_log_file, 0o600)

    def log_authentication(self, identity_id: str, success: bool,
                         remote_addr: str = None, user_agent: str = None):
        """Log authentication attempt."""
        event_data = {
            'event_type': 'authentication',
            'identity_id': identity_id,
            'success': success,
            'remote_addr': remote_addr,
            'user_agent': user_agent,
            'timestamp': time.time()
        }

        level = 'info' if success else 'warning'
        message = f"Authentication {'successful' if success else 'failed'} for identity {identity_id}"

        self.log(level, message, **event_data)
        self.security_events.append(event_data)

    def log_proof_generation(self, identity_id: str, proof_type: str,
                           metadata: Dict[str, Any] = None):
        """Log proof generation event."""
        event_data = {
            'event_type': 'proof_generation',
            'identity_id': identity_id,
            'proof_type': proof_type,
            'metadata': metadata or {},
            'timestamp': time.time()
        }

        message = f"Proof generated for identity {identity_id}, type: {proof_type}"
        self.info(message, **event_data)
        self.security_events.append(event_data)

    def log_proof_verification(self, verifier_id: str, proof_valid: bool,
                             sender_id: str = None, metadata: Dict[str, Any] = None):
        """Log proof verification event."""
        event_data = {
            'event_type': 'proof_verification',
            'verifier_id': verifier_id,
            'sender_id': sender_id,
            'proof_valid': proof_valid,
            'metadata': metadata or {},
            'timestamp': time.time()
        }

        level = 'info' if proof_valid else 'warning'
        message = f"Proof verification {'successful' if proof_valid else 'failed'} by {verifier_id}"

        self.log(level, message, **event_data)
        self.security_events.append(event_data)

    def log_key_operation(self, operation: str, identity_id: str,
                         success: bool, metadata: Dict[str, Any] = None):
        """Log key management operation."""
        event_data = {
            'event_type': 'key_operation',
            'operation': operation,
            'identity_id': identity_id,
            'success': success,
            'metadata': metadata or {},
            'timestamp': time.time()
        }

        level = 'info' if success else 'error'
        message = f"Key operation '{operation}' {'successful' if success else 'failed'} for {identity_id}"

        self.log(level, message, **event_data)
        self.security_events.append(event_data)

    def log_security_violation(self, violation_type: str, details: Dict[str, Any],
                              severity: str = 'high'):
        """Log security violation or suspicious activity."""
        event_data = {
            'event_type': 'security_violation',
            'violation_type': violation_type,
            'severity': severity,
            'details': details,
            'timestamp': time.time()
        }

        level = 'critical' if severity == 'critical' else 'error'
        message = f"Security violation detected: {violation_type}"

        self.log(level, message, **event_data)
        self.security_events.append(event_data)

    def get_recent_events(self, event_type: str = None,
                         hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent security events."""
        cutoff_time = time.time() - (hours * 3600)

        recent_events = [
            event for event in self.security_events
            if event['timestamp'] > cutoff_time
        ]

        if event_type:
            recent_events = [
                event for event in recent_events
                if event.get('event_type') == event_type
            ]

        return recent_events

    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security event summary."""
        recent_events = self.get_recent_events(hours=hours)

        summary = {
            'total_events': len(recent_events),
            'authentication_attempts': len([e for e in recent_events if e.get('event_type') == 'authentication']),
            'failed_authentications': len([e for e in recent_events if e.get('event_type') == 'authentication' and not e.get('success')]),
            'proof_generations': len([e for e in recent_events if e.get('event_type') == 'proof_generation']),
            'proof_verifications': len([e for e in recent_events if e.get('event_type') == 'proof_verification']),
            'failed_verifications': len([e for e in recent_events if e.get('event_type') == 'proof_verification' and not e.get('proof_valid')]),
            'security_violations': len([e for e in recent_events if e.get('event_type') == 'security_violation']),
            'key_operations': len([e for e in recent_events if e.get('event_type') == 'key_operation']),
            'period_hours': hours
        }

        return summary