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
            big_blind_player.add_action_history(Const.Action.BIG_BLIND, sb_amount=sb_amount)  # Pass small blind amount, not big blind amount
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

                # Check if only one player remains (all others folded)
                active_players = [p for p in table.seats.players if p.is_active()]
                print(f"DEBUG: After fold - active players: {[p.name for p in active_players]}")
                if len(active_players) == 1:
                    print(f"DEBUG: Only one player remains after fold - {active_players[0].name} wins")
                    # Set up showdown results for the single winner
                    winner = active_players[0]
                    current_state["street"] = Const.Street.SHOWDOWN
                    current_state["next_player"] = None

                    # Create showdown results for the single winner
                    from pypokerengine.engine.hand_evaluator import HandEvaluator
                    hole_cards = winner.hole_card
                    community_cards = table.get_community_card()

                    # Get the best 5-card hand for the winner
                    hand_info = HandEvaluator.gen_hand_rank_info(hole_cards, community_cards)
                    hand_rank = hand_info["hand"]["strength"]
                    best_cards = self._find_best_5_cards(hole_cards, community_cards, hand_rank)

                    current_state["showdown_results"] = {
                        "winners": [winner],
                        "hand_info": [{"uuid": winner.uuid, "hand": hand_info}],
                        "prize_map": {winner.uuid: sum(p.pay_info.amount for p in table.seats.players)}
                    }

                    # Update game state
                    game["current_state"] = current_state

                    # Return early with showdown results
                    round_state = self._get_current_round_state(dealer, table, current_state)
                    return {
                        "success": True,
                        "round_state": round_state,
                        "action_applied": action,
                        "next_player": None,
                        "street_complete": True,
                        "street_advanced": True,
                        "current_street": current_state["street"]
                    }
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
                # Calculate the add_amount (increment over previous bet)
                current_bet = player.pay_info.amount
                add_amount = amount - current_bet
                player.add_action_history(Const.Action.RAISE, amount, add_amount)
                player.pay_info.update_by_pay(amount)
            else:
                return {"error": f"Unknown action: {action}"}

            # Track that this player has acted
            current_state["players_acted"].add(table.seats.players.index(player))

            # Check if both players are all-in (special case)
            both_all_in = all(p.stack == 0 for p in table.seats.players if p.is_active())
            if both_all_in:
                print(f"DEBUG: Both players are all-in, completing street immediately")
                # Mark both players as acted (in case the other player hasn't been marked yet)
                current_state["players_acted"].add(0)
                current_state["players_acted"].add(1)
                street_complete = True
                street_advanced = self._advance_street_automatically(current_state, table)
                # The next_player is already set correctly in _advance_street_automatically
            else:
                # Move to next player
                next_player_pos = self._get_next_active_player(table, current_state["next_player"])
                current_state["next_player"] = next_player_pos
                print(f"DEBUG: After action '{action}', next_player_pos: {next_player_pos}, player name: {table.seats.players[next_player_pos].name}")
                print(f"DEBUG: Players acted this street: {current_state['players_acted']}")
                print(f"DEBUG: Player stacks - U123: {table.seats.players[0].stack}, U456: {table.seats.players[1].stack}")

                # Check if current street is complete (all players have matched bets)
                street_complete = self._is_street_complete(table, current_state)
                print(f"DEBUG: Street complete check: {street_complete}")
                if street_complete:
                    print(f"DEBUG: All players have matched bets, advancing street")

                # If street is complete, automatically advance to next street
                street_advanced = False
                if street_complete:
                    street_advanced = self._advance_street_automatically(current_state, table)
                    # The next_player is already set correctly in _advance_street_automatically
                    # No need to call _get_next_active_player again

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

        print(f"DEBUG: _is_street_complete - active_players: {[p.name for p in active_players]}")
        print(f"DEBUG: _is_street_complete - player stacks: {[p.stack for p in active_players]}")

        if len(active_players) <= 1:
            print(f"DEBUG: Street complete - only one player left")
            return True  # Only one player left, street is complete

        # For heads-up, we need both players to have acted
        if len(active_players) == 2:
            active_player_indices = {i for i, p in enumerate(table.seats.players) if p.is_active()}
            players_acted = current_state.get("players_acted", set())

            # Check if both players have acted
            if not active_player_indices.issubset(players_acted):
                print(f"DEBUG: Not all players have acted. Active: {active_player_indices}, Acted: {players_acted}")
                return False  # Not all players have acted

            # Get the highest bet amount for this street
            max_bet = max(p.pay_info.amount for p in active_players)
            print(f"DEBUG: _is_street_complete - max_bet: {max_bet}")

            # Check if all active players have matched
            for player in active_players:
                if player.pay_info.amount < max_bet:
                    print(f"DEBUG: Player {player.name} has {player.pay_info.amount} chips, needs {max_bet}")
                    return False  # Someone is behind

            # Special case: if all players are all-in (stack = 0), street is complete
            all_all_in = all(p.stack == 0 for p in active_players)
            if all_all_in:
                print(f"DEBUG: Street complete - all players are all-in")
                return True

            print(f"DEBUG: Street complete - all players acted and matched")
            return True  # All players have acted AND matched

        # For more than 2 players, use the original logic
        active_player_indices = {i for i, p in enumerate(table.seats.players) if p.is_active()}
        if not active_player_indices.issubset(current_state.get("players_acted", set())):
            print(f"DEBUG: Not all players have acted. Active: {active_player_indices}, Acted: {current_state.get('players_acted', set())}")
            return False  # Not all players have acted

        # Get the highest bet amount for this street
        max_bet = max(p.pay_info.amount for p in active_players)
        print(f"DEBUG: _is_street_complete - max_bet: {max_bet}")

        # Check if all active players have matched
        for player in active_players:
            if player.pay_info.amount < max_bet:
                print(f"DEBUG: Player {player.name} has {player.pay_info.amount} chips, needs {max_bet}")
                return False  # Someone is behind

        # Special case: if all players are all-in (stack = 0), street is complete
        all_all_in = all(p.stack == 0 for p in active_players)
        if all_all_in:
            print(f"DEBUG: Street complete - all players are all-in")
            return True

        print(f"DEBUG: Street complete - all players acted and matched")
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
                # Postflop: Big blind acts first in heads-up
                current_state["next_player"] = (table.dealer_btn + 1) % 2  # Big blind acts first postflop
                current_state["players_acted"] = set()  # Reset for new street
                print(f"DEBUG: Advanced to FLOP, dealer_btn: {table.dealer_btn}, next_player: {current_state['next_player']}, player name: {table.seats.players[current_state['next_player']].name}")

            elif current_street == Const.Street.FLOP:
                # Deal turn (1 community card)
                card = table.deck.draw_card()
                table.add_community_card(card)
                current_state["street"] = Const.Street.TURN
                # Postflop: Big blind acts first in heads-up
                current_state["next_player"] = (table.dealer_btn + 1) % 2  # Big blind acts first postflop
                current_state["players_acted"] = set()  # Reset for new street
                print(f"DEBUG: Advanced to TURN, dealer_btn: {table.dealer_btn}, next_player: {current_state['next_player']}, player name: {table.seats.players[current_state['next_player']].name}")

            elif current_street == Const.Street.TURN:
                # Deal river (1 community card)
                card = table.deck.draw_card()
                table.add_community_card(card)
                current_state["street"] = Const.Street.RIVER
                # Postflop: Big blind acts first in heads-up
                current_state["next_player"] = (table.dealer_btn + 1) % 2  # Big blind acts first postflop
                current_state["players_acted"] = set()  # Reset for new street
                print(f"DEBUG: Advanced to RIVER, dealer_btn: {table.dealer_btn}, next_player: {current_state['next_player']}, player name: {table.seats.players[current_state['next_player']].name}")

            elif current_street == Const.Street.RIVER:
                # Move to showdown - evaluate hands and determine winner
                current_state["street"] = Const.Street.SHOWDOWN
                current_state["next_player"] = None  # No next player during showdown
                current_state["players_acted"] = set()  # Reset for new street

                # Evaluate hands and determine winner
                from pypokerengine.engine.game_evaluator import GameEvaluator
                winners, hand_info, prize_map = GameEvaluator.judge(table)

                # Store showdown results
                current_state["showdown_results"] = {
                    "winners": winners,
                    "hand_info": hand_info,
                    "prize_map": prize_map
                }

                print(f"DEBUG: Advanced to SHOWDOWN, winners: {[w.name for w in winners]}")

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

        # For heads-up, simply alternate between players
        if len(players) == 2:
            return (current_pos + 1) % 2

        # For more than 2 players, find next active player
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

    def get_winning_hand(self, game_id):
        """Get winning hand information if the hand is over"""
        game = self.games.get(game_id)
        if not game:
            return None

        current_state = game["current_state"]
        if current_state.get("street") != Const.Street.SHOWDOWN:
            return None

        showdown_results = current_state.get("showdown_results")
        if not showdown_results:
            return None

        winners = showdown_results["winners"]
        hand_info = showdown_results["hand_info"]

        if not winners or not hand_info:
            return None

        # Get the first winner (assuming single winner for simplicity)
        winner = winners[0]

        # Find the winner's hand info
        winner_hand_info = None
        for info in hand_info:
            if info["uuid"] == winner.uuid:
                winner_hand_info = info
                break

        if not winner_hand_info:
            return None

        # Get the best 5 cards that make up the winning hand
        from pypokerengine.engine.hand_evaluator import HandEvaluator

        # Get the winner's hole cards and community cards
        hole_cards = winner.hole_card
        community_cards = game["table"].get_community_card()

                                        # Find the best 5-card hand combination
        hand_info = HandEvaluator.gen_hand_rank_info(hole_cards, community_cards)
        print(f"DEBUG: Hand info: {hand_info}")

        # Extract the hand rank
        hand_rank = hand_info["hand"]["strength"]
        print(f"DEBUG: Hand rank: {hand_rank}")

                # Find the exact 5 cards that make up the winning hand
        best_cards = self._find_best_5_cards(hole_cards, community_cards, hand_rank)
        print(f"DEBUG: Best cards: {[str(card) for card in best_cards]}")
        print(f"DEBUG: Hand rank: {hand_rank}")
        print(f"DEBUG: Winner: {winner.name}")

        return {
            "cards": [str(card) for card in best_cards],
            "rank": hand_rank,
            "user_id": winner.name
        }

    def _find_best_5_cards(self, hole_cards, community_cards, hand_rank):
        """Find the exact 5 cards that make up the winning hand"""
        all_cards = hole_cards + community_cards

        if hand_rank == "STRAIGHTFLUSH":
            return self._find_straight_flush_cards(all_cards)
        elif hand_rank == "FOURCARD":
            return self._find_four_card_cards(all_cards)
        elif hand_rank == "FULLHOUSE":
            return self._find_full_house_cards(all_cards)
        elif hand_rank == "FLUSH":
            return self._find_flush_cards(all_cards)
        elif hand_rank == "STRAIGHT":
            return self._find_straight_cards(all_cards)
        elif hand_rank == "THREECARD":
            return self._find_three_card_cards(all_cards)
        elif hand_rank == "TWOPAIR":
            return self._find_two_pair_cards(all_cards)
        elif hand_rank == "ONEPAIR":
            return self._find_one_pair_cards(all_cards)
        else:  # HIGH_CARD
            return self._find_high_card_cards(all_cards)

    def _find_straight_flush_cards(self, cards):
        """Find the 5 cards that make a straight flush"""
        # Group cards by suit
        suits = {}
        for card in cards:
            suit = card.suit
            if suit not in suits:
                suits[suit] = []
            suits[suit].append(card)

        # Find the suit with the most cards
        best_suit = max(suits.keys(), key=lambda s: len(suits[s]))
        suit_cards = suits[best_suit]

        # Find the highest straight in this suit
        return self._find_straight_cards(suit_cards)

    def _find_four_card_cards(self, cards):
        """Find the 5 cards that make four of a kind"""
        # Count cards by rank
        rank_counts = {}
        for card in cards:
            rank = card.rank
            if rank not in rank_counts:
                rank_counts[rank] = []
            rank_counts[rank].append(card)

        # Find the highest rank with 4 cards
        four_rank = None
        for rank in sorted(rank_counts.keys(), reverse=True):
            card_list = rank_counts[rank]
            if len(card_list) >= 4:
                four_rank = rank
                break

        if four_rank:
            four_cards = rank_counts[four_rank][:4]  # Take 4 cards of the four
            # Find the highest kicker
            kickers = [card for card in cards if card.rank != four_rank]
            kickers.sort(key=lambda c: c.rank, reverse=True)
            if kickers:
                four_cards.append(kickers[0])  # Add the highest kicker
            return four_cards

        return cards[:5]  # Fallback

    def _find_full_house_cards(self, cards):
        """Find the 5 cards that make a full house"""
        # Count cards by rank
        rank_counts = {}
        for card in cards:
            rank = card.rank
            if rank not in rank_counts:
                rank_counts[rank] = []
            rank_counts[rank].append(card)

        # Find ranks with 3 and 2 cards
        three_rank = None
        two_rank = None

        # Find the highest three of a kind first
        for rank in sorted(rank_counts.keys(), reverse=True):
            card_list = rank_counts[rank]
            if len(card_list) >= 3 and three_rank is None:
                three_rank = rank
                break

        # Find the highest pair (excluding the three of a kind rank)
        for rank in sorted(rank_counts.keys(), reverse=True):
            card_list = rank_counts[rank]
            if len(card_list) >= 2 and rank != three_rank and two_rank is None:
                two_rank = rank
                break

        if three_rank and two_rank:
            three_cards = rank_counts[three_rank][:3]
            two_cards = rank_counts[two_rank][:2]
            return three_cards + two_cards

        return cards[:5]  # Fallback

    def _find_flush_cards(self, cards):
        """Find the 5 cards that make a flush"""
        # Group cards by suit
        suits = {}
        for card in cards:
            suit = card.suit
            if suit not in suits:
                suits[suit] = []
            suits[suit].append(card)

        # Find the suit with the most cards
        best_suit = max(suits.keys(), key=lambda s: len(suits[s]))
        suit_cards = suits[best_suit]

        # Sort by rank (highest first) and take top 5
        suit_cards.sort(key=lambda c: c.rank, reverse=True)
        return suit_cards[:5]

    def _find_straight_cards(self, cards):
        """Find the 5 cards that make a straight"""
        # Get unique ranks and sort them
        unique_ranks = sorted(list(set(card.rank for card in cards)), reverse=True)

        # Look for 5 consecutive ranks, starting from the highest possible straight
        for i in range(len(unique_ranks) - 4):
            # Check if we have 5 consecutive ranks
            start_rank = unique_ranks[i]
            consecutive_ranks = [start_rank]

            for j in range(1, 5):
                if i + j < len(unique_ranks) and unique_ranks[i + j] == start_rank - j:
                    consecutive_ranks.append(unique_ranks[i + j])
                else:
                    break

            if len(consecutive_ranks) == 5:
                # Found a straight! Now get the actual cards
                straight_cards = []
                # Sort consecutive ranks in descending order for proper card selection
                consecutive_ranks.sort(reverse=True)
                for rank in consecutive_ranks:
                    # Find the highest card of this rank
                    cards_of_rank = [card for card in cards if card.rank == rank]
                    cards_of_rank.sort(key=lambda c: c.rank, reverse=True)
                    straight_cards.append(cards_of_rank[0])
                return straight_cards

        # If no straight found, return highest 5 cards
        sorted_cards = sorted(cards, key=lambda c: c.rank, reverse=True)
        return sorted_cards[:5]

    def _find_three_card_cards(self, cards):
        """Find the 5 cards that make three of a kind"""
        # Count cards by rank
        rank_counts = {}
        for card in cards:
            rank = card.rank
            if rank not in rank_counts:
                rank_counts[rank] = []
            rank_counts[rank].append(card)

        # Find the highest rank with 3 cards
        three_rank = None
        for rank in sorted(rank_counts.keys(), reverse=True):
            card_list = rank_counts[rank]
            if len(card_list) >= 3:
                three_rank = rank
                break

        if three_rank:
            three_cards = rank_counts[three_rank][:3]  # Take 3 cards of the three
            # Find the 2 highest kickers
            kickers = [card for card in cards if card.rank != three_rank]
            kickers.sort(key=lambda c: c.rank, reverse=True)
            three_cards.extend(kickers[:2])  # Add the 2 highest kickers
            return three_cards

        return cards[:5]  # Fallback

    def _find_two_pair_cards(self, cards):
        """Find the 5 cards that make two pair"""
        # Count cards by rank
        rank_counts = {}
        for card in cards:
            rank = card.rank
            if rank not in rank_counts:
                rank_counts[rank] = []
            rank_counts[rank].append(card)

        # Find ranks with 2 cards
        pairs = []
        for rank, card_list in rank_counts.items():
            if len(card_list) >= 2:
                pairs.append((rank, card_list[:2]))

        # Sort pairs by rank (highest first)
        pairs.sort(key=lambda p: p[0], reverse=True)

        if len(pairs) >= 2:
            # Take the two highest pairs
            result = pairs[0][1] + pairs[1][1]  # Add both pairs
            # Find the highest kicker
            kickers = [card for card in cards if card.rank not in [p[0] for p in pairs[:2]]]
            kickers.sort(key=lambda c: c.rank, reverse=True)
            if kickers:
                result.append(kickers[0])  # Add the highest kicker
            return result

        return cards[:5]  # Fallback

    def _find_one_pair_cards(self, cards):
        """Find the 5 cards that make one pair"""
        # Count cards by rank
        rank_counts = {}
        for card in cards:
            rank = card.rank
            if rank not in rank_counts:
                rank_counts[rank] = []
            rank_counts[rank].append(card)

        # Find the highest rank with 2 cards
        pair_rank = None
        for rank in sorted(rank_counts.keys(), reverse=True):
            card_list = rank_counts[rank]
            if len(card_list) >= 2:
                pair_rank = rank
                break

        if pair_rank:
            pair_cards = rank_counts[pair_rank][:2]  # Take 2 cards of the pair
            # Find the 3 highest kickers
            kickers = [card for card in cards if card.rank != pair_rank]
            kickers.sort(key=lambda c: c.rank, reverse=True)
            pair_cards.extend(kickers[:3])  # Add the 3 highest kickers
            return pair_cards

        return cards[:5]  # Fallback

    def _find_high_card_cards(self, cards):
        """Find the 5 highest cards"""
        # Sort by rank (highest first) and take top 5
        sorted_cards = sorted(cards, key=lambda c: c.rank, reverse=True)
        return sorted_cards[:5]

    def end_game(self, game_id):
        if game_id in self.games:
            del self.games[game_id]
            return {"message": f"Game {game_id} ended."}
        return {"error": "Game not found"}
