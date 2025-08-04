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

from libraries.KanjiRecognition import *

# TODO : Add an event which handle the end of a round and give the reason (timer ended or everyone guessed)

game_dict = {}

app = Flask(__name__)
app.logger.handlers[0].setFormatter(logging.Formatter("[%(levelname)s | %(asctime)s]: %(message)s"))
app.secret_key = secrets.token_hex()
app.logger.setLevel("DEBUG")

sio = SocketIO(app)

sio.init_app(app)

#------------------------------------------------------------
app.logger.debug("Loading the model...")
kanji_df = get_kanji_dataframe("static/models/csv/marugoto_a1_kanji_furigana.csv")
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
model = load_model("static/models/Model_250.pth", device)

# Transform for the drawings on the website and the references images
transform = transforms.Compose([
    transforms.Resize((64, 64)),
    transforms.Grayscale(num_output_channels=1),
    transforms.ToTensor(),
    transforms.Lambda(lambda x: 1.0 - x),
    transforms.Lambda(lambda x: (x > 0.2).float()),
    transforms.Normalize(mean=[0.5], std=[0.5])
])

labels, reference_vectors = get_reference_vectors(model, device, "static/models/references/", transform)
app.logger.debug("Loading is done.")
#------------------------------------------------------------

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

        game.start_game(NUMBER_OF_ROUNDS)

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

    # Game over
    if not game.next_turn():
        app.logger.info(f"Game with gamecode {gamecode} ended")
        scores = game.get_scores()
        sio.emit('game_over', [{
            "name": game.connected_players[pid].nickname, 
            "score": score
        } for pid, score in scores.items()], to=str(gamecode))
    
        # Once the game is over, we have to reset it to initial state
        game.reset_game()
    else:
        sio.emit("you_are_clue_giver", {'kanji': game.kanji_data}, to=game.selected_player.socketid)

        sio.emit("someone_was_selected", {
            'selectedPlayerId': game.selected_player.publicid,
            'selectedPlayerNickname': game.selected_player.nickname,
            'selectedCharacter': game.kanji_data["Kanji"],
            'characterImage': character_to_image_name.get(game.kanji_data["Kanji"], "unknown.png")
        }, to=str(gamecode))

        app.logger.info(f"Game with gamecode {gamecode} next turn")

        countdown_thread = threading.Thread(target=start_countdown, args=(gamecode, COUNT_DOWN_SECONDS, game.kanji_data["Kanji"]))
        countdown_thread.start()

def start_countdown(gamecode, duration_sec, selectedCharacter):
    time.sleep(10)
    app.logger.debug(f"Countdown on game with gamecode {gamecode} finished!")
    # for remaining in range(duration_sec, -1, -1):
    #     time_str = f"{remaining // 60:02}:{remaining % 60:02}"
    #     sio.emit('timer_update', {'time': time_str}, to=str(gamecode))
    #     time.sleep(1)

    # game = game_dict[gamecode]
    sio.emit('show_answer', {
        'selectedCharacter': selectedCharacter,
        'characterImage': character_to_image_name.get(selectedCharacter, "unknown.png")
    }, to=str(gamecode))

    next_turn(gamecode)

# @sio.on('request_top_number')
# def request_top_number():
#     sio.emit('update_top_number', {'number': NUMBER_OF_TOP_SCORES})

## TODO: Update this method according to the docstring
@sio.on('submit_choice')
def choice_submitted(data):
    """
     This function check if the kanji guess by the client is right one
     If it's the case, the player's score is update by a certain amount f(t, n)
     f(t, n) = the score obtain by the player's guess, where
     t = the time it took to guess, n = the number of players which have already guessed
    """
    player_uuid = request.cookies.get("uuid")
    gamecode = session.get("gamecode")
    
    if gamecode != None and player_uuid != None and game_dict[gamecode].selected_player != player_uuid:
        game = game_dict[gamecode]
        # TODO: Need to have a way to associate returned kanji with the kanji_data entry
        # (right now they aren't always the same because of the hiragana transcription) 
        if "choice" in data and data["choice"] == game.kanji_data["Kanji"]:
            app.logger.debug(f"Correct guess from {player_uuid} in game {gamecode}")
            if player_uuid not in game_dict[gamecode].player_scores:
                game.player_scores[player_uuid] = 1
            else:
                game.player_scores[player_uuid] += 1
            # print the current player scores
            app.logger.debug(f"Current player scores: {game.get_scores()}")
            
            scores = game.get_scores()
            
            sio.emit('update_scores', [{
                "name": game.connected_players[pid].nickname,
                "score": score
            } for pid, score in scores.items()], to=str(gamecode))

@sio.on('get_characters')
def getCharacters(data):
    # This function will edit the 10 cells below the canva with the 10 most probable kanjis from the drawing
    image_b64 = data["image"]
    image_b64 = image_b64.split(",")[1]
    image = base64.b64decode(image_b64)
    filename = "image.png"
    Path(filename).write_bytes(image)

    embedding = get_embedding(model, load_image(filename, transform, device))
    predicted_labels = get_N_first_labels(embedding, labels, reference_vectors, N=10)

    # Remove temporary file
    Path(filename).unlink()

    sio.emit('characters_result', {'characters': predicted_labels}, to=request.sid)


if __name__ == "__main__":
    sio.run(app, debug=True, host="127.0.0.1", port=3000)
