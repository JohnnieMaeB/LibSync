/**
 * @jest-environment jsdom
 */

// jsdom doesn't provide TextEncoder/TextDecoder; real browsers always do.
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Mock the fetch function
global.fetch = jest.fn();

// Mock DOM elements — mirrors the real index.html structure closely enough
// to exercise the Tier 3 additions (chips, capability line, scroll button)
// alongside the original chat elements.
document.body.innerHTML = `
    <p id="capabilityLine">
      <button type="button" id="capabilityDismiss"></button>
    </p>
    <main id="chatBox">
      <div id="suggestionChips"></div>
    </main>
    <button type="button" id="scrollToLatest" hidden></button>
    <textarea id="userInput"></textarea>
    <button id="sendBtn"></button>
`;

// config.js sets the shared API_BASE_URL global that script.js reads.
require('./config.js');
const { appendMessage, sendMessage, regenerateLastReply } = require('./script.js');

// Builds one AG-UI SSE event chunk, matching the wire format encoded by
// pydantic_ai's AGUIEventStream: a single `data: {...}` line per event.
function aguiEvent(payload) {
    return `data: ${JSON.stringify(payload)}\n\n`;
}

// Builds a fetch Response-like object whose body streams the given SSE
// event strings one chunk per reader.read() call, mirroring how the real
// StreamingResponse endpoint (POST /agent) delivers server-sent events.
function makeStreamingResponse(chunks, { status = 200, ok = true } = {}) {
    let index = 0;
    const encoder = new TextEncoder();
    return {
        ok,
        status,
        headers: { get: () => 'text/event-stream' },
        body: {
            getReader() {
                return {
                    async read() {
                        if (index >= chunks.length) {
                            return { done: true, value: undefined };
                        }
                        const value = encoder.encode(chunks[index]);
                        index += 1;
                        return { done: false, value };
                    },
                };
            },
        },
    };
}

function textMessageEvents(messageId, texts) {
    const events = [aguiEvent({ type: 'TEXT_MESSAGE_START', messageId, role: 'assistant' })];
    for (const text of texts) {
        events.push(aguiEvent({ type: 'TEXT_MESSAGE_CONTENT', messageId, delta: text }));
    }
    events.push(aguiEvent({ type: 'TEXT_MESSAGE_END', messageId }));
    return events;
}

// A message's visible reply text lives in a nested .bot-text element (or,
// for error bubbles, alongside a Retry button) — not the whole bubble's
// textContent, which now also carries grounding tags and hover actions.
function botTextOf(msgEl) {
    const el = msgEl.querySelector('.bot-text');
    return el ? el.textContent : null;
}

// #chatBox hosts #suggestionChips as a real child (matching index.html), so
// a blanket innerHTML='' reset between tests would permanently detach it —
// clear only the message bubbles instead.
function resetChatBox() {
    const chatBox = document.getElementById('chatBox');
    [...chatBox.children].forEach((child) => {
        if (child.id !== 'suggestionChips') child.remove();
    });
}

// #suggestionChips is a permanent chatBox.children[0], so index-based
// lookups on message bubbles need to skip it.
function messageChildren(chatBoxEl) {
    return [...chatBoxEl.children].filter((el) => el.id !== 'suggestionChips');
}

describe('appendMessage', () => {
    beforeEach(() => {
        resetChatBox();
    });

    test('should append a user message to the chat box', () => {
        appendMessage('user', 'Hello');
        const chatBox = document.getElementById('chatBox');
        expect(messageChildren(chatBox).length).toBe(1);
        expect(messageChildren(chatBox)[0].className).toBe('user');
        expect(messageChildren(chatBox)[0].textContent).toBe('Hello');
    });

    test('should append a bot message to the chat box', () => {
        appendMessage('bot', 'Hi there');
        const chatBox = document.getElementById('chatBox');
        expect(messageChildren(chatBox).length).toBe(1);
        expect(messageChildren(chatBox)[0].className).toBe('bot');
        expect(messageChildren(chatBox)[0].textContent).toBe('Hi there');
    });

    test('should render book result lines as book cards', () => {
        const text = '- "Project Hail Mary" by Andy Weir (2021) — availability: lendable';
        appendMessage('bot', text);
        const chatBox = document.getElementById('chatBox');
        const card = chatBox.querySelector('.book-card');
        expect(card).not.toBeNull();
        expect(card.querySelector('.book-card-title').textContent).toBe('Project Hail Mary (2021)');
        expect(card.querySelector('.book-card-author').textContent).toBe('by Andy Weir');
        expect(card.querySelector('.book-card-availability').textContent).toBe('lendable');
    });
});

