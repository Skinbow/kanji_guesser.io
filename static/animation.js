// Get the title's GIF
const titleGif = document.getElementById("title-gif");
// Ensures gif plays from start despite caching
titleGif.src = titleGif.src + "?" + new Date().getTime();
// After X seconds change the gif to the shaking title
setTimeout(() => {
    titleGif.src = "/static/resources/KanjiGuessr2.gif" + "?" + new Date().getTime();;
}, 2500); 

// Raining effect with kanjis + hiragana + katakana
const canvas = document.getElementById("matrixCanvas");
const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

const fontSize = 20;
const columns = Math.floor(canvas.width / fontSize);

const yPos = [];
const charAtPos = [];
const speed = [];
const characters = 
"あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん" +
"アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン" +
"日月火水木金土人大小中上下左右山川田口車門天気本文子女学校先生国年時行見来入出左右" +
"学年何高円子犬猫魚鳥花草空雨風雪川森石金土火水木" +
"早白赤青黒名花白耳口手足目耳口" +
"愛心力友話音気語読書文字電車電話";

// Initialization of the arrays
// Random offset for the start (so the raining start "beautifully")
// Random choice of char
// Random speed (relatively slow, seems better)
for (let i = 0; i < columns; i++) {
    yPos[i] = -Math.random() * canvas.height / 2;
    charAtPos[i] = characters.charAt(Math.floor(Math.random() * characters.length));
    speed[i] = Math.random() * (0.15 - 0.1) + 0.1;
}

// Function to draw the raining effect
function draw() {
    ctx.fillStyle = "rgba(206, 35, 19, 0.2)"; // Font color (dark red of the palette)
    ctx.font = fontSize + "px monospace";

    // At each call, update pos/reset randomly certains positions, chars and speeds
    for (let i = 0; i < yPos.length; i++) {
        const text = charAtPos[i];
        if (yPos[i] * fontSize > canvas.height + fontSize) {
            if (Math.random() > 0.975) {
                yPos[i] = 0;
                charAtPos[i] = characters.charAt(Math.floor(Math.random() * characters.length));
                speed[i] = Math.random() * (0.15 - 0.1) + 0.1;
            }
        }
        else {
            ctx.clearRect(i * fontSize, (yPos[i] - 1) * fontSize - 1, fontSize, fontSize + 1);
            ctx.fillText(text, i * fontSize, yPos[i] * fontSize);
            yPos[i] += speed[i];
        }
    }
    requestAnimationFrame(draw);
}
draw(); // First call
// ----------------------------------------------------------------------------------------
