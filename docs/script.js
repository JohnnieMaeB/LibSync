const sendBtn = document.getElementById("sendBtn");
const userInput = document.getElementById("userInput");
const chatBox = document.getElementById("chatBox");

const SESSION_STORAGE_KEY = "libsync_session_id";
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 600;

class RateLimitedError extends Error {}
class ServiceDownError extends Error {}

if (sendBtn) {
  sendBtn.addEventListener("click", sendMessage);
}
if (userInput) {
  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

function getOrCreateSessionId() {
  let sessionId = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }
  return sessionId;
}

function generateSessionId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for browsers/test environments without crypto.randomUUID.
  return `sid-${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithRetry(url, options) {
  let lastNetworkError;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (networkError) {
      lastNetworkError = networkError;
      if (attempt < MAX_RETRIES) {
        await sleep(RETRY_DELAY_MS * (attempt + 1));
        continue;
      }
      throw new ServiceDownError("Unable to reach the AI service.");
    }

    if (response.status === 429) {
      throw new RateLimitedError("Too many requests.");
    }
    if (response.ok) {
      return response;
    }
    if (response.status >= 500 && attempt < MAX_RETRIES) {
      await sleep(RETRY_DELAY_MS * (attempt + 1));
      continue;
    }
    throw new ServiceDownError(`Request failed with status ${response.status}`);
  }
  throw lastNetworkError || new ServiceDownError("Request failed.");
}

async function sendMessage() {
  const question = userInput.value.trim();
  if (!question) return;

  appendMessage("user", question);
  userInput.value = "";
  userInput.style.height = "auto"; // Reset height

  const loadingMsg = appendMessage("bot", "Thinking...");
  loadingMsg.classList.add("loading");

  try {
    // Streaming means the connection opens (and the "Thinking..." bubble
    // starts updating) right away instead of waiting for the full reply —
    // this is what actually hides Render's cold-start latency.
    const response = await fetchWithRetry(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: question, session_id: getOrCreateSessionId() }),
    });

    await consumeChatStream(response, loadingMsg);
  } catch (err) {
    let errorMsg = "⚠️ Error: Unable to reach AI service. Please try again later.";
    if (err instanceof RateLimitedError) {
      errorMsg = "⏳ You're sending messages a little too quickly. Please wait a moment and try again.";
    }
    loadingMsg.textContent = errorMsg;
    loadingMsg.classList.remove("loading");
    console.error(err);
  }
}

async function consumeChatStream(response, targetMsg) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sawContent = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const { event, data } = parseSseEvent(rawEvent);
      if (!event) continue;

      if (event === "session") {
        if (data.session_id) {
          localStorage.setItem(SESSION_STORAGE_KEY, data.session_id);
        }
      } else if (event === "text") {
        sawContent = true;
        targetMsg.classList.remove("loading");
        targetMsg.innerHTML = "";
        targetMsg.textContent = data.text;
      } else if (event === "books") {
        sawContent = true;
        targetMsg.classList.remove("loading");
        renderBookResult(targetMsg, data);
      } else if (event === "error") {
        targetMsg.classList.remove("loading");
        targetMsg.textContent = data.error || "⚠️ Error: Unable to reach AI service. Please try again later.";
        return;
      } else if (event === "done") {
        targetMsg.classList.remove("loading");
        if (!sawContent) {
          targetMsg.textContent = "Sorry, I couldn’t find an answer right now.";
        }
        return;
      }
    }
  }
}

function parseSseEvent(rawEvent) {
  let event = null;
  let data = null;
  for (const line of rawEvent.split("\n")) {
    if (line.startsWith("event: ")) {
      event = line.slice("event: ".length);
    } else if (line.startsWith("data: ")) {
      try {
        data = JSON.parse(line.slice("data: ".length));
      } catch {
        data = {};
      }
    }
  }
  return { event, data };
}

// Fallback pattern for the (rare, non-streaming) case a plain-text reply
// still contains prose-formatted book lines, e.g.:
// - "Project Hail Mary" by Andy Weir (2021) — availability: lendable
const BOOK_LINE_PATTERN = /^-\s*"(.+)"\s*by\s*(.+?)(?:\s*\((\d{4})\))?\s*—\s*availability:\s*(.+)$/;

function appendMessage(sender, text) {
  const msg = document.createElement("div");
  msg.className = sender;
  renderPlainTextContent(msg, text);
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
  return msg;
}

function renderPlainTextContent(el, text) {
  const lines = text.split("\n");
  const nonEmptyLines = lines.filter((line) => line.trim());
  const bookMatches = nonEmptyLines.map((line) => line.match(BOOK_LINE_PATTERN));

  if (nonEmptyLines.length > 0 && bookMatches.every(Boolean)) {
    bookMatches.forEach((match) => {
      el.appendChild(renderBookCard(match[1], match[2], match[3], match[4]));
    });
  } else {
    el.textContent = text;
  }
}

// Renders the /chat/stream "books" event payload: { intro, books: [...] }
// (see app.schemas.BookResult on the backend) as real cards from data,
// instead of parsing it back out of prose.
function renderBookResult(el, bookResult) {
  el.innerHTML = "";
  if (bookResult.intro) {
    const intro = document.createElement("div");
    intro.className = "book-result-intro";
    intro.textContent = bookResult.intro;
    el.appendChild(intro);
  }
  (bookResult.books || []).forEach((book) => {
    el.appendChild(renderBookCard(book.title, book.author, book.first_publish_year, book.availability));
  });
  chatBox.scrollTop = chatBox.scrollHeight;
}

function renderBookCard(title, author, year, availability) {
  const card = document.createElement("div");
  card.className = "book-card";

  const titleEl = document.createElement("div");
  titleEl.className = "book-card-title";
  titleEl.textContent = year ? `${title} (${year})` : title;
  card.appendChild(titleEl);

  const authorEl = document.createElement("div");
  authorEl.className = "book-card-author";
  authorEl.textContent = `by ${author}`;
  card.appendChild(authorEl);

  const badge = document.createElement("span");
  badge.className = `book-card-availability book-card-availability--${availability.trim().replace(/\s+/g, "-")}`;
  badge.textContent = availability;
  card.appendChild(badge);

  return card;
}

// Auto-resize textarea
if (userInput) {
  userInput.addEventListener("input", () => {
    userInput.style.height = "auto";
    const newHeight = Math.min(userInput.scrollHeight, 120); // max height of 120px
    userInput.style.height = newHeight + "px";
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { sendMessage, appendMessage };
}
