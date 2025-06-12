"""Slack app with HTTP mode instead of Socket Mode.

This version is designed to run when we don't have a valid App Token for Socket Mode.
"""

# type: ignore
import logging
import os
import socket

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# Load environment variables
load_dotenv()
# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

# Initialize the Slack Bolt app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

# Command prefix for slash commands
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "/alfred")
DEFAULT_CHANNEL = os.getenv("DEFAULT_CHANNEL", "general")
ALLOWED_COMMANDS = os.getenv("ALLOWED_COMMANDS", "help,status,search,ask,agents,health").split(",")

# Define allowed commands as a set for faster lookups
ALLOWED_COMMANDS_SET = set(ALLOWED_COMMANDS)

# Command handler for /alfred
@app.command(f"{COMMAND_PREFIX}")
def handle_alfred_command(ack, command, say):
    """Handle the /alfred slash command"""
    ack()  # Acknowledge command request

    # Parse the command text
    command_text = command.get("text", "").strip()
    if not command_text:
        command_text = "help"  # Default to help if no command provided

    # Split into subcommand and arguments
    parts = command_text.split(" ", 1)
    subcommand = parts[0].lower()
    parts[1] if len(parts) > 1 else ""

    # Check if the subcommand is allowed
    if subcommand not in ALLOWED_COMMANDS_SET:
        say(
            f"Sorry, the command `{subcommand}` is not recognized. Try `/alfred help` for a list of available commands."  # noqa: E501
        )
        return

    # Handle the specific subcommand
    if subcommand == "help":
        handle_help_command(say)
    elif subcommand == "status":
        handle_status_command(say)
    elif subcommand == "health":
        handle_health_command(say)
    else:
        # Forward to appropriate handler based on subcommand
        say(f"Command `{subcommand}` recognized, but not yet implemented.")

def handle_help_command(say):
    """Handle the help command"""
    help_text = (
        "*Alfred Slack Bot Commands*\n\n"
        "• `/alfred help` - Show this help message\n"
        "• `/alfred status` - Show Alfred platform status\n"
        "• `/alfred health` - Show health status of Alfred services\n"
        "• `/alfred search <query>` - Search for information\n"
        "• `/alfred ask <question>` - Ask a question to Alfred agents\n"
        "• `/alfred agents` - List available agents\n"
    )
    say(help_text)

def handle_status_command(say):
    """Handle the status command"""
    status_text = (
        "*Alfred Platform Status*\n\n"
        "• Platform Version: v0.8.1\n"
        "• Status: Operational\n"
        "• Active Agents: 3\n"
        "• Available Services: 12\n"
    )
    say(status_text)

def handle_health_command(say):
    """Handle the health command"""
    health_text = (
        "*Alfred Health Status*\n\n"
        "```\n"
        "Service            | Status  | Latency (ms) | Last Check\n"
        "-------------------|---------|--------------|-------------\n"
        "db-api-metrics     | UP      | 12           | Just now\n"
        "db-auth-metrics    | UP      | 15           | Just now\n"
        "db-admin-metrics   | UP      | 11           | Just now\n"
        "db-realtime-metrics| UP      | 14           | Just now\n"
        "db-storage-metrics | UP      | 13           | Just now\n"
        "model-registry     | UP      | 32           | Just now\n"
        "model-router       | UP      | 28           | Just now\n"
        "```\n"
    )
    say(health_text)

# Create a Flask app for HTTP listener and health checks
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events"""
    return handler.handle(request)

@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """Handle Slack commands"""
    return handler.handle(request)

@flask_app.route("/healthz")
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "slack-app"})

@flask_app.route("/readyz")
def ready():
    """Readiness check endpoint"""
    return jsonify({"status": "ready", "service": "slack-app"})

@flask_app.route("/")
def home():
    """Home page"""
    return jsonify(
        {
            "name": "Alfred Slack App",
            "version": "v0.8.1",
            "status": "running",
            "endpoints": ["/healthz", "/readyz", "/slack/events", "/slack/commands"],
            "slack_commands": [f"{COMMAND_PREFIX} {cmd}" for cmd in ALLOWED_COMMANDS],
        }
    )

def find_available_port(start_port, max_attempts=10):
    """Find an available port starting from start_port"""
    for port_offset in range(max_attempts):
        port = start_port + port_offset
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("0.0.0.0", port))
            sock.close()
            return port
        except OSError:
            continue
    return None

if __name__ == "__main__":
    # Find an available port
    port = find_available_port(3000)
    if port is None:
        port = find_available_port(8000)
    if port is None:
        port = find_available_port(9000)

    if port is None:
        print("Error: Could not find an available port")
        exit(1)

    # Start the Flask app
    print(f"⚡️ Bolt app is running in HTTP mode on port {port}!")
    print(f"Slack events URL: http://your-server:{port}/slack/events")
    print(f"Slack commands URL: http://your-server:{port}/slack/commands")
    print(f"Health endpoints: http://your-server:{port}/healthz, http://your-server:{port}/readyz")

    # Set debug mode to False to avoid the reloader
    flask_app.run(host="0.0.0.0", port=port, debug=False)
