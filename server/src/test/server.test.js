import './helpers/mockHfClient.js';

let request;
let app;

beforeAll(async () => {
    // load supertest and then the server (which will use the mocked InferenceClient)
    request = (await import('supertest')).default;
    const mod = await import('../server.js');
    app = mod.default || mod;
});

describe('POST /chat', () => {
    it('should return a reply for a valid message', async () => {
        const response = await request(app)
            .post('/chat')
            .send({ message: 'Hello, AI!' })
            .set('Accept', 'application/json');

        console.log(response.body);
        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('reply');
    });
});
