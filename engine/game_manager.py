from pypokerengine.api.game import setup_config
from .models import SetupPlayer
import random

class GameManager:
    def __init__(self):
        self.games = {}  # Stores game_id -> { engine, players, status }

    def create_game(self, game_id, players):
        if len(players) < 2:
            return {"error": "At least 2 players required."}

        config = setup_config(max_round=1, initial_stack=100, small_blind_amount=1)
        random.shuffle(players)
        player_objs = []

        for p in players:
            player = SetupPlayer(user_id=p["user_id"], stack=p["stack"])
            config.register_player(name=p["user_id"], algorithm=player)
            player_objs.append(player)

        # ✅ Correct way to start the engine and get a live game object
        engine = config._create_game()
        engine.start_new_round()

        # Assign roles based on shuffled player order
        dealer_index = 0
        sb_index = 1 % len(player_objs)
        bb_index = 2 % len(player_objs)

        for i, p in enumerate(player_objs):
            if i == dealer_index:
                p.position = "dealer"
            elif i == sb_index:
                p.position = "small_blind"
            elif i == bb_index:
                p.position = "big_blind"
            else:
                p.position = "none"

        # ✅ Store the engine and players
        self.games[game_id] = {
            "engine": engine,
            "players": player_objs,
            "status": "in_progress",
            "current_round": "preflop"
        }

        return {
            "game_id": game_id,
            "players": [
                {
                    "user_id": p.user_id,
                    "hole_cards": p.hole_card,
                    "position": p.position,
                    "stack": p.stack
                }
                for p in player_objs
            ]
        }

    def get_game(self, game_id):
        return self.games.get(game_id)

    def apply_action(self, game_id, user_id, action, amount):
        game = self.get_game(game_id)
        if not game:
            return {"error": "Game not found"}

        engine = game["engine"]

        try:
            engine.apply_action(user_id, action, amount)
        except Exception as e:
            return {"error": f"Invalid action: {str(e)}"}

        # Gather updated state
        state = engine._round_state
        next_player = state["next_player"]
        valid_actions = state["valid_actions"]
        board = state.get("community_card", [])
        pot = state["pot"]["main"]["amount"]

        return {
            "next_player": next_player,
            "valid_actions": valid_actions,
            "board": board,
            "pot": pot,
            "round_state": state
        }
