// -----------------------------------------

const gamecodeRe = new RegExp("/game/([0-9a-fA-F]{6})/.*");
const gamecode = window.location.pathname.match(gamecodeRe)[1];
let clueGiver = "";
let youAreClueGiver = false;
const scoresDict = {};
const menu = document.getElementById("menu"); // Store the menu to show it back on screen

// Rounds number info
let currentRound = 0;
let totalRound = 0;

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
    nicknames.length = 0; // reset
    nicknames.push(...data.player_nicknames);

    const playerListDiv = document.getElementById("player-list");
    playerListDiv.innerHTML = ""; // reset

    nicknames.forEach((nickname) => {
        const p = document.createElement("p");
        scoresDict[nickname] = 0;
        p.textContent = nickname;
        playerListDiv.appendChild(p);
    });
});

// Add characters to the cells
socket.on("characters_result", (data) => {
    const chars = data.characters;
    for (let i = 0; i < 10; i++) {
        const char = chars[i];
        const cell = document.getElementById("cell-" + (i+1));
        cell.innerText = char;
    }
});

// Tell the client it is the clue giver
socket.on("you_are_clue_giver", (data) => {
    const kanji = data.kanji;
    
    toggleTitle();
    switchElement(onScreen, clues);
    youAreClueGiver = true;
    
    const kanjiName = document.getElementById("kanjiName");
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
    const playerNickname = data.selectedPlayerNickname;
    clueGiver = playerNickname;
    
    if (!youAreClueGiver) {
        toggleTitle();
        switchElement(onScreen, drawingZone);
    }

    const playerListDiv = document.getElementById("player-list");
    const paragraphs = playerListDiv.querySelectorAll("p");
    let i = 0;
    paragraphs.forEach((p) => {
        if (p.innerText == playerNickname) {
            p.innerHTML = "<b>" + p.innerText + " (Clue Giver)</b><br>" + scoresDict[nicknames[i]];
        }
        else {
            p.innerText = nicknames[i] + "\n" + scoresDict[nicknames[i]];
        }
        i = i + 1;
    });
});

// Show the right answer in this round
socket.on("round_ended", (data) => {
    const kanji = data.selectedCharacter;
    const kanjiImage = data.characterImage;
    const someone_guessed = data.guessed;
    youAreClueGiver = false; // Reset the flag of the clue giver on the client
    
    // Update the number of round
    if (currentRound < totalRound) currentRound++;
    console.log(currentRound);
    const roundsInfo = document.getElementById("rounds");
    roundsInfo.innerText = `Rounds : ${currentRound}/${totalRound}`;

    const roundEndedInfo = document.getElementById("roundEndedInfo");

    if (someone_guessed) {
        roundEndedInfo.innerHTML = `<b>Kanji guessed : ${kanji} !</b>`;
    }
    else {
        // Time's up
        roundEndedInfo.innerHTML = `<b>Time's up !</b>`;
    }
    // Clear the roundEndedInfo after 3s
    setTimeout(() => {
        const roundEndedInfo = document.getElementById("roundEndedInfo");
        roundEndedInfo.innerHTML = "";
    }, 3000);
});

// Get the information of the current round and the total number of rounds
socket.on("round_started", (data) => {
    currentRound = data.current_round;
    totalRound = data.total_rounds;
    
    const roundsInfo = document.getElementById("rounds");
    roundsInfo.innerText = `Rounds : ${currentRound}/${totalRound}`;
});

// Update the players scores
socket.on("update_scores", (data) => {
    const players = data;

    const playerListDiv = document.getElementById("player-list");
    const paragraphs = playerListDiv.querySelectorAll("p");

    let i = 0;
    paragraphs.forEach((p) => {
        let name = "";
        if (players[i].name == clueGiver) {
            name = "<b>" + players[i].name + " (Clue Giver)</b><br>";
        }
        else {
            name = players[i].name + "<br>";
        }
        const score = players[i].score;
        scoresDict[players[i].name] = score;
        p.innerHTML = `${name}${score}`;
        i = i + 1;
    });
});

// Update the players scores
socket.on("game_over", (data) => {
    const name = data.name;
    const score = data.score;
    
    // Game over's information about the winner.
    const roundEndedInfo = document.getElementById("roundEndedInfo");
    roundEndedInfo.innerHTML = `<b>Game Over! <br> Winner is ${name} with ${score} points.</b>`

    // Clear the in-game information and return to menu after 5s
    setTimeout(() => {
        switchElement(onScreen, menu);
        const roundsInfo = document.getElementById("rounds");
        roundsInfo.innerText = "";
        const roundEndedInfo = document.getElementById("roundEndedInfo");
        roundEndedInfo.innerHTML = "";
        // Reset the scores
        Object.entries(scoresDict).forEach(([key, _]) => {
            scoresDict[key] = 0;
        });
    }, 5000);
});

// TODO...
// Treat the following messages:
// 'round_ended'
// 'game_over'

// Send the following:
// 'start_game'
// 'reset_game'
// 'submit_drawing'

// -----------------------------------------