const canvas = document.getElementById("pad");
const wrapper = document.getElementById("canvas-wrapper");
const ctx = canvas.getContext("2d");
const saveBtn = document.getElementById("save");
const clearBtn = document.getElementById("clear");
const undoBtn = document.getElementById("undo");
const redoBtn = document.getElementById("redo");

let strokes = [];
let redoStack = [];
let currentStroke = [];
let drawing = false;

function resizeCanvas() {
  const size = wrapper.clientWidth;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = size + "px";
  canvas.style.height = size + "px";

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.scale(dpr, dpr);
  ctx.lineCap = "round";
  ctx.lineWidth = 4;
  ctx.strokeStyle = "#000";

  redraw();
}
window.addEventListener("resize", resizeCanvas);
resizeCanvas();

function getPoint(e) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (e.clientX - rect.left),
    y: (e.clientY - rect.top)
  };
}

canvas.addEventListener("pointerdown", e => {
  drawing = true;
  currentStroke = [];
  currentStroke.push(getPoint(e));
});

canvas.addEventListener("pointermove", e => {
  if (!drawing) return;
  currentStroke.push(getPoint(e));
  redraw();
});

function endStroke() {
  if (drawing && currentStroke.length > 1) {
    strokes.push(currentStroke);
    redoStack = [];
    currentStroke = [];
    redraw();
  }
  drawing = false;
}

canvas.addEventListener("pointerup", endStroke);
canvas.addEventListener("pointerleave", endStroke);

clearBtn.onclick = () => {
  strokes = [];
  redoStack = [];
  currentStroke = [];
  redraw();
};

undoBtn.onclick = () => {
  if (strokes.length > 0) {
    redoStack.push(strokes.pop());
    redraw();
  }
};

redoBtn.onclick = () => {
  if (redoStack.length > 0) {
    strokes.push(redoStack.pop());
    redraw();
  }
};

saveBtn.onclick = async () => {
  const png = canvas.toDataURL("image/png");
  const res = await fetch("/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ png })
  });
  const j = await res.json();
  if (j.ok) console.log("Label :", j.label);
  else console.error("Erreur : ", j.error);
};

function redraw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (const stroke of strokes) {
    drawStroke(stroke);
  }

  if (drawing && currentStroke.length > 1) {
    drawStroke(currentStroke);
  }
}

function drawStroke(stroke) {
  if (stroke.length < 2) return;
  ctx.beginPath();
  ctx.moveTo(stroke[0].x, stroke[0].y);
  for (let i = 1; i < stroke.length; i++) {
    ctx.lineTo(stroke[i].x, stroke[i].y);
  }
  ctx.stroke();
}
socket.on("player_guessed", data => {
  alert(`🎉 ${data.playerNickname} a trouvé le bon kanji : ${data.kanji}`);
});