import './helpers/mockHfClient.js';
import { setMockReplyPrefix, simulateFailure, resetMock } from './helpers/mockHfClient.js';

let request;
let app;

beforeAll(async () => {
    // load supertest and then the server (which will use the mocked InferenceClient)
    request = (await import('supertest')).default;
    const mod = await import('../server.js');
    app = mod.default || mod;
});

afterEach(() => {
    resetMock();
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
        expect(response.body.reply).toContain('Hello, AI!');
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
        simulateFailure(true);
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
});
