"""
Slack bot implementation with Socket Mode and Redis integration
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.app.async_app import AsyncApp

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("bot_socket_mode")

# Redis client (embedded)
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - setup and teardown"""
    global redis_client

    # Startup
    logger.info("Initializing Redis connection...")
    # Use Redis container name when running in Docker, localhost for local dev
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379")
    redis_client = await redis.from_url(redis_url, decode_responses=True)

    # Start Socket Mode handler
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if app_token:
        handler = AsyncSocketModeHandler(slack_app, app_token)
        logger.info("Starting Socket Mode handler...")
        logger.info(f"Registered commands: {list(slack_app._slash_command_listeners.keys())}")
        # Start Socket Mode in the background
        asyncio.create_task(handler.start_async())
    else:
        logger.warning("SLACK_APP_TOKEN not found, Socket Mode disabled")

    yield

    # Shutdown
    if redis_client:
        await redis_client.close()

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

# Initialize Slack app with debug logging
slack_app = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    logger=logger,
    # Set to DEBUG to see full payloads
    log_level="DEBUG",
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Check Redis
        if redis_client:
            await redis_client.ping()
            redis_status = "healthy"
        else:
            redis_status = "not initialized"

        # Check Slack
        slack_status = "healthy" if slack_app.client else "not initialized"

        return {
            "ok": True,
            "redis": redis_status,
            "slack": slack_status,
            "socket_mode": True,
            "version": os.environ.get("TAG", "unknown"),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

# Slack command handler - register WITH slash prefix
@slack_app.command("/alfred")
async def handle_alfred_command(ack, command, say):
    """Handle /alfred commands"""
    # Acknowledge immediately with a message
    await ack("Processing your request...")
    logger.info(f"Received /alfred command: {command}")

    text = command.get("text", "").strip()
    user_id = command["user_id"]

    try:
        # Store command in Redis for processing
        command_id = f"cmd:{user_id}:{asyncio.get_event_loop().time()}"
        await redis_client.hset(
            command_id,
            mapping={
                "text": text,
                "user_id": user_id,
                "channel_id": command["channel_id"],
                "timestamp": str(asyncio.get_event_loop().time()),
            },
        )

        # Process command
        if text.startswith("ping"):
            response = f"🏓 Pong! {text[4:].strip()}"
        elif text.startswith("status"):
            # Get Redis info
            info = await redis_client.info()
            response = f"📊 Status: Redis memory={info['used_memory_human']}, commands processed={await redis_client.dbsize()}"
        elif text.startswith("help"):
            response = """🤖 Alfred Commands:
• `/alfred ping [message]` - Test connectivity
• `/alfred status` - Check system status
• `/alfred help` - Show this help"""
        else:
            response = f"🤔 Unknown command: {text}. Try `/alfred help`"

        await say(response)

        # Log to Redis
        await redis_client.rpush("command_log", f"{user_id}:{text}")

    except Exception as e:
        logger.error(f"Error processing command: {e}")
        await say(f"❌ Error: {str(e)}")

# Slack /diag command handler - register WITH slash prefix
@slack_app.command("/diag")
async def handle_diag_command(ack, command, say):
    """Handle /diag commands"""
    # Acknowledge immediately
    await ack("Running diagnostics...")
    logger.info(f"Received /diag command: {command}")

    # Get system status
    redis_status = "unknown"
    try:
        if redis_client:
            await redis_client.ping()
            redis_status = "healthy"
    except:
        redis_status = "unhealthy"

    response = f"""🔧 Diagnostics:
• Redis: {redis_status}
• Socket Mode: Active
• Version: {os.environ.get("TAG", "unknown")}
• User: <@{command["user_id"]}>
• Channel: <#{command["channel_id"]}>"""

    await say(response)

# Slack app mention handler
@slack_app.event("app_mention")
async def handle_mention(event, say):
    """Handle @alfred mentions"""
    await say(f"Hello <@{event['user']}>! Use `/alfred help` to see available commands.")

# Error handler
@slack_app.error
async def custom_error_handler(error, body, logger):
    """Handle errors gracefully"""
    logger.error(f"Error: {error}")
    logger.error(f"Request body: {body}")

async def start_socket_mode():
    """Start Socket Mode handler"""
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        logger.error("SLACK_APP_TOKEN not found! Socket Mode requires an app-level token.")
        logger.error(
            "Get it from: https://api.slack.com/apps > Your App > Basic Information > App-Level Tokens"
        )
        return

    handler = AsyncSocketModeHandler(slack_app, app_token)
    logger.info("Starting Socket Mode handler...")
    await handler.start_async()

if __name__ == "__main__":
    import uvicorn

# Start Socket Mode handler in background
    asyncio.create_task(start_socket_mode())

    # Start FastAPI for health checks
    uvicorn.run(app, host="0.0.0.0", port=8000)
