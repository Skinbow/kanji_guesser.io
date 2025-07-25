from pathlib import Path

import random
import threading
import time
import csv
import logging

# from libraries.KanjiRecognition import *

#--------------------------Example---------------------------
# print("Loading the models...")
# kanji_df = get_kanji_dataframe("resources/csv/marugoto_a1_kanji_furigana.csv")
# device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
# model = load_model("resources/models/Model_250.pth", device)

# # Transform for drawing on the website
# transform = transforms.Compose([
#     transforms.Resize((64, 64)),
#     transforms.Grayscale(num_output_channels=1),
#     transforms.ToTensor(),
#     transforms.Lambda(lambda x: 1.0 - x),
#     transforms.Lambda(lambda x: (x > 0.2).float()),
#     transforms.Normalize(mean=[0.5], std=[0.5])
# ])

# # Transform for reference images
# transform_rf = transforms.Compose([
#         transforms.Resize((64, 64)),
#         transforms.Grayscale(num_output_channels=1),
#         transforms.ToTensor(),
#         transforms.ConvertImageDtype(torch.float32),
#         transforms.Lambda(lambda x: (x > 0.2).float()),
#         transforms.Normalize(mean=[0.5], std=[0.5])
#     ])

# labels, reference_vectors = get_reference_vectors(model, device, "resources/models/references/", transform_rf)
# print("Done.")
#------------------------------------------------------------


SAVE_DIR = Path("drawings")
SAVE_DIR.mkdir(exist_ok=True)

def genid(dict):
    r_id = random.randint(100,999)
    while r_id in dict:
        r_id = random.randint(100,999)
    return r_id

# TODO: add the complete list
characterList = ['金', '木', '水', '火', '土']
character_to_image_name = {
    '金': 'gold.png',
    '木': 'wood.png',
    '水': 'water.png',
    '火': 'fire.png',
    '土': 'earth.png'
}

def get_random_kanji():
    with open('static/kanjis.csv', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        kanjis = list(reader)
    return random.choice(kanjis)

def next_turn(gamecode):
    global sio
    global game_dict
    
    game = game_dict[gamecode]

    if not hasattr(game, 'round_queue') or not game.round_queue:
        print("Game ended")
        sorted_scores = sorted(game.player_scores.items(), key=lambda item: item[1], reverse=True)
        top_scores = sorted_scores[:NUMBER_OF_TOP_SCORES]
        sio.emit('game_over', [{"name": players[pid].nickname, "score": score} for pid, score in top_scores], to=str(gamecode))
        return

    game.current_round += 1
    player_id = game.round_queue.pop(0)
    game.drawer_id = player_id

    kanji_data = get_random_kanji()
    game.current_kanji = kanji_data["Kanji"]

    game.guess_found = False

    selectedPlayer = players[player_id]
    sio.emit("you_are_drawer", {'kanji': kanji_data}, to=selectedPlayer.socketid)

    sio.emit("someone_was_selected", {
        'selectedPlayerId': player_id,
        'selectedPlayerNickname': selectedPlayer.nickname,
        'selectedCharacter': kanji_data["Kanji"],
        'characterImage': character_to_image_name.get(kanji_data["Kanji"], "unknown.png")
    }, to=str(gamecode))

    countdown_thread = threading.Thread(target=start_countdown, args=(gamecode, COUNT_DOWN_SECONDS, kanji_data["Kanji"]))
    countdown_thread.start()

# def start_game(gamecode):
#     game = game_dict[gamecode]
#     sio.emit('round_started', {'current_round': game.current_round, 'total_rounds': NUMBER_OF_ROUNDS}, to=str(gamecode))

#     player_ids = list(game.players)
#     rounds = NUMBER_OF_ROUNDS
#     game.round_queue = []

#     for _ in range(rounds):
#         round_players = player_ids.copy()
#         random.shuffle(round_players)
#         game.round_queue.extend(round_players)

#     for pid in player_ids:
#         game.player_scores[pid] = 0

#     next_turn(gamecode)


# def start_countdown(gamecode, duration_sec, selectedCharacter):
#     for remaining in range(duration_sec, -1, -1):
#         time_str = f"{remaining // 60:02}:{remaining % 60:02}"
#         sio.emit('timer_update', {'time': time_str}, to=str(gamecode))
#         time.sleep(1)

#     game = game_dict[gamecode]
#     if not game.guess_found:
#         sio.emit('show_answer', {
#             'selectedCharacter': selectedCharacter,
#             'characterImage': character_to_image_name.get(selectedCharacter, "unknown.png")
#         }, to=str(gamecode))

#     next_turn(gamecode)