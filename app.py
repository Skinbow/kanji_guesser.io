NUMBER_OF_TOP_SCORES = 1  # Number of top scores to keep
NUMBER_OF_ROUNDS = 2 # Number of rounds in the game
COUNT_DOWN_SECONDS = 20  # Countdown duration in seconds

from flask import Flask, app, render_template, request, redirect, make_response, session
from asgiref.wsgi import WsgiToAsgi
from random import randint
from http.cookies import SimpleCookie

import uvicorn
import asyncio
import socketio
import logging
import base64, uuid, re
import secrets

from src.game import Game
from src.utils import *

from libraries.KanjiRecognition import *

game_dict = {}

# Flask setup
app = Flask(__name__)
app.config.from_pyfile('config.py')
app.secret_key = secrets.token_hex()

# Logger setup
logger = logging.getLogger(__name__)
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("[%(levelname)s | %(asctime)s]: %(message)s"))
logger.addHandler(sh)
logger.setLevel("DEBUG")

# Turn WSGI Flak app into ASGI
asgi_app = WsgiToAsgi(app)

# Python-socketio server creation
sio = socketio.AsyncServer(async_mode="asgi")

# Gathering ASGI Flask and python-socketio apps into one
tapp = socketio.ASGIApp(sio, asgi_app)

#------------------------------------------------------------
def init():
    global device, model, transform, labels, reference_vectors, kanji_df
    logger.debug("Loading the model...")
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
    logger.debug("Loading is done.")
#------------------------------------------------------------

# Home page asks for nickname and sends user to game page
@app.route("/")
async def home():
    nickname = request.args.get("nickname")
    if nickname == None:
        nickname_suggestion = ""
        if "nickname" in request.cookies:
            nickname_suggestion = request.cookies["nickname"]
        return render_template("index.html", nickname_suggestion=nickname_suggestion)
    else:
        gamecode = create_game()
        logger.info(f"Created game with code {gamecode}")
        session["nickname"] = nickname
        
        resp = redirect(f"/game/{gamecode}", code=302)
        # Save nickname for future suggestions
        resp.set_cookie("nickname", nickname)
        return resp

# TODO: when more games are created, game creation slows down (should fix)
def create_game():
    gamecode = hex(randint(0x100000, 0xffffff))[2:]
    while gamecode in game_dict:
        gamecode = hex(randint(0x100000, 0xffffff))[2:]
    game_dict[gamecode] = Game()
    return gamecode

# Join game
@app.route("/game/<gamecode>")
async def join_game(gamecode):
    if gamecode not in game_dict:
        # Game not found page
        return render_template("error_page.html", error_msg="Game not found!")
    
    game = game_dict[gamecode]

    # Reconnect
    if "uuid" in request.cookies and request.cookies["uuid"] in game.disconnected_players:
        uuid_ = request.cookies["uuid"]
        if game.reconnect_player(uuid_):
            player = game.connected_players[uuid_]
            # Get old nickname
            nickname = player.nickname
            session["nickname"] = nickname
            resp = make_response(redirect(f"/game/{gamecode}/lobby", code=302))
            resp.set_cookie("reconnect")

            logger.info(f"User with nickname {nickname} and uuid {uuid_} reconnected to game {gamecode}")
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
            
            # Save nickname for future suggestions
            resp.set_cookie("nickname", nickname)
            session["uuid"] = uuid_

            # Try to add player
            if game.add_player(uuid_, nickname):
                logger.info(f"User with nickname {nickname} and uuid {uuid_} connected to game {gamecode}")
                return resp
            else:
                # Lobby full
                return render_template("error_page.html", error_msg="Lobby is full!")

        # Send user to pick nickname
        else:
            nickname_suggestion = ""
            if "nickname" in request.cookies:
                nickname_suggestion = request.cookies["nickname"]
            return render_template("index.html", nickname_suggestion=nickname_suggestion)

@app.route("/game/<gamecode>/lobby")
async def join_lobby(gamecode):
    if gamecode not in game_dict:
        # Game not found page
        return render_template("error_page.html", error_msg="Game not found!")
    
    game = game_dict[gamecode]
    nickname = session.get("nickname")
    # Send back to home page if user is in invalid state
    if nickname == None \
        or request.cookies.get("uuid") == None \
        or not game.player_in_game(request.cookies.get("uuid")):
        return redirect(f"/game/{gamecode}")
    
    session["gamecode"] = gamecode

    # Entering game lobby
    return render_template("lobby.html", gamecode=gamecode, nickname=nickname)

