"""Simple test script to check if Slack API tokens work correctly"""

# type: ignore
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Get tokens from environment variables
bot_token = os.environ.get("SLACK_BOT_TOKEN")
app_token = os.environ.get("SLACK_APP_TOKEN")
signing_secret = os.environ.get("SLACK_SIGNING_SECRET")

# Check if tokens are present
if not bot_token or not app_token or not signing_secret:
    print("Error: Missing required tokens in .env file")
    sys.exit(1)

print("Testing Slack API tokens...")

# Test the bot token with a simple API call
try:
    from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
    client = WebClient(token=bot_token)
    response = client.auth_test()

    if response["ok"]:
        print("✅ Bot Token is valid!")
        print(f"Team: {response['team']}")
        print(f"User: {response['user']}")
        print(f"URL: {response['url']}")
    else:
        print("❌ Bot Token is invalid!")
        print(f"Error: {response.get('error', 'Unknown error')}")
except SlackApiError as e:
    print("❌ Bot Token is invalid!")
    print(f"Error: {e.response['error']}")
except Exception as e:
    print("❌ Error testing Bot Token:")
    print(f"Error: {str(e)}")

# Test the app token (only needed for Socket Mode)
if os.environ.get("SOCKET_MODE", "").lower() == "true":
    try:
        if app_token.startswith("xapp-"):
            # We can't fully validate app tokens without starting Socket Mode
            print("✅ App Token has the correct format (xapp-)")
            print("  Note: Full validation requires starting Socket Mode")
        else:
            print("❌ App Token has the wrong format. Should start with 'xapp-'")
    except Exception as e:
        print("❌ Error checking App Token:")
        print(f"Error: {str(e)}")

print("\nIf the Bot Token is valid, you should be able to run the app with:")
print("python3 run.py")
print("\nIf you're still having issues, please check:")
print("1. The bot has been added to your Slack workspace")
print("2. The bot has the correct OAuth scopes")
print("3. The tokens have not been revoked")
print("4. Your network can connect to Slack's API")
