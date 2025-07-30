// -----------------------------------------

// Handling socket
const socket = io();
socket.on("connect", () => {
    console.log(socket.id);
});

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

const gamecode = document.body.dataset.gamecode;
console.log("player_list_" + gamecode);

socket.on("player_list_" + gamecode, (data) => {
    console.log("Called");
    const nicknameList = data.player_nicknames;

    const playerListDiv = document.getElementById("player-list");
    playerListDiv.innerHTML = ""; // reset

    nicknameList.forEach((nickname) => {
        const p = document.createElement("p");
        console.log(nickname);
        p.textContent = nickname;
        playerListDiv.appendChild(p);
    });
});

// TODO...
// Treat the following messages:
// "player_list"
// "you_are_drawer"
// "someone_was_selected"
// 'timer_update'???
// 'show_answer'
// 'round_started'
// 'update_scores'
// 'game_over'

// Send the following:
// 'start_game'
// 'reset_game'
// 'submit_drawing'

// -----------------------------------------