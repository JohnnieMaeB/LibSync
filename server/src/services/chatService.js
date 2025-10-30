/**
 * @file This service handles all interactions with the Hugging Face Inference API.
 * It is responsible for initializing the client, constructing the system prompt,
 * and sending user messages to the AI model.
 */
import { InferenceClient } from '@huggingface/inference';
import dotenv from 'dotenv';
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
 * Sends a user's message to the Hugging Face chat model and returns the AI's reply.
 * @param {string} message - The user's message to send to the AI.
 * @returns {Promise<string>} A promise that resolves to the AI's text reply.
 * @throws {Error} If the API call fails, an error is thrown with a user-friendly message.
 */
async function getChatReply(message) {
  try {
    // Log the incoming message for debugging purposes.
    console.log('Received message:', message);

    // Call the Hugging Face chat completion API.
    const chatCompletion = await client.chatCompletion({
      provider: "novita",
      model: "deepseek-ai/DeepSeek-V3.2-Exp", // The specific chat model to use.
      messages: [
        { role: 'system', content: systemPrompt }, // The guiding prompt for the AI.
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

// Export the function to be used by the chat controller.
export { getChatReply };