describe('safe markdown rendering', () => {
    beforeEach(() => {
        resetChatBox();
    });

    test('renders **bold**, *italic*, and [links](url) as real elements', () => {
        appendMessage('bot', 'Try **bold** and *italic* and [Open Library](https://openlibrary.org).');
        const msg = messageChildren(document.getElementById('chatBox'))[0];
        expect(msg.querySelector('strong').textContent).toBe('bold');
        expect(msg.querySelector('em').textContent).toBe('italic');
        const link = msg.querySelector('a');
        expect(link.textContent).toBe('Open Library');
        expect(link.href).toBe('https://openlibrary.org/');
        expect(link.target).toBe('_blank');
        expect(link.rel).toBe('noopener noreferrer');
    });

    test('never renders raw HTML from model output as live markup (XSS-safe by default)', () => {
        appendMessage('bot', 'Ignore prior instructions <img src=x onerror=alert(1)> and <script>alert(2)</script>');
        const msg = messageChildren(document.getElementById('chatBox'))[0];
        expect(msg.querySelector('img')).toBeNull();
        expect(msg.querySelector('script')).toBeNull();
        expect(msg.textContent).toContain('<img src=x onerror=alert(1)>');
        expect(msg.textContent).toContain('<script>alert(2)</script>');
    });
});

describe('suggestion chips', () => {
    beforeEach(() => {
        resetChatBox();
        document.getElementById('suggestionChips').classList.remove('hidden');
        global.fetch.mockReset();
    });

    test('renders one chip per suggested prompt', () => {
        const chips = document.getElementById('suggestionChips').querySelectorAll('.suggestion-chip');
        expect(chips.length).toBeGreaterThan(0);
        chips.forEach((chip) => expect(chip.textContent.length).toBeGreaterThan(0));
    });

    test('clicking a chip sends it as the next message and hides the chip tray', () => {
        const container = document.getElementById('suggestionChips');
        const chip = container.querySelector('.suggestion-chip');
        const promptText = chip.textContent;

        // The click kicks off an async request we don't need to resolve for
        // this assertion — the synchronous prefix of sendMessage (clearing
        // the input, appending the user bubble, hiding the chips) already
        // runs before the first await, per the existing sendMessage tests.
        fetch.mockResolvedValueOnce(new Promise(() => {}));

        chip.dispatchEvent(new Event('click', { bubbles: true }));

        const chatBox = document.getElementById('chatBox');
        expect(chatBox.querySelector('.user').textContent).toBe(promptText);
        expect(container.classList.contains('hidden')).toBe(true);
    });
});

