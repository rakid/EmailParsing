"""
Performance Monitoring Dashboard for SambaNova AI Integration

This module provides real-time performance monitoring and analytics for:
- API request patterns and response times
- Cache performance and hit rates
- Cost tracking and budget monitoring
- Rate limiting status and quota usage
- Batch processing efficiency
- Error rates and fallback usage

"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceDashboardConfig:
    """Configuration for performance dashboard."""

    update_interval: float = 10.0  # seconds
    history_retention: int = 1440  # minutes (24 hours)
    alert_thresholds: Dict[str, float] = None
    export_enabled: bool = True
    export_path: str = "performance_reports"

    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "error_rate": 0.05,  # 5% error rate
                "cache_hit_rate": 0.80,  # 80% cache hit rate
                "avg_response_time": 2.0,  # 2 seconds
                "daily_budget_usage": 0.90,  # 90% of daily budget
            }


@dataclass
class PerformanceSnapshot:
    """Performance snapshot at a point in time."""

    timestamp: datetime
    metrics: Dict[str, Any]
    alerts: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics,
            "alerts": self.alerts,
        }


class PerformanceAlerts:
    """Performance alerting system."""

    def __init__(self, config: PerformanceDashboardConfig):
        self.config = config
        self.alert_history: List[Dict[str, Any]] = []

    def check_alerts(self, metrics: Dict[str, Any]) -> List[str]:
        """Check for performance alerts based on metrics."""
        alerts = []
        thresholds = self.config.alert_thresholds

        # Error rate alert
        error_rate = self._calculate_error_rate(metrics)
        if error_rate > thresholds["error_rate"]:
            alerts.append(
                f"High error rate: {error_rate:.2%} (threshold: {thresholds['error_rate']:.2%})"
            )

        # Cache hit rate alert
        cache_hit_rate = metrics.get("cache_hit_rate", 0)
        if cache_hit_rate < thresholds["cache_hit_rate"]:
            alerts.append(
                f"Low cache hit rate: {cache_hit_rate:.2%} (threshold: {thresholds['cache_hit_rate']:.2%})"
            )

        # Response time alert
        avg_response_time = metrics.get("average_response_time", 0)
        if avg_response_time > thresholds["avg_response_time"]:
            alerts.append(
                f"High response time: {avg_response_time:.2f}s (threshold: {thresholds['avg_response_time']:.2f}s)"
            )

        # Budget usage alert
        budget_usage = self._calculate_budget_usage(metrics)
        if budget_usage > thresholds["daily_budget_usage"]:
            alerts.append(
                f"High budget usage: {budget_usage:.2%} (threshold: {thresholds['daily_budget_usage']:.2%})"
            )

        # Store alerts in history
        if alerts:
            self.alert_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "alerts": alerts,
                    "metrics_snapshot": metrics,
                }
            )

        return alerts

    def _calculate_error_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate error rate from metrics."""
        requests = metrics.get("requests", 0)
        errors = metrics.get("errors", 0)
        return errors / requests if requests > 0 else 0.0

    def _calculate_budget_usage(self, metrics: Dict[str, Any]) -> float:
        """Calculate budget usage percentage."""
        daily_limit = metrics.get("budget", {}).get("daily_limit", 1)
        used = metrics.get("budget", {}).get("used", 0)
        return used / daily_limit if daily_limit > 0 else 0.0

    def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts within specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            alert
            for alert in self.alert_history
            if datetime.fromisoformat(alert["timestamp"]) > cutoff
        ]


