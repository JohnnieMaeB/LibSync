import { getChatReply } from '../services/chatService.js';

export async function chatController(req, res) {
  const message = req.body && typeof req.body === 'object' ? req.body.message : undefined;
  if (!message) return res.status(400).json({ error: 'No message provided' });

  try {
    const reply = await getChatReply(message);
    res.json({ reply });
  } catch (error) {
    res.status(500).json({ error: '⚠️ Error: Unable to reach AI service. Please try again later.' });
  }
}
