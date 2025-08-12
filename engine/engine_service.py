from pypokerengine.api.emulator import Emulator
from pypokerengine.engine.data_encoder import DataEncoder
from .models import SetupPlayer
import random

# Poker Game Constants
SMALL_BLIND_AMOUNT = 1
BIG_BLIND_AMOUNT = 2
MIN_PLAYERS = 2
MAX_PLAYERS = 10
MIN_RAISE_AMOUNT = 1  # Minimum raise above current bet

# Player Position Constants
DEALER_POSITION = 0
SMALL_BLIND_POSITION = 1
BIG_BLIND_POSITION = 2

# Street Constants (PyPokerEngine values)
STREET_PREFLOP = 0
STREET_FLOP = 1
STREET_TURN = 2
STREET_RIVER = 3
STREET_SHOWDOWN = 4
STREET_FINISHED = 5

# Game Flow Constants
FIRST_PLAYER_INDEX = 0

class GameEngineService:
    def __init__(self):
        self.games = {}  # game_id → { engine, players, status }

    def start_game(self, game_id, players):
        if len(players) < MIN_PLAYERS:
            return {"error": f"At least {MIN_PLAYERS} players required."}
        if len(players) > MAX_PLAYERS:
            return {"error": f"Maximum {MAX_PLAYERS} players allowed."}

        random.shuffle(players)

        # Create emulator and set game rules
        emulator = Emulator()
        emulator.set_game_rule(
            player_num=len(players),
            max_round=10,
            small_blind_amount=SMALL_BLIND_AMOUNT,
            ante_amount=0
        )

        # Set blind structure to match our game rules
        emulator.set_blind_structure({})

        player_objs = []
        players_info = {}

        for p in players:
            player = SetupPlayer(user_id=p["user_id"], stack=p["stack"])
            emulator.register_player(p["user_id"], player)
            player_objs.append(player)
            players_info[p["user_id"]] = {"stack": p["stack"], "name": p["user_id"]}

                # Generate initial game state
        game_state = emulator.generate_initial_game_state(players_info)

        # We need to start the round to get hole cards, but handle it carefully
        # Start the round but don't process actions yet
        game_state, events = emulator.start_new_round(game_state)

        # Assign positions based on shuffled player order
        dealer_index = 0
        sb_index = 1 % len(player_objs)
        bb_index = 2 % len(player_objs)

        for i, p in enumerate(player_objs):
            if i == dealer_index:
                p.position = DEALER_POSITION  # dealer - acts first after blinds
                print(f"DEBUG: Set {p.user_id} position to {DEALER_POSITION} (dealer)")
            elif i == sb_index:
                p.position = SMALL_BLIND_POSITION  # small blind - acts second
                print(f"DEBUG: Set {p.user_id} position to {SMALL_BLIND_POSITION} (small blind)")
            elif i == bb_index:
                p.position = BIG_BLIND_POSITION  # big blind - acts third
                print(f"DEBUG: Set {p.user_id} position to {BIG_BLIND_POSITION} (big blind)")
            else:
                p.position = i  # subsequent players in order (0-indexed)
                print(f"DEBUG: Set {p.user_id} position to {i}")

        # Update hole cards and stacks from the table's Player objects
        table = game_state["table"]
        for i, player in enumerate(player_objs):
            table_player = table.seats.players[i]
            player.hole_card = [str(card) for card in table_player.hole_card]
            # Update stack to reflect blinds posted
            player.stack = table_player.stack

        # Calculate pot contributions from the blinds posted
        pot_contributions = []
        for i, player in enumerate(table.seats.players):
            # Include ALL players with their current contributions (including 0)
            pot_contributions.append({
                "user_id": player_objs[i].user_id,
                "amount": player.pay_info.amount
            })

        # Calculate total pot amount
        total_pot = sum(contribution["amount"] for contribution in pot_contributions)

        self.games[game_id] = {
            "emulator": emulator,
            "game_state": game_state,
            "players": player_objs,
            "status": "in_progress",
            "pot_contributions": pot_contributions  # Track individual pot contributions
        }

        # Debug: Print final positions before returning
        print("DEBUG: Final positions before return:")
        for p in player_objs:
            print(f"  {p.user_id}: position={p.position} (type: {type(p.position)})")

        # Calculate the current bet amount and what each player needs to call
        current_bet = max(contribution["amount"] for contribution in pot_contributions) if pot_contributions else 0

        # Generate valid actions for the dealer (position 0)
        dealer_id = player_objs[0].user_id  # Dealer is always at position 0
        dealer_contribution = next((cont["amount"] for cont in pot_contributions if cont["user_id"] == dealer_id), 0)

        raw_actions = emulator.generate_possible_actions(game_state)
        valid_actions = []

        for action in raw_actions:
            if action["action"] == "fold":
                # Fold always costs 0
                valid_actions.append({"action": "fold", "amount": 0})
            elif action["action"] == "call":
                # Calculate the actual amount the dealer needs to put in from their stack
                call_amount = current_bet - dealer_contribution
                if call_amount == 0:
                    # No more money needed = check
                    valid_actions.append({"action": "check", "amount": 0})
                else:
                    # More money needed = call
                    valid_actions.append({"action": "call", "amount": call_amount})
            elif action["action"] == "raise":
                # Keep the raise action as is (frontend needs to specify amount)
                valid_actions.append(action)

        return {
            "game_id": game_id,
            "players": [
                {
                    "user_id": p.user_id,
                    "hole_cards": p.hole_card,
                    "position": p.position,
                    "stack": p.stack
                } for p in player_objs
            ],
            "pot": pot_contributions,
            "total_pot": total_pot,
            "min_bet": BIG_BLIND_AMOUNT,  # Big blind amount (minimum bet for the game)
            "next_player": dealer_id,  # Dealer goes first
            "valid_actions": valid_actions
        }

    def apply_action(self, game_id, user_id, action, amount):
        game = self.games.get(game_id)
        if not game:
            return {"error": "Game not found"}

        emulator = game["emulator"]
        game_state = game["game_state"]

        try:
            print(f"DEBUG: Processing action for user {user_id}, action {action}, amount {amount}")
            print(f"DEBUG: Current street: {game_state.get('street')}, next_player: {game_state.get('next_player')}")

            # Validate action requirements
            if action == "raise" and amount <= 0:
                return {"error": "Raise action requires a positive amount"}
            elif action in ["fold", "call"] and amount != 0:
                print(f"DEBUG: Ignoring amount {amount} for {action} action - using calculated amount")

            # Get player objects for reference
            player_objs = game["players"]

            # If this is the first action, start the round first
            if game_state.get("next_player") is None:
                print(f"DEBUG: Starting first round for game {game_id}")
                game_state, events = emulator.start_new_round(game_state)
                # Update the game state
                game["game_state"] = game_state

                        # Now apply the action
            print(f"DEBUG: About to apply action: {action} with amount: {amount}")
            print(f"DEBUG: Current pot before action: {[p.pay_info.amount for p in game_state['table'].seats.players]}")

                        # For raise and call actions, we need to calculate the total bet amount
            if action in ["raise", "call"]:
                # Find the current player's current contribution
                current_player_contribution = 0
                for i, player in enumerate(game_state["table"].seats.players):
                    if player_objs[i].user_id == user_id:
                        current_player_contribution = player.pay_info.amount
                        break

                if action == "raise":
                    # Calculate total bet amount (current contribution + raise amount)
                    total_bet_amount = current_player_contribution + amount
                    print(f"DEBUG: Raise calculation - current contribution: {current_player_contribution}, raise by: {amount}, total bet: {total_bet_amount}")
                else:  # call
                    # Calculate total bet amount needed to call
                    current_bet = max(p.pay_info.amount for p in game_state["table"].seats.players)
                    total_bet_amount = current_bet
                    print(f"DEBUG: Call calculation - current contribution: {current_player_contribution}, current bet: {current_bet}, total bet: {total_bet_amount}")

                # Apply the action with the total bet amount
                updated_state, events = emulator.apply_action(game_state, action, total_bet_amount)
            else:
                # For fold, use the amount as is
                updated_state, events = emulator.apply_action(game_state, action, amount)

            print(f"DEBUG: Action applied, new street: {updated_state.get('street')}, next_player: {updated_state.get('next_player')}")
            print(f"DEBUG: Pot after action: {[p.pay_info.amount for p in updated_state['table'].seats.players]}")
            print(f"DEBUG: Events from emulator: {events}")

            # If the street is FINISHED, we need to continue to the next street
            if updated_state.get("street") == STREET_FINISHED:  # FINISHED
                print(f"DEBUG: Street is FINISHED, advancing to next street")
                # This means the betting round is complete, move to next street
                # We'll handle this by updating the state manually
                current_street = game_state.get("street", 0)
                next_street = current_street + 1

                # PyPokerEngine streets: 0=preflop, 1=flop, 2=turn, 3=river, 4=showdown, 5=finished
                # If we're going beyond river (street 3), we should go to showdown (street 4)
                if next_street > STREET_RIVER:
                    next_street = STREET_SHOWDOWN  # showdown

                updated_state["street"] = next_street
                updated_state["next_player"] = FIRST_PLAYER_INDEX  # Start with first player for next street

                print(f"DEBUG: Street advanced from {current_street} to {next_street}")

                # CRITICAL: Preserve the pot information - don't let it reset
                # Calculate current pot before PyPokerEngine resets it
                table = game_state["table"]

                # Track individual player contributions to the pot
                pot_contributions = []
                for i, player in enumerate(table.seats.players):
                    # Include ALL players with their current contributions (including 0)
                    pot_contributions.append({
                        "user_id": player_objs[i].user_id,
                        "amount": player.pay_info.amount
                    })

                # Store the pot contributions in the updated state
                updated_state["pot_contributions"] = pot_contributions

                # Calculate total pot amount
                current_pot_amount = sum(contribution["amount"] for contribution in pot_contributions)

                print(f"DEBUG: Preserving pot contributions: {pot_contributions}")
                print(f"DEBUG: Total pot amount: {current_pot_amount} when advancing from street {game_state.get('street')} to {updated_state['street']}")

                # Also store the pot contributions in our game tracking
                if "pot_contributions" not in game:
                    game["pot_contributions"] = []
                game["pot_contributions"].extend(pot_contributions)
                print(f"DEBUG: Accumulated pot contributions: {game['pot_contributions']}")

            # Update the game state
            game["game_state"] = updated_state
        except Exception as e:
            return {"error": f"Invalid action: {str(e)}"}

        # Extract information from the updated game state
        table = updated_state["table"]

        # CRITICAL: Extract updated pot information from the new game state
        # The emulator.apply_action() should have updated the player pay_info amounts
        updated_table = updated_state["table"]
        pot_contributions = []

        # Get the updated player objects from the game to match user_ids
        for i, player in enumerate(updated_table.seats.players):
            # Include ALL players with their current contributions (including 0)
            pot_contributions.append({
                "user_id": player_objs[i].user_id,
                "amount": player.pay_info.amount
            })

        print(f"DEBUG: Updated pot contributions from emulator: {pot_contributions}")

        # Update our game tracking with the new pot contributions
        game["pot_contributions"] = pot_contributions

        # Calculate the current bet amount and what each player needs to call
        current_bet = max(contribution["amount"] for contribution in pot_contributions) if pot_contributions else 0
        print(f"DEBUG: Current bet amount: {current_bet}")

        # Get the next player's user_id instead of just the index
        next_player_index = updated_state.get("next_player")
        next_player_id = None

        # Debug logging and safety check
        print(f"DEBUG: next_player_index={next_player_index}, player_objs length={len(player_objs)}")
        print(f"DEBUG: Player objects: {[p.user_id for p in player_objs]}")

        if next_player_index is not None and 0 <= next_player_index < len(player_objs):
            next_player_id = player_objs[next_player_index].user_id
            print(f"DEBUG: Successfully got next_player_id: {next_player_id}")
        else:
            print(f"WARNING: Invalid next_player_index: {next_player_index}")
            # If the index is invalid, try to find the next active player
            for i, player in enumerate(player_objs):
                print(f"DEBUG: Checking player {i}: {player.user_id}, stack: {player.stack}")
                if player.stack > 0:  # Find first player with chips
                    next_player_id = player.user_id
                    print(f"DEBUG: Found active player: {next_player_id}")
                    break
            else:
                print(f"WARNING: No active players found!")
                next_player_id = None

        # Calculate total pot amount
        total_pot = sum(contribution["amount"] for contribution in pot_contributions)

        # Generate valid actions with correct amounts
        raw_actions = emulator.generate_possible_actions(updated_state)
        valid_actions = []

        for action in raw_actions:
            if action["action"] == "fold":
                # Fold always costs 0
                valid_actions.append({"action": "fold", "amount": 0})
            elif action["action"] == "call":
                # Calculate the actual amount the player needs to put in from their stack
                player_contribution = next((cont["amount"] for cont in pot_contributions if cont["user_id"] == next_player_id), 0)
                call_amount = current_bet - player_contribution
                if call_amount == 0:
                    # No more money needed = check
                    valid_actions.append({"action": "check", "amount": 0})
                else:
                    # More money needed = call
                    valid_actions.append({"action": "call", "amount": call_amount})
            elif action["action"] == "raise":
                # Keep the raise action as is (frontend needs to specify amount)
                valid_actions.append(action)

        print(f"DEBUG: Generated valid actions: {valid_actions}")

        return {
            "next_player": next_player_id,
            "valid_actions": valid_actions,
            "board": [str(card) for card in table.get_community_card()],
            "pot": pot_contributions,
            "total_pot": total_pot,
            "street": updated_state.get("street"),
            "round_count": updated_state.get("round_count")
        }

    def get_state(self, game_id):
        game = self.games.get(game_id)
        if not game:
            return {"error": "Game not found"}

        emulator = game["emulator"]
        game_state = game["game_state"]
        player_objs = game["players"]  # Get player objects from stored game data

        # If the round hasn't started yet, return initial state
        if game_state.get("next_player") is None:
            return {
                "next_player": None,
                "valid_actions": [],
                "board": [],
                "pot": [],
                "total_pot": 0,
                "street": STREET_PREFLOP,  # preflop
                "round_count": 0,
                "message": "Round not started yet. Make first action to begin."
            }

        # If we're waiting for the first action, return the initial round state
        if game_state.get("street") == STREET_PREFLOP and game_state.get("pot", {}).get("main", {}).get("amount", 0) == 0:
            # This is the initial state after starting the round but before first action
            table = game_state["table"]

            # Calculate pot contributions from player pay info
            pot_contributions = []
            for i, player in enumerate(table.seats.players):
                # Include ALL players with their current contributions (including 0)
                pot_contributions.append({
                    "user_id": player_objs[i].user_id,
                    "amount": player.pay_info.amount
                })

            # Calculate total pot amount
            total_pot = sum(contribution["amount"] for contribution in pot_contributions)

            # Calculate the current bet amount and what each player needs to call
            current_bet = max(contribution["amount"] for contribution in pot_contributions) if pot_contributions else 0

            # Generate valid actions with correct amounts
            raw_actions = emulator.generate_possible_actions(game_state)
            valid_actions = []

            for action in raw_actions:
                if action["action"] == "fold":
                    # Fold always costs 0
                    valid_actions.append({"action": "fold", "amount": 0})
                elif action["action"] == "call":
                    # Calculate the actual amount the player needs to put in from their stack
                    player_contribution = next((cont["amount"] for cont in pot_contributions if cont["user_id"] == player_objs[0].user_id), 0)
                    call_amount = current_bet - player_contribution
                    if call_amount == 0:
                        # No more money needed = check
                        valid_actions.append({"action": "check", "amount": 0})
                    else:
                        # More money needed = call
                        valid_actions.append({"action": "call", "amount": call_amount})
                elif action["action"] == "raise":
                    # Keep the raise action as is (frontend needs to specify amount)
                    valid_actions.append(action)

            return {
                "next_player": player_objs[0].user_id,  # First player to act
                "valid_actions": valid_actions,
                "board": [],
                "pot": pot_contributions,  # Use calculated pot contributions
                "total_pot": total_pot,
                "street": STREET_PREFLOP,  # preflop
                "round_count": 1,
                "message": "Round started. Waiting for first action."
            }

        table = game_state["table"]

        # Extract current pot information from the game state
        pot_contributions = []
        for i, player in enumerate(table.seats.players):
            # Include ALL players with their current contributions (including 0)
            pot_contributions.append({
                "user_id": player_objs[i].user_id,
                "amount": player.pay_info.amount
            })

        print(f"DEBUG: Current pot contributions from game state: {pot_contributions}")

        # Calculate the current bet amount and what each player needs to call
        current_bet = max(contribution["amount"] for contribution in pot_contributions) if pot_contributions else 0
        print(f"DEBUG: Current bet amount: {current_bet}")

        # Get the next player's user_id instead of just the index
        next_player_index = game_state.get("next_player")
        next_player_id = None

        # Debug logging and safety check
        print(f"DEBUG: next_player_index={next_player_index}, player_objs length={len(player_objs)}")
        print(f"DEBUG: Player objects: {[p.user_id for p in player_objs]}")

        if next_player_index is not None and 0 <= next_player_index < len(player_objs):
            next_player_id = player_objs[next_player_index].user_id
            print(f"DEBUG: Successfully got next_player_id: {next_player_id}")
        else:
            print(f"WARNING: Invalid next_player_index: {next_player_index}")
            # If the index is invalid, try to find the next active player
            for i, player in enumerate(player_objs):
                print(f"DEBUG: Checking player {i}: {player.user_id}, stack: {player.stack}")
                if player.stack > 0:  # Find first player with chips
                    next_player_id = player.user_id
                    print(f"DEBUG: Found active player: {next_player_id}")
                    break
            else:
                print(f"WARNING: No active players found!")
                next_player_id = None

        # Calculate total pot amount
        total_pot = sum(contribution["amount"] for contribution in pot_contributions)

        # Generate valid actions with correct amounts
        raw_actions = emulator.generate_possible_actions(game_state)
        valid_actions = []

        for action in raw_actions:
            if action["action"] == "fold":
                # Fold always costs 0
                valid_actions.append({"action": "fold", "amount": 0})
            elif action["action"] == "call":
                # Calculate the actual amount the player needs to put in from their stack
                player_contribution = next((cont["amount"] for cont in pot_contributions if cont["user_id"] == next_player_id), 0)
                call_amount = current_bet - player_contribution
                if call_amount == 0:
                    # No more money needed = check
                    valid_actions.append({"action": "check", "amount": 0})
                else:
                    # More money needed = call
                    valid_actions.append({"action": "call", "amount": call_amount})
            elif action["action"] == "raise":
                # Keep the raise action as is (frontend needs to specify amount)
                valid_actions.append(action)

        print(f"DEBUG: Generated valid actions: {valid_actions}")

        return {
            "next_player": next_player_id,
            "valid_actions": valid_actions,
            "board": [str(card) for card in table.get_community_card()],
            "pot": pot_contributions,
            "total_pot": total_pot,
            "street": game_state.get("street"),
            "round_count": game_state.get("round_count")
        }

    def end_game(self, game_id):
        if game_id in self.games:
            del self.games[game_id]
            return {"message": f"Game {game_id} ended."}
        return {"error": "Game not found"}
