from pypokerengine.engine.dealer import Dealer
from pypokerengine.engine.table import Table
from pypokerengine.engine.player import Player
from pypokerengine.engine.round_manager import RoundManager
from pypokerengine.engine.poker_constants import PokerConstants as Const
from .models import SetupPlayer
import random

class GameEngineService:
    def __init__(self):
        self.games = {}  # game_id → { dealer, table, players, status, round_state, current_state }

    def start_game(self, game_id, players):
        if len(players) < 2:
            return {"error": "At least 2 players required."}

        # Create dealer with proper configuration
        dealer = Dealer(
            small_blind_amount=1,
            initial_stack=max(p["stack"] for p in players),
            ante=0
        )

        # Register players with the dealer
        for p in players:
            player = SetupPlayer(user_id=p["user_id"], stack=p["stack"])
            dealer.register_player(p["user_id"], player)

        # Get the table from dealer
        table = dealer.table

        # Set blind positions
        try:
            # No need to calculate blind positions since we're handling them manually
            pass
        except Exception as e:
            return {"error": f"Failed to set up game: {str(e)}"}

        # Get dealer index for blind collection and position assignment
        dealer_index = table.dealer_btn

        # Manually deal cards and set up game state
        try:
            # Shuffle the deck
            table.deck.shuffle()

            # Deal hole cards to each player
            for player in table.seats.players:
                hole_cards = table.deck.draw_cards(2)
                player.add_holecard(hole_cards)

            # Collect blinds - use dealer_index directly for consistency
            small_blind_player = table.seats.players[dealer_index]  # Dealer is small blind
            big_blind_player = table.seats.players[(dealer_index + 1) % 2]  # Other player is big blind

            # Small blind
            sb_amount = 1
            small_blind_player.collect_bet(sb_amount)
            small_blind_player.add_action_history(Const.Action.SMALL_BLIND, sb_amount=sb_amount)
            small_blind_player.pay_info.update_by_pay(sb_amount)
            print(f"DEBUG: Small blind collected {sb_amount}, pay_info.amount now: {small_blind_player.pay_info.amount}")

            # Big blind
            bb_amount = sb_amount * 2
            big_blind_player.collect_bet(bb_amount)
            big_blind_player.add_action_history(Const.Action.BIG_BLIND, sb_amount=bb_amount)
            big_blind_player.pay_info.update_by_pay(bb_amount)
            print(f"DEBUG: Big blind collected {bb_amount}, pay_info.amount now: {big_blind_player.pay_info.amount}")

        except Exception as e:
            return {"error": f"Failed to deal cards and collect blinds: {str(e)}"}

                        # Assign positions based on dealer button
        # dealer_index is already defined above in the blind collection section

        # Update player positions - we'll handle this in the heads-up logic below
        # for i, player in enumerate(table.seats.players):
        #     if i == dealer_index:
        #         player.position = "dealer"
        #     elif i == sb_pos:
        #         player.position = "small_blind"
        #     elif i == bb_pos:
        #         player.position = "big_blind"
        #     else:
        #         player.position = "none"

        # In heads-up play, dealer is also small blind
        if len(table.seats.players) == 2:
            # Clear all positions first
            for player in table.seats.players:
                player.position = "none"

            # Assign correct positions for heads-up (0 and 1, not 1 and 2)
            table.seats.players[dealer_index].position = "small_blind"
            table.seats.players[(dealer_index + 1) % 2].position = "big_blind"

            # Debug final state
            print(f"DEBUG: Final positions and amounts:")
            for i, p in enumerate(table.seats.players):
                print(f"  Player {i}: position={p.position}, pay_info.amount={p.pay_info.amount}, stack={p.stack}")

        # Create a simple game state
        current_state = {
            "round_count": 1,
            "small_blind_amount": 1,
            "street": Const.Street.PREFLOP,
            "next_player": dealer_index,  # In heads-up preflop, small blind (dealer) acts first
            "players_acted": set(),  # Track which players have acted this street
            "table": table
        }

        # Store game state
        self.games[game_id] = {
            "dealer": dealer,
            "table": table,
            "players": table.seats.players,
            "status": "in_progress",
            "current_state": current_state,
            "messages": []
        }

        # Get current round state
        round_state = self._get_current_round_state(dealer, table, current_state)

        return {
            "game_id": game_id,
            "players": [
                {
                    "user_id": p.name,  # Using name as user_id
                    "hole_cards": p.hole_card,
                    "position": getattr(p, 'position', 'none'),
                    "stack": p.stack
                } for p in table.seats.players
            ],
            "round_state": round_state
        }

    def _get_current_round_state(self, dealer, table, state=None):
        """Extract current round state from dealer and table"""
        if state is None:
            state = {}

        return {
            "dealer_btn": table.dealer_btn,
            "sb_pos": 0,  # Hardcoded for heads-up - dealer is small blind
            "bb_pos": 1,  # Hardcoded for heads-up - other player is big blind
            "community_cards": table.get_community_card(),
            "pot": self._calculate_pot(table),
            "street": state.get("street", 0),
            "next_player": state.get("next_player", 0),
            "players": [
                {
                    "uuid": p.uuid,
                    "name": p.name,
                    "stack": p.stack,
                    "hole_cards": p.hole_card,
                    "is_active": p.is_active(),
                    "position": getattr(p, 'position', 'none')
                } for p in table.seats.players
            ]
        }

    def _calculate_pot(self, table):
        """Calculate total pot from all players"""
        total_pot = 0
        for player in table.seats.players:
            # This is simplified - you'd need to track actual bets
            pass
        return total_pot

    def apply_action(self, game_id, user_id, action, amount):
        game = self.games.get(game_id)
        if not game:
            return {"error": "Game not found"}

        dealer = game["dealer"]
        table = game["table"]
        current_state = game["current_state"]

        # Find the player by user_id
        player = None
        for p in table.seats.players:
            if p.name == user_id:
                player = p
                break

        if not player:
            return {"error": "Player not found"}

        # Check if it's this player's turn
        if current_state["next_player"] != table.seats.players.index(player):
            return {"error": "Not your turn"}

        # Apply the action manually instead of using RoundManager
        try:
            # Process the action based on type
            if action == "fold":
                player.pay_info.update_to_fold()
                player.add_action_history(Const.Action.FOLD)
            elif action == "call":
                # Calculate call amount (simplified)
                call_amount = self._calculate_call_amount(table, player)
                if call_amount > 0:
                    player.collect_bet(call_amount)
                    player.add_action_history(Const.Action.CALL, call_amount)
                    player.pay_info.update_by_pay(call_amount)
            elif action == "check":
                # Check is valid when player doesn't need to put in more chips
                call_amount = self._calculate_call_amount(table, player)
                print(f"DEBUG: Player {player.name} checking, call_amount needed: {call_amount}")
                if call_amount > 0:
                    return {"error": f"Cannot check - need to call {call_amount} chips"}
                # Check is equivalent to calling with 0 amount
                player.add_action_history(Const.Action.CALL, 0)
                print(f"DEBUG: Check action recorded for {player.name}")
            elif action == "raise":
                if amount <= 0:
                    return {"error": "Raise amount must be positive"}
                player.collect_bet(amount)
                player.add_action_history(Const.Action.RAISE, amount)
                player.pay_info.update_by_pay(amount)
            else:
                return {"error": f"Unknown action: {action}"}

            # Track that this player has acted
            current_state["players_acted"].add(table.seats.players.index(player))

            # Move to next player
            next_player_pos = self._get_next_active_player(table, current_state["next_player"])
            current_state["next_player"] = next_player_pos
            print(f"DEBUG: After action '{action}', next_player_pos: {next_player_pos}, player name: {table.seats.players[next_player_pos].name}")
            print(f"DEBUG: Players acted this street: {current_state['players_acted']}")

            # Check if current street is complete (all players have matched bets)
            street_complete = self._is_street_complete(table, current_state)
            print(f"DEBUG: Street complete check: {street_complete}")
            if street_complete:
                print(f"DEBUG: All players have matched bets, advancing street")

            # If street is complete, automatically advance to next street
            street_advanced = False
            if street_complete:
                street_advanced = self._advance_street_automatically(current_state, table)

            # Update game state
            game["current_state"] = current_state
            print(f"DEBUG: Updated game state - next_player: {current_state['next_player']}")

            # Update round state
            round_state = self._get_current_round_state(dealer, table, current_state)

            # Use the updated next_player from current_state, not the old next_player_pos
            final_next_player = current_state["next_player"]
            print(f"DEBUG: Returning result - next_player: {final_next_player}, current_state next_player: {current_state['next_player']}")
            return {
                "success": True,
                "round_state": round_state,
                "action_applied": action,
                "next_player": final_next_player,
                "street_complete": street_complete,
                "street_advanced": street_advanced,
                "current_street": current_state["street"]
            }

        except Exception as e:
            return {"error": f"Invalid action: {str(e)}"}

    def _is_street_complete(self, table, current_state):
        """Check if all active players have acted AND put in equal amounts for current street"""
        active_players = [p for p in table.seats.players if p.is_active()]

        if len(active_players) <= 1:
            return True  # Only one player left, street is complete

        # Check if all active players have acted this street
        active_player_indices = {i for i, p in enumerate(table.seats.players) if p.is_active()}
        if not active_player_indices.issubset(current_state.get("players_acted", set())):
            print(f"DEBUG: Not all players have acted. Active: {active_player_indices}, Acted: {current_state.get('players_acted', set())}")
            return False  # Not all players have acted

        # Get the highest bet amount for this street
        max_bet = max(p.pay_info.amount for p in active_players)

        # Check if all active players have matched
        for player in active_players:
            if player.pay_info.amount < max_bet:
                print(f"DEBUG: Player {player.name} has {player.pay_info.amount} chips, needs {max_bet}")
                return False  # Someone is behind

        print(f"DEBUG: Street complete - all players acted and matched bets")
        return True  # All players have acted AND matched

    def _advance_street_automatically(self, current_state, table):
        """Automatically advance to the next street when betting is complete"""
        current_street = current_state["street"]

        try:
            if current_street == Const.Street.PREFLOP:
                # Deal flop (3 community cards)
                for _ in range(3):
                    card = table.deck.draw_card()
                    table.add_community_card(card)
                current_state["street"] = Const.Street.FLOP
                current_state["next_player"] = (table.dealer_btn + 1) % 2  # Big blind acts first postflop
                current_state["players_acted"] = set()  # Reset for new street
                print(f"DEBUG: Advanced to FLOP, dealer_btn: {table.dealer_btn}, next_player: {current_state['next_player']}, player name: {table.seats.players[current_state['next_player']].name}")

            elif current_street == Const.Street.FLOP:
                # Deal turn (1 community card)
                card = table.deck.draw_card()
                table.add_community_card(card)
                current_state["street"] = Const.Street.TURN
                current_state["next_player"] = (table.dealer_btn + 1) % 2  # Big blind acts first postflop
                current_state["players_acted"] = set()  # Reset for new street

            elif current_street == Const.Street.TURN:
                # Deal river (1 community card)
                card = table.deck.draw_card()
                table.add_community_card(card)
                current_state["street"] = Const.Street.RIVER
                current_state["next_player"] = (table.dealer_btn + 1) % 2  # Big blind acts first postflop
                current_state["players_acted"] = set()  # Reset for new street

            elif current_street == Const.Street.RIVER:
                # Move to showdown
                current_state["street"] = Const.Street.SHOWDOWN
                current_state["next_player"] = (table.dealer_btn + 1) % 2  # Big blind acts first postflop
                current_state["players_acted"] = set()  # Reset for new street

            else:
                return False  # Already at final street

            return True  # Street was advanced

        except Exception as e:
            print(f"Error advancing street: {e}")
            return False



    def _calculate_call_amount(self, table, player):
        """Calculate how much the player needs to call"""
        # Find the highest bet amount among all active players
        active_players = [p for p in table.seats.players if p.is_active()]
        if not active_players:
            return 0

        max_bet = max(p.pay_info.amount for p in active_players)

        # Calculate how much this player needs to call
        player_contribution = player.pay_info.amount
        call_amount = max_bet - player_contribution

        return max(0, call_amount)  # Can't call negative amounts

    def _get_next_active_player(self, table, current_pos):
        """Get the next active player position"""
        players = table.seats.players
        next_pos = (current_pos + 1) % len(players)

        # Find next active player
        for _ in range(len(players)):
            if players[next_pos].is_active() and players[next_pos].stack > 0:
                return next_pos
            next_pos = (next_pos + 1) % len(players)

        return current_pos  # If no one else is active



    def get_state(self, game_id):
        game = self.games.get(game_id)
        if not game:
            return {"error": "Game not found"}

        dealer = game["dealer"]
        table = game["table"]
        current_state = game.get("current_state", {})

        round_state = self._get_current_round_state(dealer, table, current_state)
        return round_state

    def end_game(self, game_id):
        if game_id in self.games:
            del self.games[game_id]
            return {"message": f"Game {game_id} ended."}
        return {"error": "Game not found"}
