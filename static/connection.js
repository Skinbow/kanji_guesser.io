// -----------------------------------------

const gamecodeRe = new RegExp("/game/([0-9a-fA-F]{6})/.*");
const gamecode = window.location.pathname.match(gamecodeRe)[1];

// Handling socket
const socket = io();
socket.on("connect", () => {
    socket.emit("connect_info", {"gamecode": gamecode});
});

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

const nicknames = [];

// Load the players nicknames on the bottom grid
socket.on("player_list", (data) => {
    console.log("player_list");
    nicknames.length = 0; // reset
    nicknames.push(...data.player_nicknames);

    const playerListDiv = document.getElementById("player-list");
    playerListDiv.innerHTML = ""; // reset

    nicknames.forEach((nickname) => {
        const p = document.createElement("p");
        console.log(nickname);
        p.textContent = nickname;
        playerListDiv.appendChild(p);
    });
});

// Add characters to the cells
socket.on("characters_result", (data) => {
    console.log("characters_result");
    const chars = data.characters;
    for (let i = 0; i < 10; i++) {
        const char = chars[i];
        console.log(char);
        const cell = document.getElementById("cell-" + (i+1));
        cell.innerText = char;
    }
});

// Tell the client it is the clue giver
socket.on("you_are_clue_giver", (data) => {
    console.log("you_are_clue_giver");
    const kanji = data.kanji;
    
    toggleTitle();
    switchElement("menu", clues);
    
    const kanjiName = document.getElementById("kanji-name");
    const furigana = document.getElementById("furigana");
    const explanation = document.getElementById("explanation");
    const construction = document.getElementById("construction");
    const example = document.getElementById("example");

    kanjiName.innerHTML = "<b>Kanji : </b>" + kanji.Kanji;
    furigana.innerHTML = "<b>Furigana : </b>" + kanji.Furigana;
    explanation.innerHTML = "<b>Explanation : </b>" + kanji.Explication;
    construction.innerHTML = "<b>Construction : </b>" + kanji.Construction;
    if (kanji.Exemples != null) {
        example.innerHTML = "<b>Examples : </b>" + kanji.Exemples;
    }
});

// Tell the client it is the guesser (should draw the kanji based on the clues)
// And who is the clue giver
socket.on("someone_was_selected", (data) => {
    console.log("someone_was_selected");
    //const playerID = data.selectedPlayerId; // Maybe I should keep a map between PID and Nickname ?
    const playerNickname = data.selectedPlayerNickname;
    toggleTitle();

    switchElement("menu", drawingZone);

    const playerListDiv = document.getElementById("player-list");
    const paragraphs = playerListDiv.querySelectorAll("p");
    let i = 0;
    paragraphs.forEach((p) => {
        if (p.innerText == playerNickname) {
            p.innerHTML = "<b>" + p.innerText + " (Clue Giver)</b>";
        }
        else {
            p.innerText = nicknames[i];
            console.log(nicknames, i);
        }
        i = i + 1;
    });
});

// Show the right answer in this round
socket.on("round_ended", (data) => {
    console.log("round_ended");
    const kanji = data.selectedCharacter;
    const kanjiImage = data.characterImage;
    const someone_guessed = data.guessed;

    console.log(kanji);
    console.log(kanjiImage);
    console.log("Someone guessed: " + someone_guessed);
    // TODO : Show the kanji (if the image is the way it is draw, its useful, otherwise we don't need it)

});

// Get the information of the current round and the total number of rounds
socket.on("round_started", (data) => {
    console.log("round_started");
    const currentRound = data.current_round;
    const totalRound = data.total_rounds;

    console.log(currentRound);
    console.log(totalRound);
    // TODO : Show the currentRound over totalRound on the screen
    
    const roundsInfo = document.getElementById("rounds");
    roundsInfo.innerText = `Rounds : ${currentRound}/${totalRound}`
});

// Update the players scores
socket.on("update_scores", (data) => {
    console.log("update_scores");
    const players = data;
    console.log(players);
    // TODO : For each player, update its score

    const playerListDiv = document.getElementById("player-list");
    const paragraphs = playerListDiv.querySelectorAll("p");

    // TODO : Work on it when updated (for now it doesn't work properly)
    let i = 0;
    paragraphs.forEach((p) => {
        const name = players[i].name;
        const score = players[i].score;
        p.innerText = `${name}\n${score}`;
        i = i + 1;
    });
});

// Update the players scores
socket.on("game_over", (data) => {
    console.log("game_over");
    const name = data.name;
    const score = data.score;

    console.log(name);
    console.log(score);
    // TODO : For each player, update its score
    
});

// TODO...
// Treat the following messages:
// "player_list" : Add ids
// "you_are_drawer"
// "someone_was_selected"
// 'timer_update'???
// 'round_ended'
// 'round_started'
// 'update_scores'
// 'game_over'

// Send the following:
// 'start_game'
// 'reset_game'
// 'submit_drawing'

// -----------------------------------------