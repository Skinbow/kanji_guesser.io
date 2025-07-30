NUMBER_OF_TOP_SCORES = 1  # Number of top scores to keep
NUMBER_OF_ROUNDS = 2 # Number of rounds in the game
COUNT_DOWN_SECONDS = 100  # Countdown duration in seconds

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, make_response, session
from flask_socketio import SocketIO, join_room
from random import randint

import logging
import base64, uuid, re
import secrets

from src.game import Game
from src.player import Player
from src.utils import *

game_dict = {}

app = Flask(__name__)
app.logger.handlers[0].setFormatter(logging.Formatter("[%(levelname)s ; %(asctime)s]: %(message)s"))
app.secret_key = secrets.token_hex()
sio = SocketIO(app)

sio.init_app(app)

# Home page asks for nickname and sends user to game page
@app.route("/")
def home():
    nickname = request.args.get("nickname")
    if nickname == None:
        return render_template("index.html")
    else:
        gamecode = create_game()
        app.logger.info(f"Created game with code {gamecode}")
        session["nickname"] = nickname
        return redirect(f"/game/{gamecode}", code=302)

# TODO: when more games are created, game creation slows down (should fix)
def create_game():
    gamecode = hex(randint(0x100000, 0xffffff))[2:]
    while gamecode in game_dict:
        gamecode = hex(randint(0x100000, 0xffffff))[2:]
    game_dict[gamecode] = Game()
    return gamecode

# Static files setup is automatic

# @app.route("/save", methods=["POST"])
# def save():
#     data_url = request.json.get("png")
#     match = re.match(r"^data:image/\w+;base64,(.+)$", data_url)
#     if not match:
#         return jsonify({"error": "format"}), 400
#     raw = base64.b64decode(match.group(1))
#     fname = SAVE_DIR / f"{uuid.uuid4()}.png"
#     fname.write_bytes(raw)

#     embedding = get_embedding(model, load_image(fname, transform, device))
#     predicted_labels = get_N_first_labels(embedding, labels, reference_vectors, N=15)
#     print(f"Predicted label: {predicted_labels}")

#     playerid = int(request.cookies.get("playerid", -1))
#     if playerid == -1 or playerid not in players:
#         return jsonify({"error": "invalid_player"}), 400

#     gamecode = players[playerid].gameid
#     game = game_dict[gamecode]
#     expected_kanji = getattr(game, 'current_kanji', None)
#     correct = expected_kanji in predicted_labels

#     print(f"Expected: {expected_kanji}, Correct: {correct}")

#     sid = players[playerid].socketid
#     sio.emit("drawing_checked", {
#         "expected": expected_kanji,
#         "predicted": predicted_labels,
#         "correct": correct
#     }, to=sid)

#     if correct and not getattr(game, "guess_found", False):
#         game.guess_found = True
#         game.player_scores[playerid] = game.player_scores.get(playerid, 0) + 1

#         sio.emit("player_guessed", {
#             "playerNickname": players[playerid].nickname,
#             "kanji": expected_kanji
#         }, to=str(gamecode))

#     return jsonify({"ok": True, "label": predicted_labels})

# Join game
@app.route("/game/<gamecode>")
def join_game(gamecode):
    if gamecode not in game_dict:
        # Game not found page
        return render_template("error_page.html", error_msg="Game not found!")
    
    game = game_dict[gamecode]

    # Reconnect
    if "uuid" in request.cookies and request.cookies["uuid"] in game.disconnected_players:
        uuid_ = request.cookies["uuid"]
        if game.reconnect_player(uuid_):
            player = game.disconnected_players[uuid_]
            # Get old nickname
            nickname = player.nickname
            session["nickname"] = nickname
            resp = make_response(redirect(f"/game/{gamecode}/lobby", code=302))
            resp.set_cookie("reconnect")

            app.logger.info(f"User with nickname {nickname} and uuid {uuid_} reconnected to game {gamecode}")
            return resp
        else:
            return render_template("error_page.html", error_msg="Lobby is full!")
    else:
        nickname = None
        if "nickname" in request.args:
            nickname = request.args["nickname"]
            session["nickname"] = nickname
        else:
            nickname = session.get("nickname")

        if nickname != None:
            resp = make_response(redirect(f"/game/{gamecode}/lobby", code=302))

            uuid_ = request.cookies.get("uuid")
            # User has no uuid
            if uuid_ == None:
                uuid_ = str(uuid.uuid4())
                resp.set_cookie("uuid", uuid_, httponly=True)

            # Try to add player
            if game.add_player(uuid_, nickname):
                app.logger.info(f"User with nickname {nickname} and uuid {uuid_} connected to game {gamecode}")
                return resp
            else:
                # Lobby full
                return render_template("error_page.html", error_msg="Lobby is full!")

        # Send user to pick nickname
        else:
            return render_template("index.html")

@app.route("/game/<gamecode>/lobby")
def join_lobby(gamecode):
    if gamecode not in game_dict:
        # Game not found page
        return render_template("error_page.html", error_msg="Game not found!")
    
    game = game_dict[gamecode]
    nickname = session.get("nickname")
    # Send back to home page if user is in invalid state
    if nickname == None \
        or request.cookies.get("uuid") == None \
        or not game.check_player(request.cookies.get("uuid")):
        return redirect("/")
    
    session["gamecode"] = gamecode

    # Entering game lobby
    return render_template("lobby.html", gamecode=gamecode, nickname=nickname)

#################### Socket logic ####################

