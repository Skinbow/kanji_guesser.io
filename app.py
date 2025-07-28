NUMBER_OF_TOP_SCORES = 1  # Number of top scores to keep
NUMBER_OF_ROUNDS = 2 # Number of rounds in the game
COUNT_DOWN_SECONDS = 100  # Countdown duration in seconds

from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, make_response, session
from flask_socketio import SocketIO, join_room

import base64, uuid, re
import secrets

from src.game import Game
from src.player import Player
from random import randint

game_dict = {}

app = Flask(__name__)
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

# TODO : Add this security to every resources
@app.route("/script.js")
def index():
    return send_from_directory('static', 'script.js')

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

# @app.route()
# if 'playerid' in request.cookies:
#     playerid = int(request.cookies['playerid'])
#     game = game_dict[int(gamecode)]
#     is_drawer = hasattr(game, 'drawer_id') and playerid == game.drawer_id
#     kanji = get_random_kanji()
#     print("DEBUG kanji keys:", kanji)
#     return render_template("lobby.html",
#                             gamecode=gamecode,
#                             nickname=players[playerid].nickname,
#                             is_drawer=is_drawer,
#                             kanji=kanji if is_drawer else None)
# else:
#     return redirect("index.html", code=302)


# Socket logic

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

    room = ""
    if game.in_progress and request.cookies.get("reconnect") != None:
        room = "play_" + str(gamecode)
    else:
        room = "wait_" + str(gamecode)
    
    # Make the client join the right room upon connection
    join_room(room)

    print(f"[DEBUG] {[game.connected_players[id].nickname for id in game.connected_players]}") # DEBUG
    print("[DEBUG] player_list_" + str(gamecode))
    # Socket messaging
    # sio.emit("player_list" + str(gamecode), {
    #     'playerids': game.connected_players,
    #     'ingame_playerids': gamecode.ingame_players,
    #     'player_nicknames' : [game.connected_players[id] for id in game.connected_players],
    #     'NUMBER_OF_PLAYERS': len(game.connected_players)
    # }, to=room)

    sio.emit("player_list_" + str(gamecode), {
        'player_nicknames' : [game.connected_players[id].nickname for id in game.connected_players]
    }, to=room)

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

# # For debugging purposes
# @sio.on('game_start_ack')
# def game_start_ack():
#     gamecode = players[playerids[request.sid]].gameid
#     print(f"Game with code {gamecode} started!")

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
