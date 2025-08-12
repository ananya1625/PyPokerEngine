import random
import string

class LobbyManager:
    def __init__(self):
        self.lobbies = {}  # code -> {"owner": user_id, "players": [user_id]}

    def _generate_code(self):
        chars = string.ascii_uppercase + "123456789"
        while True:
            code = ''.join(random.choices(chars, k=4))
            if code not in self.lobbies:
                return code

    def create_lobby(self, owner_id):
        code = self._generate_code()
        self.lobbies[code] = {
            "owner": owner_id,
            "players": [owner_id]
        }
        return code

    def join_lobby(self, user_id, code):
        code = code.upper()
        if code not in self.lobbies:
            return False, "🚫 That game code does not exist."

        lobby = self.lobbies[code]

        if user_id in lobby["players"]:
            return False, f"You're already in the game hosted by <@{lobby['owner']}>."

        lobby["players"].append(user_id)
        return True, f"✅ You've joined <@{lobby['owner']}>'s game!"

    def get_lobby(self, code):
        return self.lobbies.get(code.upper())

    def get_players(self, code):
        lobby = self.get_lobby(code)
        return lobby["players"] if lobby else []

    def is_owner(self, user_id, code):
        lobby = self.get_lobby(code)
        return lobby and lobby["owner"] == user_id

    def clear_lobby(self, code):
        if code.upper() in self.lobbies:
            del self.lobbies[code.upper()]
