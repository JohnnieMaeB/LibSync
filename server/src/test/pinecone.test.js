import './helpers/mockPineconeClient.js';
import { simulateFailure, resetMock } from './helpers/mockPineconeClient.js';

let request;
let app;

beforeAll(async () => {
    request = (await import('supertest')).default;
    const mod = await import('../server.js');
    app = mod.default || mod;
});

afterEach(() => {
    resetMock();
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

    it('should return 400 if vector is missing', async () => {
        const response = await request(app)
            .post('/api/query')
            .send({})
            .set('Accept', 'application/json');

        expect(response.status).toBe(400);
        expect(response.body).toHaveProperty('error', 'Query vector is required.');
    });

    it('should handle Pinecone client errors and return 500', async () => {
        simulateFailure(true);
        const response = await request(app)
            .post('/api/query')
            .send({ vector: [0.1, 0.2, 0.3] })
            .set('Accept', 'application/json');

        expect(response.status).toBe(500);
        expect(response.body).toHaveProperty('error', 'Failed to query Pinecone index.');
    });
});
