// Get the title's GIF
const titleGif = document.getElementById("title-gif");
// After X seconds change the gif to the shaking title
setTimeout(() => {
    titleGif.src = "static/resources/KanjiGuessr2.gif";
}, 2500); 
// -----------------------------------------

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