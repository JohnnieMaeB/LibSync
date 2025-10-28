import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import rateLimit from 'express-rate-limit';
import chatRoutes from './routes/chat.js';
import pineconeRoutes from './routes/pinecone.js';

dotenv.config();
const app = express();
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later.' },
});

app.use(cors());
app.use(express.json());
app.use(limiter);
app.use(chatRoutes);
app.use(pineconeRoutes);

const PORT = process.env.PORT || 3000;
const isTestEnv = process.env.NODE_ENV === 'test';

if (!isTestEnv) {
  app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
}

export default app;
