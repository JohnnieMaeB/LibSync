const sendBtn = document.getElementById("sendBtn");
const userInput = document.getElementById("userInput");
const chatBox = document.getElementById("chatBox");


sendBtn.addEventListener("click", sendMessage);
userInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

async function sendMessage() {
  const question = userInput.value.trim();
  if (!question) return;

  appendMessage("user", question);
  userInput.value = "";

  const loadingMsg = appendMessage("bot", "Thinking...");
  loadingMsg.classList.add("loading");

  try {
    const response = await fetch("https://libsync.onrender.com/chat", {  // <-- point to your backend
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: question }),  // send the user question
    });

    const data = await response.json();
    const botReply = data?.reply || "Sorry, I couldn’t find an answer right now.";


    loadingMsg.remove();
    appendMessage("bot", botReply);
  } catch (err) {
    loadingMsg.remove();
    appendMessage("bot", "⚠️ Error: Unable to reach AI service. Please try again later.");
    console.error(err);
  }
}

function appendMessage(sender, text) {
  const msg = document.createElement("div");
  msg.className = sender;
  msg.innerHTML = text;
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
  return msg;
}
