"""Test if the Slack tokens are being read correctly"""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Get the tokens
bot_token = os.environ.get("SLACK_BOT_TOKEN")
app_token = os.environ.get("SLACK_APP_TOKEN")
signing_secret = os.environ.get("SLACK_SIGNING_SECRET")

# Check token format (without revealing the actual tokens)
def check_token(token, prefix, name):
    if not token:
        return f"{name}: ❌ Missing"
    if not token.startswith(prefix):
        return f"{name}: ❌ Invalid format (should start with {prefix})"
    # Mask the token except the first 5 and last 4 characters
    masked = f"{token[:5]}...{token[-4:]}" if len(token) > 10 else "too short"
    return f"{name}: ✅ Valid format - {masked}"

# Print the token checks
print(check_token(bot_token, "xoxb-", "SLACK_BOT_TOKEN"))
print(check_token(app_token, "xapp-", "SLACK_APP_TOKEN"))
print(f"SLACK_SIGNING_SECRET: {'✅ Present' if signing_secret else '❌ Missing'}")

# Try to make a simple API call to Slack
try:
    import requests

# Attempt to call the auth.test API
    response = requests.post(
        "https://slack.com/api/auth.test",
        headers={"Authorization": f"Bearer {bot_token}"},
    )

    # Print the response
    print("\nAPI test result:")
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"\nError making API call: {e}")
