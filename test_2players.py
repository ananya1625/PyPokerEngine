#!/usr/bin/env python3
"""
2-Player Poker Engine Test
Run with: python3 test_2players.py
"""

import sys
import os
import unittest

# Add the current directory to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.engine_service import GameEngineService
from pypokerengine.engine.poker_constants import PokerConstants as Const


class Test2PlayerGame(unittest.TestCase):

    def setUp(self):
        """Set up a fresh game engine service for each test"""
        self.engine = GameEngineService()
        self.game_id = "test_game_001"

        # Create two test players
        self.players = [
            {"user_id": "player1", "stack": 100},
            {"user_id": "player2", "stack": 100}
        ]

    def test_start_game_2_players(self):
        """Test starting a 2-player game"""
        result = self.engine.start_game(self.game_id, self.players)

        # Check that game started successfully
        self.assertIn("game_id", result)
        self.assertEqual(result["game_id"], self.game_id)

        # Check that both players are in the game
        self.assertEqual(len(result["players"]), 2)

        # Check that players have hole cards
        for player in result["players"]:
            self.assertIn("hole_cards", player)
            self.assertEqual(len(player["hole_cards"]), 2)
            self.assertIn("position", player)
            self.assertIn("stack", player)

        # Check round state
        self.assertIn("round_state", result)
        round_state = result["round_state"]
        self.assertEqual(round_state["dealer_btn"], 0)  # First player is dealer
        self.assertEqual(round_state["sb_pos"], 0)  # Dealer is small blind in heads-up
        self.assertEqual(round_state["bb_pos"], 1)  # Other player is big blind
        self.assertEqual(round_state["street"], Const.Street.PREFLOP)

    def test_blind_collection(self):
        """Test that blinds are collected correctly"""
        result = self.engine.start_game(self.game_id, self.players)

        # Get the game state
        game = self.engine.games[self.game_id]
        table = game["table"]

        # Check that small blind (dealer) has 1 chip
        small_blind_player = table.seats.players[0]
        self.assertEqual(small_blind_player.pay_info.amount, 1)
        self.assertEqual(small_blind_player.stack, 99)  # 100 - 1

        # Check that big blind has 2 chips
        big_blind_player = table.seats.players[1]
        self.assertEqual(big_blind_player.pay_info.amount, 2)
        self.assertEqual(big_blind_player.stack, 98)  # 100 - 2

    def test_preflop_betting_round(self):
        """Test preflop betting round with fold"""
        result = self.engine.start_game(self.game_id, self.players)

        # Player 1 (small blind) folds
        action_result = self.engine.apply_action(self.game_id, "player1", "fold", 0)

        # Check that action was successful
        self.assertIn("success", action_result)
        self.assertTrue(action_result["success"])
        self.assertEqual(action_result["action_applied"], "fold")

        # Check that game moved to showdown (since one player folded)
        self.assertEqual(action_result["current_street"], Const.Street.SHOWDOWN)
        self.assertTrue(action_result["street_advanced"])

    def test_preflop_betting_round_call(self):
        """Test preflop betting round with call"""
        result = self.engine.start_game(self.game_id, self.players)

        # Player 1 (small blind) calls the big blind
        action_result = self.engine.apply_action(self.game_id, "player1", "call", 1)

        # Check that action was successful
        self.assertIn("success", action_result)
        self.assertTrue(action_result["success"])
        self.assertEqual(action_result["action_applied"], "call")

        # Check that it's now player 2's turn
        self.assertEqual(action_result["next_player"], 1)
        self.assertFalse(action_result["street_complete"])

    def test_preflop_betting_round_raise(self):
        """Test preflop betting round with raise"""
        result = self.engine.start_game(self.game_id, self.players)

        # Player 1 (small blind) raises to 5
        action_result = self.engine.apply_action(self.game_id, "player1", "raise", 5)

        # Check that action was successful
        self.assertIn("success", action_result)
        self.assertTrue(action_result["success"])
        self.assertEqual(action_result["action_applied"], "raise")

        # Check that it's now player 2's turn
        self.assertEqual(action_result["next_player"], 1)
        self.assertFalse(action_result["street_complete"])

    def test_complete_preflop_round(self):
        """Test completing the preflop round and advancing to flop"""
        result = self.engine.start_game(self.game_id, self.players)

        # Player 1 (small blind) calls the big blind
        action_result = self.engine.apply_action(self.game_id, "player1", "call", 1)
        self.assertTrue(action_result["success"])

        # Player 2 (big blind) checks (no more action needed)
        action_result = self.engine.apply_action(self.game_id, "player2", "check", 0)

        # Check that action was successful
        self.assertIn("success", action_result)
        self.assertTrue(action_result["success"])
        self.assertEqual(action_result["action_applied"], "check")

        # Check that street is complete and advanced to flop
        self.assertTrue(action_result["street_complete"])
        self.assertTrue(action_result["street_advanced"])
        self.assertEqual(action_result["current_street"], Const.Street.FLOP)

    def test_flop_betting_round(self):
        """Test flop betting round"""
        # Start game and complete preflop
        result = self.engine.start_game(self.game_id, self.players)
        self.engine.apply_action(self.game_id, "player1", "call", 1)
        self.engine.apply_action(self.game_id, "player2", "check", 0)

        # Get current state
        game = self.engine.games[self.game_id]
        current_state = game["current_state"]

        # Check that we're on the flop
        self.assertEqual(current_state["street"], Const.Street.FLOP)

        # Check that community cards were dealt
        table = game["table"]
        community_cards = table.get_community_card()
        self.assertEqual(len(community_cards), 3)  # Flop has 3 cards

        # Check that big blind acts first postflop
        self.assertEqual(current_state["next_player"], 1)  # Big blind acts first

    def test_turn_betting_round(self):
        """Test turn betting round"""
        # Start game and complete preflop and flop
        result = self.engine.start_game(self.game_id, self.players)
        self.engine.apply_action(self.game_id, "player1", "call", 1)
        self.engine.apply_action(self.game_id, "player2", "check", 0)

        # Complete flop (both players check)
        self.engine.apply_action(self.game_id, "player2", "check", 0)
        self.engine.apply_action(self.game_id, "player1", "check", 0)

        # Get current state
        game = self.engine.games[self.game_id]
        current_state = game["current_state"]

        # Check that we're on the turn
        self.assertEqual(current_state["street"], Const.Street.TURN)

        # Check that 4th community card was dealt
        table = game["table"]
        community_cards = table.get_community_card()
        self.assertEqual(len(community_cards), 4)  # Turn has 4 cards

    def test_river_betting_round(self):
        """Test river betting round"""
        # Start game and complete preflop, flop, and turn
        result = self.engine.start_game(self.game_id, self.players)
        self.engine.apply_action(self.game_id, "player1", "call", 1)
        self.engine.apply_action(self.game_id, "player2", "check", 0)

        # Complete flop (both players check)
        self.engine.apply_action(self.game_id, "player2", "check", 0)
        self.engine.apply_action(self.game_id, "player1", "check", 0)

        # Complete turn (both players check)
        self.engine.apply_action(self.game_id, "player2", "check", 0)
        self.engine.apply_action(self.game_id, "player1", "check", 0)

        # Get current state
        game = self.engine.games[self.game_id]
        current_state = game["current_state"]

        # Check that we're on the river
        self.assertEqual(current_state["street"], Const.Street.RIVER)

        # Check that 5th community card was dealt
        table = game["table"]
        community_cards = table.get_community_card()
        self.assertEqual(len(community_cards), 5)  # River has 5 cards

    def test_showdown_after_fold(self):
        """Test showdown when one player folds"""
        result = self.engine.start_game(self.game_id, self.players)

        # Player 1 folds
        action_result = self.engine.apply_action(self.game_id, "player1", "fold", 0)

        # Check that game moved to showdown
        self.assertEqual(action_result["current_street"], Const.Street.SHOWDOWN)

        # Get winning hand
        winning_hand = self.engine.get_winning_hand(self.game_id)
        self.assertIsNotNone(winning_hand)
        self.assertEqual(winning_hand["user_id"], "player2")  # Player 2 wins by default

    def test_showdown_after_complete_hand(self):
        """Test showdown after completing all betting rounds"""
        # Start game and complete all streets
        result = self.engine.start_game(self.game_id, self.players)
        self.engine.apply_action(self.game_id, "player1", "call", 1)
        self.engine.apply_action(self.game_id, "player2", "check", 0)

        # Complete flop (both players check)
        self.engine.apply_action(self.game_id, "player2", "check", 0)
        self.engine.apply_action(self.game_id, "player1", "check", 0)

        # Complete turn (both players check)
        self.engine.apply_action(self.game_id, "player2", "check", 0)
        self.engine.apply_action(self.game_id, "player1", "check", 0)

        # Complete river (both players check)
        self.engine.apply_action(self.game_id, "player2", "check", 0)
        action_result = self.engine.apply_action(self.game_id, "player1", "check", 0)

        # Check that game moved to showdown
        self.assertEqual(action_result["current_street"], Const.Street.SHOWDOWN)

        # Get winning hand
        winning_hand = self.engine.get_winning_hand(self.game_id)
        self.assertIsNotNone(winning_hand)
        self.assertIn("cards", winning_hand)
        self.assertIn("rank", winning_hand)
        self.assertIn("user_id", winning_hand)

    def test_invalid_actions(self):
        """Test invalid actions are rejected"""
        result = self.engine.start_game(self.game_id, self.players)

        # Test invalid action type
        action_result = self.engine.apply_action(self.game_id, "player1", "invalid_action", 0)
        self.assertIn("error", action_result)

        # Test action out of turn
        action_result = self.engine.apply_action(self.game_id, "player2", "call", 0)
        self.assertIn("error", action_result)
        self.assertIn("Not your turn", action_result["error"])

    def test_game_state_retrieval(self):
        """Test retrieving game state"""
        result = self.engine.start_game(self.game_id, self.players)

        # Get current state
        state = self.engine.get_state(self.game_id)

        # Check that state contains expected fields
        self.assertIn("dealer_btn", state)
        self.assertIn("sb_pos", state)
        self.assertIn("bb_pos", state)
        self.assertIn("community_cards", state)
        self.assertIn("pot", state)
        self.assertIn("street", state)
        self.assertIn("next_player", state)
        self.assertIn("players", state)

        # Check that players array has correct structure
        self.assertEqual(len(state["players"]), 2)
        for player in state["players"]:
            self.assertIn("uuid", player)
            self.assertIn("name", player)
            self.assertIn("stack", player)
            self.assertIn("hole_cards", player)
            self.assertIn("is_active", player)
            self.assertIn("position", player)

    def test_end_game(self):
        """Test ending a game"""
        result = self.engine.start_game(self.game_id, self.players)

        # Verify game exists
        self.assertIn(self.game_id, self.engine.games)

        # End the game
        end_result = self.engine.end_game(self.game_id)
        self.assertIn("message", end_result)

        # Verify game was removed
        self.assertNotIn(self.game_id, self.engine.games)

    def test_multiple_games(self):
        """Test running multiple games simultaneously"""
        game_id_1 = "game_001"
        game_id_2 = "game_002"

        # Start first game
        result1 = self.engine.start_game(game_id_1, self.players)
        self.assertEqual(result1["game_id"], game_id_1)

        # Start second game
        result2 = self.engine.start_game(game_id_2, self.players)
        self.assertEqual(result2["game_id"], game_id_2)

        # Verify both games exist
        self.assertIn(game_id_1, self.engine.games)
        self.assertIn(game_id_2, self.engine.games)

        # Clean up
        self.engine.end_game(game_id_1)
        self.engine.end_game(game_id_2)


def run_tests():
    """Run all 2-player tests with nice output"""
    print("Running 2-player poker engine tests...")
    print("=" * 60)

    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(Test2PlayerGame)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")

    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)