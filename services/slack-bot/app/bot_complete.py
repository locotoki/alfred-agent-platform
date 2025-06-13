"""
Complete Slack bot implementation with Redis integration
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.app.async_app import AsyncApp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client (embedded)
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - setup and teardown"""
    global redis_client

    # Startup
    logger.info("Initializing Redis connection...")
    redis_client = await redis.from_url("redis://localhost:6379", decode_responses=True)

    # Initialize Slack app
    slack_app.client.retry_handlers.append(AsyncRetryHandler(max_retry_count=2))

    yield

    # Shutdown
    if redis_client:
        await redis_client.close()

# Initialize FastAPI with lifespan
app = FastAPI(lifespan=lifespan)

# Initialize Slack app
slack_app = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True,
)

# Slack request handler
handler = AsyncSlackRequestHandler(slack_app)

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
            "version": os.environ.get("TAG", "unknown"),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/slack/events")
async def slack_events(req):
    """Handle Slack events"""
    return await handler.handle(req)

# Slack command handler
@slack_app.command("/alfred")
async def handle_alfred_command(ack, command, say):
    """Handle /alfred commands"""
    await ack()

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
