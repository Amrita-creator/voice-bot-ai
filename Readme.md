# 🎙️ Multilingual AI Voice Assistant

A smart multilingual AI-powered voice assistant built using **Flask + Hugging Face + Speech Recognition + Text-to-Speech**.

This project supports:

* Hindi
* Telugu
* Hinglish
* Voice-based interaction
* Conversational memory
* AI-enhanced responses
* Demo scheduling flow
* Pricing & product discussions
* Context-aware conversations

Unlike traditional keyword-only chatbots, this assistant combines:

* Rule-based intent detection
* Hugging Face AI response enhancement
* Context memory
* Semantic conversational handling

to create a more natural multilingual AI assistant experience.

---

# ✨ Features

## 🧠 AI + Rule-Based Hybrid Architecture

The assistant uses:

* Rule-based intent detection for stability
* Hugging Face LLM for conversational enhancement
* Context memory for follow-up handling

This keeps the system:

* lightweight
* fast
* beginner-friendly
* internship-ready

---

## 🌍 Multilingual Support

Supports:

* Hindi
* Telugu
* Hinglish
* Telugu words written in English

Example:

```text
User: Demo kavali
Bot: Sure 😊 Demo arrange cheddam. Morning ya evening convenient untundi?
```

---

## 🎤 Voice Features

### Speech-to-Text (STT)

* Browser Web Speech API
* Voice input support
* Hindi speech recognition

### Text-to-Speech (TTS)

* Browser SpeechSynthesis
* Hindi voice preference
* Real-time voice responses

---

## 💬 Conversational Memory

The assistant remembers:

* user name
* selected language
* last intent
* timing preferences
* follow-up states
* team size context

Example flow:

```text
User: Demo chahiye
Bot: Morning ya evening?

User: Morning
Bot: Online demo kavala?

User: Online
Bot: Email ID share cheyyandi.
```

---

## 🤖 AI-Enhanced Conversations

Hugging Face LLM improves:

* conversational quality
* response smoothness
* multilingual flow
* natural follow-ups
* contextual understanding

The AI layer rewrites and enhances base responses generated using `pick_response()`.

---

# 🛠️ Tech Stack

## Backend

* Python
* Flask
* Regex NLP
* Hugging Face Inference API

## Frontend

* HTML
* CSS
* JavaScript

## Voice

* Web Speech API
* SpeechSynthesis API

## AI/NLP

* Hugging Face LLM
* Semantic intent matching
* Context-aware response generation

---

# 📂 Project Structure

```text
voice-bot/
│
├── app.py
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
├── logs/
│   └── chat_logs.txt
├── requirements.txt
└── README.md
```

---

# ⚙️ Installation

## 1️⃣ Clone Repository

```bash
git clone <your-repo-url>
cd voice-bot
```

---

## 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate environment:

### Windows

```bash
venv\Scripts\activate
```

### Linux/Mac

```bash
source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Add Hugging Face API Key

Inside `app.py`:

```python
HF_API_TOKEN = "YOUR_API_KEY"
```

---

## 5️⃣ Run Flask App

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

---

# 🌐 Ngrok Deployment

## Start Flask

```bash
python app.py
```

## Start ngrok

```bash
ngrok http 5000
```

Use the generated public URL.

---

# 🧠 Core Functionalities

## ✅ Intent Detection

Handles:

* greetings
* help
* demo requests
* pricing queries
* product discussions
* timing confirmation
* online/offline demo flow
* contact handling
* thank-you responses
* goodbye handling

---

## ✅ Context-Aware Flow

Conversation state tracking using:

```python
conversation_memory
```

Stores:

```python
{
    "name": None,
    "language": "mixed",
    "last_intent": None,
    "pending_followup": None,
    "confirmed_timing": None,
    "team_size": None,
}
```

---

## ✅ Semantic Matching

The assistant supports indirect conversational phrases.

Example:

```text
"Demo arrange karo"
"Show demo"
"Demo kavali"
```

all map to the same intent.

---

# 🎯 Example Conversation

```text
User: Hello mera naam Amrita hai
Bot: Namaste Amrita ji 😊 Meeku demo kavala ya pricing details?

User: Demo wala
Bot: Bilkul 😊 Demo arrange cheddam. Morning ya evening convenient untundi?

User: Morning
Bot: Morning timing fix chesanu 😊 Online lo continue cheddama?

User: Online
Bot: Sure 😊 Google Meet session setup cheddam. Contact email pampandi.
```

---

# 🚀 Future Improvements

Planned improvements:

* better semantic understanding
* database integration
* WhatsApp integration
* persistent memory
* admin dashboard
* analytics panel
* appointment booking system
* vector search embeddings
* multilingual expansion

---

# 📌 Project Highlights

✅ Multilingual AI Voice Assistant

✅ Hindi + Telugu conversational flow

✅ Hugging Face AI integration

✅ Context-aware conversation handling

✅ Voice input + output

✅ Lightweight architecture

✅ Internship-ready AI project

---

# 👨‍💻 Author

Developed by Amrita Chaturvedi.

Built as an AI internship project focused on:

* conversational AI
* multilingual NLP
* voice interaction
* AI-enhanced assistants

---

# 📄 License

This project is open-source and available for educational purposes.
