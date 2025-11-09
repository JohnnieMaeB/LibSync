/**
 * @file This service is responsible for constructing the system prompt for the AI model.
 * It centralizes the logic for creating both default and context-enriched prompts.
 */

import { alaBillOfRights } from '../bot-context/bill-of-rights.js';
import { alaCoreValues } from '../bot-context/core-values.js';
import { personaPrompt } from '../bot-context/identitiy.js';
import { rusaGuidelines } from '../bot-context/RUSA-guidlines.js';

/**
 * The base system prompt provides the AI with its core identity and guiding principles.
 * It is structured using XML-style tags to create a clear hierarchy for the model to follow.
 */
const defaultSystemPrompt = `
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
 * Creates a system prompt, dynamically injecting Pinecone search results if they are provided.
 * If no results are provided, it returns the default system prompt.
 * @param {Array<object>} [pineconeResults] - An optional array of match objects from the Pinecone query.
 * @returns {string} The constructed system prompt.
 */
export function getSystemPrompt(pineconeResults) {
  // If there are no Pinecone results, or the results array is empty, return the default prompt.
  if (!pineconeResults || pineconeResults.length === 0) {
    return defaultSystemPrompt;
  }

  // Format the Pinecone results into an XML-like structure for the AI model.
  // This helps the model distinguish the search results from other parts of the prompt.
  const searchResultsText = pineconeResults
    .map(
      (result) =>
        `<document_chunk source="${result.metadata.source}">${result.metadata.text}</document_chunk>`
    )
    .join('\n');

  // Return the complete system prompt with the search results embedded.
  // The base prompt is included to ensure the AI always has its core instructions.
  return `${defaultSystemPrompt}

<pinecone_search_results>
${searchResultsText}
</pinecone_search_results>
`;
}
