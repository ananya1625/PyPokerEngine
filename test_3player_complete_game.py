#!/usr/bin/env python3
"""
Complete 3-Player Poker Game Test
This test simulates a full poker hand with 3 players from start to showdown.
"""

import requests
import json
import time
from typing import Dict, Any

class PokerGameTester:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.game_id = "test_3p_complete"
        self.session = requests.Session()

    def log(self, message: str):
        """Log messages with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def make_request(self, endpoint: str, data: Dict[str, Any] = None, method: str = "POST") -> Dict[str, Any]:
        """Make HTTP request and return JSON response"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = self.session.get(url)
            else:
                response = self.session.post(url, json=data, headers={"Content-Type": "application/json"})

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Request failed: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            self.log(f"❌ JSON decode failed: {e}")
            return {"error": "Invalid JSON response"}

    def start_game(self) -> bool:
        """Start a new 3-player game"""
        self.log("🎮 Starting 3-player poker game...")

        data = {
            "game_id": self.game_id,
            "players": [
                {"user_id": "player1", "stack": 1000},
                {"user_id": "player2", "stack": 1000},
                {"user_id": "player3", "stack": 1000}
            ]
        }

        response = self.make_request("/start-game", data)

        if "error" in response:
            self.log(f"❌ Failed to start game: {response['error']}")
            return False

        self.log(f"✅ Game started successfully!")
        self.log(f"   Game ID: {response['game_id']}")
        self.log(f"   Next Player: {response['next_player']}")
        self.log(f"   Min Bet: {response['min_bet']}")
        self.log(f"   Total Pot: {response['total_pot']}")

        # Log player positions and stacks
        for player in response['players']:
            self.log(f"   {player['user_id']}: position={player['position']}, stack={player['stack']}")

        # Log pot contributions
        for pot_entry in response['pot']:
            self.log(f"   Pot: {pot_entry['user_id']} contributed {pot_entry['amount']} chips")

        return True

    def get_game_state(self) -> Dict[str, Any]:
        """Get current game state"""
        response = self.make_request(f"/state/{self.game_id}", method="GET")
        return response

    def make_action(self, user_id: str, action: str, amount: int = 0) -> bool:
        """Make a player action"""
        self.log(f"🎯 {user_id} {action.upper()}s" + (f" {amount}" if amount > 0 else ""))

        data = {
            "game_id": self.game_id,
            "user_id": user_id,
            "action": action,
            "amount": amount
        }

        response = self.make_request("/action", data)

        if "error" in response:
            self.log(f"❌ Action failed: {response['error']}")
            return False

        self.log(f"✅ Action successful!")
        if "next_player" in response:
            self.log(f"   Next Player: {response['next_player']}")
        if "street_complete" in response:
            self.log(f"   Street Complete: {response['street_complete']}")
        if "street_advanced" in response:
            self.log(f"   Street Advanced: {response['street_advanced']}")

        return True

    def play_preflop(self) -> bool:
        """Play through the preflop betting round"""
        self.log("\n🃏 === PREFLOP ROUND ===")

        # Player 1 (UTG) calls the big blind
        if not self.make_action("player1", "call", 2):
            return False

        # Player 2 (small blind) calls the additional 1 chip
        if not self.make_action("player2", "call", 1):
            return False

        # Player 3 (big blind) checks (no action needed, already posted)
        if not self.make_action("player3", "check"):
            return False

        self.log("✅ Preflop betting complete!")
        return True

    def play_flop(self) -> bool:
        """Play through the flop betting round"""
        self.log("\n🃏 === FLOP ROUND ===")

        # Get current state to see who acts first
        state = self.get_game_state()
        if "error" in state:
            self.log(f"❌ Failed to get game state: {state['error']}")
            return False

        # Player 1 (dealer) acts first postflop
        if not self.make_action("player1", "check"):
            return False

        # Player 2 (small blind) bets 50
        if not self.make_action("player2", "raise", 50):
            return False

        # Player 3 (big blind) folds
        if not self.make_action("player3", "fold"):
            return False

        # Player 1 calls the 50 bet
        if not self.make_action("player1", "call", 50):
            return False

        self.log("✅ Flop betting complete!")
        return True

    def play_turn(self) -> bool:
        """Play through the turn betting round"""
        self.log("\n🃏 === TURN ROUND ===")

        # Player 1 (dealer) acts first
        if not self.make_action("player1", "check"):
            return False

        # Player 2 bets 100
        if not self.make_action("player2", "raise", 100):
            return False

        # Player 1 calls the 100 bet
        if not self.make_action("player1", "call", 100):
            return False

        self.log("✅ Turn betting complete!")
        return True

    def play_river(self) -> bool:
        """Play through the river betting round"""
        self.log("\n🃏 === RIVER ROUND ===")

        # Player 1 (dealer) acts first
        if not self.make_action("player1", "check"):
            return False

        # Player 2 bets 200
        if not self.make_action("player2", "raise", 200):
            return False

        # Player 1 calls the 200 bet
        if not self.make_action("player1", "call", 200):
            return False

        self.log("✅ River betting complete!")
        return True

    def check_showdown(self) -> bool:
        """Check the showdown results"""
        self.log("\n🃏 === SHOWDOWN ===")

        # Get final game state
        state = self.get_game_state()
        if "error" in state:
            self.log(f"❌ Failed to get final state: {state['error']}")
            return False

        self.log("✅ Hand complete! Final state:")
        self.log(f"   Total Pot: {state.get('total_pot', 'N/A')}")
        self.log(f"   Street: {state.get('street', 'N/A')}")

        # Log final player stacks
        for player in state.get('players', []):
            self.log(f"   {player['user_id']}: stack={player['stack']}")

        return True

    def end_game(self) -> bool:
        """End the game"""
        self.log("\n🏁 Ending game...")

        data = {"game_id": self.game_id}
        response = self.make_request("/end-game", data)

        if "error" in response:
            self.log(f"❌ Failed to end game: {response['error']}")
            return False

        self.log("✅ Game ended successfully!")
        return True

    def run_complete_game(self) -> bool:
        """Run the complete 3-player poker game"""
        self.log("🚀 Starting Complete 3-Player Poker Game Test")
        self.log("=" * 50)

        try:
            # Start the game
            if not self.start_game():
                return False

            # Play through all betting rounds
            if not self.play_preflop():
                return False

            if not self.play_flop():
                return False

            if not self.play_turn():
                return False

            if not self.play_river():
                return False

            # Check showdown
            if not self.check_showdown():
                return False

            # End the game
            if not self.end_game():
                return False

            self.log("\n🎉 Complete game test finished successfully!")
            return True

        except Exception as e:
            self.log(f"❌ Test failed with exception: {e}")
            return False

def main():
    """Main test runner"""
    print("🎯 3-Player Poker Game Complete Test")
    print("=" * 50)

    tester = PokerGameTester()
    success = tester.run_complete_game()

    if success:
        print("\n✅ All tests passed! The 3-player poker game is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the logs above for details.")

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())