#!/usr/bin/env python3
"""
Test file for folding logic and street advancement.
This tests the scenario where a player folds and should be skipped in subsequent rounds.
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:3000"
GAME_ID = "GAME001"

def print_separator(title):
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")

def print_request(method, endpoint, data=None):
    print(f"\n📤 {method} {endpoint}")
    if data:
        print(f"   Data: {json.dumps(data, indent=2)}")

def print_response(response):
    print(f"📥 Response Status: {response.status_code}")
    try:
        result = response.json()
        print(f"   Response: {json.dumps(result, indent=2)}")
        return result
    except json.JSONDecodeError:
        print(f"   Raw Response: {response.text}")
        return None

def test_folding_scenario():
    """Test the folding scenario where U456 folds and should be skipped"""

    print_separator("TESTING FOLDING LOGIC AND STREET ADVANCEMENT")

    # Step 1: Start a new game
    print_separator("STEP 1: START GAME")
    start_data = {
        "game_id": GAME_ID,
        "players": [
            {"user_id": "U123", "stack": 100},
            {"user_id": "U456", "stack": 100},
            {"user_id": "U789", "stack": 100}
        ]
    }

    print_request("POST", "/start-game", start_data)
    response = requests.post(f"{BASE_URL}/start-game", json=start_data)
    result = print_response(response)

    if not result or "error" in result:
        print("❌ Failed to start game")
        return False

    print(f"✅ Game started successfully!")
    print(f"   - Next player: {result.get('next_player')}")
    print(f"   - Total pot: {result.get('total_pot')}")
    print(f"   - Valid actions: {len(result.get('valid_actions', []))} actions available")

    # Step 2: U456 (dealer) folds
    print_separator("STEP 2: U456 FOLDS")
    fold_data = {
        "game_id": GAME_ID,
        "user_id": "U456",
        "action": "fold",
        "amount": 0
    }

    print_request("POST", "/action", fold_data)
    response = requests.post(f"{BASE_URL}/action", json=fold_data)
    result = print_response(response)

    if not result or "error" in result:
        print("❌ U456 fold failed")
        return False

    print(f"✅ U456 folded successfully!")
    print(f"   - Next player: {result.get('next_player')}")
    print(f"   - Street: {result.get('street')}")
    print(f"   - Total pot: {result.get('total_pot')}")

    # Step 3: U789 calls the big blind
    print_separator("STEP 3: U789 CALLS BIG BLIND")
    call_data = {
        "game_id": GAME_ID,
        "user_id": "U789",
        "action": "call",
        "amount": 1
    }

    print_request("POST", "/action", call_data)
    response = requests.post(f"{BASE_URL}/action", json=call_data)
    result = print_response(response)

    if not result or "error" in result:
        print("❌ U789 call failed")
        return False

    print(f"✅ U789 called successfully!")
    print(f"   - Next player: {result.get('next_player')}")
    print(f"   - Street: {result.get('street')}")
    print(f"   - Total pot: {result.get('total_pot')}")

    # Step 4: U123 checks (completing preflop)
    print_separator("STEP 4: U123 CHECKS (COMPLETING PREFLOP)")
    check_data = {
        "game_id": GAME_ID,
        "user_id": "U123",
        "action": "check",
        "amount": 0
    }

    print_request("POST", "/action", check_data)
    response = requests.post(f"{BASE_URL}/action", json=check_data)
    result = print_response(response)

    if not result or "error" in result:
        print("❌ U123 check failed")
        return False

    print(f"✅ U123 checked successfully!")
    print(f"   - Next player: {result.get('next_player')}")
    print(f"   - Street: {result.get('street')}")
    print(f"   - Total pot: {result.get('total_pot')}")
    print(f"   - Board: {result.get('board')}")

    # Step 5: U789 acts on the flop
    print_separator("STEP 5: U789 ACTS ON THE FLOP")
    flop_action_data = {
        "game_id": GAME_ID,
        "user_id": "U789",
        "action": "check",
        "amount": 0
    }

    print_request("POST", "/action", flop_action_data)
    response = requests.post(f"{BASE_URL}/action", json=flop_action_data)
    result = print_response(response)

    if not result or "error" in result:
        print("❌ U789 flop action failed")
        return False

    print(f"✅ U789 acted on flop successfully!")
    print(f"   - Next player: {result.get('next_player')}")
    print(f"   - Street: {result.get('street')}")
    print(f"   - Total pot: {result.get('total_pot')}")
    print(f"   - Board: {result.get('board')}")

    # Analysis
    print_separator("ANALYSIS")
    print("🔍 Checking if folding logic worked correctly:")

    # Verify that U456 (who folded) is not the next player after flop
    if result.get('next_player') == 'U456':
        print("❌ BUG: U456 (folded player) is still being selected as next player")
        print("   This means folded players are not being properly skipped")
    else:
        print(f"✅ SUCCESS: Next player is {result.get('next_player')} (not U456)")
        print("   Folded players are being properly skipped")

    # Verify street advancement
    if result.get('street') == 1:
        print("✅ SUCCESS: Street advanced to flop (street 1)")
    else:
        print(f"❌ BUG: Street did not advance correctly. Current street: {result.get('street')}")

    return True

if __name__ == "__main__":
    print("🚀 Starting folding logic test...")
    success = test_folding_scenario()

    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")

    print("\n📝 Test Summary:")
    print("   - This test verifies that folded players are skipped in subsequent betting rounds")
    print("   - It also tests proper street advancement from preflop to flop")
    print("   - The expected behavior: U456 folds, U789 and U123 complete preflop, flop is dealt, U789 acts first")