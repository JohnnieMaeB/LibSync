/**
 * @file This controller handles HTTP requests for querying the Pinecone service.
 * It is responsible for validating the request body, calling the service,
 * and sending the appropriate HTTP response.
 */
import { queryPinecone } from '../services/pineconeService.js';

/**
 * Handles a POST request to query the Pinecone index.
 * @param {object} req - The Express request object. Expects a JSON body with a 'vector' property.
 * @param {object} res - The Express response object.
 */
export async function queryController(req, res) {
  // Extract the query vector and optional topK parameter from the request body.
  const { vector, topK } = req.body;

  // Validate that the required 'vector' property is present.
  if (!vector) {
    return res.status(400).json({ error: 'Query vector is required.' });
  }

  try {
    // Call the Pinecone service with the provided vector and topK value.
    const results = await queryPinecone(vector, topK);
    // Send a 200 OK response with the query results.
    res.json(results);
  } catch (error) {
    // If the service throws an error, send a 500 Internal Server Error response.
    res.status(500).json({ error: 'Failed to query Pinecone index.' });
  }
}
