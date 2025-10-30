/**
 * @file This is the main entry point for the Express server.
 * It sets up the server, configures middleware, and registers all API routes.
 * The application is structured using a Controller/Service pattern to separate concerns.
 */
import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import rateLimit from 'express-rate-limit';
import chatRoutes from './routes/chat.js';
import pineconeRoutes from './routes/pinecone.js';

// Load environment variables from a .env file into process.env.
dotenv.config();

// Create an instance of the Express application.
const app = express();

// Set up a rate limiter to prevent abuse.
// This allows 100 requests per 15 minutes from a single IP.
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later.' },
});

// --- Middleware Setup ---
// Enable Cross-Origin Resource Sharing (CORS) for all routes.
app.use(cors());
// Parse incoming JSON requests.
app.use(express.json());
// Apply the rate limiter to all requests.
app.use(limiter);

// --- Route Registration ---
// Register the chat and Pinecone API routes.
app.use(chatRoutes);
app.use(pineconeRoutes);

// --- Server Initialization ---
const PORT = process.env.PORT || 3000;
// Check if the environment is for testing. If not, start the server.
// This prevents the server from starting automatically during tests.
const isTestEnv = process.env.NODE_ENV === 'test';
if (!isTestEnv) {
  app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
}

// Export the app instance to be used by the test suite.
export default app;
