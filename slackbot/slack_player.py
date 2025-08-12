from pypokerengine.players import BasePokerPlayer

# You will fill in this callback from Slack later
pending_inputs = {}  # Maps user_id to {"event": ..., "response": (action, amount)}

class SlackPlayer(BasePokerPlayer):
    def __init__(self, user_id, slack_client):
        self.user_id = user_id
        self.slack_client = slack_client

    def declare_action(self, valid_actions, hole_card, round_state):
        # Prompt user in Slack
        self._prompt_user(valid_actions, hole_card, round_state)

        # Block until a response is received
        return self._wait_for_response()

    def _prompt_user(self, valid_actions, hole_card, round_state):
        # Save a placeholder in shared store so Slack knows to resume this
        pending_inputs[self.user_id] = {"event": round_state, "response": None}

        # Format buttons (simplified for now)
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"<@{self.user_id}>, it's your turn! Choose your move:"}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": action["action"]},
                        "value": action["action"],
                        "action_id": f"poker_{action['action']}"
                    }
                    for action in valid_actions
                ]
            }
        ]

        self.slack_client.chat_postMessage(
            channel=self.user_id,
            text="It's your turn to play poker!",
            blocks=blocks
        )

    def _wait_for_response(self):
        import time
        while pending_inputs[self.user_id]["response"] is None:
            time.sleep(0.5)  # Polling every 0.5s
        return pending_inputs[self.user_id]["response"]
