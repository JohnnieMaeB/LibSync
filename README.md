# 📚 AI Library Assistant — Portfolio Demo

![Status: Live](https://img.shields.io/badge/Status-Live-brightgreen) ![Frontend](https://img.shields.io/badge/Frontend-GitHub-blue) ![Backend](https://img.shields.io/badge/Backend-Render-purple)

# 🚀 LibSync

**LibSync** is an AI-powered chatbot designed to assist users with library services. Built with modern web technologies and Hugging Face's inference API, LibSync demonstrates a full-stack workflow, cloud deployment, and AI integration.

---

## 🎯 Purpose

LibSync provides a conversational interface for library patrons, enabling natural language questions and helpful responses.  
The project is currently in **active development**, focusing on technical experimentation, deployment workflows, and AI capabilities.

---

## 🛠️ Tech Stack

- **Frontend:** Vanilla JavaScript, HTML, CSS  
- **Backend:** Node.js, Express.js  
- **AI Integration:** Hugging Face Inference API, `InferenceClient`  
- **Cloud Deployment:** [Render](https://render.com/)

---

## 🏆 Skills Demonstrated

This project showcases a variety of in-demand skills, including:

- **Full-Stack Development:** Building and connecting frontend (JS/HTML/CSS) with backend (Node.js/Express)  
- **API Integration:** Using Hugging Face Inference API to generate AI responses  
- **Cloud Deployment:** Deploying backend on Render, frontend on GitHub Pages  
- **Environment Configuration & Security:** Managing environment variables, securing API tokens  
- **Debugging & Logging:** Implementing request/response logging for monitoring and troubleshooting  
- **Project Workflow:** Version control with Git, branching, and basic CI/CD awareness  
- **UI/UX Design:** Real-time chat interface, responsive and interactive frontend design  

---

## ✨ Features

- Real-time chat interface  
- Hugging Face AI responses  
- Cloud deployment for remote access  

---

## 💻 Local Setup

1. **Clone the repository**  

```bash
git clone <your-repo-url>
cd LibSync
```

2. Install backend dependencies

```bash
cd ai-library-backend
npm install
```

3. Create a .env file in ai-library-backend with your Hugging Face token:

```
HUGGINGFACE_TOKEN=your_huggingface_api_token_here
PORT=3000
```

4. Run the backend locally

```bash
node server.js
```

5. Run the frontend locally
Open index.html in your browser. Make sure the fetch call in your JS points to your local backend:

```JavaScript
const response = await fetch("http://localhost:3000/chat", { ... });
```

6. Start chatting! 💬

---

## ☁️ Cloud Deployment (Render)

- **Start Command:** `node server.js`  
- **Environment Variables:** Set `HUGGINGFACE_TOKEN` on Render  

Once deployed, update the frontend `fetch` URL to point to your Render URL:

```JavaScript
const response = await fetch("https://<your-render-app>.onrender.com/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ message: question }),
});
```
---

## 🛠️ Next Steps

- **Vector Database Integration:** Add **Pinecone** for semantic search and retrieval of library policies and resources. Automate vector DB creation and upsert operations using **GitHub Actions** as Infrastructure as Code (IaC).  
- **Model refinement:** Narrow AI responses to library-specific queries and improve policy adherence through prompt and model tuning.  
- **Frontend improvements:** Enhanced UI/UX, loading indicators, error handling, and session persistence for a smoother chat experience.  
- **Testing:** Unit, integration, and end-to-end tests for backend stability and API reliability.  
- **Additional features:** Logging, authentication, and advanced security optimizations.  
- **Deployment optimization:** Expand **CI/CD** pipelines for automated testing, vector updates, and production deployment.  


---

## 🚀 Featured Deployment

Experience LibSync in action! Interact with the chatbot and explore the UI:

| Environment | Link |
|-------------|------|
| Prod | [🌐 Visit LibSync](https://your-username.github.io/your-repo-name/) |

Interact with the chatbot, explore the interface, and see the project in action.  

> **Note:** This is a demo project running exclusively on free-tier services. The backend on Render may spin down after periods of inactivity, which can result in a delay of up to ~50 seconds for the AI to respond when waking from idle.

