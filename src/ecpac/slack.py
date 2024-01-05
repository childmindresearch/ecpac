"""Slack-related functions."""

import json
import os
import shlex

SLACK_WEBHOOK_URL: str | None = os.environ.get("SLACK_WEBHOOK_URL")


def slack_webhook_available() -> bool:
    """Check if a Slack webhook URL is available."""
    return SLACK_WEBHOOK_URL is not None and len(SLACK_WEBHOOK_URL) > 0


def slack_message_bash(data: dict) -> str:
    """Generate a bash command to send a message to Slack."""
    if not slack_webhook_available():
        return ""
    return shlex.join(
        ["curl", "-X", "POST", "-H", "Content-type: application/json", "--data", json.dumps(data), SLACK_WEBHOOK_URL],
    )


def slack_message_bash_mrkdwn(text: str) -> str:
    """Generate a bash command to send a message to Slack.

    `mrkdwn` is not a typo but a Slack-specific markdown-like syntax.
    """
    return slack_message_bash({"text": text})
