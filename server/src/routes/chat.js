/**
 * @file This file defines the Express routes for the chat API endpoint.
 * It maps the /chat endpoint to its corresponding controller function.
 */
import { Router } from 'express';
import { chatController } from '../controllers/chatController.js';

// Create a new Express router instance.
const router = Router();

// Define the route for the chat functionality.
// POST /chat will be handled by the chatController.
router.post('/chat', chatController);

// Export the router to be used in the main server file.
export default router;