#################### Socket logic ####################

async def socket_request_is_valid(player_uuid, gamecode):
    if gamecode == None \
    or gamecode not in game_dict:
        return False
    
    game = game_dict[gamecode]

    if player_uuid == None \
    or not game.player_in_game(player_uuid):
        return False
    
    return True

@sio.event
async def connect(sid, environ):
    player_uuid = ""
    # Extract player uuid from http cookie
    for header in environ.get("asgi.scope").get("headers"):
        if header[0] == b"cookie":
            cookie = SimpleCookie()
            cookie.load(header[1].decode())
            cookies = {k: v.value for k, v in cookie.items()}
            
            player_uuid = cookies.get("uuid", "")

    if player_uuid == "":
        await sio.disconnect(sid)
    else:
        await sio.save_session(sid, {"uuid": player_uuid})
    
    logger.debug(f"Connected player's id: {player_uuid}")

@sio.event
async def connect_info(sid, data):
    gamecode = data["gamecode"]
    
    # Adding gamecode to socket session data
    sock_session = await sio.get_session(sid)
    sock_session["gamecode"] = gamecode
    await sio.save_session(sid, sock_session)

    player_uuid = sock_session.get("uuid")

    if not await socket_request_is_valid(player_uuid, gamecode):
        logger.debug("Invalid 1")
        logger.debug(f"{player_uuid} {gamecode}")
        await sio.disconnect(sid)
        return

    game = game_dict[gamecode]

    # Save socket id
    player = game.connected_players.get(player_uuid)
    player.set_socketid(sid)

    # Make the client join the right room upon connection
    await sio.enter_room(sid, str(gamecode))

    logger.debug(f"{[game.connected_players[id].nickname for id in game.connected_players]}")
    logger.debug("player_list for" + str(gamecode))

    # Send updated player list
    await sio.emit("player_list", {
        'player_nicknames' : [p.nickname for p in game.connected_players.values()],
        'player_ids': [p.publicid for p in game.connected_players.values()]
    }, to=str(gamecode))

    logger.debug(f"Sent player list to {game.connected_players[player_uuid].nickname}")

@sio.event
async def disconnect(sid, reason):
    sock_session = await sio.get_session(sid)
    player_uuid = sock_session.get("uuid")
    gamecode = sock_session.get("gamecode")

    if not await socket_request_is_valid(player_uuid, gamecode):
        logger.debug("Invalid 2 " + sid)
        return
    
    game = game_dict[gamecode]
    
    player = game.connected_players.get(player_uuid)
    nickname = player.nickname

    if game.in_progress:
        game.disconnect_player(player_uuid)
    else:
        game.remove_player(player_uuid)

    # Notify other players
    await sio.emit("player_list", {
        'player_nicknames' : [p.nickname for p in game.connected_players.values()],
        'player_ids': [p.publicid for p in game.connected_players.values()]
    }, to=str(gamecode))

    logger.info(f"User with nickname {nickname} and uuid {player_uuid} disconnected from game {gamecode}")
    
    # Remove game after 10s of inactivity
    if game.is_empty():
        await asyncio.create_task(game_remove_countdown(gamecode))


async def game_remove_countdown(gamecode):
    await asyncio.sleep(10)
    if game_dict[gamecode].is_empty():
        game_dict.pop(gamecode)
    else:
        logger.debug(f"Game with gamecode {gamecode} was not removed, as someone joined.")

@sio.event
async def start_game(sid):
    sock_session = await sio.get_session(sid)
    player_uuid = sock_session.get("uuid")
    gamecode = sock_session.get("gamecode")

    if not await socket_request_is_valid(player_uuid, gamecode):
        logger.debug("Invalid 3")
        await sio.disconnect(sid)
        return
    
    game = game_dict[gamecode]
    
    if game.admin == player_uuid:
        logger.info(f"Game with code {gamecode} started!")

        game.start_game(NUMBER_OF_ROUNDS)

        await sio.emit('round_started', {
            'current_round': game.current_round,
            'total_rounds': NUMBER_OF_ROUNDS
        }, to=str(gamecode))

        asyncio.create_task(next_turn(gamecode))

