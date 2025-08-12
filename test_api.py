#!/usr/bin/env python3
"""
Test file for PyPokerEngine API endpoints
Run this file to test all the poker game functionality
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:3000"
GAME_ID = "TEST_GAME_001"

def print_separator(title):
    """Print a nice separator with title"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_request(method, endpoint, data=None):
    """Print the request being made"""
    print(f"\n🔵 {method} {endpoint}")
    if data:
        print(f"📤 Request Data: {json.dumps(data, indent=2)}")

def print_response(response):
    """Print the response details"""
    print(f"📥 Status: {response.status_code}")
    try:
        response_data = response.json()
        print(f"📥 Response: {json.dumps(response_data, indent=2)}")
        return response_data
    except json.JSONDecodeError:
        print(f"📥 Response: {response.text}")
        return None

def test_start_game():
    """Test starting a new game"""
    print_separator("STARTING NEW GAME")

    data = {
        "game_id": GAME_ID,
        "players": [
            {"user_id": "U123", "stack": 100},
            {"user_id": "U456", "stack": 100},
            {"user_id": "U789", "stack": 100}
        ]
    }

    print_request("POST", "/start-game", data)
    response = requests.post(f"{BASE_URL}/start-game", json=data)
    result = print_response(response)

    # Validate response
    if result and "game_id" in result:
        print("✅ Game started successfully!")
        print(f"   - Game ID: {result['game_id']}")
        print(f"   - Players: {len(result['players'])}")

        # Check that hole cards are populated
        for player in result['players']:
            if player['hole_cards']:
                print(f"   - {player['user_id']}: {player['hole_cards']} ({player['position']})")
            else:
                print(f"   ⚠️  {player['user_id']}: No hole cards!")

        return True
    else:
        print("❌ Failed to start game")
        return False

def test_get_initial_state():
    """Test getting the initial game state"""
    print_separator("GETTING INITIAL GAME STATE")

    print_request("GET", f"/state/{GAME_ID}")
    response = requests.get(f"{BASE_URL}/state/{GAME_ID}")
    result = print_response(response)

    # Validate response
    if result and "next_player" in result:
        print("✅ Initial state retrieved successfully!")
        print(f"   - Next player: {result['next_player']}")
        print(f"   - Street: {result['street']} (0=preflop)")
        print(f"   - Pot: {result['pot']}")
        print(f"   - Board: {result['board']}")
        print(f"   - Valid actions: {len(result['valid_actions'])} actions available")

        return True
    else:
        print("❌ Failed to get initial state")
        return False

def test_player_action(user_id, action, amount=0):
    """Test a player making an action"""
    print_separator(f"PLAYER {user_id} ACTION: {action.upper()}")

    data = {
        "game_id": GAME_ID,
        "user_id": user_id,
        "action": action,
        "amount": amount
    }

    print_request("POST", "/action", data)
    response = requests.post(f"{BASE_URL}/action", json=data)
    result = print_response(response)

    # Validate response
    if result and "next_player" in result:
        print(f"✅ Action successful! Next player: {result['next_player']}")
        print(f"   - Street: {result['street']}")
        print(f"   - Pot: {result['pot']}")
        print(f"   - Board: {result['board']}")
        print(f"   - Valid actions: {len(result['valid_actions'])} actions available")

        return True
    else:
        print("❌ Action failed")
        return False

def test_get_state():
    """Test getting current game state"""
    print_separator("GETTING CURRENT GAME STATE")

    print_request("GET", f"/state/{GAME_ID}")
    response = requests.get(f"{BASE_URL}/state/{GAME_ID}")
    result = print_response(response)

    if result:
        print("✅ State retrieved successfully!")
        return True
    else:
        print("❌ Failed to get state")
        return False

def test_end_game():
    """Test ending the game"""
    print_separator("ENDING GAME")

    print_request("POST", f"/end-game/{GAME_ID}")
    response = requests.post(f"{BASE_URL}/end-game/{GAME_ID}")
    result = print_response(response)

    if result and "message" in result:
        print("✅ Game ended successfully!")
        return True
    else:
        print("❌ Failed to end game")
        return False

