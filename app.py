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
    result = engine.start_game(game_id, players)
    return jsonify(result)

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
    return jsonify(result)

@app.route("/state/<game_id>", methods=["GET"])
def get_state(game_id):
    result = engine.get_state(game_id)
    return jsonify(result)

@app.route("/end-game/<game_id>", methods=["POST"])
def end_game(game_id):
    result = engine.end_game(game_id)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
