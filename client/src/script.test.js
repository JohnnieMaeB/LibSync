/**
 * @jest-environment jsdom
 */

// Mock the fetch function
global.fetch = jest.fn();

// Mock DOM elements
document.body.innerHTML = `
    <div id="chatBox"></div>
    <textarea id="userInput"></textarea>
    <button id="sendBtn"></button>
`;

// Import the functions to be tested
const { appendMessage, sendMessage } = require('./script.js');

describe('appendMessage', () => {
    beforeEach(() => {
        document.getElementById('chatBox').innerHTML = '';
    });

    test('should append a user message to the chat box', () => {
        appendMessage('user', 'Hello');
        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children.length).toBe(1);
        expect(chatBox.children[0].className).toBe('user');
        expect(chatBox.children[0].innerHTML).toBe('Hello');
    });

    test('should append a bot message to the chat box', () => {
        appendMessage('bot', 'Hi there');
        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children.length).toBe(1);
        expect(chatBox.children[0].className).toBe('bot');
        expect(chatBox.children[0].innerHTML).toBe('Hi there');
    });
});

describe('sendMessage', () => {
    let userInput;

    beforeEach(() => {
        userInput = document.getElementById('userInput');
        document.getElementById('chatBox').innerHTML = '';
        global.fetch.mockClear();
    });

    test('should not send a message if the input is empty', async () => {
        userInput.value = '';
        await sendMessage();
        expect(fetch).not.toHaveBeenCalled();
    });

    test('should send a message and receive a successful response', async () => {
        userInput.value = 'Test message';
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ reply: 'Test reply' }),
        });

        await sendMessage();

        expect(fetch).toHaveBeenCalledWith('https://libsync.onrender.com/chat', expect.any(Object));
        const chatBox = document.getElementById('chatBox');
        expect(chatBox.children.length).toBe(2); // user message + bot reply
        expect(chatBox.children[1].className).toBe('bot');
        expect(chatBox.children[1].innerHTML).toBe('Test reply');
    });

    test('should handle fetch errors gracefully', async () => {
        userInput.value = 'Another message';
        fetch.mockRejectedValueOnce(new Error('API is down'));

        await sendMessage();

        const chatBox = document.getElementById('chatBox');
        // user message, loading message (which becomes the error message)
        expect(chatBox.children.length).toBe(2);
        expect(chatBox.children[1].textContent).toBe('⚠️ Error: Unable to reach AI service. Please try again later.');
    });
});