def run_full_game_simulation():
    """Run a complete poker hand simulation"""
    print_separator("RUNNING FULL POKER HAND SIMULATION")

    # Start the game
    if not test_start_game():
        return False

    time.sleep(1)  # Small delay

    # Get initial state
    if not test_get_initial_state():
        return False

    time.sleep(1)

    # Preflop betting round
    print_separator("PREFLOP BETTING ROUND")

    # Player 1 (U456) - Dealer - Call
    if not test_player_action("U456", "call", 0):
        return False
    time.sleep(0.5)

    # Player 2 (U123) - Small Blind - Call
    if not test_player_action("U123", "call", 0):
        return False
    time.sleep(0.5)

    # Player 3 (U789) - Big Blind - Check
    if not test_player_action("U789", "call", 0):
        return False
    time.sleep(0.5)

    # Check state after preflop
    if not test_get_state():
        return False
    time.sleep(1)

    # Flop betting round
    print_separator("FLOP BETTING ROUND")

    # All players check
    if not test_player_action("U456", "call", 0):
        return False
    time.sleep(0.5)

    if not test_player_action("U123", "call", 0):
        return False
    time.sleep(0.5)

    if not test_player_action("U789", "call", 0):
        return False
    time.sleep(0.5)

    # Check state after flop
    if not test_get_state():
        return False
    time.sleep(1)

    # Turn betting round
    print_separator("TURN BETTING ROUND")

    # All players check
    if not test_player_action("U456", "call", 0):
        return False
    time.sleep(0.5)

    if not test_player_action("U123", "call", 0):
        return False
    time.sleep(0.5)

    if not test_player_action("U789", "call", 0):
        return False
    time.sleep(0.5)

    # Check state after turn
    if not test_get_state():
        return False
    time.sleep(1)

    # River betting round
    print_separator("RIVER BETTING ROUND")

    # All players check
    if not test_player_action("U456", "call", 0):
        return False
    time.sleep(0.5)

    if not test_player_action("U123", "call", 0):
        return False
    time.sleep(0.5)

    if not test_player_action("U789", "call", 0):
        return False
    time.sleep(0.5)

    # Final state check
    if not test_get_state():
        return False
    time.sleep(1)

    # End the game
    if not test_end_game():
        return False

    print_separator("SIMULATION COMPLETE")
    print("🎉 Full poker hand simulation completed successfully!")
    return True

def test_error_cases():
    """Test various error cases"""
    print_separator("TESTING ERROR CASES")

    # Test invalid game ID
    print("\n🔵 Testing invalid game ID...")
    response = requests.get(f"{BASE_URL}/state/INVALID_GAME")
    result = print_response(response)
    if result and "error" in result:
        print("✅ Error handling works for invalid game ID")

    # Test invalid action
    print("\n🔵 Testing invalid action...")
    data = {
        "game_id": GAME_ID,
        "user_id": "U123",
        "action": "invalid_action",
        "amount": 0
    }
    response = requests.post(f"{BASE_URL}/action", json=data)
    result = print_response(response)
    if result and "error" in result:
        print("✅ Error handling works for invalid actions")

    # Test missing fields
    print("\n🔵 Testing missing fields...")
    data = {
        "game_id": GAME_ID,
        "user_id": "U123"
        # Missing action and amount
    }
    response = requests.post(f"{BASE_URL}/action", json=data)
    result = print_response(response)
    if result and "error" in result:
        print("✅ Error handling works for missing fields")

if __name__ == "__main__":
    print("🚀 Starting PyPokerEngine API Tests")
    print(f"📍 Testing against: {BASE_URL}")

    try:
        # Run the full simulation
        success = run_full_game_simulation()

        if success:
            print("\n🎯 All tests passed! The API is working correctly.")
        else:
            print("\n💥 Some tests failed. Check the output above for details.")

        # Test error cases
        test_error_cases()

    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {BASE_URL}")
        print("   Make sure the Flask app is running on port 3000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    print("\n🏁 Testing complete!")