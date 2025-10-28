import { Pinecone } from "@pinecone-database/pinecone";
import dotenv from "dotenv";

dotenv.config();

const pinecone = new Pinecone({
  apiKey: process.env.PINECONE_API_KEY,
});

const indexName = "libsync-policy-index";
const index = pinecone.index(indexName);

/**
 * Queries the Pinecone index.
 * @param {number[]} vector - The query vector.
 * @param {number} topK - The number of results to return.
 * @returns {Promise<object>} - The query results.
 */
async function queryPinecone(vector, topK = 5) {
  if (!vector) {
    throw new Error("Query vector is required.");
  }

  try {
    const queryResponse = await index.query({
      topK,
      vector,
      includeValues: true,
      includeMetadata: true,
    });
    return queryResponse;
  } catch (error) {
    console.error("Error querying Pinecone:", error);
    throw new Error("Failed to query Pinecone index.");
  }
}

export { queryPinecone };
