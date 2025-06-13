"""Telegram adapter for Alfred platform.

This module implements a FastAPI application that serves as a Telegram
adapter for the Alfred platform. It handles incoming webhook requests
from Telegram, processes the messages and routes them to Alfred.
"""

import json
import logging
import os
import time
from typing import Any, Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    
,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Telegram Adapter", description="Telegram adapter for Alfred Agent Platform")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics
REQUEST_COUNT = Counter(
    "telegram_adapter_requests_total",
    "Total number of requests to the Telegram adapter",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "telegram_adapter_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

MESSAGE_COUNT = Counter(
    "telegram_adapter_messages_total",
    "Total number of messages processed by the Telegram adapter",
    ["type"],  # type can be "text", "command", etc.
)

# Get Telegram bot token from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set in environment variables")

# Initialize the Telegram bot application
bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN or "").build()

# Alfred Core service connection - adjust as needed for your environment
A
RED_CORE_URL = os.getenv("A
RED_CORE_URL", "http://agent-core:8011")

async def route_to_alfred(user_id: str, message: str) -> Optional[str]:
    """Route the message to Alfred Core service and get a response.

    This is a placeholder implementation - integrate with your actual Alfred Core API.
    """
    try:
        # Placeholder for actual API call to Alfred
        # In a real implementation, you would make an HTTP request to your core service
        logger.info(f"Routing message to Alfred Core: {message}")

        # Simulate a response for now - replace with actual API call
        response = f"Received your message: {message}"
        return response
    except Exception as e:
        logger.error(f"Error routing message to Alfred: {e}")
        return None

# Command handler for /start
async def start_command(update: Update, context):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    MESSAGE_COUNT.labels(type="command").inc()
    await update.message.reply_text(
        f"Hello {user.first_name}! I am Alfred, your personal assistant."
    )

# Command handler for /help
async def help_command(update: Update, context):
    """Send a message when the command /help is issued."""
    MESSAGE_COUNT.labels(type="command").inc()
    await update.message.reply_text(
        "I can help you with a variety of tasks. Just send me a message!"
    )

# Message handler for text messages
async def message_handler(update: Update, context):
    """Handle incoming text messages."""
    user_id = str(update.effective_user.id)
    message_text = update.message.text

    # Increment message counter
    MESSAGE_COUNT.labels(type="text").inc()

    # Start timing for latency measurement
    start_time = time.time()

    # Route the message to Alfred and get a response
    response = await route_to_alfred(user_id, message_text)

    # Record latency
    latency = time.time() - start_time
    REQUEST_LATENCY.labels(method="POST", endpoint="/alfred/message").observe(latency)

    if response:
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("Sorry, I couldn't process your request at the moment.")

# Register handlers
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

# Start the bot in webhook mode
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

@app.post("/telegram/webhook", status_code=status.HTTP_200_OK)
async def telegram_webhook(req: Request) -> dict:
    """Handle Telegram webhook updates."""
    start_time = time.time()
    try:
        update_data = await req.json()
        logger.info(f"Received update: {json.dumps(update_data)}")

        # Process the update
        update = Update.de_json(update_data, bot_app.bot)
        await bot_app.process_update(update)

        REQUEST_COUNT.labels(method="POST", endpoint="/telegram/webhook", status_code="200").inc()
        REQUEST_LATENCY.labels(method="POST", endpoint="/telegram/webhook").observe(
            time.time() - start_time
        )
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}")
        REQUEST_COUNT.labels(method="POST", endpoint="/telegram/webhook", status_code="500").inc()
        REQUEST_LATENCY.labels(method="POST", endpoint="/telegram/webhook").observe(
            time.time() - start_time
        )
        return {"ok": False, "error": str(e)}

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """Health check endpoint."""
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status_code="200").inc()
    return {"status": "healthy", "service": "telegram-adapter"}

@app.get("/metrics", status_code=status.HTTP_200_OK)
async def metrics() -> Any:
    """Metrics endpoint for Prometheus."""
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
