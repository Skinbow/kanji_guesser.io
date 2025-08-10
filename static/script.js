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