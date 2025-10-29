/**
 * @file This controller handles HTTP requests for the chat service.
 * It is responsible for validating the user's message, calling the chat service,
 * and sending the AI's reply as an HTTP response.
 */
import { getChatReply } from '../services/chatService.js';

/**
 * Handles a POST request to the /chat endpoint.
 * @param {object} req - The Express request object. Expects a JSON body with a 'message' property.
 * @param {object} res - The Express response object.
 */
export async function chatController(req, res) {
  // Defensively extract the message from the request body.
  // This handles cases where the body might not be a valid object.
  const message = req.body && typeof req.body === 'object' ? req.body.message : undefined;
  // If no message is provided, send a 400 Bad Request response.
  if (!message) return res.status(400).json({ error: 'No message provided' });

  try {
    // Call the chat service to get a reply from the AI model.
    const reply = await getChatReply(message);
    // Send a 200 OK response with the AI's reply.
    res.json({ reply });
  } catch (error) {
    // If the chat service throws an error (e.g., API is down), send a 500 Internal Server Error response.
    res.status(500).json({ error: '⚠️ Error: Unable to reach AI service. Please try again later.' });
  }
}
