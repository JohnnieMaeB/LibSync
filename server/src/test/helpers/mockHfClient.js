import { jest } from '@jest/globals';

// Centralized mock for the Hugging Face Inference client used in tests.
// Import this file before importing the app so the real module is replaced.
jest.unstable_mockModule('@huggingface/inference', () => {
    return {
        InferenceClient: function (token) {
            this.chatCompletion = async ({ messages }) => {
                return {
                    choices: [
                        { message: { content: `Mock reply for: ${messages?.[0]?.content || ''}` } }
                    ]
                };
            };
        }
    };
});

