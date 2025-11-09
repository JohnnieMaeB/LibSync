import './helpers/mockHfClient.js';
import './helpers/mockPineconeClient.js';
import { simulateFailure as simulateHfFailure, resetMock as resetHfMock } from './helpers/mockHfClient.js';
import { simulateFailure as simulatePineconeFailure, resetMock as resetPineconeMock } from './helpers/mockPineconeClient.js';

let request;
let app;

beforeAll(async () => {
    request = (await import('supertest')).default;
    const mod = await import('../server.js');
    app = mod.default || mod;
});

afterEach(() => {
    resetPineconeMock();
    resetHfMock();
});

describe('POST /api/query', () => {
    it('should return search results for a valid query', async () => {
        const response = await request(app)
            .post('/api/query')
            .send({ vector: [0.1, 0.2, 0.3] })
            .set('Accept', 'application/json');

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('matches');
        expect(Array.isArray(response.body.matches)).toBe(true);
    });

    it('should return search results for a valid query with topK', async () => {
        const response = await request(app)
            .post('/api/query')
            .send({ vector: [0.1, 0.2, 0.3], topK: 10 })
            .set('Accept', 'application/json');

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('matches');
        expect(Array.isArray(response.body.matches)).toBe(true);
    });

    it('should return 400 if vector is missing', async () => {
        const response = await request(app)
            .post('/api/query')
            .send({})
            .set('Accept', 'application/json');

        expect(response.status).toBe(400);
        expect(response.body).toHaveProperty('error', 'Query vector is required.');
    });

    it('should handle Pinecone client errors and return 500', async () => {
        simulatePineconeFailure(true);
        const response = await request(app)
            .post('/api/query')
            .send({ vector: [0.1, 0.2, 0.3] })
            .set('Accept', 'application/json');

        expect(response.status).toBe(500);
        expect(response.body).toHaveProperty('error', 'Failed to query Pinecone index.');
    });
});

describe('Chat Integration with Pinecone', () => {
    // This test verifies the "happy path" for the Pinecone integration.
    it('should include Pinecone context in the system prompt', async () => {
        const response = await request(app)
            .post('/chat')
            .send({ message: 'What are the library hours?' })
            .set('Accept', 'application/json');

        expect(response.status).toBe(200);
        // We check if the AI's reply contains the text from our mocked Pinecone result.
        // This confirms that the context was successfully retrieved and injected into the prompt.
        expect(response.body.reply).toContain('Mocked search result');
        // We also check for the XML tags to ensure the prompt is structured correctly.
        expect(response.body.reply).toContain('<pinecone_search_results>');
    });

    // This test simulates a failure when querying Pinecone and ensures the application
    // gracefully falls back to the default system prompt.
    it('should fall back to the default prompt if Pinecone fails', async () => {
        simulatePineconeFailure(true); // Simulate a failure in the Pinecone mock.
        const response = await request(app)
            .post('/chat')
            .send({ message: 'What are the library hours?' })
            .set('Accept', 'application/json');

        expect(response.status).toBe(200);
        // We assert that the reply does NOT contain the Pinecone context,
        // which confirms that the fallback to the default prompt was successful.
        expect(response.body.reply).not.toContain('Mocked search result');
        // We also check that the XML tags are not present in the final prompt.
        expect(response.body.reply).not.toContain('<pinecone_search_results>');
    });

    // This test simulates a failure in the embedding generation and checks that
    // the system falls back to the default prompt, just like a Pinecone query failure.
    it('should fall back to default prompt if embedding fails', async () => {
        simulateHfFailure(false, true); // Simulate only an embedding failure.
        const response = await request(app)
            .post('/chat')
            .send({ message: 'Message that will trigger embedding failure' })
            .set('Accept', 'application/json');

        expect(response.status).toBe(200);
        // The assertions are the same as the Pinecone failure test:
        // the reply should not contain any Pinecone-specific context or tags.
        expect(response.body.reply).not.toContain('Mocked search result');
        expect(response.body.reply).not.toContain('<pinecone_search_results>');
    });
});
