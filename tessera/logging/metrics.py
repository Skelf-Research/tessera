"""
Metrics collection and monitoring for Tessera.
Tracks performance, usage, and system health metrics.
"""

import time
import threading
import json
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import os


@dataclass
class ProofMetrics:
    """Metrics for proof operations."""

    total_generated: int = 0
    total_verified: int = 0
    successful_verifications: int = 0
    failed_verifications: int = 0
    avg_generation_time: float = 0.0
    avg_verification_time: float = 0.0
    generation_times: deque = None
    verification_times: deque = None

    def __post_init__(self):
        if self.generation_times is None:
            self.generation_times = deque(maxlen=1000)
        if self.verification_times is None:
            self.verification_times = deque(maxlen=1000)


@dataclass
class NetworkMetrics:
    """Metrics for network operations."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    response_times: deque = None
    active_connections: int = 0
    bandwidth_bytes: int = 0

    def __post_init__(self):
        if self.response_times is None:
            self.response_times = deque(maxlen=1000)


@dataclass
class KeyMetrics:
    """Metrics for key operations."""

    total_keys_generated: int = 0
    total_keys_rotated: int = 0
    total_backups_created: int = 0
    avg_key_generation_time: float = 0.0
    key_generation_times: deque = None
    active_identities: int = 0

    def __post_init__(self):
        if self.key_generation_times is None:
            self.key_generation_times = deque(maxlen=1000)


class MetricsCollector:
    """
    Centralized metrics collection system.
    Thread-safe collection and aggregation of system metrics.
    """

    def __init__(self, metrics_dir: str = None, persist_interval: int = 300):
        """
        Initialize metrics collector.

        Args:
            metrics_dir: Directory for metrics storage
            persist_interval: Interval in seconds to persist metrics to disk
        """
        self._lock = threading.RLock()

        # Set up metrics directory
        if metrics_dir is None:
            metrics_dir = os.path.expanduser("~/.tessera/metrics")

        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.metrics_dir, 0o700)

        # Initialize metric storage
        self.proof_metrics = ProofMetrics()
        self.network_metrics = NetworkMetrics()
        self.key_metrics = KeyMetrics()

        # Custom metrics storage
        self.custom_metrics: Dict[str, Any] = defaultdict(int)
        self.time_series: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Persistence
        self.persist_interval = persist_interval
        self._last_persist = time.time()

        # Load existing metrics
        self._load_metrics()

        # Start persistence thread
        self._persistence_thread = threading.Thread(
            target=self._persistence_worker, daemon=True
        )
        self._persistence_thread.start()

    def record_proof_generation(self, duration: float, success: bool = True):
        """Record proof generation metrics."""
        with self._lock:
            self.proof_metrics.total_generated += 1
            if success:
                self.proof_metrics.generation_times.append(duration)
                self._update_average(
                    self.proof_metrics.generation_times,
                    lambda avg: setattr(self.proof_metrics, "avg_generation_time", avg),
                )

            self._record_time_series(
                "proof_generation",
                {"timestamp": time.time(), "duration": duration, "success": success},
            )

    def record_proof_verification(self, duration: float, success: bool):
        """Record proof verification metrics."""
        with self._lock:
            self.proof_metrics.total_verified += 1
            if success:
                self.proof_metrics.successful_verifications += 1
            else:
                self.proof_metrics.failed_verifications += 1

            self.proof_metrics.verification_times.append(duration)
            self._update_average(
                self.proof_metrics.verification_times,
                lambda avg: setattr(self.proof_metrics, "avg_verification_time", avg),
            )

            self._record_time_series(
                "proof_verification",
                {"timestamp": time.time(), "duration": duration, "success": success},
            )

    def record_network_request(
        self, duration: float, success: bool, bytes_transferred: int = 0
    ):
        """Record network request metrics."""
        with self._lock:
            self.network_metrics.total_requests += 1
            if success:
                self.network_metrics.successful_requests += 1
            else:
                self.network_metrics.failed_requests += 1

            self.network_metrics.response_times.append(duration)
            self.network_metrics.bandwidth_bytes += bytes_transferred

            self._update_average(
                self.network_metrics.response_times,
                lambda avg: setattr(self.network_metrics, "avg_response_time", avg),
            )

            self._record_time_series(
                "network_request",
                {
                    "timestamp": time.time(),
                    "duration": duration,
                    "success": success,
                    "bytes": bytes_transferred,
                },
            )

    def record_key_operation(
        self, operation: str, duration: float, success: bool = True
    ):
        """Record key management operation metrics."""
        with self._lock:
            if operation == "generation" and success:
                self.key_metrics.total_keys_generated += 1
                self.key_metrics.key_generation_times.append(duration)
                self._update_average(
                    self.key_metrics.key_generation_times,
                    lambda avg: setattr(
                        self.key_metrics, "avg_key_generation_time", avg
                    ),
                )
            elif operation == "rotation" and success:
                self.key_metrics.total_keys_rotated += 1
            elif operation == "backup" and success:
                self.key_metrics.total_backups_created += 1

            self._record_time_series(
                f"key_{operation}",
                {"timestamp": time.time(), "duration": duration, "success": success},
            )

    def update_active_connections(self, count: int):
        """Update active connection count."""
        with self._lock:
            self.network_metrics.active_connections = count

    def update_active_identities(self, count: int):
        """Update active identity count."""
        with self._lock:
            self.key_metrics.active_identities = count

    def increment_custom_metric(self, name: str, value: int = 1):
        """Increment a custom metric."""
        with self._lock:
            self.custom_metrics[name] += value

    def set_custom_metric(self, name: str, value: Any):
        """Set a custom metric value."""
        with self._lock:
            self.custom_metrics[name] = value

    def record_custom_time_series(self, name: str, value: Any):
        """Record a custom time series data point."""
        with self._lock:
            self._record_time_series(name, {"timestamp": time.time(), "value": value})

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        with self._lock:
            return {
                "proof_metrics": {
                    "total_generated": self.proof_metrics.total_generated,
                    "total_verified": self.proof_metrics.total_verified,
                    "successful_verifications": self.proof_metrics.successful_verifications,
                    "failed_verifications": self.proof_metrics.failed_verifications,
                    "verification_success_rate": (
                        self.proof_metrics.successful_verifications
                        / max(1, self.proof_metrics.total_verified)
                    ),
                    "avg_generation_time": self.proof_metrics.avg_generation_time,
                    "avg_verification_time": self.proof_metrics.avg_verification_time,
                },
                "network_metrics": {
                    "total_requests": self.network_metrics.total_requests,
                    "successful_requests": self.network_metrics.successful_requests,
                    "failed_requests": self.network_metrics.failed_requests,
                    "success_rate": (
                        self.network_metrics.successful_requests
                        / max(1, self.network_metrics.total_requests)
                    ),
                    "avg_response_time": self.network_metrics.avg_response_time,
                    "active_connections": self.network_metrics.active_connections,
                    "total_bandwidth_bytes": self.network_metrics.bandwidth_bytes,
                },
                "key_metrics": {
                    "total_keys_generated": self.key_metrics.total_keys_generated,
                    "total_keys_rotated": self.key_metrics.total_keys_rotated,
                    "total_backups_created": self.key_metrics.total_backups_created,
                    "avg_key_generation_time": self.key_metrics.avg_key_generation_time,
                    "active_identities": self.key_metrics.active_identities,
                },
                "custom_metrics": dict(self.custom_metrics),
                "collection_timestamp": time.time(),
            }

    def get_time_series(
        self, metric_name: str, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get time series data for a specific metric."""
        with self._lock:
            if metric_name not in self.time_series:
                return []

            cutoff_time = time.time() - (hours * 3600)
            return [
                data
                for data in self.time_series[metric_name]
                if data.get("timestamp", 0) > cutoff_time
            ]

    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate performance report for specified time period."""
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)

            # Analyze proof performance
            proof_gen_data = [
                d
                for d in self.time_series.get("proof_generation", [])
                if d.get("timestamp", 0) > cutoff_time and d.get("success")
            ]
            proof_ver_data = [
                d
                for d in self.time_series.get("proof_verification", [])
                if d.get("timestamp", 0) > cutoff_time
            ]

            # Analyze network performance
            network_data = [
                d
                for d in self.time_series.get("network_request", [])
                if d.get("timestamp", 0) > cutoff_time
            ]

            report = {
                "period_hours": hours,
                "proof_performance": {
                    "total_generations": len(proof_gen_data),
                    "avg_generation_time": sum(
                        d.get("duration", 0) for d in proof_gen_data
                    )
                    / max(1, len(proof_gen_data)),
                    "total_verifications": len(proof_ver_data),
                    "successful_verifications": len(
                        [d for d in proof_ver_data if d.get("success")]
                    ),
                    "verification_success_rate": len(
                        [d for d in proof_ver_data if d.get("success")]
                    )
                    / max(1, len(proof_ver_data)),
                },
                "network_performance": {
                    "total_requests": len(network_data),
                    "successful_requests": len(
                        [d for d in network_data if d.get("success")]
                    ),
                    "avg_response_time": sum(d.get("duration", 0) for d in network_data)
                    / max(1, len(network_data)),
                    "total_bandwidth": sum(d.get("bytes", 0) for d in network_data),
                },
                "generated_at": time.time(),
            }

            return report

    def _update_average(self, values: deque, setter_func):
        """Update running average for a metric."""
        if values:
            avg = sum(values) / len(values)
            setter_func(avg)

    def _record_time_series(self, name: str, data: Dict[str, Any]):
        """Record time series data point."""
        self.time_series[name].append(data)

    def _persistence_worker(self):
        """Background worker for persisting metrics."""
        while True:
            try:
                time.sleep(60)  # Check every minute
                if time.time() - self._last_persist > self.persist_interval:
                    self._persist_metrics()
            except Exception:
                pass  # Continue running even if persistence fails

    def _persist_metrics(self):
        """Persist metrics to disk."""
        try:
            with self._lock:
                metrics_data = {
                    "proof_metrics": asdict(self.proof_metrics),
                    "network_metrics": asdict(self.network_metrics),
                    "key_metrics": asdict(self.key_metrics),
                    "custom_metrics": dict(self.custom_metrics),
                    "timestamp": time.time(),
                }

                # Convert deques to lists for JSON serialization
                for metric_type in ["proof_metrics", "network_metrics", "key_metrics"]:
                    for key, value in metrics_data[metric_type].items():
                        if isinstance(value, deque):
                            metrics_data[metric_type][key] = list(value)

                metrics_file = self.metrics_dir / "current_metrics.json"
                with open(metrics_file, "w") as f:
                    json.dump(metrics_data, f, indent=2)

                os.chmod(metrics_file, 0o600)
                self._last_persist = time.time()

        except Exception:
            pass  # Fail silently to avoid disrupting main operations

    def _load_metrics(self):
        """Load persisted metrics from disk."""
        try:
            metrics_file = self.metrics_dir / "current_metrics.json"
            if not metrics_file.exists():
                return

            with open(metrics_file, "r") as f:
                metrics_data = json.load(f)

            # Restore metrics
            if "proof_metrics" in metrics_data:
                proof_data = metrics_data["proof_metrics"]
                self.proof_metrics.total_generated = proof_data.get(
                    "total_generated", 0
                )
                self.proof_metrics.total_verified = proof_data.get("total_verified", 0)
                self.proof_metrics.successful_verifications = proof_data.get(
                    "successful_verifications", 0
                )
                self.proof_metrics.failed_verifications = proof_data.get(
                    "failed_verifications", 0
                )
                self.proof_metrics.avg_generation_time = proof_data.get(
                    "avg_generation_time", 0.0
                )
                self.proof_metrics.avg_verification_time = proof_data.get(
                    "avg_verification_time", 0.0
                )

            if "network_metrics" in metrics_data:
                network_data = metrics_data["network_metrics"]
                self.network_metrics.total_requests = network_data.get(
                    "total_requests", 0
                )
                self.network_metrics.successful_requests = network_data.get(
                    "successful_requests", 0
                )
                self.network_metrics.failed_requests = network_data.get(
                    "failed_requests", 0
                )
                self.network_metrics.avg_response_time = network_data.get(
                    "avg_response_time", 0.0
                )
                self.network_metrics.bandwidth_bytes = network_data.get(
                    "bandwidth_bytes", 0
                )

            if "key_metrics" in metrics_data:
                key_data = metrics_data["key_metrics"]
                self.key_metrics.total_keys_generated = key_data.get(
                    "total_keys_generated", 0
                )
                self.key_metrics.total_keys_rotated = key_data.get(
                    "total_keys_rotated", 0
                )
                self.key_metrics.total_backups_created = key_data.get(
                    "total_backups_created", 0
                )
                self.key_metrics.avg_key_generation_time = key_data.get(
                    "avg_key_generation_time", 0.0
                )

            if "custom_metrics" in metrics_data:
                self.custom_metrics.update(metrics_data["custom_metrics"])

        except Exception:
            pass  # Fail silently and start with fresh metrics
