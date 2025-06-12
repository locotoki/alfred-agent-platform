"""Development server for the Slack app.

Runs the Flask server only for testing health endpoints.
"""

from dotenv import load_dotenv
from flask import Flask, jsonify

# Load environment variables
load_dotenv()
# Create a Flask app for health checks
app = Flask(__name__)

@app.route("/healthz")
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "slack-app"})

@app.route("/readyz")
def ready():
    """Readiness check endpoint"""
    return jsonify({"status": "ready", "service": "slack-app"})

@app.route("/")
def home():
    """Home page"""
    return jsonify(
        {
            "name": "Alfred Slack App",
            "version": "v0.8.1",
            "status": "development",
            "endpoints": ["/healthz", "/readyz"],
            "slack_commands": [
                {"command": "/alfred help", "description": "Show help message"},
                {"command": "/alfred status", "description": "Show platform status"},
                {"command": "/alfred health", "description": "Check service health"},
            ],
        }
    )

@app.route("/mock/health")
def mock_health_command():
    """Mock the /alfred health command response"""
    health_response = {
        "text": (
            "*Alfred Health Status*\n\n```\n"
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
    }
    return jsonify(health_response)

if __name__ == "__main__":
    port = 8502  # Use a much higher port to avoid conflicts
    print(f"⚡️ Development server is running on port {port}! (No Slack connection)")
    print("Health endpoints available at:")
    print(f"  - http://localhost:{port}/healthz")
    print(f"  - http://localhost:{port}/readyz")
    print(f"  - http://localhost:{port}/mock/health (simulates /alfred health command)")
    print("\nTo run with real Slack tokens, update .env with valid credentials")
    print("and run: python run.py")
    app.run(host="0.0.0.0", port=port, debug=True)