@sio.event
async def reset_game(sid):
    sock_session = await sio.get_session(sid)
    player_uuid = sock_session.get("uuid")
    gamecode = sock_session.get("gamecode")

    if not await socket_request_is_valid(player_uuid, gamecode):
        logger.debug("Invalid 4")
        await sio.disconnect(sid)
        return

    game = game_dict[gamecode]

    if game.admin == player_uuid:
        logger.info(f"Game with code {gamecode} has been reset")
        game.reset_game()
        await sio.emit('update_scores', [], to=str(gamecode))

async def next_turn(gamecode):
    game = game_dict[gamecode]

    # Game over
    if not game.next_turn():
        logger.info(f"Game with gamecode {gamecode} ended")
        scores = game.get_scores()
        await sio.emit('game_over', [{
            "name": game.connected_players[pid].nickname, 
            "score": score
        } for pid, score in scores.items()], to=str(gamecode))
    
        # Once the game is over, we have to reset it to initial state
        game.reset_game()
    else:
        await sio.emit("you_are_clue_giver", {'kanji': game.kanji_data}, to=game.selected_player.socketid)

        await sio.emit("someone_was_selected", {
            'selectedPlayerId': game.selected_player.publicid,
            'selectedPlayerNickname': game.selected_player.nickname,
            'selectedCharacter': game.kanji_data["Kanji"],
            'characterImage': character_to_image_name.get(game.kanji_data["Kanji"], "unknown.png")
        }, to=str(gamecode))

        logger.info(f"Game with gamecode {gamecode} next turn")

        await start_countdown(gamecode, COUNT_DOWN_SECONDS, game.kanji_data["Kanji"])

async def start_countdown(gamecode, duration_sec, selectedCharacter):
    game = game_dict[gamecode]
    
    game.guess_found_flag = asyncio.Event()
    guessed = True
    try:
        await asyncio.wait_for(game.guess_found_flag.wait(), duration_sec)
        guessed = True
    except asyncio.TimeoutError:
        logger.debug(f"Countdown on game with gamecode {gamecode} finished!")
        guessed = False

    await sio.emit('round_ended', {
        'selectedCharacter': selectedCharacter,
        'characterImage': character_to_image_name.get(selectedCharacter, "unknown.png"),
        'guessed': guessed
    }, to=str(gamecode))
    
    await next_turn(gamecode)

# @sio.on('request_top_number')
# def request_top_number():
#     sio.emit('update_top_number', {'number': NUMBER_OF_TOP_SCORES})

## TODO: Update this method according to the docstring
@sio.on('submit_choice')
async def choice_submitted(sid, data):
    """
     This function check if the kanji guess by the client is right one
     If it's the case, the player's score is update by a certain amount f(t, n)
     f(t, n) = the score obtain by the player's guess, where
     t = the time it took to guess, n = the number of players which have already guessed
    """
    sock_session = await sio.get_session(sid)
    player_uuid = sock_session.get("uuid")
    gamecode = sock_session.get("gamecode")

    if not await socket_request_is_valid(player_uuid, gamecode):
        logger.debug("Invalid 5")
        await sio.disconnect(sid)
        return
    
    game = game_dict[gamecode]
    
    if game.selected_player != player_uuid:
        # TODO: Need to have a way to associate returned kanji with the kanji_data entry
        # (right now they aren't always the same because of the hiragana transcription) 
        if "choice" in data and data["choice"] == game.kanji_data["Kanji"]:
            logger.debug(f"Correct guess from {player_uuid} in game {gamecode}")
            if player_uuid not in game_dict[gamecode].player_scores:
                game.player_scores[player_uuid] = 1
            else:
                game.player_scores[player_uuid] += 1
            # print the current player scores
            logger.debug(f"Current player scores: {game.get_scores()}")
            
            scores = game.get_scores()
            await game.set_guess_found(True)
            
            await sio.emit('update_scores', [{
                "name": game.connected_players[pid].nickname,
                "score": score
            } for pid, score in scores.items()], to=str(gamecode))

@sio.event
async def get_characters(sid, data):
    sock_session = await sio.get_session(sid)
    player_uuid = sock_session.get("uuid")
    gamecode = sock_session.get("gamecode")

    if not await socket_request_is_valid(player_uuid, gamecode):
        logger.debug("Invalid 6")
        await sio.disconnect(sid)
        return

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

    await sio.emit('characters_result', {'characters': predicted_labels}, to=sid)

async def main():
    config = uvicorn.Config(tapp, host="127.0.0.1", port=3000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    init()
    asyncio.run(main())
    
