from src.player import Player

MAX_PLAYERS = 16

class Game:
    def __init__(self):
        # Server logic
        self.connected_players = {}
        self.ingame_players = {}
        self.admin = None
        self.in_progress = False
        self.disconnected_players = {}
        
        # Game logic
        self.player_scores = {}
        self.selected_player = None
        self.selected_character = None
        self.current_round = 1
        self.guess_found = False

    def is_empty(self):
        return len(self.connected_players) == 0

    def add_player(self, player_uuid, nickname):
        if len(self.connected_players) >= MAX_PLAYERS:
            return False
        else:
            if self.admin == None:
                self.admin = player_uuid
            self.connected_players[player_uuid] = Player(player_uuid, nickname)
            return True
    
    def remove_player(self, player_uuid):
        if player_uuid not in self.connected_players:
            return False

        self.connected_players.pop(player_uuid)
        # Select new admin if admin leaves
        if self.admin == player_uuid:
            if len(self.connected_players) != 0:
                self.admin = self.connected_players[0]
        if player_uuid in self.player_scores:
            self.player_scores.pop(player_uuid)
        return True
    
    def disconnect_player(self, player_uuid):
        if player_uuid in self.connected_players:
            player = self.connected_players.pop(player_uuid)
            self.disconnected_players[player_uuid] = player
            return True
        else:
            return False
        
    def reconnect_player(self, player_uuid):
        if player_uuid in self.disconnected_players:
            player = self.disconnected_players.pop(player_uuid)
            self.connected_players[player_uuid] = player
            return True
        else:
            return False
    
    def check_player(self, playerid):
        return playerid in self.connected_players or \
               playerid in self.disconnected_players