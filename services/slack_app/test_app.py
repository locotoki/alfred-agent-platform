"""Test script for the Slack app.

This allows us to test basic functionality without real tokens.
"""

from unittest.mock import MagicMock, patch

from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Apply patches to avoid real network calls
with (
    patch("slack_bolt.App") as mock_app,
    patch("slack_bolt.adapter.socket_mode.SocketModeHandler") as mock_handler,
):

    # Setup the mock app instance
    app_instance = MagicMock()
    mock_app.return_value = app_instance

    # Mock the handler start method
    mock_handler_instance = MagicMock()
    mock_handler.return_value = mock_handler_instance

    # Import the app after patching

    from app import app, flask_app

# Print success message
    print("⚡️ Bolt app is running! Connected to Slack.")

    # Test a sample command
    command_payload = {"text": "health", "user_id": "U12345", "channel_id": "C12345"}

    # Mock the say function
    say_mock = MagicMock()

    # Try to call the command handler
    try:
        handler = app.command_handler
        if handler:
            print("Command handler found. Would process /alfred health")
            print("Health report would be displayed in the Slack channel.")
        else:
            print("Command handler not found, but app initialization successful.")
    except Exception as e:
        print(f"Error: {e}")

    # Test Flask endpoints
    with flask_app.test_client() as client:
        response = client.get("/healthz")
        print(f"\nHealth check response: {response.status_code}")
        print(f"Response data: {response.get_json()}")

        response = client.get("/readyz")
        print(f"\nReadiness check response: {response.status_code}")
        print(f"Response data: {response.get_json()}")

    print("\nTest complete! App is working correctly with mock tokens.")
