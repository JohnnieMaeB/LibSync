import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import { InferenceClient } from "@huggingface/inference";

dotenv.config();
const app = express();
app.use(cors());
app.use(express.json());

// Initialize the Hugging Face Inference client
const client = new InferenceClient(process.env.HUGGINGFACE_TOKEN);

// Endpoint for chat messages
app.post("/chat", async (req, res) => {
  const { message } = req.body;
  if (!message) return res.status(400).json({ error: "No message provided" });

  try {
    console.log("Received message:", message);

    const chatCompletion = await client.chatCompletion({
      provider: "hf-inference",
      model: "katanemo/Arch-Router-1.5B", // change this to any public Hugging Face chat model
      messages: [{ role: "user", content: message }],
    });

    console.log("Hugging Face reply:", chatCompletion.choices[0].message.content);

    res.json({ reply: chatCompletion.choices[0].message.content });
  } catch (error) {
    console.error("HF API error:", error.httpResponse);
    res.status(500).json({ error: "⚠️ Error: Unable to reach AI service. Please try again later." });
  }
});

const PORT = process.env.PORT || 3000;
const isTestEnv = process.env.NODE_ENV === 'test';

if (!isTestEnv) {
  app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
}

export default app; // Export the app for testing (ESM)