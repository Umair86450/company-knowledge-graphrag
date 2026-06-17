let sessionId = null;

const usernameInput = document.getElementById("username");
const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send");
const composer = document.getElementById("composer");
const messages = document.getElementById("messages");
const newChatButton = document.getElementById("new-chat");

function syncEnabled() {
  const ready = usernameInput.value.trim().length > 0;
  messageInput.disabled = !ready;
  sendButton.disabled = !ready;
}

function inline(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

function renderMarkdown(text) {
  const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  let html = "";
  let listTag = null;

  const closeList = () => {
    if (listTag) {
      html += `</${listTag}>`;
      listTag = null;
    }
  };

  for (const line of escaped.split("\n")) {
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+\.\s+(.*)$/);
    if (bullet) {
      if (listTag !== "ul") { closeList(); html += "<ul>"; listTag = "ul"; }
      html += `<li>${inline(bullet[1])}</li>`;
    } else if (numbered) {
      if (listTag !== "ol") { closeList(); html += "<ol>"; listTag = "ol"; }
      html += `<li>${inline(numbered[1])}</li>`;
    } else if (line.trim() === "") {
      closeList();
    } else {
      closeList();
      html += `<p>${inline(line)}</p>`;
    }
  }
  closeList();
  return html;
}

function addBubble(text, kind) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${kind}`;
  if (kind === "assistant") {
    bubble.innerHTML = renderMarkdown(text);
  } else {
    bubble.textContent = text;
  }
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

newChatButton.addEventListener("click", () => {
  sessionId = null;
  messages.innerHTML = "";
  messageInput.focus();
});

usernameInput.addEventListener("input", syncEnabled);
syncEnabled();
