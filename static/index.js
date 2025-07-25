function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
}

socket.on("connect", () => {
  console.log(socket.id);
});

socket.on("connect_error", () => {
  console.log("whoops");
});

socket.on("game_start", () => {
  socket.emit('request_top_number');
  socket.emit("game_start_ack");
});

socket.on("end_game", () => {
    document.cookie = "";
    window.location = "/";
    console.log(socket.id);
});

// Show button when player count reaches 10
socket.on('player_list', (data) => {
    const playerids = data.playerids;
    const ingame_playerids = data.ingame_playerids;
    const playernicknames = data.playernicknames;
    const NUMBER_OF_PLAYERS = data.NUMBER_OF_PLAYERS;
    // if (playerids.length >= NUMBER_OF_PLAYERS) {
    //     document.getElementById('startButton').style.display = 'block';
    // } else {
    //     document.getElementById('startButton').style.display = 'none';
    // }

    const list = document.getElementById("playerList");
    if (!list) return;
    list.innerHTML = "";
    for (let i = 0; i < playerids.length; i++) {
        const li = document.createElement("li");
        li.textContent = playernicknames[i];
        // console.log(playernicknames[i]);
        // console.log(playerids[i]);
        // console.log("Mycookie: " + getCookie('playerid'));
        if (playerids[i] === getCookie('playerid')) {
            li.style.fontWeight = 'bold'; // Highlight the current player
            li.textContent += ' (わたし)'; // Add "(You)" to the current player
        }
        list.appendChild(li);
    }
});

// Updates leaderboard
socket.on('update_top_number', (data) => {
    document.getElementById('top_number').innerHTML = "🔝 " + "Current Top " + data.number+":";
});

// Emit when someone clicks the button
// document.getElementById('startButton').addEventListener('click', () => {
//     socket.emit('start_game');
//     if (document.getElementById('startButton').innerText === 'Start Game') {
//         socket.emit('reset_game');
//     }

// });

// Signals whose turn it is
socket.on('someone_was_selected', (data) => {
    const selectedPlayerId = data.selectedPlayerId;
    const selectedPlayerNickname = data.selectedPlayerNickname;
    const selectedCharacter = data.selectedCharacter;
    const selectedImage = data.characterImage;
    
    console.log("Selected player is:", selectedPlayerNickname);

    if (selectedPlayerId === getCookie('playerid')) {
        document.getElementById('result').innerHTML = '🎯 You were chosen!';

        document.getElementById("canvas-wrapper").innerHTML = `
            <img src="/static/images/${selectedImage}" alt="${selectedCharacter}" class="canvas-wrapper">
        `;
        document.getElementById('save').style.display = 'none';
        document.getElementById('clear').style.display = 'none';
    } else {
        document.getElementById('result').innerHTML = `🎯 ${selectedPlayerNickname} was chosen!`;
        document.getElementById("canvas-wrapper").innerHTML = `
            <canvas id="pad"></canvas>
        `;
        initCanvas();
        document.getElementById('save').style.display = 'block';
        document.getElementById('clear').style.display = 'block';
    }
    document.getElementById('startButton').style.display = 'none';
});

socket.on('update_scores', (top_scores) => {
    const scoreList = document.getElementById("scoreList");
    if (!scoreList) return;
    scoreList.innerHTML = "";  
    top_scores.forEach(player => {
        const li = document.createElement("li");
        li.textContent = `${player.name}: ${player.score}`;
        scoreList.appendChild(li);
    });
    
});

socket.on('timer_update', (data) => {
    const display = document.getElementById("timerDisplay");
    display.textContent = "⏱️ Time left: " + data.time;
});

socket.on('show_answer', (data) => {
    const selectedCharacter = data.selectedCharacter;
    const selectedImage = data.characterImage;
    document.getElementById("canvas-wrapper").innerHTML = `
        <img src="/static/images/${selectedImage}" alt="${selectedCharacter}" class="canvas-wrapper">
    `;
    document.getElementById('startButton').style.display = 'block';
    document.getElementById('startButton').textContent = 'Next Round';
    document.getElementById('save').style.display = 'none';
    document.getElementById('clear').style.display = 'none';
});

socket.on('round_started', (data) => {
    const current_round = data.current_round;
    const total_rounds = data.total_rounds;
    document.getElementById('roundDisplay').textContent = `🎬 Round ${current_round} of ${total_rounds}`;
});

socket.on('game_over', (data) => {
    document.getElementById("canvas-wrapper").innerHTML = `
        <h2>Game Over!</h2>
        <p>Final Scores:</p>
        <ul id="finalScoreList"></ul>
    `;
    document.getElementById('startButton').textContent = 'Start Game';
    document.getElementById('startButton').style.display = 'block';
    const scoreList = document.getElementById("finalScoreList");
    if (!scoreList) return;
    scoreList.innerHTML = "";
    data.forEach(player => {
        const li = document.createElement("li");
        li.textContent = `${player.name}: ${player.score}`;
        if (player.name === sessionStorage.getItem('playerid')) {
            li.style.fontWeight = 'bold'; // Highlight the current player
            li.textContent += ' (わたし)'; // Add "(You)" to the current player
        }
        scoreList.appendChild(li);
    });
});