@sio.on('connect')
def connect():
    player_uuid = request.cookies.get("uuid")
    gamecode = session.get("gamecode")

    if gamecode == None \
    or gamecode not in game_dict:
        # Game not found page
        return render_template("error_page.html", error_msg="Game not found!")
    
    game = game_dict[gamecode]

    if player_uuid == None \
    or not game_dict[gamecode].check_player(player_uuid):
        # User not in game
        return render_template("error_page.html", error_msg="You have done something wrong!")

    player = game.connected_players.get(player_uuid)
    ## Hmm
    assert(player != None)
    player.set_socketid(request.sid)
    
    # Make the client join the right room upon connection
    join_room(str(gamecode))

    app.logger.debug(f"{[game.connected_players[id].nickname for id in game.connected_players]}") # DEBUG
    app.logger.debug("player_list for" + str(gamecode))
    # Socket messaging
    sio.emit("player_list", {
        'player_nicknames' : [p.nickname for p in game.connected_players.values()],
        'player_ids': [p.publicid for p in game.connected_players.values()]
    }, to=str(gamecode))

@sio.on('disconnect')
def disconnect():
    player_uuid = request.cookies.get("uuid")
    gamecode = session.get("gamecode")

    if gamecode != None and player_uuid != None:
        game = game_dict[gamecode]
        
        player = game.connected_players.get(player_uuid)
        nickname = player.nickname

        if game.in_progress:
            game.disconnect_player(player_uuid)
        else:
            game.remove_player(player_uuid)
    
        # Remove game
        if game.is_empty():
            game_dict.pop(gamecode)

        app.logger.info(f"User with nickname {nickname} and uuid {player_uuid} disconnected from game {gamecode}")

@sio.on('start_game')
def start_game():
    player_uuid = request.cookies.get("uuid")
    gamecode = session.get("gamecode")
    if gamecode != None and player_uuid != None and game_dict[gamecode].admin == player_uuid:
        game = game_dict[gamecode]
        app.logger.info(f"Game with code {gamecode} started!")

        game.start_game()

        sio.emit('round_started', {
            'current_round': game.current_round,
            'total_rounds': NUMBER_OF_ROUNDS
        }, to=str(gamecode))

        next_turn(gamecode)

@sio.on('reset_game')
def reset_game():
    player_uuid = request.cookies.get("uuid")
    gamecode = session.get("gamecode")
    if gamecode != None and player_uuid != None and game_dict[gamecode].admin == player_uuid:
        app.logger.info(f"Game with code {gamecode} has been reset")
        game_dict[gamecode].reset_game()
        sio.emit('update_scores', [], to=str(gamecode))

def next_turn(gamecode):
    game = game_dict[gamecode]

    if not hasattr(game, 'round_queue') or not game.round_queue:
        app.logger.info(f"Game with gamecode {gamecode} ended")
        top_scores = game.get_top_scores(NUMBER_OF_TOP_SCORES)
        sio.emit('game_over', [{
            "name": game.connected_players[pid].nickname, 
            "score": score
        } for pid, score in top_scores], to=str(gamecode))
    
        # Once the game is over, we have to reset it to initial state
        game.reset_game()

    game.next_turn()

    sio.emit("you_are_drawer", {'kanji': game.kanji_data}, to=game.selected_player.socketid)

    sio.emit("someone_was_selected", {
        'selectedPlayerId': game.selected_player.publicid,
        'selectedPlayerNickname': game.selected_player.nickname,
        'selectedCharacter': game.kanji_data["Kanji"],
        'characterImage': character_to_image_name.get(game.kanji_data["Kanji"], "unknown.png")
    }, to=str(gamecode))

    countdown_thread = threading.Thread(target=start_countdown, args=(gamecode, COUNT_DOWN_SECONDS, game.kanji_data["Kanji"]))
    countdown_thread.start()

def start_countdown(gamecode, duration_sec, selectedCharacter):
    for remaining in range(duration_sec, -1, -1):
        time_str = f"{remaining // 60:02}:{remaining % 60:02}"
        sio.emit('timer_update', {'time': time_str}, to=str(gamecode))
        time.sleep(1)

    game = game_dict[gamecode]
    if not game.guess_found:
        sio.emit('show_answer', {
            'selectedCharacter': selectedCharacter,
            'characterImage': character_to_image_name.get(selectedCharacter, "unknown.png")
        }, to=str(gamecode))

    next_turn(gamecode)

# @sio.on('request_top_number')
# def request_top_number():
#     sio.emit('update_top_number', {'number': NUMBER_OF_TOP_SCORES})

# @sio.on('reset_game')
# def reset_game(gamecode):
#     game_dict[gamecode].player_scores = {}
#     print("Game has been reset.")
#     sio.emit('update_scores', [], to=str(gamecode))
#     game_dict[gamecode].current_round = 1


# ## TODO: Modify this to display real scores
# @sio.event
# def save_button_clicked_generate_random_score():
#     sid = request.sid
#     playerid = players[sid].playerid
#     gamecode = players[playerid].gameid
    
#     # generate 0 or 1 randomly
#     random_score = random.randint(0, 1)
#     print(f"Generated random score: {random_score}")
#     if playerid not in game_dict[gamecode].player_scores:
#         game_dict[gamecode].player_scores[playerid] = 0
#     else:
#         game_dict[gamecode].player_scores[playerid] += random_score
#     # print the current player scores
#     print(f"Current player scores: {game_dict[gamecode].player_scores}")
    
#     # order the player scores by score
#     sorted_scores = sorted(game_dict[gamecode].player_scores.items(), key=lambda item: item[1], reverse=True)
#     # keep only the top 1 scores
#     top_scores = sorted_scores[:NUMBER_OF_TOP_SCORES]
    
    
#     sio.emit('update_scores', [
#     {"name": name, "score": score} for name, score in top_scores
# ], to=str(gamecode))

if __name__ == "__main__":
    sio.run(app, debug=True, host="127.0.0.1", port=3000)
