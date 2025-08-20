// Drawing zone and its button
const drawingZone = document.createElement("div");
drawingZone.innerHTML = `
<div id="drawing-wrapper">
    <canvas id="drawCanvas" width="400" height="400"></canvas>
    <div id="button-container">
        <div role="button" id="clearBtn" tabindex="0" class="button" onclick="clearCanva()">
            <img src="${clearIcon}" class="icon">
        </div>
        <div role="button" tabindex="0" class="button" onclick="undo()">
            <img src="${undoIcon}" class="icon">
        </div>
        <div role="button" tabindex="0" class="button" onclick="redo()">
            <img src="${redoIcon}" class="icon">
        </div>
    </div>
</div>
<div class="grid-container">
  <div class="cell" id="cell-1">一</div>
  <div class="cell" id="cell-2">二</div>
  <div class="cell" id="cell-3">三</div>
  <div class="cell" id="cell-4">四</div>
  <div class="cell" id="cell-5">五</div>
  <div class="cell" id="cell-6">六</div>
  <div class="cell" id="cell-7">七</div>
  <div class="cell" id="cell-8">八</div>
  <div class="cell" id="cell-9">九</div>
  <div class="cell" id="cell-10">十</div>
</div>
`;
drawingZone.id = "drawing";

// Actual ID of the element on screen (default : "menu")
let onScreen = "menu";

// Function to swap two element in the DOM
function switchElement(toChangeID, newElement) {
    const toChange = document.getElementById(toChangeID);
    if (!toChange) return; /* Invalid element */
    toChange.replaceWith(newElement);
    // Change the value of the onScreen element
    onScreen = newElement.id;
    clearCanva();
}

function toggleTitle() {
    const titleContainer = document.getElementById("title-container");
    if (titleContainer) {
        titleContainer.hidden = true;
    }
}

// Start the game by removing the title and changing the menu in the drawing canva
function startGame() {
    socket.emit("start_game");
}

const drawCanvas = drawingZone.querySelector("#drawCanvas");
const context = drawCanvas.getContext("2d", { willReadFrequently: true });
let isDrawing = false;
drawCanvas.style.touchAction = "none";

// Event listeners on the canva
drawCanvas.addEventListener("pointerdown", startDrawing);
drawCanvas.addEventListener("pointerup", stopDrawing);
drawCanvas.addEventListener("pointerleave", stopDrawing);
drawCanvas.addEventListener("pointermove", drawing);

for (i = 0; i < 10; i++) {
    cell = drawingZone.querySelector(`#cell-${i+1}`);
    if (cell) {
        cell.addEventListener("click", (event) => {
            console.log(`Submit : ${event.target.textContent}`);
            socket.emit("submit_choice", { "choice": event.target.textContent});
        });
    }
}

let lastPos = null;

// Start of the drawing routine
function startDrawing (event) {
    event.preventDefault();
    isDrawing = true;
    lastPos = getPosition(event);
}

// Stop of the drawing routine
function stopDrawing (event) {
    event.preventDefault();
    if (isDrawing) {
        isDrawing = false;
        lastPos = null;
        saveState();
        const imageData = drawCanvas.toDataURL("image/png");
        socket.emit("get_characters", {image: imageData})
    }
}

// Handle the drawing on the canva
function drawing(event) {
    event.preventDefault();
    if (!isDrawing || !lastPos) return;

    const currPos = getPosition(event);
    const pressure =  event.pressure || 1;

    const midPoint = {
        x: (lastPos.x + currPos.x) / 2,
        y: (lastPos.y + currPos.y) / 2  
    }

    context.beginPath();
    context.lineWidth = pressure * 5;
    context.lineCap = "round";
    context.strokeStyle = "#000";
    context.moveTo(lastPos.x, lastPos.y);
    context.lineTo(currPos.x, currPos.y);
    context.stroke();
    context.closePath();

    lastPos = currPos;
}

// Return the relative position to the canva
function getPosition(event) {
    const rect = drawCanvas.getBoundingClientRect();
    return {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
    }
}

// Button handle to clear the canva
function clearCanva() {
    context.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    saveState();
}

// History to handle undo/redo
let history = [];
let currState = 0;

// Save the state of the canva in the history
function saveState() {
    history = history.slice(0, currState); // Cut the old futures

    history.push(context.getImageData(0, 0, drawCanvas.width, drawCanvas.height));

    if (history.length > 20) { // 20 states maximum
        history.shift();
    }
    else {
        currState++;
    }
}

// Undo an action
function undo() {
    if (currState > 1) {
        currState--;
        context.putImageData(history[currState - 1], 0, 0);
        const imageData = drawCanvas.toDataURL("image/png");
        socket.emit("get_characters", {image: imageData})
    }
}

// Redo an action
function redo() {
    if (currState < history.length) {
        currState++;
        context.putImageData(history[currState - 1], 0, 0);
        const imageData = drawCanvas.toDataURL("image/png");
        socket.emit("get_characters", {image: imageData})
    }
}

saveState(); // Save the blank canvas