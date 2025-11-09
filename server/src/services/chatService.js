/**
 * @file This service orchestrates the chat workflow, integrating various services
 * to generate a context-aware AI response.
 */

import { InferenceClient } from '@huggingface/inference';
import dotenv from 'dotenv';
import { getEmbedding } from './embeddingService.js';
import { queryPinecone } from './pineconeService.js';
import { getSystemPrompt } from './promptService.js';

// Load environment variables.
dotenv.config();

// Initialize a dedicated Hugging Face client for chat completion.
const chatClient = new InferenceClient(process.env.HUGGINGFACE_TOKEN);

/**
 * Orchestrates the process of getting a context-aware AI reply.
 * @param {string} message - The user's message.
 * @returns {Promise<string>} A promise that resolves to the AI's reply.
 */
export async function getChatReply(message) {
  try {
    console.log('Received message:', message);

    let pineconeMatches = [];
    try {
      // 1. Get embedding for the user's message.
      const vector = await getEmbedding(message);
      // 2. Query Pinecone for context.
      const pineconeResponse = await queryPinecone(vector, 3);
      if (pineconeResponse?.matches?.length > 0) {
        pineconeMatches = pineconeResponse.matches;
        console.log('Pinecone context retrieved.');
      }
    } catch (error) {
      console.error('Error fetching or processing Pinecone context:', error.message);
      // Non-fatal, proceed without Pinecone context.
    }

    // 3. Construct the system prompt.
    const finalSystemPrompt = getSystemPrompt(pineconeMatches);

    // 4. Call the Hugging Face chat completion API.
    const chatCompletion = await chatClient.chatCompletion({
      provider: "novita",
      model: "deepseek-ai/DeepSeek-V3.2-Exp",
      messages: [
        { role: 'system', content: finalSystemPrompt },
        { role: 'user', content: message },
      ],
    });

    const reply = chatCompletion.choices[0].message.content;
    console.log('Hugging Face reply:', reply);
    return reply;
  } catch (error) {
    console.error('HF API error:', error.httpResponse);
    throw new Error('⚠️ Error: Unable to reach AI service. Please try again later.');
  }
}
