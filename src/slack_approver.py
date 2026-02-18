import os
import requests
import logging
import json
from typing import Optional
from dotenv import load_dotenv

# Initialize project-level logging for better audit trails
logging.basicConfig(level=logging.INFO, format='%(asctime)s - NexusOps - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class SlackApprovalGate:
    """
    Governor Pattern: Manages manual intervention for high-risk agentic actions.
    Integrates with Slack Webhooks for alerts and local CLI for state resolution.
    """
    def __init__(self):
        self._webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not self._webhook_url:
            logger.warning("SLACK_WEBHOOK_URL missing. System will default to CLI-only mode.")

    def dispatch_alert(self, action_context: str) -> None:
        """
        Asynchronously notifies the SRE team via Slack of a pending governor block.
        """
        if not self._webhook_url:
            return

        # Professional Block Kit-style formatting for better scannability
        payload = {
            "text": "🚨 NexusOps Governor Action Required",
            "attachments": [
                {
                    "color": "#eb4034",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": f"*Action Pending:* `{action_context}`"}
                        },
                        {
                            "type": "context",
                            "elements": [{"type": "mrkdwn", "text": "_Governor is currently holding execution for manual validation._"}]
                        }
                    ]
                }
            ]
        }

        try:
            # Use a timeout to prevent the agent from hanging on a network blip
            response = requests.post(
                self._webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Dispatched Slack alert for action: {action_context}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to reach Slack API: {str(e)}")

    def await_validation(self) -> bool:
        """
        Blocks execution until a manual signal is received. 
        In production, this would poll an external state-store or wait for a callback.
        """
        print("\n" + "!" * 60)
        print("[GOVERNOR BLOCK] MANUAL VALIDATION REQUIRED")
        print("!" * 60)
        print("The agent is requesting permission to execute a destructive or high-risk tool.")
        
        while True:
            try:
                user_input = input("\nAuthorize execution? (confirm/abort): ").lower().strip()
                if user_input in ['confirm', 'c', 'yes']:
                    logger.info("Manual override: Action Authorized.")
                    return True
                if user_input in ['abort', 'a', 'no']:
                    logger.warning("Manual override: Action Terminated by User.")
                    return False
                print("Invalid command. Use 'confirm' to proceed or 'abort' to stop.")
            except KeyboardInterrupt:
                # Handle unexpected exits gracefully
                print("\n[!] Emergency abort triggered.")
                return False

# Shared instance for the LangGraph state machine
governor = SlackApprovalGate()
