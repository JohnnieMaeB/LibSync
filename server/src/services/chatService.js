import { InferenceClient } from '@huggingface/inference';
import dotenv from 'dotenv';
import { rusaGuidelines } from '../bot-context/RUSA-guidlines.js';
import { alaBillOfRights } from '../bot-context/bill-of-rights.js';
import { alaCoreValues } from '../bot-context/core-values.js';
import { personaPrompt } from '../bot-context/identitiy.js';

dotenv.config();
const client = new InferenceClient(process.env.HUGGINGFACE_TOKEN);

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

async function getChatReply(message) {
  try {
    console.log('Received message:', message);

    const chatCompletion = await client.chatCompletion({
      provider: 'hf-inference',
      model: 'katanemo/Arch-Router-1.5B',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: message },
      ],
    });

    console.log('Hugging Face reply:', chatCompletion.choices[0].message.content);
    return chatCompletion.choices[0].message.content;
  } catch (error) {
    console.error('HF API error:', error.httpResponse);
    throw new Error('⚠️ Error: Unable to reach AI service. Please try again later.');
  }
}

export { getChatReply };
