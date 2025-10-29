/**
 * @file This service handles all interactions with the Pinecone vector database.
 * It is responsible for initializing the client and querying the index.
 */
import { Pinecone } from "@pinecone-database/pinecone";
import dotenv from "dotenv";

// Load environment variables from a .env file into process.env
dotenv.config();

// Initialize the Pinecone client with the API key from environment variables.
// This ensures that sensitive credentials are not hardcoded in the source code.
const pinecone = new Pinecone({
  apiKey: process.env.PINECONE_API_KEY,
});

// Define the name of the Pinecone index to be used for the application.
const indexName = "libsync-policy-index";
// Get a reference to the specific index.
const index = pinecone.index(indexName);

/**
 * Queries the Pinecone index with a given vector to find the most similar items.
 * @param {number[]} vector - The embedding vector to search for.
 * @param {number} topK - The number of top results to return. Defaults to 5, a reasonable number to prevent overly large responses.
 * @returns {Promise<object>} - A promise that resolves to the query results from Pinecone.
 * @throws {Error} If the query vector is not provided or if the query fails.
 */
async function queryPinecone(vector, topK = 5) {
  // A query vector is essential for performing a search.
  if (!vector) {
    throw new Error("Query vector is required.");
  }

  try {
    // Perform the query against the Pinecone index.
    // We include values and metadata to get the full context of the search results.
    const queryResponse = await index.query({
      topK,
      vector,
      includeValues: true,
      includeMetadata: true,
    });
    return queryResponse;
  } catch (error) {
    // Log the detailed error for debugging purposes and throw a generic error
    // to the caller to avoid exposing implementation details.
    console.error("Error querying Pinecone:", error);
    throw new Error("Failed to query Pinecone index.");
  }
}

// Export the query function to be used by other parts of the application (e.g., controllers).
export { queryPinecone };
