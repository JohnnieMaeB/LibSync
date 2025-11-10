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
 * Queries the Pinecone index with a given text query to find the most similar items.
 * Pinecone will handle the embedding of the query text.
 * @param {string} queryText - The text to search for.
 * @param {number} topK - The number of top results to return. Defaults to 3.
 * @returns {Promise<object>} - A promise that resolves to the query results from Pinecone.
 * @throws {Error} If the query text is not provided or if the query fails.
 */
export async function queryPinecone(queryText, topK = 3) {
  if (!queryText) {
    throw new Error("Query text is required.");
  }

  try {
    // Perform the query against the Pinecone index using a text-based query.
    // Pinecone will automatically generate the embedding for the query text.
    const queryResponse = await index.query({
      topK,
      // The query is now an object with the text to be embedded.
      query: {
        inputs: {
          text: queryText
        }
      },
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
