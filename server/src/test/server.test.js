import './helpers/mockHfClient.js';
import './helpers/mockPineconeClient.js';
import { setMockReplyPrefix, simulateFailure as simulateHfFailure, resetMock as resetHfMock } from './helpers/mockHfClient.js';
import { simulateFailure as simulatePineconeFailure, resetMock as resetPineconeMock } from './helpers/mockPineconeClient.js';


let request;
let app;

beforeAll(async () => {
    // load supertest and then the server (which will use the mocked InferenceClient)
    request = (await import('supertest')).default;
    const mod = await import('../server.js');
    app = mod.default || mod;
});

afterEach(() => {
    resetHfMock();
    resetPineconeMock();
});

describe('POST /chat', () => {
    //Happy path test
    it('should return a reply for a valid message', async () => {
        const response = await request(app)
            .post('/chat')
            .send({ message: 'Hello, AI!' })
            .set('Accept', 'application/json');

        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('reply');
        expect(typeof response.body.reply).toBe('string');
    });

    it('should return 400 if message is missing', async () => {
        const response = await request(app)
            .post('/chat')
            .send({})
            .set('Accept', 'application/json');

        expect(response.status).toBe(400);
        expect(response.body).toHaveProperty('error');
    });

    it('should handle HF client errors and return 500', async () => {
        simulateHfFailure(true);
        const response = await request(app)
            .post('/chat')
            .send({ message: 'Trigger failure' })
            .set('Accept', 'application/json');

        expect(response.status).toBe(500);
        expect(response.body).toHaveProperty('error');
    });

    it('should handle very large messages', async () => {
        const large = 'x'.repeat(10000);
        const response = await request(app)
            .post('/chat')
            .send({ message: large })
            .set('Accept', 'application/json');

        expect(response.status).toBe(200);
        expect(response.body.reply).toContain('x');
    });

    it('should return 400 for non-JSON content', async () => {
        const response = await request(app)
            .post('/chat')
            .send('plain text')
            .set('Content-Type', 'text/plain');

        // Express will not parse body as JSON and our handler will see no message
        expect([400, 415]).toContain(response.status);
    });

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

describe('Rate Limiting', () => {
    it('should allow a single request', async () => {
        const response = await request(app)
            .post('/chat')
            .send({ message: 'test' });
        expect(response.status).toBe(200);
    });

    it('should return 429 after 100 requests', async () => {
        // Express-rate-limit's memory store is not reset between tests in the same suite,
        // so we need to account for the single request in the previous test.
        const promises = [];
        for (let i = 0; i < 100; i++) {
            promises.push(request(app).post('/chat').send({ message: 'test' }));
        }
        await Promise.all(promises);

        const response = await request(app)
            .post('/chat')
            .send({ message: 'test' });
        expect(response.status).toBe(429);
        expect(response.body).toHaveProperty('error', 'Too many requests, please try again later.');
    });
});
