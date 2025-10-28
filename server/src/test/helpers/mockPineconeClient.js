import { jest } from '@jest/globals';

let shouldThrow = false;

// We mock the Pinecone client to avoid making actual API calls during tests.
// This allows us to test our application's behavior in isolation and
// ensures that our tests are fast, reliable, and don't depend on external services.
jest.unstable_mockModule('@pinecone-database/pinecone', () => ({
  Pinecone: jest.fn().mockImplementation(() => ({
    // We chain the mock to allow for a fluent API-like call `pinecone.index('index-name').query()`.
    index: jest.fn().mockReturnThis(),
    // The query method is the most important one to mock.
    // It's an async function that returns a promise, so we mock it as such.
    query: jest.fn().mockImplementation(async () => {
      if (shouldThrow) {
        // This allows us to simulate failures in our tests.
        throw new Error('Mocked Pinecone failure');
      }
      // We return a mocked response that has the same shape as the real API response.
      return {
        matches: [
          {
            id: '1',
            score: 0.98,
            values: [0.1, 0.2, 0.3],
            metadata: { text: 'Mocked search result' },
          },
        ],
      };
    }),
  })),
}));

export function simulateFailure(value = true) {
  shouldThrow = value;
}

export function resetMock() {
  shouldThrow = false;
}
