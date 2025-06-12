import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

import httpx
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from fastapi import FastAPI, HTTPException, Request

log = logging.getLogger("wa-adapter")
log.setLevel(logging.INFO)

ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")
IN_TOPIC = os.getenv("WA_INBOUND_TOPIC", "wa.inbound")  # events to core
OUT_TOPIC = os.getenv("WA_OUTBOUND_TOPIC", "wa.outbound")  # replies from core

PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
GRAPH_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

app = FastAPI(title="WhatsApp Adapter (Sandbox)")
producer: AIOKafkaProducer  < /dev/null |  None = None
consumer: AIOKafkaConsumer | None = None
http: httpx.AsyncClient | None = None

@app.on_event("startup")
async def startup() -> None:
    if not ENABLED:
        log.warning("WhatsApp adapter disabled (WHATSAPP_ENABLED=false)")
        return
    global producer, consumer, http
    http = httpx.AsyncClient(timeout=10)
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKERS)
    await producer.start()
    consumer = AIOKafkaConsumer(
        OUT_TOPIC,
        bootstrap_servers=KAFKA_BROKERS,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="wa-adapter",
    )
    await consumer.start()
    asyncio.create_task(_drain_outbound())  # background loop
    log.info("Startup complete – Kafka bridge running")

@app.on_event("shutdown")
async def shutdown() -> None:
    if producer:
        await producer.stop()
    if consumer:
        await consumer.stop()
    if http:
        await http.aclose()

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "enabled": ENABLED,
        "kafka": bool(producer) and bool(consumer),
    }

@app.post("/webhook")
async def webhook(req: Request):
    """
    Receives Meta webhook calls; pushes the body to Kafka for agent-core.
    """
    if not ENABLED:
        raise HTTPException(status_code=503, detail="adapter disabled")

    body: Dict[str, Any] = await req.json()
    await producer.send_and_wait(IN_TOPIC, json.dumps(body).encode())
    return {"received": True}

async def _drain_outbound() -> None:
    """
    Background task: consume messages from agent-core and send via Graph API.
    Expected message schema:
      {
        "to": "<E.164 number>",
        "type": "text",
        "text": {"body": "hello world"}
      }
    """
    assert consumer and http, "consumer/http not initialised"
    async for msg in consumer:
        try:
            payload = json.loads(msg.value)
            headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
            r = await http.post(GRAPH_URL, json=payload, headers=headers)
            if r.status_code >= 300:
                log.error("WhatsApp send failure %s – %s", r.status_code, r.text[:200])
        except Exception as exc:
            log.exception("Error handling outbound message: %s", exc)
