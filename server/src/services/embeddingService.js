/**
 * @file This service handles the generation of sentence embeddings using the Hugging Face Inference API.
 * Embeddings are numerical representations of text that capture semantic meaning,
 * allowing for tasks like similarity searches in a vector database.
 */

import { InferenceClient } from '@huggingface/inference';
import dotenv from 'dotenv';

// Load environment variables from a .env file.
dotenv.config();

// Initialize the Hugging Face Inference client.
const client = new InferenceClient(process.env.HUGGINGFACE_TOKEN);

/**
 * Generates a sentence embedding for a given text using a Hugging Face model.
 * Text embeddings are a critical component of the RAG (Retrieval-Augmented Generation) pipeline.
 * They convert human-readable text into a high-dimensional vector that captures the text's
 * semantic meaning. This vector can then be used to perform similarity searches in a
 * vector database like Pinecone to find relevant documents or context.
 * @param {string} text - The text to embed.
 * @returns {Promise<number[]>} A promise that resolves to the embedding vector.
 * @throws {Error} If the embedding generation fails.
 */
export async function getEmbedding(text) {
  try {
    // Use the Hugging Face client to generate a sentence embedding.
    // The chosen model is 'sentence-transformers/all-MiniLM-L6-v2', a popular model
    // known for its balance of performance and efficiency.
    const embedding = await client.sentenceEmbedding({
      model: 'sentence-transformers/all-MiniLM-L6-v2',
      inputs: text,
    });
    return embedding;
  } catch (error) {
    // Log the error for debugging and rethrow it to be handled by the caller.
    console.error('Error getting embedding:', error);
    throw new Error('Failed to generate text embedding.');
  }
}
