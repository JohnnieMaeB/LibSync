/**
 * @file This module provides a centralized mock for the Hugging Face Inference client.
 * By using `jest.unstable_mockModule`, we can replace the actual `@huggingface/inference`
 * module with our mock implementation in any test file that imports this helper.
 * This is crucial for isolating our tests from external API calls, ensuring they
 * are fast, deterministic, and can run offline.
 *
 * This file must be imported before the main application (`server.js`) in the test setup
 * to ensure the mock is in place before the application initializes its clients.
 */

import { jest } from '@jest/globals';

// A prefix for mock replies to make them easily identifiable in test outputs.
let mockReplyPrefix = 'Mock reply for: ';
// Flags to control the mock's behavior, allowing us to simulate failure scenarios.
let shouldThrowChat = false;

jest.unstable_mockModule('@huggingface/inference', () => {
  return {
    // We mock the InferenceClient class.
    InferenceClient: function (token) {
      /**
       * Mocks the chatCompletion method.
       * This is the primary method used by the chat service to get AI responses.
       */
      this.chatCompletion = async ({ messages }) => {
        if (shouldThrowChat) {
          const err = new Error('Mocked HF failure');
          err.httpResponse = { status: 401, body: '' };
          throw err;
        }
        // A key feature of this mock is that it includes the system prompt in its reply.
        // This allows us to write tests that assert the correctness of the dynamically
        // generated system prompt, which is essential for verifying the Pinecone integration.
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
    },
  };
});

/**
 * A test utility to customize the prefix of the mock replies.
 * @param {string} prefix - The prefix to use for mock replies.
 */
export function setMockReplyPrefix(prefix) {
  mockReplyPrefix = prefix;
}

/**
 * A test utility to simulate failure modes in the mock client.
 * @param {boolean} shouldFailChat - If true, `chatCompletion` will throw an error.
 */
export function simulateFailure(shouldFailChat = true) {
  shouldThrowChat = shouldFailChat;
}

/**
 * Resets the mock's state. This is crucial to call in `afterEach` to ensure
 * that tests are isolated from each other.
 */
export function resetMock() {
  mockReplyPrefix = 'Mock reply for: ';
  shouldThrowChat = false;
}
