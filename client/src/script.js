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

const DEFAULT_ERROR_MSG = "⚠️ Error: Unable to reach AI service. Please try again later.";

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
    const response = await fetchWithRetry(`${API_BASE_URL}/agent`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(buildRunAgentInput(question)),
    });

    await consumeAgentStream(response, loadingMsg);
  } catch (err) {
    let errorMsg = DEFAULT_ERROR_MSG;
    if (err instanceof RateLimitedError) {
      errorMsg = "⏳ You're sending messages a little too quickly. Please wait a moment and try again.";
    }
    loadingMsg.textContent = errorMsg;
    loadingMsg.classList.remove("loading");
    console.error(err);
  }
}

// Builds an AG-UI RunAgentInput body. The backend (see server/app/routers/agent.py)
// keeps full conversation history server-side, keyed by threadId, so only the
// new user turn is sent here — not the whole message array.
function buildRunAgentInput(question) {
  return {
    threadId: getOrCreateSessionId(),
    runId: generateSessionId(),
    state: null,
    messages: [{ id: generateSessionId(), role: "user", content: question }],
    tools: [],
    context: [],
    forwardedProps: null,
  };
}

// Consumes the AG-UI SSE event stream from POST /agent and drives a single
// bot message bubble: incremental text as TEXT_MESSAGE_CONTENT deltas arrive,
// a "Searching..." state while a tool call is in flight, and CUSTOM events
// dispatched by name to a card renderer (see renderCustomEvent).
async function consumeAgentStream(response, targetMsg) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const ctx = {
    targetMsg,
    activeTextMessageId: null,
    currentText: "",
    textEl: null,
    hasContent: false,
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const event = parseAgUiEvent(rawEvent);
      if (!event || !event.type) continue;

      if (handleAgentEvent(event, ctx) === "stop") {
        return;
      }
    }
  }
}

function parseAgUiEvent(rawEvent) {
  const dataLines = rawEvent
    .split("\n")
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.slice("data: ".length));
  if (dataLines.length === 0) return null;
  try {
    return JSON.parse(dataLines.join("\n"));
  } catch {
    return null;
  }
}

// Clears the "Thinking..."/"Searching..." placeholder exactly once, the
// first time any real content (text or a card) arrives. Text and cards can
// arrive in either order (a tool call's card typically resolves before the
// model's trailing narration, but not always) and must coexist as siblings
// in the bubble afterward — neither should wipe the other out.
function ensureContentStarted(ctx) {
  if (!ctx.hasContent) {
    ctx.targetMsg.classList.remove("loading");
    ctx.targetMsg.innerHTML = "";
    ctx.hasContent = true;
  }
}

// Returns "stop" when the caller should stop reading the stream.
function handleAgentEvent(event, ctx) {
  switch (event.type) {
    case "TEXT_MESSAGE_START":
      ctx.activeTextMessageId = event.messageId;
      ctx.currentText = "";
      ctx.textEl = null;
      return;
    case "TEXT_MESSAGE_CONTENT":
      if (event.messageId !== ctx.activeTextMessageId) {
        ctx.activeTextMessageId = event.messageId;
        ctx.currentText = "";
        ctx.textEl = null;
      }
      ctx.currentText += event.delta;
      ensureContentStarted(ctx);
      if (!ctx.textEl) {
        ctx.textEl = document.createElement("div");
        ctx.textEl.className = "bot-text";
        ctx.targetMsg.appendChild(ctx.textEl);
      }
      ctx.textEl.textContent = ctx.currentText;
      return;
    case "TOOL_CALL_START":
      if (!ctx.hasContent) {
        ctx.targetMsg.textContent = "Searching...";
        ctx.targetMsg.classList.add("loading");
      }
      return;
    case "CUSTOM":
      renderCustomEvent(event, ctx);
      return;
    case "RUN_ERROR":
      ctx.targetMsg.classList.remove("loading");
      ctx.targetMsg.textContent = event.message || DEFAULT_ERROR_MSG;
      return "stop";
    case "RUN_FINISHED":
      ctx.targetMsg.classList.remove("loading");
      if (!ctx.hasContent) {
        ctx.targetMsg.textContent = "Sorry, I couldn’t find an answer right now.";
      }
      return "stop";
    default:
      return;
  }
}

// Dispatches a CUSTOM AG-UI event (see app/agent.py's _custom_event helper)
// to the right card renderer by name.
function renderCustomEvent(event, ctx) {
  ensureContentStarted(ctx);
  if (event.name === "book_card") {
    const book = event.value || {};
    ctx.targetMsg.appendChild(
      renderBookCard(book.title, book.author, book.first_publish_year, book.availability, book.cover_url, book.url),
    );
  } else if (event.name === "research_results") {
    ctx.targetMsg.appendChild(renderResearchResult(event.value || {}));
  } else if (event.name === "citation") {
    ctx.targetMsg.appendChild(renderCitationCard(event.value || {}));
  }
}

