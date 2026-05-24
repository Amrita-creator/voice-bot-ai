// DOM Elements
const micButton = document.getElementById("micButton");
const chatMessages = document.getElementById("chatMessages");
const liveTranscript = document.getElementById("liveTranscript");
const statusIndicator = document.getElementById("statusIndicator");
const statusDot = statusIndicator.querySelector(".status-dot");
const statusText = statusIndicator.querySelector(".status-text");
const clearChatBtn = document.getElementById("clearChat");
const viewLogsBtn = document.getElementById("viewLogs");
const logsModal = document.getElementById("logsModal");
const closeModalBtn = document.getElementById("closeModal");
const logsContent = document.getElementById("logsContent");
const downloadLogsBtn = document.getElementById("downloadLogs");
const clearLogsBtn = document.getElementById("clearLogs");
const transcriptContainer = document.getElementById("transcriptContainer");

// Speech Recognition Setup
let recognition = null;
let isListening = false;
let conversationHistory = [];

// Check for browser support
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();

  // Configure recognition
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.lang = "hi-IN"; // Hindi as primary, will also catch Telugu

  // Try to add multiple languages
  try {
    recognition.lang = "hi-IN";
  } catch (e) {
    console.log("Multi-language not supported, using Hindi");
  }

  recognition.onstart = () => {
    isListening = true;
    updateUI("listening");
    liveTranscript.textContent = "Listening... बोलिए / చెప్పండి";
    liveTranscript.classList.add("listening");
  };

  recognition.onresult = (event) => {
    let interimTranscript = "";
    let finalTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const transcript = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += transcript;
      } else {
        interimTranscript += transcript;
      }
    }

    // Update live transcript
    if (finalTranscript) {
      liveTranscript.textContent = finalTranscript;
      // Process the final transcript
      processUserInput(finalTranscript);
    } else if (interimTranscript) {
      liveTranscript.textContent = interimTranscript + "...";
    }
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error:", event.error);
    isListening = false;
    updateUI("error");

    let errorMessage = "Error occurred. Try again.";
    if (event.error === "no-speech") {
      errorMessage = "No speech detected. Please try again.";
    } else if (event.error === "not-allowed") {
      errorMessage = "Microphone access denied. Please enable it.";
    } else if (event.error === "network") {
      errorMessage = "Network error. Check your connection.";
    }

    liveTranscript.textContent = errorMessage;
    liveTranscript.classList.remove("listening");
  };

  recognition.onend = () => {
    isListening = false;
    updateUI("ready");
    liveTranscript.classList.remove("listening");
  };
} else {
  // Browser doesn't support speech recognition
  micButton.disabled = true;
  micButton.innerHTML =
    '<span class="mic-icon">❌</span><span class="mic-text">Not Supported</span>';
  liveTranscript.textContent =
    "Speech recognition not supported in this browser. Try Chrome.";
  statusText.textContent = "Unsupported";
}

// Update UI based on state
function updateUI(state) {
  switch (state) {
    case "listening":
      micButton.classList.add("listening");
      micButton.querySelector(".mic-text").textContent = "Listening...";
      statusDot.classList.add("listening");
      statusText.textContent = "Listening";
      break;
    case "processing":
      micButton.classList.remove("listening");
      micButton.querySelector(".mic-text").textContent = "Processing...";
      statusText.textContent = "Processing";
      break;
    case "speaking":
      micButton.querySelector(".mic-text").textContent = "Speaking...";
      statusText.textContent = "Speaking";
      break;
    case "ready":
      micButton.classList.remove("listening");
      micButton.querySelector(".mic-text").textContent = "Tap to Speak";
      statusDot.classList.remove("listening");
      statusText.textContent = "Ready";
      break;
    case "error":
      micButton.classList.remove("listening");
      micButton.querySelector(".mic-text").textContent = "Try Again";
      statusDot.classList.remove("listening");
      statusText.textContent = "Error";
      break;
  }
}

