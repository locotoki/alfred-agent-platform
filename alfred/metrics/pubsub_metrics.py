#!/usr/bin/env python3

import os
import time

import requests
from flask import Flask, Response, jsonify
from prometheus_client import REGISTRY, Counter, Gauge, generate_latest

app = Flask(__name__)
# Create metrics
pubsub_availability = Gauge("pubsub_availability", "Availability of the PubSub emulator")
pubsub_topics_total = Gauge("pubsub_topics_total", "Total number of PubSub topics")
pubsub_subscriptions_total = Gauge(
    "pubsub_subscriptions_total", "Total number of PubSub subscriptions"
)
health_requests = Counter("pubsub_health_requests", "Number of health check requests")

# Configuration
PUBSUB_URL = os.getenv("PUBSUB_URL", "http://pubsub-emulator:8085")
PROJECT_ID = os.getenv("PROJECT_ID", "alfred-agent-platform")
COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "15"))


def collect_metrics():
    """Collect metrics from PubSub emulator"""
    try:
        # Check PubSub availability
        response = requests.get(f"{PUBSUB_URL}/v1/projects/{PROJECT_ID}/topics")
        if response.status_code == 200:
            pubsub_availability.set(1)

            # Get number of topics
            data = response.json()
            if "topics" in data:
                pubsub_topics_total.set(len(data["topics"]))
            else:
                pubsub_topics_total.set(0)

            # Get subscriptions
            try:
                subs_response = requests.get(f"{PUBSUB_URL}/v1/projects/{PROJECT_ID}/subscriptions")
                if subs_response.status_code == 200:
                    subs_data = subs_response.json()
                    if "subscriptions" in subs_data:
                        pubsub_subscriptions_total.set(len(subs_data["subscriptions"]))
                    else:
                        pubsub_subscriptions_total.set(0)
                else:
                    pubsub_subscriptions_total.set(0)
            except Exception as e:
                print(f"Error fetching subscriptions: {e}")
                pubsub_subscriptions_total.set(0)
        else:
            pubsub_availability.set(0)
            pubsub_topics_total.set(0)
            pubsub_subscriptions_total.set(0)
    except Exception as e:
        print(f"Error collecting metrics: {e}")
        pubsub_availability.set(0)
        pubsub_topics_total.set(0)
        pubsub_subscriptions_total.set(0)


@app.route("/metrics")
def metrics():
    collect_metrics()
    return Response(generate_latest(REGISTRY), mimetype="text/plain")


@app.route("/health")
def health():
    health_requests.inc()
    try:
        collect_metrics()
        status = "ok" if pubsub_availability._value.get() == 1 else "error"
        return jsonify({"status": status, "version": "1.0.0", "services": {"pubsub": status}})
    except Exception as e:
        return jsonify({"status": "error", "version": "1.0.0", "error": str(e)}), 500


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


# Start background metrics collection
def background_collector():
    """Collect metrics periodically in the background"""
    while True:
        collect_metrics()
        time.sleep(COLLECTION_INTERVAL)


if __name__ == "__main__":
    # Start metrics collection in the background

    import threading

    collector_thread = threading.Thread(target=background_collector, daemon=True)
    collector_thread.start()

    # Start the server
    port = int(os.getenv("PORT", "9103"))
    app.run(host="0.0.0.0", port=port)
