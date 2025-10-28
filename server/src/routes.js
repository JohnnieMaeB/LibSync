import { Router } from 'express';
import { InferenceClient } from '@huggingface/inference';
import { queryPinecone } from './pinecone.js';
import { rusaGuidelines } from './bot-context/RUSA-guidlines.js';
import { alaBillOfRights } from './bot-context/bill-of-rights.js';
import { alaCoreValues } from './bot-context/core-values.js';
import { personaPrompt } from './bot-context/identitiy.js';

const router = Router();
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

// Endpoint for chat messages
router.post('/chat', async (req, res) => {
  // Be defensive: req.body may not be an object if the client sent non-JSON content.
  const message = req.body && typeof req.body === 'object' ? req.body.message : undefined;
  if (!message) return res.status(400).json({ error: 'No message provided' });

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

    res.json({ reply: chatCompletion.choices[0].message.content });
  } catch (error) {
    console.error('HF API error:', error.httpResponse);
    res.status(500).json({ error: '⚠️ Error: Unable to reach AI service. Please try again later.' });
  }
});

// Endpoint for Pinecone queries
router.post('/api/query', async (req, res) => {
  const { vector, topK } = req.body;

  if (!vector) {
    return res.status(400).json({ error: 'Query vector is required.' });
  }

  try {
    const results = await queryPinecone(vector, topK);
    res.json(results);
  } catch (error) {
    res.status(500).json({ error: 'Failed to query Pinecone index.' });
  }
});

export default router;