class PerformanceReporter:
    """Performance reporting and export functionality."""

    def __init__(self, config: PerformanceDashboardConfig):
        self.config = config
        self.export_path = Path(config.export_path)
        self.export_path.mkdir(parents=True, exist_ok=True)

    def generate_summary_report(
        self, snapshots: List[PerformanceSnapshot]
    ) -> Dict[str, Any]:
        """Generate summary performance report."""
        if not snapshots:
            return {"error": "No data available"}

        # Calculate summary statistics
        metrics_list = [snapshot.metrics for snapshot in snapshots]

        summary = {
            "report_period": {
                "start": snapshots[0].timestamp.isoformat(),
                "end": snapshots[-1].timestamp.isoformat(),
                "duration_hours": (
                    snapshots[-1].timestamp - snapshots[0].timestamp
                ).total_seconds()
                / 3600,
            },
            "performance_summary": {
                "total_requests": sum(m.get("requests", 0) for m in metrics_list),
                "total_errors": sum(m.get("errors", 0) for m in metrics_list),
                "avg_cache_hit_rate": self._calculate_average(
                    metrics_list, "cache_hit_rate"
                ),
                "avg_response_time": self._calculate_average(
                    metrics_list, "average_response_time"
                ),
                "total_cost": sum(m.get("total_cost", 0) for m in metrics_list),
            },
            "trends": {
                "response_time_trend": self._calculate_trend(
                    metrics_list, "average_response_time"
                ),
                "cache_performance_trend": self._calculate_trend(
                    metrics_list, "cache_hit_rate"
                ),
                "error_rate_trend": self._calculate_trend(metrics_list, "errors"),
                "cost_trend": self._calculate_trend(metrics_list, "total_cost"),
            },
            "recommendations": self._generate_recommendations(metrics_list),
        }

        return summary

    def _calculate_average(self, metrics_list: List[Dict[str, Any]], key: str) -> float:
        """Calculate average for a metric across snapshots."""
        values = [m.get(key, 0) for m in metrics_list if key in m]
        return sum(values) / len(values) if values else 0.0

    def _calculate_trend(self, metrics_list: List[Dict[str, Any]], key: str) -> str:
        """Calculate trend direction for a metric."""
        values = [m.get(key, 0) for m in metrics_list if key in m]
        if len(values) < 2:
            return "insufficient_data"

        # Simple trend calculation (first half vs second half)
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid if mid > 0 else 0
        second_half_avg = (
            sum(values[mid:]) / (len(values) - mid) if len(values) - mid > 0 else 0
        )

        if second_half_avg > first_half_avg * 1.05:
            return "increasing"
        elif second_half_avg < first_half_avg * 0.95:
            return "decreasing"
        else:
            return "stable"

    def _generate_recommendations(
        self, metrics_list: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate performance recommendations based on metrics."""
        recommendations = []

        # Cache performance recommendations
        avg_cache_hit_rate = self._calculate_average(metrics_list, "cache_hit_rate")
        if avg_cache_hit_rate < 0.7:
            recommendations.append(
                "Consider increasing cache TTL or improving content similarity detection"
            )

        # Response time recommendations
        avg_response_time = self._calculate_average(
            metrics_list, "average_response_time"
        )
        if avg_response_time > 2.0:
            recommendations.append(
                "High response times detected - consider enabling batch processing or reducing request complexity"
            )

        # Error rate recommendations
        total_requests = sum(m.get("requests", 0) for m in metrics_list)
        total_errors = sum(m.get("errors", 0) for m in metrics_list)
        error_rate = total_errors / total_requests if total_requests > 0 else 0
        if error_rate > 0.05:
            recommendations.append(
                "High error rate - review API usage patterns and implement better fallback mechanisms"
            )

        # Cost optimization recommendations
        cost_trend = self._calculate_trend(metrics_list, "total_cost")
        if cost_trend == "increasing":
            recommendations.append(
                "Cost trend is increasing - review caching strategy and consider batch processing"
            )

        return recommendations

    def export_report(
        self, report: Dict[str, Any], report_type: str = "summary"
    ) -> str:
        """Export report to file."""
        if not self.config.export_enabled:
            return "Export disabled"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_report_{timestamp}.json"
        filepath = self.export_path / filename

        try:
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"Performance report exported to: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export report: {e}")
            return f"Export failed: {e}"


class PerformanceDashboard:
    """Main performance monitoring dashboard."""

    def __init__(
        self, performance_optimizer, config: Optional[PerformanceDashboardConfig] = None
    ):
        self.performance_optimizer = performance_optimizer
        self.config = config or PerformanceDashboardConfig()
        self.alerts = PerformanceAlerts(self.config)
        self.reporter = PerformanceReporter(self.config)

        # Performance history
        self.snapshots: List[PerformanceSnapshot] = []
        self.monitoring_active = False

        logger.info("Performance dashboard initialized")

    async def start_monitoring(self):
        """Start continuous performance monitoring."""
        self.monitoring_active = True
        logger.info("Starting performance monitoring...")

        while self.monitoring_active:
            try:
                # Collect current metrics
                metrics = self.performance_optimizer.get_performance_report()

                # Check for alerts
                alerts = self.alerts.check_alerts(metrics)

                # Create snapshot
                snapshot = PerformanceSnapshot(
                    timestamp=datetime.now(), metrics=metrics, alerts=alerts
                )

                # Store snapshot
                self.snapshots.append(snapshot)

                # Cleanup old snapshots
                self._cleanup_old_snapshots()

                # Log alerts
                if alerts:
                    for alert in alerts:
                        logger.warning(f"Performance Alert: {alert}")

                # Wait for next update
                await asyncio.sleep(self.config.update_interval)

            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(self.config.update_interval)

    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        logger.info("Performance monitoring stopped")

    def _cleanup_old_snapshots(self):
        """Remove old snapshots beyond retention period."""
        cutoff = datetime.now() - timedelta(minutes=self.config.history_retention)
        self.snapshots = [
            snapshot for snapshot in self.snapshots if snapshot.timestamp > cutoff
        ]

    def get_current_status(self) -> Dict[str, Any]:
        """Get current performance status."""
        if not self.snapshots:
            return {"status": "No data available"}

        latest_snapshot = self.snapshots[-1]
        recent_alerts = self.alerts.get_recent_alerts(hours=1)

        return {
            "timestamp": latest_snapshot.timestamp.isoformat(),
            "current_metrics": latest_snapshot.metrics,
            "active_alerts": latest_snapshot.alerts,
            "recent_alerts_count": len(recent_alerts),
            "monitoring_active": self.monitoring_active,
            "snapshots_count": len(self.snapshots),
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary report."""
        return self.reporter.generate_summary_report(self.snapshots)

    def export_performance_report(self) -> str:
        """Export current performance report."""
        summary = self.get_performance_summary()
        return self.reporter.export_report(summary, "performance_summary")

    def get_historical_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get historical performance data."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            snapshot.to_dict()
            for snapshot in self.snapshots
            if snapshot.timestamp > cutoff
        ]


# Factory function for creating dashboard
def create_performance_dashboard(
    performance_optimizer, config: Optional[PerformanceDashboardConfig] = None
) -> PerformanceDashboard:
    """Create and configure performance dashboard."""
    return PerformanceDashboard(performance_optimizer, config)
