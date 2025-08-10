from random import randint, shuffle

from src.player import Player
from src.utils import get_random_kanji

MAX_PLAYERS = 16

class Game:
    def __init__(self):
        # Server logic
        self.connected_players = {}
        self.ingame_players = {}
        self.admin = None
        self.disconnected_players = {}
        self.used_publicids = []
        self.available_publicids = list(range(MAX_PLAYERS))
        self.in_progress = False
        self.rounds_num = 2

        # Game logic
        self.round_queue = []
        self.player_scores = {}
        self.selected_player = None
        self.selected_character = None
        self.current_round = 1
        self.guess_found = False
        self.guess_found_flag = None

    def is_empty(self):
        return len(self.connected_players) == 0

    def add_player(self, player_uuid, nickname):
        if len(self.connected_players) >= MAX_PLAYERS:
            return False
        else:
            publicid = self.get_new_publicid()
            if self.admin == None:
                self.admin = player_uuid
            player = Player(player_uuid, nickname)
            player.set_publicid(publicid)
            self.connected_players[player_uuid] = player
            self.player_scores[player_uuid] = 0
            return True
    
    def remove_player(self, player_uuid):
        if player_uuid not in self.connected_players:
            return False

        player = self.connected_players.pop(player_uuid)
        self.free_publicid(player.publicid)
        # Select new admin if admin leaves
        if self.admin == player_uuid:
            if len(self.connected_players) != 0:
                self.admin = self.connected_players.keys[0]
        if player_uuid in self.player_scores:
            self.player_scores.pop(player_uuid)
        return True
    
    def disconnect_player(self, player_uuid):
        if player_uuid in self.connected_players:
            player = self.connected_players.pop(player_uuid)
            self.disconnected_players[player_uuid] = player
            self.free_publicid(player.publicid)
            return True
        else:
            return False
        
    def reconnect_player(self, player_uuid):
        if player_uuid in self.disconnected_players:
            player = self.disconnected_players.pop(player_uuid)
            publicid = self.get_new_publicid()
            player.set_publicid(publicid)
            self.connected_players[player_uuid] = player
            return True
        else:
            return False
    
    def player_in_game(self, playerid):
        return playerid in self.connected_players
    
    def get_new_publicid(self):
        publicid = self.available_publicids.pop()
        self.used_publicids.append(publicid)
        return publicid

    def free_publicid(self, publicid):
        self.used_publicids.remove(publicid)
        self.available_publicids.append(publicid)

#################### Game logic ####################

    def start_game(self, num_rounds):
        self.in_progress = True

        self.set_round_queue()

        for puuid in self.connected_players.keys():
            self.player_scores[puuid] = 0

    # Sets selected players order
    def set_round_queue(self):
        player_uuids = list(self.connected_players.keys())
        shuffle(player_uuids)
        self.round_queue = player_uuids

    def next_turn(self):
        self.current_round += 1

        self.kanji_data = get_random_kanji()
        self.current_kanji = self.kanji_data["Kanji"]

        self.guess_found = False

        if len(self.round_queue) == 0:
            return False
        else:
            for puuid in self.round_queue:
                if puuid in self.connected_players:
                    self.round_queue.remove(puuid)
                    self.selected_player = self.connected_players[puuid]
                    return True
            # None of the players in queue are connected
            return False

    def reset_game(self):
        self.disconnected_players.clear()
        self.player_scores.clear()
        self.current_round = 1
        self.selected_player = None
        self.selected_character = None
        self.guess_found = False
        self.in_progress = False

    def get_scores(self):
        return {pid: score for pid, score in self.player_scores.items() if pid in self.connected_players}
        # sorted_scores = sorted(self.player_scores.items(), key=lambda item: item[1], reverse=True)
        # top_scores = sorted_scores[:num]
        #return top_scores
    
    async def set_guess_found(self, v):
        self.guess_found = v
        if v and self.guess_found_flag != None:
            self.guess_found_flag.set()