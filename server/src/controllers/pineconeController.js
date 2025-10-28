import { queryPinecone } from '../services/pineconeService.js';

export async function queryController(req, res) {
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
}
