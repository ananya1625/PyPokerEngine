from flask import Flask, request, jsonify
from engine.engine_service import GameEngineService

app = Flask(__name__)
engine = GameEngineService()

@app.route("/start-game", methods=["POST"])
def start_game():
    data = request.json
    game_id = data.get("game_id")
    players = data.get("players", [])

    if not game_id or not players:
        return jsonify({"error": "Missing game_id or players"}), 400

    # Start the game using the engine
    result = engine.start_game(game_id, players)

    if "error" in result:
        return jsonify(result), 400

    # Get the game state from the engine
    game = engine.games[game_id]
    table = game["table"]
    current_state = game["current_state"]

    # Transform the response to match the expected format
    transformed_response = {
        "game_id": result["game_id"],
        "min_bet": 0,  # Will be calculated based on call amount
        "next_player": result["round_state"]["players"][result["round_state"]["next_player"]]["name"],
        "players": [],
        "pot": [],
        "total_pot": 3,  # Small blind (1) + Big blind (2)
        "valid_actions": []
    }

    # Transform players data using PyPokerEngine's built-in methods
    for i, player in enumerate(result["players"]):
        # Convert hole cards to string format using PyPokerEngine's __str__ method
        hole_cards = [str(card) for card in player["hole_cards"]]

        # Convert position to numeric format
        position_map = {"dealer": 0, "small_blind": 0, "big_blind": 1, "none": 2}
        position = position_map.get(player["position"], 2)

        transformed_response["players"].append({
            "hole_cards": hole_cards,
            "position": position,
            "stack": player["stack"],
            "user_id": player["user_id"]
        })

    # Create pot structure using PyPokerEngine's PayInfo
    for i, player in enumerate(table.seats.players):
        pot_amount = player.pay_info.amount if hasattr(player, 'pay_info') else 0

        transformed_response["pot"].append({
            "amount": pot_amount,
            "user_id": player.name
        })

    # Calculate total pot from individual contributions
    transformed_response["total_pot"] = sum(p["amount"] for p in transformed_response["pot"])

        # Generate valid actions using our corrected calculation
    next_player_pos = current_state["next_player"]
    next_player = table.seats.players[next_player_pos]

    # Calculate valid actions manually to get correct amounts
    active_players = [p for p in table.seats.players if p.is_active()]
    max_bet = max(p.pay_info.amount for p in active_players) if active_players else 0

        # Calculate call amount for the next player
    # In heads-up play, we need to calculate what the small blind will need to call
    if len(table.seats.players) == 2:
        # Debug position values
        print(f"DEBUG: next_player.position={next_player.position}")
        print(f"DEBUG: next_player.name={next_player.name}")
        for i, p in enumerate(table.seats.players):
            print(f"DEBUG: Player {i} position={p.position}, name={p.name}")

        # Find small blind and big blind players
        small_blind_player = None
        big_blind_player = None
        for p in table.seats.players:
            if p.position == "small_blind":
                small_blind_player = p
            elif p.position == "big_blind":
                big_blind_player = p

        if small_blind_player and big_blind_player:
            # Calculate what small blind needs to call (big blind amount - small blind amount)
            call_amount = big_blind_player.pay_info.amount - small_blind_player.pay_info.amount
            print(f"DEBUG: Small blind needs to call: {big_blind_player.pay_info.amount} - {small_blind_player.pay_info.amount} = {call_amount}")
            print(f"DEBUG: Small blind player: {small_blind_player.name}, pot: {small_blind_player.pay_info.amount}, stack: {small_blind_player.stack}")
            print(f"DEBUG: Big blind player: {big_blind_player.name}, pot: {big_blind_player.pay_info.amount}, stack: {big_blind_player.stack}")
            print(f"DEBUG: Final call_amount: {call_amount}")
        else:
            call_amount = 0
            print(f"DEBUG: Could not find both blind players")
    else:
        # For more than 2 players, use the old logic
        player_contribution = next_player.pay_info.amount
        call_amount = max(0, max_bet - player_contribution)

    call_amount = max(0, call_amount)  # Can't call negative amounts



    # Calculate raise amounts
    min_raise = max_bet + 1  # Must raise at least 1 more than current bet
    max_raise = next_player.stack

        # Add valid actions
    transformed_response["valid_actions"].append({"action": "fold", "amount": 0})
    transformed_response["valid_actions"].append({"action": "call", "amount": call_amount})
    transformed_response["valid_actions"].append({
        "action": "raise",
        "amount": {"max": max_raise, "min": min_raise}
    })

    # Set min_bet to match the call amount
    transformed_response["min_bet"] = call_amount

    return jsonify(transformed_response)

