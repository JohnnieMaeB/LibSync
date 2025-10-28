import { jest } from '@jest/globals';

let shouldThrow = false;

jest.unstable_mockModule('@pinecone-database/pinecone', () => ({
  Pinecone: jest.fn().mockImplementation(() => ({
    index: jest.fn().mockReturnThis(),
    query: jest.fn().mockImplementation(async () => {
      if (shouldThrow) {
        throw new Error('Mocked Pinecone failure');
      }
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