// Renders a citation CUSTOM event payload (see app.schemas.Citation on the
// backend) as a citation card: formatted text, a copy-to-clipboard button,
// and a style switcher that re-formats via GET /citation/{doi} instead of
// re-running the whole lookup_and_cite tool call.
function renderCitationCard(citation) {
  const card = document.createElement("div");
  card.className = "citation-card";

  const textEl = document.createElement("p");
  textEl.className = "citation-card-text";
  textEl.textContent = citation.formatted;
  card.appendChild(textEl);

  const controls = document.createElement("div");
  controls.className = "citation-card-controls";

  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.className = "citation-card-copy";
  copyBtn.textContent = "Copy";
  copyBtn.addEventListener("click", () => {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(textEl.textContent);
    }
    copyBtn.textContent = "Copied!";
    setTimeout(() => {
      copyBtn.textContent = "Copy";
    }, 1500);
  });
  controls.appendChild(copyBtn);

  if (citation.doi && citation.available_styles && citation.available_styles.length > 1) {
    const select = document.createElement("select");
    select.className = "citation-card-style-select";
    citation.available_styles.forEach((style) => {
      const option = document.createElement("option");
      option.value = style;
      option.textContent = style.toUpperCase();
      if (style === citation.style) option.selected = true;
      select.appendChild(option);
    });
    select.addEventListener("change", async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/citation/${citation.doi}?style=${encodeURIComponent(select.value)}`);
        if (!response.ok) return;
        const data = await response.json();
        textEl.textContent = data.formatted;
        citation.style = data.style;
      } catch {
        // Network hiccup: leave the previously formatted text in place.
      }
    });
    controls.appendChild(select);
  }

  card.appendChild(controls);
  return card;
}

// Renders a research_results CUSTOM event payload (see app.schemas.ResearchResult
// on the backend) as a result-list card: one entry per work, each with an
// expandable abstract instead of dumping the full text inline.
function renderResearchResult(result) {
  const container = document.createElement("div");
  container.className = "research-result";

  if (result.intro) {
    const intro = document.createElement("div");
    intro.className = "research-result-intro";
    intro.textContent = result.intro;
    container.appendChild(intro);
  }

  (result.works || []).forEach((work) => {
    container.appendChild(renderScholarlyWorkCard(work));
  });

  return container;
}

function renderScholarlyWorkCard(work) {
  const card = document.createElement("div");
  card.className = "work-card";

  const titleEl = document.createElement(work.doi ? "a" : "div");
  titleEl.className = "work-card-title";
  titleEl.textContent = work.year ? `${work.title} (${work.year})` : work.title;
  if (work.doi) {
    titleEl.href = work.doi;
    titleEl.target = "_blank";
    titleEl.rel = "noopener noreferrer";
  }
  card.appendChild(titleEl);

  const authorsEl = document.createElement("div");
  authorsEl.className = "work-card-authors";
  authorsEl.textContent = work.authors;
  card.appendChild(authorsEl);

  const meta = document.createElement("div");
  meta.className = "work-card-meta";

  const citationBadge = document.createElement("span");
  citationBadge.className = "work-card-citations";
  citationBadge.textContent = `${work.citation_count} citation${work.citation_count === 1 ? "" : "s"}`;
  meta.appendChild(citationBadge);

  const oaBadge = document.createElement("span");
  oaBadge.className = `work-card-oa work-card-oa--${work.is_oa ? "open" : "closed"}`;
  oaBadge.textContent = work.is_oa ? "Open access" : "Not open access";
  meta.appendChild(oaBadge);

  card.appendChild(meta);

  if (work.abstract) {
    const details = document.createElement("details");
    details.className = "work-card-abstract";
    const summary = document.createElement("summary");
    summary.textContent = "Abstract";
    details.appendChild(summary);
    const abstractText = document.createElement("p");
    abstractText.textContent = work.abstract;
    details.appendChild(abstractText);
    card.appendChild(details);
  }

  return card;
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

// Renders one book as a real card from data (title, author, availability,
// and — once a tool call supplies them, see Phase 9's book_card CUSTOM event
// — a cover image and an Open Library link-out) instead of prose.
function renderBookCard(title, author, year, availability, coverUrl, url) {
  const card = document.createElement("div");
  card.className = "book-card";

  if (coverUrl) {
    const cover = document.createElement("img");
    cover.className = "book-card-cover";
    cover.src = coverUrl;
    cover.alt = `Cover of ${title}`;
    card.appendChild(cover);
  }

  const body = document.createElement("div");
  body.className = "book-card-body";

  const titleEl = document.createElement(url ? "a" : "div");
  titleEl.className = "book-card-title";
  titleEl.textContent = year ? `${title} (${year})` : title;
  if (url) {
    titleEl.href = url;
    titleEl.target = "_blank";
    titleEl.rel = "noopener noreferrer";
  }
  body.appendChild(titleEl);

  const authorEl = document.createElement("div");
  authorEl.className = "book-card-author";
  authorEl.textContent = `by ${author}`;
  body.appendChild(authorEl);

  const badge = document.createElement("span");
  badge.className = `book-card-availability book-card-availability--${availability.trim().replace(/\s+/g, "-")}`;
  badge.textContent = availability;
  body.appendChild(badge);

  card.appendChild(body);
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
