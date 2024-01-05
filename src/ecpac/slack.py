import json
import os

SLACK_WEBHOOK_URL: str | None = os.environ.get("SLACK_WEBHOOK_URL")


def slack_webhook_available() -> bool:
    """Check if a Slack webhook URL is available."""
    return SLACK_WEBHOOK_URL is not None


def slack_message_bash(text: str) -> str:
    """Generate a bash command to send a message to Slack."""
    if SLACK_WEBHOOK_URL is None:
        return ""
    data = json.dumps({"text": text})
    return f"curl -X POST -H 'Content-type: application/json' --data '{data}' {SLACK_WEBHOOK_URL}"
