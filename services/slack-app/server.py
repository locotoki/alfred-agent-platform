"""FastAPI server for Slack App integration with Socket Mode"""

# type: ignore
import logging
import os
import threading

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Alfred Slack App", description="Slack integration for Alfred Agent Platform")

# Metrics
REQUESTS = Counter("slack_app_requests_total", "Total requests", ["endpoint"])
COMMANDS = Counter("slack_app_commands_total", "Slash commands received", ["command"])

# Create Slack app with Socket Mode
slack_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

# Register slash command handlers
@slack_app.command("/alfred")
def handle_alfred_command(ack, command, client):
    """Handle the /alfred slash command"""
    ack()

    # Parse subcommand and arguments
    args = command["text"].split()
    subcommand = args[0] if args else "help"

    # Track command metrics
    COMMANDS.labels(command=f"/alfred {subcommand}").inc()

    if subcommand == "help":
        client.chat_postMessage(
            channel=command["channel_id"],
            text="Available commands:\n• `/alfred help` - Show this help message\n• `/alfred health [service]` - Check service health\n• `/alfred remediate <service>` - Attempt to remediate service issues",  # noqa: E501
        )
    elif subcommand == "health":
        service = args[1] if len(args) > 1 else "all"
        # Call health check endpoint and post result
        client.chat_postMessage(
            channel=command["channel_id"],
            text=f"Checking health for {service}... Please wait.",
        )
        # TODO: Call /internal/health endpoint and update message
    elif subcommand == "remediate":
        if len(args) < 2:
            client.chat_postMessage(
                channel=command["channel_id"],
                text="Error: Please specify a service to remediate.",
            )
            return

        service = args[1]
        # Call remediation endpoint
        client.chat_postMessage(
            channel=command["channel_id"],
            text=f"Initiating remediation for {service}...",
        )
        # TODO: Call /internal/remediation/trigger endpoint
    else:
        client.chat_postMessage(
            channel=command["channel_id"],
            text=f"Unknown command: {subcommand}\nUse `/alfred help` to see available commands.",
        )

# FastAPI endpoints
@app.get("/health")
def health_check():
    """Health check endpoint for the Slack app"""
    REQUESTS.labels(endpoint="/health").inc()
    return {"status": "healthy"}

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    REQUESTS.labels(endpoint="/metrics").inc()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

def start_socket_mode():
    """Start Socket Mode handler in a separate thread"""
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        logger.error("SLACK_APP_TOKEN not found in environment")
        return

    handler = SocketModeHandler(slack_app, app_token)
    handler.start()

# Start Socket Mode on application startup
@app.on_event("startup")
def startup_event():
    """Start Socket Mode handler when the FastAPI app starts"""
    thread = threading.Thread(target=start_socket_mode)
    thread.daemon = True
    thread.start()
    logger.info("Socket Mode started in background thread")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