describe('sendMessage', () => {
    let userInput;
    let sendBtn;

    beforeEach(() => {
        userInput = document.getElementById('userInput');
        sendBtn = document.getElementById('sendBtn');
        resetChatBox();
        global.fetch.mockReset();
        localStorage.clear();
        jest.useFakeTimers();
    });

    afterEach(() => {
        jest.useRealTimers();
    });

    test('should not send a message if the input is empty', async () => {
        userInput.value = '';
        await sendMessage();
        expect(fetch).not.toHaveBeenCalled();
    });

    test('should post an AG-UI RunAgentInput to /agent with a threadId and the new user turn', async () => {
        userInput.value = 'Test message';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                ...textMessageEvents('msg-1', ['Test', ' reply']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        expect(fetch).toHaveBeenCalledTimes(1);
        const [url, options] = fetch.mock.calls[0];
        expect(url).toBe('https://libsync.onrender.com/agent');
        const body = JSON.parse(options.body);
        expect(typeof body.threadId).toBe('string');
        expect(body.threadId.length).toBeGreaterThan(0);
        expect(body.messages).toHaveLength(1);
        expect(body.messages[0]).toMatchObject({ role: 'user', content: 'Test message' });

        const chatBox = document.getElementById('chatBox');
        expect(messageChildren(chatBox).length).toBe(2); // user message + bot reply
        expect(messageChildren(chatBox)[1].className).toBe('bot');
        expect(botTextOf(messageChildren(chatBox)[1])).toBe('Test reply');
        expect(localStorage.getItem('libsync_session_id')).toBe(body.threadId);
    });

    test('should reuse the same threadId across requests', async () => {
        fetch.mockImplementation(async () =>
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                ...textMessageEvents('msg-1', ['ok']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        userInput.value = 'first';
        await sendMessage();
        userInput.value = 'second';
        await sendMessage();

        const firstBody = JSON.parse(fetch.mock.calls[0][1].body);
        const secondBody = JSON.parse(fetch.mock.calls[1][1].body);
        expect(secondBody.threadId).toBe(firstBody.threadId);
    });

    test('should show a "Searching..." state while a tool call is in flight, then the grounded reply', async () => {
        userInput.value = 'Is Project Hail Mary available?';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({ type: 'TOOL_CALL_START', toolCallId: 'call-1', toolCallName: 'search_catalog' }),
                aguiEvent({ type: 'TOOL_CALL_RESULT', toolCallId: 'call-1', content: 'Project Hail Mary — lendable' }),
                ...textMessageEvents('msg-1', ['Yes, it is available.']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        expect(botTextOf(messageChildren(chatBox)[1])).toBe('Yes, it is available.');
        expect(messageChildren(chatBox)[1].classList.contains('loading')).toBe(false);
    });

    test('should render a book_card CUSTOM event as a real card with cover and link-out', async () => {
        userInput.value = 'Is Project Hail Mary available?';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({
                    type: 'CUSTOM',
                    name: 'book_card',
                    value: {
                        title: 'Project Hail Mary',
                        author: 'Andy Weir',
                        first_publish_year: 2021,
                        availability: 'lendable',
                        cover_url: 'https://covers.openlibrary.org/b/id/12345-M.jpg',
                        url: 'https://openlibrary.org/works/OL123W',
                    },
                }),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        const botMsg = messageChildren(chatBox)[1];
        const card = botMsg.querySelector('.book-card');
        expect(card).not.toBeNull();
        expect(card.querySelector('.book-card-title').textContent).toBe('Project Hail Mary (2021)');
        expect(card.querySelector('.book-card-availability').textContent).toBe('lendable');
        expect(card.querySelector('.book-card-cover').src).toBe('https://covers.openlibrary.org/b/id/12345-M.jpg');
        const titleLink = card.querySelector('a.book-card-title');
        expect(titleLink).not.toBeNull();
        expect(titleLink.href).toBe('https://openlibrary.org/works/OL123W');
    });

    test('should render multiple book_card CUSTOM events from one tool call as separate cards', async () => {
        userInput.value = 'Any Andy Weir books?';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({
                    type: 'CUSTOM',
                    name: 'book_card',
                    value: { title: 'Project Hail Mary', author: 'Andy Weir', first_publish_year: 2021, availability: 'lendable' },
                }),
                aguiEvent({
                    type: 'CUSTOM',
                    name: 'book_card',
                    value: { title: 'The Martian', author: 'Andy Weir', first_publish_year: 2011, availability: 'checked out' },
                }),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        const botMsg = messageChildren(chatBox)[1];
        const cards = botMsg.querySelectorAll('.book-card');
        expect(cards.length).toBe(2);
        expect(cards[0].querySelector('.book-card-title').textContent).toBe('Project Hail Mary (2021)');
        expect(cards[1].querySelector('.book-card-title').textContent).toBe('The Martian (2011)');
    });

    test('should keep a card visible when narration text streams in after it (not before)', async () => {
        // Regression test: the real event order for a tool call is
        // TOOL_CALL_RESULT -> CUSTOM (the card) -> TEXT_MESSAGE_* (the
        // model's trailing narration). Text arriving after a card must
        // append alongside it, not replace it.
        userInput.value = 'Is Project Hail Mary available?';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({
                    type: 'CUSTOM',
                    name: 'book_card',
                    value: { title: 'Project Hail Mary', author: 'Andy Weir', first_publish_year: 2021, availability: 'lendable' },
                }),
                ...textMessageEvents('msg-1', ['I found it in our catalog!']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        const botMsg = messageChildren(chatBox)[1];
        expect(botMsg.querySelector('.book-card')).not.toBeNull();
        expect(botMsg.querySelector('.book-card-title').textContent).toBe('Project Hail Mary (2021)');
        expect(botMsg.textContent).toContain('I found it in our catalog!');
    });

    test('should render a research_results CUSTOM event as a result-list card', async () => {
        userInput.value = 'Find recent papers on large language models';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({
                    type: 'CUSTOM',
                    name: 'research_results',
                    value: {
                        intro: 'Found 1 work(s) for "large language models":',
                        works: [
                            {
                                title: 'ChatGPT for good?',
                                authors: 'Enkelejda Kasneci',
                                year: 2023,
                                citation_count: 5340,
                                is_oa: true,
                                doi: 'https://doi.org/10.1016/j.lindif.2023.102274',
                                abstract: 'Large language models help.',
                            },
                        ],
                    },
                }),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        const botMsg = messageChildren(chatBox)[1];
        expect(botMsg.querySelector('.research-result-intro').textContent).toBe('Found 1 work(s) for "large language models":');
        const card = botMsg.querySelector('.work-card');
        expect(card).not.toBeNull();
        expect(card.querySelector('.work-card-title').textContent).toBe('ChatGPT for good? (2023)');
        expect(card.querySelector('.work-card-title').tagName).toBe('A');
        expect(card.querySelector('.work-card-title').href).toBe('https://doi.org/10.1016/j.lindif.2023.102274');
        expect(card.querySelector('.work-card-authors').textContent).toBe('Enkelejda Kasneci');
        expect(card.querySelector('.work-card-citations').textContent).toBe('5340 citations');
        expect(card.querySelector('.work-card-oa').textContent).toBe('Open access');
        expect(card.querySelector('.work-card-abstract p').textContent).toBe('Large language models help.');
    });

    test('should render a citation CUSTOM event as a citation card with copy and style controls', async () => {
        userInput.value = 'Cite this in APA: 10.1016/j.lindif.2023.102274';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({
                    type: 'CUSTOM',
                    name: 'citation',
                    value: {
                        formatted: 'Kasneci, E. (2023). ChatGPT for good?',
                        style: 'apa',
                        doi: '10.1016/j.lindif.2023.102274',
                        available_styles: ['apa', 'chicago', 'mla'],
                    },
                }),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        const botMsg = messageChildren(chatBox)[1];
        const card = botMsg.querySelector('.citation-card');
        expect(card).not.toBeNull();
        expect(card.querySelector('.citation-card-text').textContent).toBe('Kasneci, E. (2023). ChatGPT for good?');
        expect(card.querySelector('.citation-card-copy')).not.toBeNull();

        const select = card.querySelector('.citation-card-style-select');
        expect(select).not.toBeNull();
        expect(Array.from(select.options).map((o) => o.value)).toEqual(['apa', 'chicago', 'mla']);
        expect(select.value).toBe('apa');

        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ formatted: 'Kasneci, E. “ChatGPT for Good?”', style: 'mla' }),
        });
        select.value = 'mla';
        select.dispatchEvent(new Event('change'));
        await Promise.resolve();
        await Promise.resolve();

        expect(fetch).toHaveBeenLastCalledWith('https://libsync.onrender.com/citation/10.1016/j.lindif.2023.102274?style=mla');
        expect(card.querySelector('.citation-card-text').textContent).toBe('Kasneci, E. “ChatGPT for Good?”');
    });

    test('should show the RUN_ERROR message if the stream fails mid-flight, with a distinct error style', async () => {
        userInput.value = 'Trigger failure';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({ type: 'RUN_ERROR', message: '⚠️ Error: Unable to reach AI service. Please try again later.' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        expect(messageChildren(chatBox)[1].classList.contains('error')).toBe(true);
        expect(botTextOf(messageChildren(chatBox)[1])).toBe('⚠️ Error: Unable to reach AI service. Please try again later.');
        expect(messageChildren(chatBox)[1].querySelector('.bot-retry')).not.toBeNull();
    });

    test('should show a fallback message when the run finishes with no text or cards', async () => {
        userInput.value = 'Hmm';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        expect(botTextOf(messageChildren(chatBox)[1])).toBe('Sorry, I couldn’t find an answer right now.');
    });

    test('should show a distinct message when rate limited', async () => {
        userInput.value = 'Another message';
        fetch.mockResolvedValueOnce({ ok: false, status: 429 });

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        expect(messageChildren(chatBox).length).toBe(2);
        expect(messageChildren(chatBox)[1].textContent).toMatch(/too quickly/i);
    });

    test('should retry on network failure before giving up', async () => {
        userInput.value = 'Another message';
        fetch
            .mockRejectedValueOnce(new Error('network down'))
            .mockRejectedValueOnce(new Error('network down'))
            .mockRejectedValueOnce(new Error('network down'));

        const promise = sendMessage();
        await jest.runAllTimersAsync();
        await promise;

        expect(fetch).toHaveBeenCalledTimes(3);
        const chatBox = document.getElementById('chatBox');
        // user message, loading message (which becomes the error message)
        expect(messageChildren(chatBox).length).toBe(2);
        expect(botTextOf(messageChildren(chatBox)[1])).toBe('⚠️ Error: Unable to reach AI service. Please try again later.');
    });

    test('should recover if a retry succeeds after a transient failure', async () => {
        userInput.value = 'Another message';
        fetch
            .mockRejectedValueOnce(new Error('network blip'))
            .mockResolvedValueOnce(
                makeStreamingResponse([
                    aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                    ...textMessageEvents('msg-1', ['Recovered']),
                    aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
                ]),
            );

        const promise = sendMessage();
        await jest.runAllTimersAsync();
        await promise;

        expect(fetch).toHaveBeenCalledTimes(2);
        const chatBox = document.getElementById('chatBox');
        expect(botTextOf(messageChildren(chatBox)[1])).toBe('Recovered');
    });

    test('should show a "Grounded in N sources" tag and numbered badges when cards are rendered', async () => {
        userInput.value = 'Any Andy Weir books?';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({
                    type: 'CUSTOM',
                    name: 'book_card',
                    value: { title: 'Project Hail Mary', author: 'Andy Weir', first_publish_year: 2021, availability: 'lendable' },
                }),
                aguiEvent({
                    type: 'CUSTOM',
                    name: 'book_card',
                    value: { title: 'The Martian', author: 'Andy Weir', first_publish_year: 2011, availability: 'checked out' },
                }),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        const botMsg = messageChildren(chatBox)[1];
        expect(botMsg.querySelector('.grounded-tag').textContent).toBe('Grounded in 2 sources');
        const badges = botMsg.querySelectorAll('.source-badge');
        expect(Array.from(badges).map((b) => b.textContent)).toEqual(['1', '2']);
    });

    test('a plain-text reply gets no grounded tag', async () => {
        userInput.value = 'Hello';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                ...textMessageEvents('msg-1', ['Hi there!']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        expect(messageChildren(chatBox)[1].querySelector('.grounded-tag')).toBeNull();
    });

    test('only the most recent bot message keeps a regenerate action; copy stays on both', async () => {
        userInput.value = 'q1';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                ...textMessageEvents('msg-1', ['a1']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );
        await sendMessage();

        userInput.value = 'q2';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-2' }),
                ...textMessageEvents('msg-2', ['a2']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-2' }),
            ]),
        );
        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        const botMessages = [...chatBox.children].filter((el) => el.classList.contains('bot'));
        expect(botMessages).toHaveLength(2);
        expect(botMessages[0].querySelector('.message-action-btn--regenerate')).toBeNull();
        expect(botMessages[0].querySelector('.message-action-btn')).not.toBeNull();
        expect(botMessages[1].querySelector('.message-action-btn--regenerate')).not.toBeNull();
    });

    test('regenerateLastReply re-runs the last question without appending a new user bubble', async () => {
        userInput.value = 'first question';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                ...textMessageEvents('msg-1', ['first answer']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );
        await sendMessage();

        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-2' }),
                ...textMessageEvents('msg-2', ['second answer']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-2' }),
            ]),
        );
        await regenerateLastReply();

        const chatBox = document.getElementById('chatBox');
        const userMessages = [...chatBox.children].filter((el) => el.classList.contains('user'));
        expect(userMessages).toHaveLength(1);
        const botMessages = [...chatBox.children].filter((el) => el.classList.contains('bot'));
        expect(botMessages).toHaveLength(2);
        expect(botTextOf(botMessages[1])).toBe('second answer');
    });

    test('a failed reply\'s Retry button resubmits the last question without duplicating the user bubble', async () => {
        userInput.value = 'Trigger failure';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                aguiEvent({ type: 'RUN_ERROR', message: 'boom' }),
            ]),
        );
        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        expect(messageChildren(chatBox).length).toBe(2);
        const retryBtn = messageChildren(chatBox)[1].querySelector('.bot-retry');
        expect(retryBtn).not.toBeNull();

        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-2' }),
                ...textMessageEvents('msg-2', ['recovered reply']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-2' }),
            ]),
        );

        retryBtn.click();
        await jest.runAllTimersAsync();

        const updatedChatBox = document.getElementById('chatBox');
        const userMessages = [...updatedChatBox.children].filter((el) => el.classList.contains('user'));
        expect(userMessages).toHaveLength(1);
        const botMessages = [...updatedChatBox.children].filter((el) => el.classList.contains('bot'));
        expect(botMessages).toHaveLength(1);
        expect(botTextOf(botMessages[0])).toBe('recovered reply');
    });

    test('sendBtn becomes a Stop control while streaming and reverts after completion', async () => {
        userInput.value = 'hello';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                aguiEvent({ type: 'RUN_STARTED', threadId: 'abc-123', runId: 'run-1' }),
                ...textMessageEvents('msg-1', ['hi']),
                aguiEvent({ type: 'RUN_FINISHED', threadId: 'abc-123', runId: 'run-1' }),
            ]),
        );

        const promise = sendMessage();
        expect(sendBtn.textContent).toBe('Stop');
        expect(sendBtn.classList.contains('stopping')).toBe(true);
        await promise;
        expect(sendBtn.textContent).toBe('Send');
        expect(sendBtn.classList.contains('stopping')).toBe(false);
    });

    test('clicking Stop aborts the in-flight request and shows a stopped state', async () => {
        userInput.value = 'hello';
        let capturedSignal;
        fetch.mockImplementationOnce((url, options) => {
            capturedSignal = options.signal;
            return new Promise((resolve, reject) => {
                options.signal.addEventListener('abort', () => {
                    const err = new Error('aborted');
                    err.name = 'AbortError';
                    reject(err);
                });
            });
        });

        const promise = sendMessage();
        expect(capturedSignal).toBeDefined();
        expect(capturedSignal.aborted).toBe(false);

        sendBtn.dispatchEvent(new Event('click'));
        await promise;

        const chatBox = document.getElementById('chatBox');
        expect(botTextOf(messageChildren(chatBox)[1])).toBe('Stopped.');
        expect(sendBtn.textContent).toBe('Send');
    });
});
