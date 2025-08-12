from slack_bolt import App
from slackbot.slack_player import pending_inputs

def register_handlers(app: App):
    valid_actions = ["fold", "call", "raise"]

    for action in valid_actions:
        @app.action(f"poker_{action}")
        def handle_action(ack, body, logger):
            ack()
            user_id = body["user"]["id"]
            logger.info(f"Received action from {user_id}: {action}")

            # Set the pending response so SlackPlayer unblocks
            if user_id in pending_inputs:
                if action == "raise":
                    # For now, raise amount is hardcoded to 20
                    pending_inputs[user_id]["response"] = (action, 20)
                else:
                    pending_inputs[user_id]["response"] = (action, 0)
