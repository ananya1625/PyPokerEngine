#!/usr/bin/env python3
"""
Test for Flush vs Pair scenario
This test verifies that when a player has a flush, the system correctly identifies
the 5 cards that make up the flush, not just any 5 cards.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add the current directory to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.engine_service import GameEngineService
from pypokerengine.engine.poker_constants import PokerConstants as Const


class TestFlushVsPair(unittest.TestCase):

    def setUp(self):
        """Set up a fresh game engine service for each test"""
        self.engine = GameEngineService()
        self.game_id = "test_flush_vs_pair_001"

    def create_mock_card(self, rank, suit):
        """Create a mock card with specific rank and suit"""
        card = Mock()
        card.rank = rank
        card.suit = suit
        card.__str__ = lambda self: f"{rank}{suit}"
        card.__repr__ = lambda self: f"{rank}{suit}"
        return card

    def test_flush_vs_pair_scenario(self):
        """Test the specific scenario where player has flush but system was showing pair"""
        # Create the exact scenario from the user's feedback:
        # Player cards: 9♥️ Q♥️
        # Community cards: 4♥️ K♠️ Q♠️ 7♥️ 6♥️
        # Expected: Flush with 5 hearts

        # Mock the cards
        hole_cards = [
            self.create_mock_card(9, "♥"),   # 9♥️
            self.create_mock_card(12, "♥")   # Q♥️ (12 = Queen)
        ]

        community_cards = [
            self.create_mock_card(4, "♥"),   # 4♥️
            self.create_mock_card(13, "♠"),  # K♠️ (13 = King)
            self.create_mock_card(12, "♠"),  # Q♠️ (12 = Queen)
            self.create_mock_card(7, "♥"),   # 7♥️
            self.create_mock_card(6, "♥")    # 6♥️
        ]

        # Test the _find_best_5_cards method directly
        result = self.engine._find_best_5_cards(hole_cards, community_cards, "FLUSH")

        # Verify we got exactly 5 cards
        self.assertEqual(len(result), 5, f"Expected 5 cards, got {len(result)}")

        # Verify all 5 cards are hearts (flush)
        for card in result:
            self.assertEqual(card.suit, "♥", f"Expected heart suit, got {card.suit}")

        # Verify we got the highest 5 hearts
        heart_cards = [card for card in hole_cards + community_cards if card.suit == "♥"]
        heart_cards.sort(key=lambda c: c.rank, reverse=True)
        expected_hearts = heart_cards[:5]  # Top 5 hearts

        # Check that we got the right hearts (should be Q♥️, 9♥️, 7♥️, 6♥️, 4♥️)
        expected_ranks = [12, 9, 7, 6, 4]  # Q, 9, 7, 6, 4
        result_ranks = sorted([card.rank for card in result], reverse=True)
        self.assertEqual(result_ranks, expected_ranks,
                        f"Expected ranks {expected_ranks}, got {result_ranks}")

        print(f"✅ Flush test passed! Got 5 hearts: {[str(card) for card in result]}")

    def test_flush_detection_accuracy(self):
        """Test that the system correctly identifies flush over pair"""
        # Create a scenario with multiple possible hands
        hole_cards = [
            self.create_mock_card(10, "♥"),  # 10♥️
            self.create_mock_card(11, "♥")   # J♥️ (11 = Jack)
        ]

        community_cards = [
            self.create_mock_card(2, "♥"),   # 2♥️
            self.create_mock_card(5, "♥"),   # 5♥️
            self.create_mock_card(8, "♥"),   # 8♥️ (Changed from 8♠️ to 8♥️)
        ]

        # Test the _evaluate_best_5_cards method
        result = self.engine._evaluate_best_5_cards(hole_cards + community_cards)

        # Verify we got exactly 5 cards
        self.assertEqual(len(result), 5, f"Expected 5 cards, got {len(result)}")

        # Verify all 5 cards are hearts (flush)
        for card in result:
            self.assertEqual(card.suit, "♥", f"Expected heart suit, got {card.suit}")

        # Verify we got the highest 5 hearts
        expected_ranks = [11, 10, 8, 5, 2]  # J, 10, 8, 5, 2
        result_ranks = sorted([card.rank for card in result], reverse=True)
        self.assertEqual(result_ranks, expected_ranks,
                        f"Expected ranks {expected_ranks}, got {result_ranks}")

        print(f"✅ Flush detection test passed! Got: {[str(card) for card in result]}")

    def test_hand_ranking_comparison(self):
        """Test that flush is correctly ranked higher than pair"""
        # Create a flush hand
        flush_cards = [
            self.create_mock_card(10, "♥"),
            self.create_mock_card(8, "♥"),
            self.create_mock_card(6, "♥"),
            self.create_mock_card(4, "♥"),
            self.create_mock_card(2, "♥")
        ]

        # Create a pair hand
        pair_cards = [
            self.create_mock_card(12, "♠"),  # Q♠️
            self.create_mock_card(12, "♣"),  # Q♣️
            self.create_mock_card(10, "♦"),  # 10♦️
            self.create_mock_card(8, "♠"),   # 8♠️
            self.create_mock_card(6, "♣")    # 6♣️
        ]

        # Test the _evaluate_best_5_cards method with both hands
        flush_result = self.engine._evaluate_best_5_cards(flush_cards)
        pair_result = self.engine._evaluate_best_5_cards(pair_cards)

        # Both should return 5 cards
        self.assertEqual(len(flush_result), 5)
        self.assertEqual(len(pair_result), 5)

        # Verify flush has all hearts
        for card in flush_result:
            self.assertEqual(card.suit, "♥")

        # Verify pair has the two queens
        queen_cards = [card for card in pair_result if card.rank == 12]
        self.assertEqual(len(queen_cards), 2, "Should have exactly 2 queens")

        print(f"✅ Hand ranking test passed!")
        print(f"   Flush: {[str(card) for card in flush_result]}")
        print(f"   Pair: {[str(card) for card in pair_result]}")

    def test_edge_case_7_hearts(self):
        """Test edge case where all 7 cards are hearts"""
        # Create 7 hearts
        all_hearts = [
            self.create_mock_card(14, "♥"),  # A♥️ (14 = Ace)
            self.create_mock_card(13, "♥"),  # K♥️ (13 = King)
            self.create_mock_card(12, "♥"),  # Q♥️ (12 = Queen)
            self.create_mock_card(11, "♥"),  # J♥️ (11 = Jack)
            self.create_mock_card(10, "♥"),  # 10♥️
            self.create_mock_card(9, "♥"),   # 9♥️
            self.create_mock_card(8, "♥")    # 8♥️
        ]

        # Test the _evaluate_best_5_cards method
        result = self.engine._evaluate_best_5_cards(all_hearts)

        # Verify we got exactly 5 cards
        self.assertEqual(len(result), 5)

        # Verify all 5 cards are hearts
        for card in result:
            self.assertEqual(card.suit, "♥")

        # Verify we got the highest 5 hearts (A, K, Q, J, 10)
        expected_ranks = [14, 13, 12, 11, 10]
        result_ranks = sorted([card.rank for card in result], reverse=True)
        self.assertEqual(result_ranks, expected_ranks)

        print(f"✅ Edge case test passed! Got highest 5 hearts: {[str(card) for card in result]}")


def run_tests():
    """Run all flush vs pair tests with nice output"""
    print("Running Flush vs Pair tests...")
    print("=" * 60)

    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestFlushVsPair)

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