let sessionId = null;

const usernameInput = document.getElementById("username");
const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send");
const composer = document.getElementById("composer");
const messages = document.getElementById("messages");

function syncEnabled() {
  const ready = usernameInput.value.trim().length > 0;
  messageInput.disabled = !ready;
  sendButton.disabled = !ready;
}

function addBubble(text, kind) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${kind}`;
  bubble.textContent = text;
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

async function sendMessage(username, message) {
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, message, session_id: sessionId }),
  });
  if (!response.ok) {
    throw new Error("Request failed");
  }
  return response.json();
}

composer.addEventListener("submit", async (event) => {
  event.preventDefault();

  const username = usernameInput.value.trim();
  const message = messageInput.value.trim();
  if (!username || !message) {
    return;
  }

  addBubble(message, "user");
  messageInput.value = "";
  sendButton.disabled = true;

  const loading = addBubble("Thinking...", "assistant loading");

  try {
    const data = await sendMessage(username, message);
    sessionId = data.session_id;
    loading.remove();
    addBubble(data.reply, "assistant");
  } catch (error) {
    loading.remove();
    addBubble("Something went wrong. Please try again.", "error");
  } finally {
    sendButton.disabled = false;
    messageInput.focus();
  }
});

usernameInput.addEventListener("input", syncEnabled);
syncEnabled();
