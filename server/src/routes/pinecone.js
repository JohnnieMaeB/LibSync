import { Router } from 'express';
import { queryController } from '../controllers/pineconeController.js';

const router = Router();

router.post('/api/query', queryController);

export default router;
