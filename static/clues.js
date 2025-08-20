// Print the information of the kanji for the clue giver
const clues = document.createElement("div");
clues.innerHTML = `
<p id="kanjiName" class="clues"></p>
<p id="furigana" class="clues"></p>
<p id="explanation" class="clues"></p>
<p id="construction" class="clues"></p>
<p id="example" class="clues"></p>
`
clues.id = "cluesInfo";