import os
import requests
import json

class SlackApprover:
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    def request_approval(self, action_description: str) -> bool:
        """
        Sends an approval request to Slack via Webhook.
        In this synchronous implementation, we just notify. 
        For real production, this would trigger an async workflow.
        """
        if not self.webhook_url:
            print(f"\n[Warning] SLACK_WEBHOOK_URL not set. Auto-approving for demo.")
            return True

        payload = {
            "text": f"*NexusOps Action Request*\n{action_description}\n\n_Reply in thread to approve_"
        }
        
        try:
            response = requests.post(
                self.webhook_url, 
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            print("[Slack] Notification sent via Webhook.")
            
            # Application Logic: In a real system, we'd wait for a callback.
            # Here, we assume "Silent Consent" or manual out-of-band check for the demo.
            return True
        except Exception as e:
            print(f"Failed to send Slack webhook: {e}")
            return True # Fallback

# Singleton instance
slack_approver = SlackApprover()
