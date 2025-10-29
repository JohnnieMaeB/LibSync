/**
 * @file This file defines the Express routes for Pinecone-related API endpoints.
 * It maps the endpoints to their corresponding controller functions.
 */
import { Router } from 'express';
import { queryController } from '../controllers/pineconeController.js';

// Create a new Express router instance.
const router = Router();

// Define the route for querying the Pinecone index.
// POST /api/query will be handled by the queryController.
router.post('/api/query', queryController);

// Export the router to be used in the main server file.
export default router;
