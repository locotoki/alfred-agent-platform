"""Dependency tracking for health checks.

This module provides a way to track service dependencies.
"""

from typing import Dict

import structlog

logger = structlog.get_logger(__name__)
class DependencyTracker:
    """Tracks dependencies and their health status"""

    def __init__(self, service_name: str):
        """Initialize the dependency tracker.

        Args:
            service_name: The name of the service this tracker belongs to
        """
        self.service_name = service_name
        self.dependencies: Dict[str, str] = {}

    def register_dependency(self, name: str, status: str = "ok") -> None:
        """Register a dependency with the health check system.

        Args:
            name: The name of the dependency
            status: The initial status of the dependency.
        """
        self.dependencies[name] = status
        logger.info(
            "Registered dependency",
            service=self.service_name,
            dependency=name,
            status=status,
        )

    def update_dependency_status(self, name: str, status: str) -> None:
        """Update the status of a dependency.

        Args:
            name: The name of the dependency
            status: The new status of the dependency.
        """
        if name in self.dependencies:
            self.dependencies[name] = status
            logger.info(
                "Updated dependency status",
                service=self.service_name,
                dependency=name,
                status=status,
            )
        else:
            logger.warning(
                "Attempted to update unknown dependency",
                service=self.service_name,
                dependency=name,
            )

    def check_dependencies(self) -> Dict[str, str]:
        """Check all service dependencies and return their status.

        Returns:
            A dictionary mapping dependency names to their status.
        """
        return self.dependencies.copy()
