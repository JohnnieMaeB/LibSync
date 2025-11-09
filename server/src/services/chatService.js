/**
 * @file This service handles all interactions with the Hugging Face Inference API.
 * It is responsible for initializing the client, constructing the system prompt,
 * and sending user messages to the AI model.
 */
import { InferenceClient } from '@huggingface/inference';
import dotenv from 'dotenv';
import { queryPinecone } from './pineconeService.js';
import { rusaGuidelines } from '../bot-context/RUSA-guidlines.js';
import { alaBillOfRights } from '../bot-context/bill-of-rights.js';
import { alaCoreValues } from '../bot-context/core-values.js';
import { personaPrompt } from '../bot-context/identitiy.js';

// Load environment variables from a .env file into process.env.
// This is crucial for loading the Hugging Face token before the client is initialized.
dotenv.config();
// Initialize the Hugging Face Inference client with the token from environment variables.
const client = new InferenceClient(process.env.HUGGINGFACE_TOKEN);

/**
 * The system prompt provides the AI with its core identity, instructions, and knowledge base.
 * It is structured using XML-style tags to create a clear hierarchy for the model to follow.
 * This prompt is sent with every user message to guide the AI's responses.
 */
const systemPrompt = `
<primary_instructions>
${personaPrompt}
</primary_instructions>

<guiding_principles>
<knowledge_source name="RUSA Guidelines for Behavioral Performance">
${rusaGuidelines}
</knowledge_source>

<knowledge_source name="ALA Library Bill of Rights">
${alaBillOfRights}
</knowledge_source>

<knowledge_source name="ALA Core Values of Librarianship">
${alaCoreValues}
</knowledge_source>

</guiding_principles>
`;

/**
 * Creates a dynamic system prompt by injecting Pinecone search results for context.
 * @param {Array<object>} pineconeResults - An array of match objects from the Pinecone query.
 * @returns {string} The constructed system prompt with search results integrated.
 */
function createSystemPrompt(pineconeResults) {
  // Format the Pinecone results into an XML-like structure for the AI model.
  // This helps the model distinguish the search results from other parts of the prompt.
  const searchResultsText = pineconeResults
    .map(
      (result) =>
        `<document_chunk source="${result.metadata.source}">${result.metadata.text}</document_chunk>`
    )
    .join('\n');

  // Return the complete system prompt with the search results embedded.
  return `
<primary_instructions>
${personaPrompt}
</primary_instructions>

<guiding_principles>
<knowledge_source name="RUSA Guidelines for Behavioral Performance">
${rusaGuidelines}
</knowledge_source>

<knowledge_source name="ALA Library Bill of Rights">
${alaBillOfRights}
</knowledge_source>

<knowledge_source name="ALA Core Values of Librarianship">
${alaCoreValues}
</knowledge_source>

</guiding_principles>

<pinecone_search_results>
${searchResultsText}
</pinecone_search_results>
`;
}

/**
 * Sends a user's message to the Hugging Face chat model and returns the AI's reply.
 * @param {string} message - The user's message to send to the AI.
 * @returns {Promise<string>} A promise that resolves to the AI's text reply.
 * @throws {Error} If the API call fails, an error is thrown with a user-friendly message.
 */
async function getChatReply(message) {
  try {
    // Log the incoming message for debugging purposes.
    console.log('Received message:', message);

    let finalSystemPrompt = systemPrompt; // Default prompt

    try {
      // 1. Get the embedding for the user's message.
      const vector = await getEmbedding(message);

      // 2. Query Pinecone for context, requesting the top 3 results.
      const pineconeResponse = await queryPinecone(vector, 3);

      // 3. If there are relevant results, create a dynamic prompt.
      if (pineconeResponse && pineconeResponse.matches && pineconeResponse.matches.length > 0) {
        console.log('Pinecone context retrieved. Creating dynamic prompt.');
        finalSystemPrompt = createSystemPrompt(pineconeResponse.matches);
      } else {
        // This is not an error, it just means no relevant context was found.
        console.log('No relevant Pinecone context found. Using default prompt.');
      }
    } catch (pineconeError) {
      // If Pinecone or the embedding service fails, log the error and fall back to the default prompt.
      // This ensures the bot remains operational even if the vector search is down.
      console.error('Pinecone integration error:', pineconeError.message);
      console.log('Falling back to default system prompt.');
      // finalSystemPrompt is already set to the default, so no action is needed.
    }

    // Call the Hugging Face chat completion API.
    const chatCompletion = await client.chatCompletion({
      provider: "novita",
      model: "deepseek-ai/DeepSeek-V3.2-Exp", // The specific chat model to use.
      messages: [
        { role: 'system', content: finalSystemPrompt }, // The guiding prompt for the AI.
        { role: 'user', content: message }, // The user's message.
      ],
    });

    // Log the AI's reply for debugging.
    console.log('Hugging Face reply:', chatCompletion.choices[0].message.content);
    // Extract and return the content of the AI's message.
    return chatCompletion.choices[0].message.content;
  } catch (error) {
    // Log the detailed error from the API for debugging and throw a generic
    // error to the caller.
    console.error('HF API error:', error.httpResponse);
    throw new Error('⚠️ Error: Unable to reach AI service. Please try again later.');
  }
}

/**
 * Generates a sentence embedding for a given text using a Hugging Face model.
 * @param {string} text - The text to embed.
 * @returns {Promise<number[]>} A promise that resolves to the embedding vector.
 * @throws {Error} If the embedding generation fails.
 */
async function getEmbedding(text) {
  try {
    // Use the Hugging Face client to generate a sentence embedding.
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

// Export the function to be used by the chat controller.
export { getChatReply };
