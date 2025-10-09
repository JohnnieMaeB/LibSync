# 📚 AI Library Assistant — Portfolio Demo

An elegant, browser-based chatbot built with HTML, CSS, and JavaScript.  
Connects to Hugging Face’s open AI models to simulate a friendly digital librarian.

## ✨ Features
- Real AI responses (via Hugging Face Inference API)
- Fully client-side — no server needed
- Dark mode design with chat bubbles
- Smooth UX with loading animation
- Portable and perfect for GitHub Pages or portfolios

## 🧠 Tech Stack
- HTML5, CSS3, Vanilla JavaScript
- Hugging Face Inference API (`facebook/blenderbot-400M-distill`)

## 🚀 Setup

Follow these steps to get the project up and running:

### 1️⃣ Get a Hugging Face API Key
1. Go to [Hugging Face Tokens](https://huggingface.co/settings/tokens).  
2. Click **New token** and copy it.  

### 2️⃣ Set up the backend
```bash
cd ai-library-backend
npm init -y
npm install express node-fetch dotenv cors
```
3️⃣ Project structure

Your ai-library-backend/ folder should look like this:

```
ai-library-backend/
├─ server.js
├─ .env
└─ package.json
```

4️⃣ Configure environment variables

Create a .env file in the project root with the following:
```
HUGGINGFACE_TOKEN=your_hf_token_here
PORT=3000
```

5️⃣ Start the server

```
node server.js
```