// Add message to chat
function addMessage(text, isUser = false) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${isUser ? "user-message" : "bot-message"}`;

  messageDiv.innerHTML = `
        <div class="message-avatar">${isUser ? "👤" : "🤖"}</div>
        <div class="message-content">
            <p>${text}</p>
        </div>
    `;

  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Add to conversation history
  conversationHistory.push({
    role: isUser ? "user" : "bot",
    content: text,
  });
}

// Process user input and get bot response
async function processUserInput(text) {
  if (!text.trim()) return;

  // Add user message to chat
  addMessage(text, true);
  updateUI("processing");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: text,
        history: conversationHistory,
      }),
    });

    if (!response.ok) throw new Error("Server error");

    const data = await response.json();
    const botResponse = data.response;

    // Add bot message to chat
    addMessage(botResponse, false);

    // Speak the response
    speakText(botResponse);
  } catch (error) {
    console.error("Error:", error);
    addMessage("Sorry, kuch problem ho gaya. Please try again.", false);
    updateUI("ready");
  }
}

// Text to Speech
function speakText(text) {
  if ("speechSynthesis" in window) {
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const cleanText = text.replace(
      /[\u{1F300}-\u{1FAFF}|\u{2600}-\u{27BF}]/gu,
      "",
    );

    const utterance = new SpeechSynthesisUtterance(cleanText);

    // Try to find Hindi voice
    const voices = window.speechSynthesis.getVoices();
    const hindiVoice = voices.find(
      (voice) => voice.lang.includes("hi") || voice.lang.includes("IN"),
    );

    if (hindiVoice) {
      utterance.voice = hindiVoice;
    }

    utterance.rate = 0.9;
    utterance.pitch = 1;

    utterance.onstart = () => {
      updateUI("speaking");
    };

    utterance.onend = () => {
      updateUI("ready");
    };

    utterance.onerror = () => {
      updateUI("ready");
    };

    window.speechSynthesis.speak(utterance);
  } else {
    updateUI("ready");
  }
}

// Load voices when they're ready
if ("speechSynthesis" in window) {
  window.speechSynthesis.onvoiceschanged = () => {
    window.speechSynthesis.getVoices();
  };
}

// Mic button click handler
micButton.addEventListener("click", () => {
  if (!recognition) return;

  if (isListening) {
    recognition.stop();
  } else {
    try {
      recognition.start();
    } catch (e) {
      console.log("Recognition already started");
    }
  }
});

// Clear chat
clearChatBtn.addEventListener("click", () => {
  chatMessages.innerHTML = `
        <div class="message bot-message">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <p>Namaste! 🙏 Main aapka voice assistant hoon. Hindi aur Telugu dono mein baat kar sakte hain. Mic button dabayein aur bolna shuru karein!</p>
            </div>
        </div>
    `;
  conversationHistory = [];
  liveTranscript.textContent = "Mic button dabayein aur bolna shuru karein...";
});

// View logs
viewLogsBtn.addEventListener("click", async () => {
  try {
    const response = await fetch("/logs");
    const logs = await response.json();

    if (logs.length === 0) {
      logsContent.innerHTML =
        '<div class="empty-logs">📭 No conversation logs yet</div>';
    } else {
      logsContent.innerHTML = logs
        .map(
          (log) => `
                <div class="log-entry">
                    <div class="timestamp">${new Date(log.timestamp).toLocaleString()}</div>
                    <div class="user-log">👤 User: ${log.user}</div>
                    <div class="bot-log">🤖 Bot: ${log.bot}</div>
                </div>
            `,
        )
        .join("");
    }

    logsModal.classList.add("active");
  } catch (error) {
    console.error("Error loading logs:", error);
  }
});

// Close modal
closeModalBtn.addEventListener("click", () => {
  logsModal.classList.remove("active");
});

logsModal.addEventListener("click", (e) => {
  if (e.target === logsModal) {
    logsModal.classList.remove("active");
  }
});

// Download logs
downloadLogsBtn.addEventListener("click", async () => {
  try {
    const response = await fetch("/logs");
    const logs = await response.json();

    // Create text format
    let textContent = "Voice Bot Conversation Logs\n";
    textContent += "=".repeat(40) + "\n\n";

    logs.forEach((log) => {
      textContent += `[${new Date(log.timestamp).toLocaleString()}]\n`;
      textContent += `User: ${log.user}\n`;
      textContent += `Bot: ${log.bot}\n\n`;
    });

    // Download as file
    const blob = new Blob([textContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "chat_logs.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error("Error downloading logs:", error);
  }
});

// Clear all logs
clearLogsBtn.addEventListener("click", async () => {
  if (confirm("Are you sure you want to clear all logs?")) {
    try {
      await fetch("/clear-logs", { method: "POST" });
      logsContent.innerHTML =
        '<div class="empty-logs">📭 No conversation logs yet</div>';
    } catch (error) {
      console.error("Error clearing logs:", error);
    }
  }
});

// Keyboard shortcut for mic
document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && e.target === document.body) {
    e.preventDefault();
    micButton.click();
  }
});
