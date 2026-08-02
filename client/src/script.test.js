/**
 * @jest-environment jsdom
 */

// jsdom doesn't provide TextEncoder/TextDecoder; real browsers always do.
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Mock the fetch function
global.fetch = jest.fn();

// Mock DOM elements
document.body.innerHTML = `
    <div id="chatBox"></div>
    <textarea id="userInput"></textarea>
    <button id="sendBtn"></button>
`;

// config.js sets the shared API_BASE_URL global that script.js reads.
require('./config.js');
const { appendMessage, sendMessage } = require('./script.js');

function sse(event, data) {
    return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

// Builds a fetch Response-like object whose body streams the given SSE
// event strings one chunk per reader.read() call, mirroring how the real
// StreamingResponse endpoint delivers server-sent events.
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

describe('appendMessage', () => {
    beforeEach(() => {
        document.getElementById('chatBox').innerHTML = '';
    });

    test('should append a user message to the chat box', () => {
        appendMessage('user', 'Hello');
        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children.length).toBe(1);
        expect(chatBox.children[0].className).toBe('user');
        expect(chatBox.children[0].textContent).toBe('Hello');
    });

    test('should append a bot message to the chat box', () => {
        appendMessage('bot', 'Hi there');
        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children.length).toBe(1);
        expect(chatBox.children[0].className).toBe('bot');
        expect(chatBox.children[0].textContent).toBe('Hi there');
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

describe('sendMessage', () => {
    let userInput;

    beforeEach(() => {
        userInput = document.getElementById('userInput');
        document.getElementById('chatBox').innerHTML = '';
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

    test('should stream a session id and text reply into the bot bubble', async () => {
        userInput.value = 'Test message';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                sse('session', { session_id: 'abc-123' }),
                sse('text', { text: 'Test' }),
                sse('text', { text: 'Test reply' }),
                sse('done', {}),
            ]),
        );

        await sendMessage();

        expect(fetch).toHaveBeenCalledTimes(1);
        const [url, options] = fetch.mock.calls[0];
        expect(url).toBe('https://libsync.onrender.com/chat/stream');
        const body = JSON.parse(options.body);
        expect(body.message).toBe('Test message');
        expect(typeof body.session_id).toBe('string');
        expect(body.session_id.length).toBeGreaterThan(0);

        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children.length).toBe(2); // user message + bot reply
        expect(chatBox.children[1].className).toBe('bot');
        expect(chatBox.children[1].textContent).toBe('Test reply');
        expect(localStorage.getItem('libsync_session_id')).toBe('abc-123');
    });

    test('should reuse the same session id across requests', async () => {
        // Mirrors real server behavior: it echoes back whatever session_id
        // the client sent (see server/app/routers/chat.py).
        fetch.mockImplementation(async (url, options) => {
            const body = JSON.parse(options.body);
            return makeStreamingResponse([
                sse('session', { session_id: body.session_id }),
                sse('text', { text: 'ok' }),
                sse('done', {}),
            ]);
        });

        userInput.value = 'first';
        await sendMessage();
        userInput.value = 'second';
        await sendMessage();

        const firstBody = JSON.parse(fetch.mock.calls[0][1].body);
        const secondBody = JSON.parse(fetch.mock.calls[1][1].body);
        expect(secondBody.session_id).toBe(firstBody.session_id);
    });

    test('should render a structured books event as book cards', async () => {
        userInput.value = 'Is Project Hail Mary available?';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                sse('session', { session_id: 'abc-123' }),
                sse('books', {
                    intro: 'Found one match:',
                    books: [
                        { title: 'Project Hail Mary', author: 'Andy Weir', first_publish_year: 2021, availability: 'lendable' },
                    ],
                }),
                sse('done', {}),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        const botMsg = chatBox.children[1];
        expect(botMsg.querySelector('.book-result-intro').textContent).toBe('Found one match:');
        const card = botMsg.querySelector('.book-card');
        expect(card.querySelector('.book-card-title').textContent).toBe('Project Hail Mary (2021)');
        expect(card.querySelector('.book-card-availability').textContent).toBe('lendable');
    });

    test('should show the error event message if the stream fails mid-flight', async () => {
        userInput.value = 'Trigger failure';
        fetch.mockResolvedValueOnce(
            makeStreamingResponse([
                sse('session', { session_id: 'abc-123' }),
                sse('error', { error: '⚠️ Error: Unable to reach AI service. Please try again later.' }),
            ]),
        );

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children[1].textContent).toBe('⚠️ Error: Unable to reach AI service. Please try again later.');
    });

    test('should show a distinct message when rate limited', async () => {
        userInput.value = 'Another message';
        fetch.mockResolvedValueOnce({ ok: false, status: 429 });

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children.length).toBe(2);
        expect(chatBox.children[1].textContent).toMatch(/too quickly/i);
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
        expect(chatBox.children.length).toBe(2);
        expect(chatBox.children[1].textContent).toBe('⚠️ Error: Unable to reach AI service. Please try again later.');
    });

    test('should recover if a retry succeeds after a transient failure', async () => {
        userInput.value = 'Another message';
        fetch
            .mockRejectedValueOnce(new Error('network blip'))
            .mockResolvedValueOnce(
                makeStreamingResponse([
                    sse('session', { session_id: 'abc-123' }),
                    sse('text', { text: 'Recovered' }),
                    sse('done', {}),
                ]),
            );

        const promise = sendMessage();
        await jest.runAllTimersAsync();
        await promise;

        expect(fetch).toHaveBeenCalledTimes(2);
        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children[1].textContent).toBe('Recovered');
    });
});
