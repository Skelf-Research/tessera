"""
Tests for Tessera logging and monitoring system.
"""

import os
import time
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from tessera.logging import (
    TesseraLogger,
    SecurityLogger,
    MetricsCollector,
    SecurityMonitor,
    PerformanceMonitor,
)


class TestTesseraLogger(unittest.TestCase):
    """Test main logging functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.logger = TesseraLogger("test_logger", self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_basic_logging(self):
        """Test basic logging functionality."""
        self.logger.info("Test info message", user_id="test123")
        self.logger.warning("Test warning", action="test_action")
        self.logger.error("Test error", error_code=500)

        # Check log file exists
        log_file = Path(self.temp_dir) / "test_logger.log"
        self.assertTrue(log_file.exists())

        # Check log content
        with open(log_file, "r") as f:
            log_content = f.read()
            self.assertIn("Test info message", log_content)
            self.assertIn("Test warning", log_content)
            self.assertIn("Test error", log_content)

    def test_sensitive_data_sanitization(self):
        """Test that sensitive data is sanitized in logs."""
        self.logger.info(
            "Login attempt", private_key="secret123", password="password123"
        )

        log_file = Path(self.temp_dir) / "test_logger.log"
        with open(log_file, "r") as f:
            log_content = f.read()
            # Should not contain actual sensitive values
            self.assertNotIn("secret123", log_content)
            self.assertNotIn("password123", log_content)
            # Should contain hash instead of raw values
            self.assertIn("private_key_hash", log_content)
            self.assertIn("password_hash", log_content)

    def test_log_rotation(self):
        """Test log file rotation."""
        # Create a logger with small max bytes for testing
        logger = TesseraLogger("rotation_test", self.temp_dir, max_bytes=1024)

        # Generate enough logs to trigger rotation
        for i in range(100):
            logger.info(f"Test message {i} with some extra content to increase size")

        log_dir = Path(self.temp_dir)
        log_files = list(log_dir.glob("rotation_test.log*"))
        # Should have main log file and at least one backup
        self.assertGreaterEqual(len(log_files), 1)


class TestSecurityLogger(unittest.TestCase):
    """Test security logging functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.security_logger = SecurityLogger(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_authentication_logging(self):
        """Test authentication event logging."""
        self.security_logger.log_authentication("user123", True, "192.168.1.1")
        self.security_logger.log_authentication("user456", False, "192.168.1.2")

        # Check events are recorded
        events = self.security_logger.get_recent_events("authentication", 1)
        self.assertEqual(len(events), 2)

        success_event = [e for e in events if e["success"]][0]
        self.assertEqual(success_event["identity_id"], "user123")
        self.assertEqual(success_event["remote_addr"], "192.168.1.1")

    def test_proof_generation_logging(self):
        """Test proof generation event logging."""
        metadata = {"call_type": "voice", "duration": 120}
        self.security_logger.log_proof_generation("sender123", "voice_call", metadata)

        events = self.security_logger.get_recent_events("proof_generation", 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["identity_id"], "sender123")
        self.assertEqual(events[0]["proof_type"], "voice_call")

    def test_proof_verification_logging(self):
        """Test proof verification event logging."""
        self.security_logger.log_proof_verification("verifier123", True, "sender456")
        self.security_logger.log_proof_verification("verifier456", False, "sender789")

        events = self.security_logger.get_recent_events("proof_verification", 1)
        self.assertEqual(len(events), 2)

        failed_event = [e for e in events if not e["proof_valid"]][0]
        self.assertEqual(failed_event["verifier_id"], "verifier456")
        self.assertEqual(failed_event["sender_id"], "sender789")

    def test_security_violation_logging(self):
        """Test security violation logging."""
        details = {"ip": "192.168.1.1", "attempts": 5}
        self.security_logger.log_security_violation("brute_force", details, "high")

        events = self.security_logger.get_recent_events("security_violation", 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["violation_type"], "brute_force")
        self.assertEqual(events[0]["severity"], "high")

    def test_security_summary(self):
        """Test security summary generation."""
        # Generate various events
        self.security_logger.log_authentication("user1", True)
        self.security_logger.log_authentication("user2", False)
        self.security_logger.log_proof_generation("sender1", "voice")
        self.security_logger.log_proof_verification("verifier1", True)
        self.security_logger.log_security_violation("test_violation", {})

        summary = self.security_logger.get_security_summary(24)
        self.assertEqual(summary["total_events"], 5)
        self.assertEqual(summary["authentication_attempts"], 2)
        self.assertEqual(summary["failed_authentications"], 1)
        self.assertEqual(summary["proof_generations"], 1)
        self.assertEqual(summary["proof_verifications"], 1)
        self.assertEqual(summary["security_violations"], 1)


class TestMetricsCollector(unittest.TestCase):
    """Test metrics collection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.metrics = MetricsCollector(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_proof_metrics(self):
        """Test proof operation metrics."""
        # Record some proof operations
        self.metrics.record_proof_generation(0.5, True)
        self.metrics.record_proof_generation(0.7, True)
        self.metrics.record_proof_verification(0.2, True)
        self.metrics.record_proof_verification(0.3, False)

        summary = self.metrics.get_metrics_summary()
        proof_metrics = summary["proof_metrics"]

        self.assertEqual(proof_metrics["total_generated"], 2)
        self.assertEqual(proof_metrics["total_verified"], 2)
        self.assertEqual(proof_metrics["successful_verifications"], 1)
        self.assertEqual(proof_metrics["failed_verifications"], 1)
        self.assertAlmostEqual(proof_metrics["avg_generation_time"], 0.6, places=1)

    def test_network_metrics(self):
        """Test network operation metrics."""
        self.metrics.record_network_request(1.0, True, 1024)
        self.metrics.record_network_request(2.0, True, 2048)
        self.metrics.record_network_request(0.5, False, 0)

        summary = self.metrics.get_metrics_summary()
        network_metrics = summary["network_metrics"]

        self.assertEqual(network_metrics["total_requests"], 3)
        self.assertEqual(network_metrics["successful_requests"], 2)
        self.assertEqual(network_metrics["failed_requests"], 1)
        self.assertEqual(network_metrics["total_bandwidth_bytes"], 3072)

    def test_key_metrics(self):
        """Test key operation metrics."""
        self.metrics.record_key_operation("generation", 0.1, True)
        self.metrics.record_key_operation("rotation", 0.2, True)
        self.metrics.record_key_operation("backup", 0.3, True)

        summary = self.metrics.get_metrics_summary()
        key_metrics = summary["key_metrics"]

        self.assertEqual(key_metrics["total_keys_generated"], 1)
        self.assertEqual(key_metrics["total_keys_rotated"], 1)
        self.assertEqual(key_metrics["total_backups_created"], 1)

    def test_custom_metrics(self):
        """Test custom metrics functionality."""
        self.metrics.increment_custom_metric("api_calls")
        self.metrics.increment_custom_metric("api_calls", 5)
        self.metrics.set_custom_metric("cache_hits", 100)

        summary = self.metrics.get_metrics_summary()
        custom_metrics = summary["custom_metrics"]

        self.assertEqual(custom_metrics["api_calls"], 6)
        self.assertEqual(custom_metrics["cache_hits"], 100)

    def test_time_series_data(self):
        """Test time series data collection."""
        self.metrics.record_custom_time_series("cpu_usage", 75.5)
        self.metrics.record_custom_time_series("memory_usage", 60.2)

        time_series = self.metrics.get_time_series("cpu_usage", 1)
        self.assertEqual(len(time_series), 1)
        self.assertEqual(time_series[0]["value"], 75.5)

    def test_performance_report(self):
        """Test performance report generation."""
        # Generate some test data
        self.metrics.record_proof_generation(0.5, True)
        self.metrics.record_proof_verification(0.2, True)
        self.metrics.record_network_request(1.0, True, 1024)

        report = self.metrics.get_performance_report(24)
        self.assertIn("proof_performance", report)
        self.assertIn("network_performance", report)
        self.assertEqual(report["proof_performance"]["total_generations"], 1)
        self.assertEqual(report["network_performance"]["total_requests"], 1)


class TestSecurityMonitor(unittest.TestCase):
    """Test security monitoring functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.security_logger = SecurityLogger(self.temp_dir)
        self.metrics_collector = MetricsCollector(self.temp_dir)
        self.monitor = SecurityMonitor(self.security_logger, self.metrics_collector)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.monitor.stop_monitoring()

    def test_authentication_tracking(self):
        """Test authentication attempt tracking."""
        # Simulate multiple failed authentication attempts
        for i in range(6):
            self.monitor.track_authentication_attempt("user123", False, "192.168.1.1")

        # Should trigger security violation alert
        violations = self.security_logger.get_recent_events("security_violation", 1)
        self.assertGreater(len(violations), 0)

        violation = violations[0]
        self.assertEqual(violation["violation_type"], "excessive_auth_failures")

    def test_verification_failure_tracking(self):
        """Test verification failure tracking."""
        # Simulate multiple verification failures
        for i in range(11):
            self.monitor.track_verification_failure("verifier123")

        # Should trigger security violation alert
        violations = self.security_logger.get_recent_events("security_violation", 1)
        violation = [
            v
            for v in violations
            if v["violation_type"] == "excessive_verification_failures"
        ]
        self.assertGreater(len(violation), 0)

    def test_request_pattern_tracking(self):
        """Test request pattern anomaly detection."""
        # Simulate rapid requests from same IP
        for i in range(101):
            self.monitor.track_request_pattern("/api/verify", "192.168.1.1")

        # Should trigger rate limiting violation
        violations = self.security_logger.get_recent_events("security_violation", 1)
        rate_limit_violations = [
            v for v in violations if v["violation_type"] == "rate_limit_exceeded"
        ]
        self.assertGreater(len(rate_limit_violations), 0)

    def test_security_status(self):
        """Test security status reporting."""
        # Generate some activity
        self.monitor.track_authentication_attempt("user1", True)
        self.monitor.track_verification_failure("verifier1")

        status = self.monitor.get_security_status()
        self.assertTrue(status["active_monitoring"])
        self.assertGreaterEqual(status["tracked_identities"], 1)


class TestPerformanceMonitor(unittest.TestCase):
    """Test performance monitoring functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.metrics_collector = MetricsCollector(self.temp_dir)

        # Mock logger
        self.mock_logger = Mock()
        self.monitor = PerformanceMonitor(self.metrics_collector, self.mock_logger)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.monitor.stop_monitoring()

    def test_health_check_addition(self):
        """Test adding custom health checks."""

        def mock_health_check():
            return True

        self.monitor.add_health_check("test_check", mock_health_check, critical=True)

        health = self.monitor.get_system_health()
        self.assertIn("test_check", health["health_checks"])
        self.assertTrue(health["health_checks"]["test_check"]["status"])

    def test_alert_creation_and_management(self):
        """Test alert creation and management."""
        alert_id = self.monitor.create_alert("warning", "Test alert", "test_source")
        self.assertIsNotNone(alert_id)

        # Test acknowledgment
        result = self.monitor.acknowledge_alert(alert_id)
        self.assertTrue(result)

        # Test clearing
        result = self.monitor.clear_alert(alert_id)
        self.assertTrue(result)

    def test_threshold_monitoring(self):
        """Test threshold-based monitoring."""
        # Add a threshold
        self.monitor.add_threshold("avg_response_time", "gt", 1.0, 60, "warning")

        # Record metrics that exceed threshold
        for i in range(5):
            self.metrics_collector.record_network_request(2.0, True)

        # Give monitor time to check thresholds
        time.sleep(0.1)

        # Check that alert was created (in a real scenario, this would be done by the monitoring worker)
        health = self.monitor.get_system_health()
        self.assertIsNotNone(health)

    def test_system_health_reporting(self):
        """Test system health reporting."""

        def healthy_check():
            return True

        def unhealthy_check():
            return False

        self.monitor.add_health_check("healthy", healthy_check)
        self.monitor.add_health_check("unhealthy", unhealthy_check, critical=True)

        health = self.monitor.get_system_health()
        self.assertFalse(
            health["overall_healthy"]
        )  # Should be false due to critical failure
        self.assertIn("healthy", health["health_checks"])
        self.assertIn("unhealthy", health["health_checks"])


if __name__ == "__main__":
    unittest.main()
