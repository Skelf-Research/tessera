"""
System monitoring and alerting for Tessera.
Provides real-time monitoring, health checks, and anomaly detection.
"""

import time
import threading
import statistics
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
from datetime import datetime, timedelta

from .logger import SecurityLogger
from .metrics import MetricsCollector


@dataclass
class HealthCheck:
    """Health check definition."""

    name: str
    check_func: Callable[[], bool]
    critical: bool = False
    interval: int = 60
    timeout: int = 30
    last_run: float = 0
    last_status: bool = True
    consecutive_failures: int = 0


@dataclass
class Alert:
    """Alert definition."""

    id: str
    severity: str
    message: str
    timestamp: float
    source: str
    metadata: Dict[str, Any]
    acknowledged: bool = False


@dataclass
class Threshold:
    """Monitoring threshold definition."""

    metric_name: str
    operator: str  # 'gt', 'lt', 'eq'
    value: float
    duration: int  # seconds
    severity: str


class SecurityMonitor:
    """
    Security monitoring and threat detection.
    Monitors for suspicious patterns and security violations.
    """

    def __init__(
        self, security_logger: SecurityLogger, metrics_collector: MetricsCollector
    ):
        self.security_logger = security_logger
        self.metrics_collector = metrics_collector
        self._lock = threading.RLock()

        # Tracking for anomaly detection
        self.auth_attempts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.failed_verifications: deque = deque(maxlen=1000)
        self.request_patterns: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=1000)
        )

        # Thresholds for alerts
        self.thresholds = {
            "max_auth_failures_per_minute": 5,
            "max_verification_failures_per_minute": 10,
            "max_requests_per_minute": 100,
            "suspicious_request_pattern_threshold": 0.8,
        }

        # Start monitoring thread
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_worker, daemon=True
        )
        self._monitoring_thread.start()

    def track_authentication_attempt(
        self, identity_id: str, success: bool, remote_addr: str = None
    ):
        """Track authentication attempt for anomaly detection."""
        with self._lock:
            timestamp = time.time()
            self.auth_attempts[identity_id].append(
                {"timestamp": timestamp, "success": success, "remote_addr": remote_addr}
            )

            # Check for suspicious patterns
            if not success:
                self._check_auth_failure_pattern(identity_id, remote_addr)

    def track_verification_failure(
        self, verifier_id: str, metadata: Dict[str, Any] = None
    ):
        """Track proof verification failure."""
        with self._lock:
            self.failed_verifications.append(
                {
                    "timestamp": time.time(),
                    "verifier_id": verifier_id,
                    "metadata": metadata or {},
                }
            )

            self._check_verification_failure_pattern()

    def track_request_pattern(
        self, endpoint: str, remote_addr: str, user_agent: str = None
    ):
        """Track request patterns for anomaly detection."""
        with self._lock:
            pattern_key = f"{remote_addr}:{endpoint}"
            self.request_patterns[pattern_key].append(
                {"timestamp": time.time(), "user_agent": user_agent}
            )

            self._check_request_pattern_anomaly(pattern_key, remote_addr)

    def _check_auth_failure_pattern(self, identity_id: str, remote_addr: str):
        """Check for suspicious authentication failure patterns."""
        recent_failures = [
            attempt
            for attempt in self.auth_attempts[identity_id]
            if not attempt["success"] and time.time() - attempt["timestamp"] < 60
        ]

        if len(recent_failures) >= self.thresholds["max_auth_failures_per_minute"]:
            self.security_logger.log_security_violation(
                "excessive_auth_failures",
                {
                    "identity_id": identity_id,
                    "remote_addr": remote_addr,
                    "failure_count": len(recent_failures),
                    "time_window": "1_minute",
                },
                severity="high",
            )

    def _check_verification_failure_pattern(self):
        """Check for suspicious verification failure patterns."""
        recent_failures = [
            failure
            for failure in self.failed_verifications
            if time.time() - failure["timestamp"] < 60
        ]

        if (
            len(recent_failures)
            >= self.thresholds["max_verification_failures_per_minute"]
        ):
            self.security_logger.log_security_violation(
                "excessive_verification_failures",
                {"failure_count": len(recent_failures), "time_window": "1_minute"},
                severity="high",
            )

    def _check_request_pattern_anomaly(self, pattern_key: str, remote_addr: str):
        """Check for anomalous request patterns."""
        recent_requests = [
            req
            for req in self.request_patterns[pattern_key]
            if time.time() - req["timestamp"] < 60
        ]

        # Check rate limiting
        if len(recent_requests) >= self.thresholds["max_requests_per_minute"]:
            self.security_logger.log_security_violation(
                "rate_limit_exceeded",
                {
                    "remote_addr": remote_addr,
                    "request_count": len(recent_requests),
                    "time_window": "1_minute",
                },
                severity="medium",
            )

        # Check for bot-like behavior (identical user agents, perfect timing)
        if len(recent_requests) > 10:
            user_agents = [
                req.get("user_agent")
                for req in recent_requests
                if req.get("user_agent")
            ]
            if len(set(user_agents)) == 1 and len(user_agents) > 5:
                timestamps = [req["timestamp"] for req in recent_requests]
                if len(timestamps) > 5:
                    intervals = [
                        timestamps[i] - timestamps[i - 1]
                        for i in range(1, len(timestamps))
                    ]
                    if statistics.stdev(intervals) < 0.1:  # Very consistent timing
                        self.security_logger.log_security_violation(
                            "bot_like_behavior",
                            {
                                "remote_addr": remote_addr,
                                "request_count": len(recent_requests),
                                "user_agent": user_agents[0] if user_agents else None,
                                "timing_consistency": statistics.stdev(intervals),
                            },
                            severity="medium",
                        )

    def _monitoring_worker(self):
        """Background worker for continuous monitoring."""
        while self._monitoring_active:
            try:
                time.sleep(30)  # Check every 30 seconds
                self._cleanup_old_data()
                self._check_system_health()
            except Exception as e:
                self.security_logger.error(f"Security monitoring error: {e}")

    def _cleanup_old_data(self):
        """Clean up old tracking data."""
        with self._lock:
            cutoff_time = time.time() - 3600  # Keep 1 hour of data

            # Clean auth attempts
            for identity_id in list(self.auth_attempts.keys()):
                attempts = self.auth_attempts[identity_id]
                while attempts and attempts[0]["timestamp"] < cutoff_time:
                    attempts.popleft()
                if not attempts:
                    del self.auth_attempts[identity_id]

            # Clean request patterns
            for pattern_key in list(self.request_patterns.keys()):
                requests = self.request_patterns[pattern_key]
                while requests and requests[0]["timestamp"] < cutoff_time:
                    requests.popleft()
                if not requests:
                    del self.request_patterns[pattern_key]

    def _check_system_health(self):
        """Perform system health checks."""
        # Check for anomalous patterns in metrics
        metrics_summary = self.metrics_collector.get_metrics_summary()

        # Check verification success rate
        proof_metrics = metrics_summary.get("proof_metrics", {})
        success_rate = proof_metrics.get("verification_success_rate", 1.0)
        if success_rate < 0.9:  # Less than 90% success rate
            self.security_logger.log_security_violation(
                "low_verification_success_rate",
                {
                    "success_rate": success_rate,
                    "total_verifications": proof_metrics.get("total_verified", 0),
                },
                severity="medium",
            )

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security monitoring status."""
        with self._lock:
            current_time = time.time()

            # Count recent events
            recent_auth_failures = sum(
                len(
                    [
                        a
                        for a in attempts
                        if not a["success"] and current_time - a["timestamp"] < 300
                    ]
                )
                for attempts in self.auth_attempts.values()
            )

            recent_verification_failures = len(
                [
                    f
                    for f in self.failed_verifications
                    if current_time - f["timestamp"] < 300
                ]
            )

            return {
                "active_monitoring": self._monitoring_active,
                "tracked_identities": len(self.auth_attempts),
                "recent_auth_failures": recent_auth_failures,
                "recent_verification_failures": recent_verification_failures,
                "tracked_request_patterns": len(self.request_patterns),
                "security_violations_24h": len(
                    self.security_logger.get_recent_events("security_violation", 24)
                ),
                "last_check": current_time,
            }

    def stop_monitoring(self):
        """Stop security monitoring."""
        self._monitoring_active = False


class PerformanceMonitor:
    """
    Performance monitoring and alerting system.
    Tracks system performance and generates alerts for anomalies.
    """

    def __init__(self, metrics_collector: MetricsCollector, logger):
        self.metrics_collector = metrics_collector
        self.logger = logger
        self._lock = threading.RLock()

        # Health checks
        self.health_checks: List[HealthCheck] = []

        # Alerts
        self.active_alerts: List[Alert] = []
        self.alert_history: deque = deque(maxlen=1000)

        # Thresholds
        self.thresholds: List[Threshold] = [
            Threshold("avg_response_time", "gt", 5.0, 300, "warning"),
            Threshold("avg_verification_time", "gt", 2.0, 300, "warning"),
            Threshold("verification_success_rate", "lt", 0.95, 600, "critical"),
            Threshold("active_connections", "gt", 1000, 60, "warning"),
        ]

        # Start monitoring
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_worker, daemon=True
        )
        self._monitoring_thread.start()

    def add_health_check(
        self,
        name: str,
        check_func: Callable[[], bool],
        critical: bool = False,
        interval: int = 60,
    ):
        """Add a custom health check."""
        with self._lock:
            health_check = HealthCheck(
                name=name, check_func=check_func, critical=critical, interval=interval
            )
            self.health_checks.append(health_check)

    def add_threshold(
        self,
        metric_name: str,
        operator: str,
        value: float,
        duration: int = 300,
        severity: str = "warning",
    ):
        """Add a monitoring threshold."""
        with self._lock:
            threshold = Threshold(metric_name, operator, value, duration, severity)
            self.thresholds.append(threshold)

    def create_alert(
        self, severity: str, message: str, source: str, metadata: Dict[str, Any] = None
    ) -> str:
        """Create a new alert."""
        with self._lock:
            alert_id = f"alert_{int(time.time())}_{len(self.active_alerts)}"
            alert = Alert(
                id=alert_id,
                severity=severity,
                message=message,
                timestamp=time.time(),
                source=source,
                metadata=metadata or {},
            )

            self.active_alerts.append(alert)
            self.alert_history.append(alert)

            self.logger.warning(
                f"Alert created: {message}", alert_id=alert_id, severity=severity
            )
            return alert_id

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            for alert in self.active_alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    self.logger.info(f"Alert acknowledged: {alert_id}")
                    return True
            return False

    def clear_alert(self, alert_id: str) -> bool:
        """Clear an alert."""
        with self._lock:
            for i, alert in enumerate(self.active_alerts):
                if alert.id == alert_id:
                    del self.active_alerts[i]
                    self.logger.info(f"Alert cleared: {alert_id}")
                    return True
            return False

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        with self._lock:
            health_status = {}
            overall_healthy = True

            # Run health checks
            for check in self.health_checks:
                if time.time() - check.last_run > check.interval:
                    try:
                        check.last_status = check.check_func()
                        check.last_run = time.time()
                        if not check.last_status:
                            check.consecutive_failures += 1
                        else:
                            check.consecutive_failures = 0
                    except Exception as e:
                        check.last_status = False
                        check.consecutive_failures += 1
                        self.logger.error(f"Health check {check.name} failed: {e}")

                health_status[check.name] = {
                    "status": check.last_status,
                    "critical": check.critical,
                    "consecutive_failures": check.consecutive_failures,
                    "last_run": check.last_run,
                }

                if check.critical and not check.last_status:
                    overall_healthy = False

            # Check active alerts
            critical_alerts = [
                a for a in self.active_alerts if a.severity == "critical"
            ]
            if critical_alerts:
                overall_healthy = False

            return {
                "overall_healthy": overall_healthy,
                "health_checks": health_status,
                "active_alerts": len(self.active_alerts),
                "critical_alerts": len(critical_alerts),
                "metrics_summary": self.metrics_collector.get_metrics_summary(),
                "last_update": time.time(),
            }

    def get_performance_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance alerts from specified time period."""
        cutoff_time = time.time() - (hours * 3600)

        recent_alerts = [
            {
                "id": alert.id,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp,
                "source": alert.source,
                "acknowledged": alert.acknowledged,
                "metadata": alert.metadata,
            }
            for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ]

        return recent_alerts

    def _monitoring_worker(self):
        """Background monitoring worker."""
        while self._monitoring_active:
            try:
                time.sleep(60)  # Check every minute
                self._check_thresholds()
                self._check_health()
            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")

    def _check_thresholds(self):
        """Check all monitoring thresholds."""
        metrics_summary = self.metrics_collector.get_metrics_summary()

        for threshold in self.thresholds:
            try:
                value = self._extract_metric_value(
                    metrics_summary, threshold.metric_name
                )
                if value is None:
                    continue

                threshold_breached = False
                if threshold.operator == "gt" and value > threshold.value:
                    threshold_breached = True
                elif threshold.operator == "lt" and value < threshold.value:
                    threshold_breached = True
                elif (
                    threshold.operator == "eq" and abs(value - threshold.value) < 0.001
                ):
                    threshold_breached = True

                if threshold_breached:
                    alert_message = f"Threshold breached: {threshold.metric_name} {threshold.operator} {threshold.value} (current: {value})"

                    # Check if alert already exists
                    existing_alert = any(
                        alert.source == f"threshold_{threshold.metric_name}"
                        and not alert.acknowledged
                        for alert in self.active_alerts
                    )

                    if not existing_alert:
                        self.create_alert(
                            threshold.severity,
                            alert_message,
                            f"threshold_{threshold.metric_name}",
                            {
                                "metric_name": threshold.metric_name,
                                "current_value": value,
                                "threshold_value": threshold.value,
                            },
                        )

            except Exception as e:
                self.logger.error(
                    f"Error checking threshold {threshold.metric_name}: {e}"
                )

    def _extract_metric_value(
        self, metrics_summary: Dict[str, Any], metric_path: str
    ) -> Optional[float]:
        """Extract metric value from nested metrics summary."""
        try:
            parts = metric_path.split(".")
            current = metrics_summary

            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None

            return float(current) if isinstance(current, (int, float)) else None
        except:
            return None

    def _check_health(self):
        """Perform health checks."""
        # This will be called by the monitoring worker
        # Health checks are run on-demand in get_system_health()
        pass

    def stop_monitoring(self):
        """Stop performance monitoring."""
        self._monitoring_active = False