@app.route("/action", methods=["POST"])
def action():
    data = request.json
    game_id = data.get("game_id")
    user_id = data.get("user_id")
    action = data.get("action")
    amount = data.get("amount", 0)

    if not all([game_id, user_id, action]):
        return jsonify({"error": "Missing required fields"}), 400

    result = engine.apply_action(game_id, user_id, action, amount)

    if "error" in result:
        return jsonify(result), 400

    # Start with the internal response fields
    transformed_response = {
        "success": result.get("success", True),
        "action_applied": result.get("action_applied", action),
        "next_player": result.get("next_player", 0),
        "should_advance_street": result.get("should_advance_street", False),
        "current_street": result.get("current_street", 0),
        "round_state": {}  # We'll transform this below
    }

    # Add client-facing fields
    if "round_state" in result:
        round_state = result["round_state"]

        # Get the game to access table for pot calculation
        game = engine.games.get(game_id)
        if game:
            table = game["table"]
            current_state = game["current_state"]

            # Transform next_player from index to player name
            next_player_pos = result.get("next_player", 0)
            next_player = table.seats.players[next_player_pos]
            transformed_response["next_player"] = next_player.name
            print(f"DEBUG: Action response - next_player_pos: {next_player_pos}, next_player.name: {next_player.name}")
            print(f"DEBUG: Table player order - Player 0: {table.seats.players[0].name}, Player 1: {table.seats.players[1].name}")

            # Extract board (community cards)
            community_cards = round_state.get("community_cards", [])
            transformed_response["board"] = [str(card) for card in community_cards]

            # Transform pot to match /start-game format
            pot = []
            for player in table.seats.players:
                pot_amount = player.pay_info.amount if hasattr(player, 'pay_info') else 0
                pot.append({
                    "amount": pot_amount,
                    "user_id": player.name
                })
            transformed_response["pot"] = pot

            # Calculate total pot
            transformed_response["total_pot"] = sum(p["amount"] for p in pot)

            # Set street
            transformed_response["street"] = round_state.get("street", 0)

            # Generate valid actions for the next player
            active_players = [p for p in table.seats.players if p.is_active()]
            max_bet = max(p.pay_info.amount for p in active_players) if active_players else 0

            # Calculate call amount for the next player
            if len(table.seats.players) == 2:
                # Find small blind and big blind players
                small_blind_player = None
                big_blind_player = None
                for p in table.seats.players:
                    if p.position == "small_blind":
                        small_blind_player = p
                    elif p.position == "big_blind":
                        big_blind_player = p

                if small_blind_player and big_blind_player:
                    # Calculate what small blind needs to call (big blind amount - small blind amount)
                    call_amount = big_blind_player.pay_info.amount - small_blind_player.pay_info.amount
                else:
                    call_amount = 0
            else:
                # For more than 2 players, use the old logic
                player_contribution = next_player.pay_info.amount
                call_amount = max(0, max_bet - player_contribution)

            call_amount = max(0, call_amount)  # Can't call negative amounts

            # Calculate raise amounts
            min_raise = max_bet + 1  # Must raise at least 1 more than current bet
            max_raise = next_player.stack

            # Add valid actions
            valid_actions = []
            valid_actions.append({"action": "fold", "amount": 0})

            # If call amount is 0, it's a check, otherwise it's a call
            if call_amount == 0:
                valid_actions.append({"action": "check", "amount": 0})
            else:
                valid_actions.append({"action": "call", "amount": call_amount})

            valid_actions.append({
                "action": "raise",
                "amount": {"max": max_raise, "min": min_raise}
            })

            transformed_response["valid_actions"] = valid_actions

    # Transform round_state to handle Card objects
    if "round_state" in result:
        round_state = result["round_state"]

        # Transform players data to handle Card objects
        transformed_players = []
        for player in round_state.get("players", []):
            # Convert hole cards to string format
            hole_cards = [str(card) for card in player.get("hole_cards", [])]

            transformed_players.append({
                "name": player.get("name", ""),
                "stack": player.get("stack", 0),
                "hole_cards": hole_cards,
                "is_active": player.get("is_active", True),
                "position": player.get("position", "none")
            })

        # Transform community cards to string format
        community_cards = [str(card) for card in round_state.get("community_cards", [])]

        # Move players to top level
        transformed_response["players"] = transformed_players

        transformed_response["round_state"] = {
            "dealer_btn": round_state.get("dealer_btn", 0),
            "sb_pos": round_state.get("sb_pos", 0),
            "bb_pos": round_state.get("bb_pos", 0),
            "community_cards": community_cards,
            "pot": round_state.get("pot", 0),
            "street": round_state.get("street", 0),
            "next_player": round_state.get("next_player", 0)
        }

    return jsonify(transformed_response)

@app.route("/state/<game_id>", methods=["GET"])
def get_state(game_id):
    result = engine.get_state(game_id)

    if "error" in result:
        return jsonify(result), 400

    # Get the game to access table for pot calculation
    game = engine.games.get(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 400

    table = game["table"]

    # Transform the response to handle Card objects
    transformed_response = {
        "dealer_btn": result.get("dealer_btn", 0),
        "sb_pos": result.get("sb_pos", 0),
        "bb_pos": result.get("bb_pos", 0),
        "community_cards": [],
        "pot": [],  # Will be calculated from player.pay_info.amount
        "street": result.get("street", 0),
        "next_player": "",  # Will be transformed from index to player name
        "players": []
    }

    # Transform community cards to string format
    if "community_cards" in result:
        transformed_response["community_cards"] = [str(card) for card in result["community_cards"]]

    # Transform players data to handle Card objects and calculate pot
    for player in result.get("players", []):
        # Convert hole cards to string format
        hole_cards = [str(card) for card in player.get("hole_cards", [])]

        transformed_response["players"].append({
            "name": player.get("name", ""),
            "stack": player.get("stack", 0),
            "hole_cards": hole_cards,
            "is_active": player.get("is_active", True),
            "position": player.get("position", "none")
        })

    # Transform next_player from index to player name
    next_player_pos = result.get("next_player", 0)
    if 0 <= next_player_pos < len(table.seats.players):
        next_player = table.seats.players[next_player_pos]
        transformed_response["next_player"] = next_player.name
    else:
        transformed_response["next_player"] = ""

    # Calculate pot from player.pay_info.amount (matching /start-game format)
    for i, player in enumerate(table.seats.players):
        pot_amount = player.pay_info.amount if hasattr(player, 'pay_info') else 0
        transformed_response["pot"].append({
            "amount": pot_amount,
            "user_id": player.name
        })

    # Calculate total pot
    transformed_response["total_pot"] = sum(p["amount"] for p in transformed_response["pot"])

    return jsonify(transformed_response)

@app.route("/end-game/<game_id>", methods=["POST"])
def end_game(game_id):
    result = engine.end_game(game_id)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
