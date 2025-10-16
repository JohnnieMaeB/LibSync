
import { jest } from '@jest/globals';

// Centralized mock for the Hugging Face Inference client used in tests.
// Import this file before importing the app so the real module is replaced.

let mockReplyPrefix = 'Mock reply for: ';
let shouldThrow = false;

jest.unstable_mockModule('@huggingface/inference', () => {
    return {
        InferenceClient: function (token) {
            this.chatCompletion = async ({ messages }) => {
                if (shouldThrow) {
                    const err = new Error('Mocked HF failure');
                    err.httpResponse = { status: 401, body: '' };
                    throw err;
                }
                return {
                    choices: [
                        { message: { content: `${mockReplyPrefix}${messages?.[0]?.content || ''}` } }
                    ]
                };
            };
        }
    };
});

export function setMockReplyPrefix(prefix) {
    mockReplyPrefix = prefix;
}

export function simulateFailure(value = true) {
    shouldThrow = value;
}

export function resetMock() {
    mockReplyPrefix = 'Mock reply for: ';
    shouldThrow = false;
}


