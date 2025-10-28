import { Router } from 'express';
import { queryPinecone } from '../pinecone.js';

const router = Router();

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
