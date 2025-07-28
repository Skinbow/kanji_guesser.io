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

function createGame() {
    const form = document.getElementById("gameForm");
    const nickname = form.nickname.value;
    if (nickname) {
        window.location.href = `/?nickname=${encodeURIComponent(nickname)}`;
    }
}

function joinGame() {
    const form = document.getElementById("gameForm");
    const nickname = form.nickname.value;
    const gamecode = form.gamecode.value;
    if (nickname) {
        window.location.href = `/game/${encodeURIComponent(gamecode)}?nickname=${encodeURIComponent(nickname)}`;
    }
}

// TODO...

// -----------------------------------------