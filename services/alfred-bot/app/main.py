# type: ignore
import os
from contextlib import asynccontextmanager

import redis
import structlog
from fastapi import FastAPI, Request
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler

from libs.a2a_adapter import (
    
,
    A2AEnvelope,
    PolicyMiddleware,
    PubSubTransport,
    SupabaseTransport,
)
from libs.agent_core.health import create_health_app

logger = structlog.get_logger(__name__)
# Initialize services
pubsub_transport = PubSubTransport(project_id=os.getenv("GCP_PROJECT_ID", "alfred-agent-platform"))

supabase_transport = SupabaseTransport(database_url=os.getenv("DATABASE_URL"))

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
policy_middleware = PolicyMiddleware(redis_client)

# Initialize Slack app
slack_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

@slack_app.command("/alfred")
async def handle_alfred_command(ack, body, client):
    """Handle /alfred slash command"""
    await ack()

    try:
        command_text = body.get("text", "").strip()
        user_id = body["user_id"]
        channel_id = body["channel_id"]

        # Parse command
        parts = command_text.split(maxsplit=1)
        if not parts:
            await client.chat_postMessage(
                channel=channel_id,
                text="Please specify a command. Try `/alfred help` for available commands.",
            )
            return

        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Handle different commands
        if command == "help":
            await show_help(client, channel_id)
        elif command == "ping":
            await handle_ping(client, channel_id, user_id)
        elif command == "trend":
            await handle_trend_analysis(client, channel_id, user_id, args)
        else:
            await client.chat_postMessage(
                channel=channel_id,
                text=f"Unknown command: {command}. Try `/alfred help` for available commands.",
            )

    except Exception as e:
        logger.error("command_handling_failed", error=str(e))
        await client.chat_postMessage(
            channel=channel_id,
            text="Sorry, something went wrong. Please try again later.",
        )

async def handle_ping(client, channel_id, user_id):
    """Handle ping command"""
    envelope = A2AEnvelope(intent="PING", content={"message": "ping", "user_id": user_id})

    try:
        await pubsub_transport.publish_task(envelope)

        await client.chat_postMessage(
            channel=channel_id, text=f"Ping task created! Task ID: {envelope.task_id}"
        )
    except Exception as e:
        logger.error("ping_failed", error=str(e))
        await client.chat_postMessage(
            channel=channel_id, text="Failed to create ping task. Please try again."
        )

async def handle_trend_analysis(client, channel_id, user_id, query):
    """Handle trend analysis command"""
    if not query:
        await client.chat_postMessage(
            channel=channel_id,
            text=(
                "Please provide a trend to analyze. "
                "Example: `/alfred trend artificial intelligence`"
            ),
        )
        return

    envelope = A2AEnvelope(
        intent="TREND_ANALYSIS",
        content={"query": query, "user_id": user_id, "channel_id": channel_id},
    )

    try:
        # Store task
        await supabase_transport.store_task(envelope)

        # Publish task
        await pubsub_transport.publish_task(envelope)

        await client.chat_postMessage(
            channel=channel_id,
            text=f"Analyzing trends for: {query}\nTask ID: {envelope.task_id}",
        )
    except Exception as e:
        logger.error("trend_analysis_failed", error=str(e))
        await client.chat_postMessage(
            channel=channel_id, text="Failed to start trend analysis. Please try again."
        )

async def show_help(client, channel_id):
    """Show help message"""
    help_text = """
*Alfred Bot Commands:*
- `/alfred help` - Show this help message
- `/alfred ping` - Test bot responsiveness
- `/alfred trend <topic>` - Analyze trends for a topic
- `/alfred status <task_id>` - Check task status
- `/alfred cancel <task_id>` - Cancel a running task
    """

    await client.chat_postMessage(channel=channel_id, text=help_text)

# Create FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    await supabase_transport.connect()
    logger.info("alfred_bot_started")

    yield

    # Shutdown
    await supabase_transport.disconnect()
    logger.info("alfred_bot_stopped")

app = FastAPI(title="Alfred Bot", lifespan=lifespan)

# Add health check endpoints
health_app = create_health_app("alfred-bot", "1.0.0")
app.mount("/health", health_app)

# Add Slack handler
slack_handler = SlackRequestHandler(slack_app)

@app.post("/slack/events")
async def slack_events(request: Request):
    """Handle Slack events"""
    return await slack_handler.handle(request)
