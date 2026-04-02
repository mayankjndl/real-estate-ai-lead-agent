# Internship Project: Real Estate AI Lead Agent (Backend)
**By: Mayank Jindal (AI and LLM Automation Intern)**

## 🌟 Overview
For this project, my goal was to build a "Client-Grade" AI assistant for a real estate company. Unlike a simple chatbot, this system acts as a real sales assistant that qualifies users and captures them as high-quality leads.

## 🛠️ What I Built
I developed the entire backend system that powers the AI's "brain" and the data storage. Here is a simplified breakdown:

### 1. Smart Memory (Session-Based)
I built a system where the AI doesn't forget. If a user says "I am looking for a 2BHK" and then later says "My budget is 80L," the AI remembers both pieces of information to give a personalized recommendation.

### 2. Intelligent Data Extraction
I implemented a "silent" extraction tool. While the AI is talking to the user, it is also working in the background to identify and save important details into our database:
- **Name & Phone Number**
- **Budget Range**
- **Desired Location**
- **Intent** (Buying, Renting, or Investing)

### 3. Lead Scoring System
To help sales teams focus on the best clients, I built a scoring logic. The AI automatically labels every lead as:
- **High Intent:** Ready to buy soon with a clear budget.
- **Medium Intent:** Interested but needs more info.
- **Low Intent:** Just browsing or exploring.

### 4. Professional Analytics Dashboard
I created secured "Client-Grade" API endpoints so the company founders (Piyush and Yashraj) can see exactly how the agent is performing:
- **Total Leads Captured**
- **Conversion Rate** (how many users became leads)
- **Intent Breakdown** (how many buyers vs. renters)

### 5. Security & Stability
- **API Security:** I added an "X-API-Key" security layer to protect sensitive lead data.
- **Robust Testing:** I tested the system against **30+ real-world scenarios** to ensure it never breaks and always moves the user toward sharing their contact details.

## 💻 Tech Stack Used
- **FastAPI:** For a high-speed, professional web server.
- **SQLAlchemy & SQLite:** To securely store user messages and lead data locally.
- **Google Gemini 1.5 Flash:** The latest AI model for fast and smart reasoning.
- **Pydantic:** To ensure all data entering the system is clean and accurate.

---
*This backend is designed to be easily customized for any real estate client by simply updating the configuration.*
