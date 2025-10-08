# 📚 AI Library Assistant — Portfolio Demo

An elegant, browser-based chatbot built with HTML, CSS, and JavaScript.  
Connects to Hugging Face’s open AI models to simulate a friendly digital librarian.

## ✨ Features
- Real AI responses (via Hugging Face Inference API)
- Dark mode design with chat bubbles
- Smooth UX with loading animation
- Portable and perfect for GitHub Pages or portfolios

## 🧠 Tech Stack
- HTML5, CSS3, Vanilla JavaScript
- Hugging Face Inference API (`facebook/blenderbot-400M-distill`)

## 🚀 Setup
1. Get a free API key:
   - Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
   - Click “New token” → Copy it
2. Paste your key into `script.js`:
   ```js
   const HF_API_KEY = "your_token_here";
