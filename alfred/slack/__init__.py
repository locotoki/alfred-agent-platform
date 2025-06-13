"""Alfred Slack integration module"""

from typing import TYPE_CHECKING, List

from .diagnostics import DiagnosticsBot

if TYPE_CHECKING:
    from .app import create_slack_app
__all__: List[str] = ["DiagnosticsBot", "create_slack_app"]
