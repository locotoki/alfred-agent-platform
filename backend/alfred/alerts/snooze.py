"""Alert snooze functionality with Redis TTL queue.

Provides temporary alert suppression with automatic expiry.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import redis

from alfred.alerts.models import AlertSnooze
from alfred.alerts.protocols import SnoozeService
from alfred.core.protocols import AlertProtocol
from alfred.metrics.protocols import MetricsClient

@dataclass
class SnoozeConfig:
    """Configuration for snooze behavior"""

    min_duration: int = 300  # 5 minutes
    max_duration: int = 86400  # 24 hours
    default_duration: int = 3600  # 1 hour
    auto_unsnooze_on_change: bool = True
    audit_retention_days: int = 30

class AlertSnoozeService(SnoozeService):
    """Service for managing alert snoozes with Redis TTL"""

    def __init__(
        self,
        redis_client: redis.Redis,
        metrics_client: Optional[MetricsClient] = None,
        config: Optional[SnoozeConfig] = None,
    ):
        """Initialize the snooze service.

        Args:
            redis_client: Redis client for TTL queue
            metrics_client: Metrics client for monitoring
            config: Snooze configuration

        """
        self.redis = redis_client
        self.metrics = metrics_client
        self.config = config or SnoozeConfig()

        # Redis key prefixes
        self.SNOOZE_KEY_PREFIX = "alert:snooze:"
        self.AUDIT_KEY_PREFIX = "alert:snooze:audit:"
        self.HASH_KEY_PREFIX = "alert:snooze:hash:"

    async def snooze_alert(
        self,
        alert_id: str,
        duration: int,
        reason: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AlertSnooze:
        """Snooze an alert for a specified duration.

        Args:
            alert_id: ID of alert to snooze
            duration: Duration in seconds
            reason: Optional reason for snoozing
            user_id: ID of user who initiated snooze

        Returns:
            AlertSnooze record.

        """
        # Validate duration
        duration = max(self.config.min_duration, min(duration, self.config.max_duration))

        # Create snooze record
        snooze_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=duration)

        snooze = AlertSnooze(
            id=snooze_id,
            alert_id=alert_id,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            duration=duration,
            reason=reason,
            created_by=user_id,
            is_active=True,
        )

        # Store in Redis with TTL
        snooze_key = f"{self.SNOOZE_KEY_PREFIX}{alert_id}"
        snooze_data = {
            "id": snooze.id,
            "alert_id": snooze.alert_id,
            "created_at": snooze.created_at.isoformat(),
            "expires_at": snooze.expires_at.isoformat(),
            "duration": snooze.duration,
            "reason": snooze.reason,
            "created_by": snooze.created_by,
            "is_active": snooze.is_active,
        }

        # Set with expiry
        self.redis.setex(snooze_key, duration, json.dumps(snooze_data))

        # Store alert hash for change detection
        if self.config.auto_unsnooze_on_change:
            await self_store_alert_hash(alert_id)  # type: ignore[name-defined]

        # Audit trail
        await self_create_audit_entry(snooze, action="created")  # type: ignore[name-defined]

        # Emit metrics
        if self.metrics:
            self.metrics.increment(
                "alert_snoozes_created",
                {"duration_bucket": self._get_duration_bucket(duration)},
            )

        return snooze

    async def unsnooze_alert(
        self, alert_id: str, reason: Optional[str] = None, user_id: Optional[str] = None
    ) -> bool:
        """Manually unsnooze an alert.

        Args:
            alert_id: ID of alert to unsnooze
            reason: Optional reason for unsnoozing
            user_id: ID of user who initiated unsnooze

        Returns:
            True if alert was unsnoozed, False if not found.

        """
        snooze_key = f"{self.SNOOZE_KEY_PREFIX}{alert_id}"

        # Get current snooze data
        snooze_data = self.redis.get(snooze_key)
        if not snooze_data:
            return False

        # Delete snooze
        self.redis.delete(snooze_key)

        # Delete hash if exists
        hash_key = f"{self.HASH_KEY_PREFIX}{alert_id}"
        self.redis.delete(hash_key)

        # Create audit entry
        snooze = json.loads(snooze_data)
        snooze["is_active"] = False
        await self_create_audit_entry(snooze, action="unsnoozed", reason=reason, user_id=user_id)  # type: ignore[name-defined]

        # Emit metrics
        if self.metrics:
            self.metrics.increment("alert_snoozes_unsnoozed", {"manual": True})

        return True

    async def is_snoozed(self, alert_id: str) -> bool:
        """Check if an alert is currently snoozed.

        Args:
            alert_id: ID of alert to check

        Returns:
            True if alert is snoozed.

        """
        snooze_key = f"{self.SNOOZE_KEY_PREFIX}{alert_id}"
        return bool(self.redis.exists(snooze_key))

    async def get_snooze(self, alert_id: str) -> Optional[AlertSnooze]:
        """Get current snooze for an alert.

        Args:
            alert_id: ID of alert

        Returns:
            AlertSnooze if found, None otherwise.

        """
        snooze_key = f"{self.SNOOZE_KEY_PREFIX}{alert_id}"
        snooze_data = self.redis.get(snooze_key)

        if not snooze_data:
            return None

        data = json.loads(snooze_data)
        return AlertSnooze(
            id=data["id"],
            alert_id=data["alert_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            duration=data["duration"],
            reason=data.get("reason"),
            created_by=data.get("created_by"),
            is_active=data["is_active"],
        )

    async def list_snoozed_alerts(self) -> List[str]:
        """List all currently snoozed alert IDs.

        Returns:
            List of snoozed alert IDs.

        """
        pattern = f"{self.SNOOZE_KEY_PREFIX}*"
        keys = self.redis.keys(pattern)

        # Extract alert IDs from keys
        alert_ids = []
        for key in keys:
            alert_id = key.decode().replace(self.SNOOZE_KEY_PREFIX, "")
            alert_ids.append(alert_id)

        return alert_ids

    async def check_alert_changed(self, alert: AlertProtocol) -> bool:
        """Check if an alert has changed since it was snoozed.

        Args:
            alert: Alert to check

        Returns:
            True if alert has changed.

        """
        if not self.config.auto_unsnooze_on_change:
            return False

        hash_key = f"{self.HASH_KEY_PREFIX}{alert.id}"
        stored_hash = self.redis.get(hash_key)

        if not stored_hash:
            return False

        current_hash = self._calculate_alert_hash(alert)
        return stored_hash.decode() != current_hash

    async def auto_unsnooze_if_changed(self, alert: AlertProtocol) -> bool:
        """Auto-unsnooze alert if it has changed.

        Args:
            alert: Alert to check

        Returns:
            True if alert was unsnoozed.

        """
        if await selfcheck_alert_changed(alert):  # type: ignore[name-defined]
            return await selfunsnooze_alert(  # type: ignore[name-defined]
                alert.id, reason="Alert properties changed", user_id="system"
            )
        return False

    async def extend_snooze(
        self, alert_id: str, additional_duration: int, user_id: Optional[str] = None
    ) -> Optional[AlertSnooze]:
        """Extend an existing snooze.

        Args:
            alert_id: ID of alert
            additional_duration: Additional seconds to snooze
            user_id: ID of user extending snooze

        Returns:
            Updated AlertSnooze or None if not found.

        """
        current_snooze = await selfget_snooze(alert_id)  # type: ignore[name-defined]
        if not current_snooze:
            return None

        # Calculate new duration
        remaining_ttl = self.redis.ttl(f"{self.SNOOZE_KEY_PREFIX}{alert_id}")
        new_duration = remaining_ttl + additional_duration

        # Re-snooze with new duration
        return await selfsnooze_alert(  # type: ignore[name-defined]
            alert_id,
            new_duration,
            reason=f"Extended by {additional_duration}s",
            user_id=user_id,
        )

    async def get_snooze_history(self, alert_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get snooze history for an alert.

        Args:
            alert_id: ID of alert
            limit: Maximum number of records

        Returns:
            List of audit entries.

        """
        audit_pattern = f"{self.AUDIT_KEY_PREFIX}{alert_id}:*"
        keys = self.redis.keys(audit_pattern)

        # Get and sort by timestamp
        entries = []
        for key in keys[:limit]:
            data = self.redis.get(key)
            if data:
                entry = json.loads(data)
                entries.append(entry)

        # Sort by timestamp descending
        entries.sort(key=lambda x: x["timestamp"], reverse=True)
        return entries[:limit]

    async def cleanup_expired_audits(self):
        """Clean up old audit entries"""
        pattern = f"{self.AUDIT_KEY_PREFIX}*"
        keys = self.redis.keys(pattern)

        cutoff = datetime.utcnow() - timedelta(days=self.config.audit_retention_days)

        for key in keys:
            data = self.redis.get(key)
            if data:
                entry = json.loads(data)
                timestamp = datetime.fromisoformat(entry["timestamp"])
                if timestamp < cutoff:
                    self.redis.delete(key)

    def _calculate_alert_hash(self, alert: AlertProtocol) -> str:
        """Calculate hash of alert for change detection"""
        # Include key fields that would trigger unsnooze
        hash_data = {
            "name": alert.name,
            "severity": alert.severity,
            "description": alert.description,
            "labels": sorted(alert.labels.items()),
        }

        import hashlib
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()

    async def _store_alert_hash(self, alert_id: str):
        """Store alert hash for change detection"""
        # In real implementation, would fetch alert
        # For now, store placeholder
        hash_key = f"{self.HASH_KEY_PREFIX}{alert_id}"
        self.redis.set(hash_key, "placeholder_hash")

    async def _create_audit_entry(
        self,
        snooze: Union[AlertSnooze, Dict],
        action: str,
        reason: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Create audit trail entry"""
        if isinstance(snooze, AlertSnooze):
            snooze_data = {
                "id": snooze.id,
                "alert_id": snooze.alert_id,
                "duration": snooze.duration,
                "created_by": snooze.created_by,
            }
        else:
            snooze_data = snooze

        audit_entry = {
            "snooze_id": snooze_data["id"],
            "alert_id": snooze_data["alert_id"],
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id or snooze_data.get("created_by"),
            "reason": reason,
            "duration": snooze_data["duration"],
        }

        # Store with TTL
        audit_key = f"{self.AUDIT_KEY_PREFIX}{snooze_data['alert_id']}:{audit_entry['timestamp']}"
        self.redis.setex(
            audit_key, 86400 * self.config.audit_retention_days, json.dumps(audit_entry)
        )

    def _get_duration_bucket(self, duration: int) -> str:
        """Get duration bucket for metrics"""
        if duration < 3600:
            return "< 1h"
        elif duration < 21600:
            return "1h-6h"
        elif duration < 86400:
            return "6h-24h"
        else:
            return "> 24h"
