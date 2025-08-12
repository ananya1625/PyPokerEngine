from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv
import threading

from slackbot.lobby_manager import LobbyManager
from slackbot.slack_handlers import register_handlers
from slackbot.slack_player import SlackPlayer

# Load environment variables
load_dotenv()

# Initialize Slack app
app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

# Register button action handlers
register_handlers(app)

# Lobby store
lobby_manager = LobbyManager()


# ---------- GAME LOOP ----------
def run_poker_game(code, player_ids, slack_client):
    from pypokerengine.api.game import setup_config, start_poker

    config = setup_config(max_round=10, initial_stack=1000, small_blind_amount=20)

    for uid in player_ids:
        player = SlackPlayer(user_id=uid, slack_client=slack_client)
        config.register_player(name=uid, algorithm=player)

    game_result = start_poker(config, verbose=1)

    # Notify players the game is over
    for uid in player_ids:
        slack_client.chat_postMessage(
            channel=uid,
            text="🃏 Game over! Thanks for playing.\n(More detailed results coming soon.)"
        )

    # Clean up the lobby
    lobby_manager.clear_lobby(code)


# ---------- /start ----------
@app.command("/start")
def start_game(ack, body, respond):
    ack()
    user_id = body["user_id"]
    code = lobby_manager.create_lobby(user_id)

    respond(
        f"🎲 Game started by <@{user_id}>!\n"
        f"Your game code is *{code}*.\n"
        f"Share this with teammates. They can join using `/join {code}`"
    )


# ---------- /join ABCD ----------
@app.command("/join")
def join_game(ack, body, respond, command):
    ack()
    user_id = body["user_id"]
    text = command.get("text", "").strip().upper()

    if not text or len(text) != 4:
        respond("❌ Please provide a valid 4-character game code like `/join F3BZ`.")
        return

    success, message = lobby_manager.join_lobby(user_id, text)
    respond(message)


# ---------- /begin ABCD ----------
@app.command("/begin")
def begin_game(ack, body, respond, command):
    ack()
    user_id = body["user_id"]
    text = command.get("text", "").strip().upper()

    if not text or len(text) != 4:
        respond("❌ Please provide a valid 4-character game code like `/begin F3BZ`.")
        return

    code = text
    if not lobby_manager.is_owner(user_id, code):
        respond("🚫 Only the host can start this game.")
        return

    players = lobby_manager.get_players(code)
    if len(players) < 2:
        respond("👥 You need at least 2 players to start.")
        return

    respond(f"♠️ Starting game *{code}* with players: {', '.join(f'<@{p}>' for p in players)}")

    thread = threading.Thread(
        target=run_poker_game,
        args=(code, players, app.client),
        daemon=True
    )
    thread.start()


# ---------- MAIN ----------
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
