"""Mock server for the Slack app.

This server simulates the complete functionality without requiring real Slack
authentication.
"""

from flask import Flask, Response, jsonify, request

app = Flask(__name__)
# Store mock state
class MockState:
    health_reports = []
    channels = ["general", "random", "dev"]
    commands_executed = []

state = MockState()

# Home page with basic info
@app.route("/")
def home():
    return jsonify(
        {
            "name": "Alfred Slack App Mock Server",
            "version": "v0.8.1",
            "status": "running",
            "features": ["Command simulation", "Health checks", "Service status"],
        }
    )

# Health endpoints
@app.route("/healthz")
def health():
    return jsonify({"status": "ok", "service": "slack-app"})

@app.route("/readyz")
def ready():
    return jsonify({"status": "ready", "service": "slack-app"})

# Mock Slack API endpoints
@app.route("/api/auth.test", methods=["POST"])
def auth_test():
    return jsonify(
        {
            "ok": True,
            "url": "https://alfred-workspace.slack.com/",
            "team": "Alfred Platform",
            "user": "alfred_bot",
            "team_id": "T12345",
            "user_id": "U12345",
        }
    )

@app.route("/api/chat.postMessage", methods=["POST"])
def post_message():
    data = request.json or {}
    channel = data.get("channel", "general")
    text = data.get("text", "")

    # Store the message for history
    if text and "health" in text.lower():
        state.health_reports.append({"channel": channel, "text": text, "timestamp": "now"})

    return jsonify(
        {
            "ok": True,
            "channel": channel,
            "ts": "1234567890.123456",
            "message": {
                "text": text,
                "username": "alfred_bot",
                "bot_id": "B12345",
                "type": "message",
            },
        }
    )

# Command endpoint
@app.route("/slack/commands", methods=["POST"])
def slack_commands():
    command = request.form.get("command", "/alfred")
    text = request.form.get("text", "help")
    channel_id = request.form.get("channel_id", "C12345")
    user_id = request.form.get("user_id", "U12345")

    # Store the command
    state.commands_executed.append(
        {"command": command, "text": text, "channel_id": channel_id, "user_id": user_id}
    )

    # Process different commands
    if text == "help" or not text:
        response = {
            "text": "*Alfred Slack Bot Commands*\n\n"
            "• `/alfred help` - Show this help message\n"
            "• `/alfred status` - Show Alfred platform status\n"
            "• `/alfred health` - Show health status of Alfred services\n"
            "• `/alfred search <query>` - Search for information\n"
            "• `/alfred ask <question>` - Ask a question to Alfred agents\n"
            "• `/alfred agents` - List available agents\n"
        }
    elif text == "status":
        response = {
            "text": "*Alfred Platform Status*\n\n"
            "• Platform Version: v0.8.1\n"
            "• Status: Operational\n"
            "• Active Agents: 3\n"
            "• Available Services: 12\n"
        }
    elif text == "health":
        response = {
            "text": "*Alfred Health Status*\n\n"
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
        }
    elif text.startswith("search "):
        query = text[7:]
        response = {
            "text": f"Searching for: *{query}*\n\n"
            f"Found 3 results related to '{query}':\n"
            f"1. Documentation on {query}\n"
            f"2. Agent capabilities for {query}\n"
            f"3. Recent discussions about {query}\n"
        }
    elif text.startswith("ask "):
        question = text[4:]
        response = {
            "text": f"Question: *{question}*\n\n"
            f"I'm analyzing your question and consulting with the appropriate agents...\n\n"
            f"Answer: Based on my analysis, the answer to your question is related to Alfred's capabilities in this area.\n"  # noqa: E501
        }
    elif text == "agents":
        response = {
            "text": "*Available Alfred Agents*\n\n"
            "• Financial Tax Agent - Tax and financial analysis\n"
            "• Legal Compliance Agent - Legal and compliance guidance\n"
            "• Social Intelligence Agent - Social media and trend analysis\n"
        }
    else:
        response = {
            "text": f"Command not recognized: `{text}`\n"
            f"Try `/alfred help` for a list of available commands."
        }

    return jsonify(response)

# Mock events endpoint
@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json or {}
    event = data.get("event", {})
    event_type = event.get("type")

    if event_type == "app_mention":
        return jsonify({"ok": True})

    return jsonify({"ok": True})

# Status page with app information
@app.route("/status")
def status():
    return jsonify(
        {
            "app": "Alfred Slack App",
            "status": "running",
            "commands_executed": state.commands_executed,
            "health_reports": state.health_reports,
            "channels": state,
        }
    )

# Frontend UI for testing
@app.route("/ui")
def ui():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Alfred Slack App Simulator</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }  # noqa: E501
            .terminal { background: #1e1e1e; color: #ddd; padding: 15px; border-radius: 5px; font-family: monospace; }  # noqa: E501
            .output { white-space: pre-wrap; }
            h1, h2 { color: #333; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; }
            input[type="text"] { width: 100%; padding: 8px; box-sizing: border-box; }
            button { background: #4CAF50; color: white; border: none; padding: 10px 15px; cursor: pointer; border-radius: 3px; }  # noqa: E501
            .success { background: #dff0d8; color: #3c763d; padding: 10px; border-radius: 5px; margin: 10px 0; }  # noqa: E501
        </style>
    </head>
    <body>
        <h1>Alfred Slack App Simulator</h1>
        <p>Use this interface to simulate Slack commands without requiring real Slack authentication.</p>  # noqa: E501

        <div class="terminal">
            <div class="output">⚡️ Bolt app is running! Connected to Slack.</div>
        </div>

        <h2>Test Commands</h2>
        <div class="form-group">
            <label for="command">Slack Command:</label>
            <input type="text" id="command" value="/alfred" readonly>
        </div>
        <div class="form-group">
            <label for="text">Command Text:</label>
            <input type="text" id="text" placeholder="help, status, health, etc.">
        </div>
        <button id="send-command">Send Command</button>

        <div id="result" style="margin-top: 20px;"></div>

        <script>
            document.getElementById('send-command').addEventListener('click', function() {
                const command = document.getElementById('command').value;
                const text = document.getElementById('text').value || 'help';

                fetch('/slack/commands', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: `command=${encodeURIComponent(command)}&text=${encodeURIComponent(text)}`
                })
                .then(response => response.json())
                .then(data => {
                    const resultDiv = document.getElementById('result');
                    resultDiv.innerHTML = `<div class="success">Command executed!</div><div class="terminal"><div class="output">${data.text.replace(/\\n/g, '<br>').replace(/\\*/g, '<strong>').replace(/\\`/g, '<code>').replace(/\\`\\`\\`/g, '')}</div></div>`;  # noqa: E501
                })
                .catch(error => {
                    console.error('Error:', error);
                    const resultDiv = document.getElementById('result');
                    resultDiv.innerHTML = `<div class="error">Error: ${error}</div>`;
                });
            });
        </script>
    </body>
    </html>
    """
    return Response(html, content_type="text/html")

if __name__ == "__main__":
    port = 5000
    print(f"⚡️ Mock Slack App server is running on port {port}!")
    print(f"Visit http://localhost:{port}/ui to interact with the mock server")
    print("The following endpoints are available:")
    print(f"  - http://localhost:{port}/healthz - Health check endpoint")
    print(f"  - http://localhost:{port}/readyz - Readiness check endpoint")
    print(f"  - http://localhost:{port}/ui - Interactive UI for testing commands")
    print(f"  - http://localhost:{port}/status - Status page with app information")
    app.run(host="0.0.0.0", port=port, debug=True)
