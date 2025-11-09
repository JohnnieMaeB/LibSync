
import { jest } from '@jest/globals';

// Centralized mock for the Hugging Face Inference client used in tests.
// Import this file before importing the app so the real module is replaced.

let mockReplyPrefix = 'Mock reply for: ';
let shouldThrowChat = false;
let shouldThrowEmbedding = false;

jest.unstable_mockModule('@huggingface/inference', () => {
  return {
    InferenceClient: function (token) {
      this.chatCompletion = async ({ messages }) => {
        if (shouldThrowChat) {
          const err = new Error('Mocked HF failure');
          err.httpResponse = { status: 401, body: '' };
          throw err;
        }
        // The mock now includes the entire system prompt in the reply,
        // allowing us to assert that Pinecone context was included.
        const systemPromptContent = messages.find((m) => m.role === 'system')?.content || '';
        const userMessage = messages.find((m) => m.role === 'user')?.content || '';
        return {
          choices: [
            {
              message: {
                content: `${mockReplyPrefix}${userMessage}\nSystemPrompt:\n${systemPromptContent}`,
              },
            },
          ],
        };
      };
      this.sentenceEmbedding = async ({ model, inputs }) => {
        if (shouldThrowEmbedding) {
          throw new Error('Mocked embedding failure');
        }
        // Return a dummy vector. The values don't matter, just the shape.
        return [0.1, 0.2, 0.3, 0.4, 0.5];
      };
    },
  };
});

export function setMockReplyPrefix(prefix) {
  mockReplyPrefix = prefix;
}

export function simulateFailure(shouldFailChat = true, shouldFailEmbedding = false) {
  shouldThrowChat = shouldFailChat;
  shouldThrowEmbedding = shouldFailEmbedding;
}

export function resetMock() {
  mockReplyPrefix = 'Mock reply for: ';
  shouldThrowChat = false;
  shouldThrowEmbedding = false;
}


