const API_BASE = "http://localhost:5000";

const messagesDiv = document.getElementById("messages");
const queryInput = document.getElementById("queryInput");
const queryForm = document.getElementById("queryForm");
const sendBtn = document.getElementById("sendBtn");
const recordBtn = document.getElementById("recordBtn");
const languageSelector = document.getElementById("languageSelector");
const loadingOverlay = document.getElementById("loadingOverlay");
const historyList = document.getElementById("historyList");

const messageHistory = [];
let isRecording = false;
let recognition = null;

if (window.SpeechRecognition || window.webkitSpeechRecognition) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.addEventListener("result", (event) => {
        const transcript = event.results[0][0].transcript.trim();
        queryInput.value = transcript;
        if (transcript) {
            addMessage(transcript, "user");
            handleQuery(new Event("submit"));
        }
    });
    recognition.addEventListener("end", () => {
        stopRecognition();
    });
    recognition.addEventListener("error", (event) => {
        console.error("Speech recognition error:", event.error);
        alert("Voice recognition error: " + event.error);
        stopRecognition();
    });
}

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    queryForm.addEventListener("submit", handleQuery);
    recordBtn.addEventListener("click", toggleRecording);
    languageSelector.addEventListener("change", updatePageLanguage);
    updatePageLanguage();
});

const translations = {
    en: {
        ready: "Ready",
        language_label: "Language",
        welcome: "Welcome to the KSP Crime Assistant. Submit inquiries on crime policy and reporting.",
        query_placeholder: "Enter your inquiry regarding crime policy or reporting procedures.",
        suggestion_theft: "What is theft?",
        suggestion_types: "Crime types",
        suggestion_assault: "What is assault?",
        chat_history_title: "Chat History",
        no_history: "No questions recorded yet.",
        faq_title: "FAQ",
        faq_fir: "How do I draft an FIR?",
        faq_theft: "What should I do after a theft?",
        faq_assault: "How can I report an assault?",
        faq_evidence: "What evidence should I collect for a complaint?",
        actions_title: "Actions",
        clear_chat: "Clear Chat",
    },
    hi: {
        ready: "तैयार",
        language_label: "भाषा",
        welcome: "KSP क्राइम असिस्टेंट में आपका स्वागत है। अपराध नीति और रिपोर्टिंग के बारे में पूछताछ करें।",
        query_placeholder: "अपराध नीति या रिपोर्टिंग प्रक्रियाओं के बारे में अपनी पूछताछ दर्ज करें।",
        suggestion_theft: "चोरी क्या है?",
        suggestion_types: "अपराध के प्रकार",
        suggestion_assault: "हमले क्या हैं?",
        chat_history_title: "चैट इतिहास",
        no_history: "कोई सवाल दर्ज नहीं किया गया।",
        faq_title: "पूछे जाने वाले प्रश्न",
        faq_fir: "मैं FIR कैसे लिखूं?",
        faq_theft: "चोरी के बाद मुझे क्या करना चाहिए?",
        faq_assault: "मैं हमले की रिपोर्ट कैसे करूं?",
        faq_evidence: "मुझसे शिकायत के लिए मुझे कौन सा साक्ष्य एकत्र करना चाहिए?",
        actions_title: "कार्रवाई",
        clear_chat: "चैट साफ़ करें",
    },
    kn: {
        ready: "ಸಜ್ಜು",
        language_label: "ಭಾಷೆ",
        welcome: "KSP ಕ್ರೈಂ ಅಸಿಸ್ಟಂಟ್ ಗೆ ಸ್ವಾಗತ. ಅಪರಾಧ ನೀತಿ ಮತ್ತು ವರದಿಗೊಳಿಸುವಿಕೆ ಕುರಿತು ಪ್ರಶ್ನೆ ಕೇಳಿ.",
        query_placeholder: "ಅಪರಾಧ ನೀತಿ ಅಥವಾ ವರದಿ ಪ್ರಕ್ರಿಯೆಗಳ ಬಗ್ಗೆ ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ನಮೂದಿಸಿ.",
        suggestion_theft: "ಕಳ್ಳತನವೆಂದರೆ ಏನು?",
        suggestion_types: "ಅಪರಾಧಗಳ ಪ್ರಕಾರಗಳು",
        suggestion_assault: "ದಾಳಿ ಎಂದರೆ ಏನು?",
        chat_history_title: "ಚಾಟ್ ಇತಿಹಾಸ",
        no_history: "ಯಾವುದೇ ಪ್ರಶ್ನೆಗಳನ್ನು ದಾಖಲಿಸಲಿಲ್ಲ.",
        faq_title: "ಆಕ್ವಿಷನ್‌ಗಳು",
        faq_fir: "ನಾನು FIR ಅನ್ನು ಹೇಗೆ ತಯಾರಿಸಬಹುದು?",
        faq_theft: "ಕಳ್ಳತನದ ನಂತರ ನಾನು ಏನು ಮಾಡಿ?",
        faq_assault: "ನಾನು ದಾಳಿಯನ್ನು ಹೇಗೆ ವರದಿ ಮಾಡಬಹುದು?",
        faq_evidence: "ಅಭ್ಯರ್ಥಿಗಾಗಿ ಯಾವ ಸಾಕ್ಷ್ಯವನ್ನು ಸಂಗ್ರಹಿಸಬೇಕು?",
        actions_title: "ಕಾರ್ಯಗಳು",
        clear_chat: "ಚಾಟ್ ತೆರವುಗೊಳಿಸಿ",
    },
};

function showLoading(show = true) {
    if (show) {
        loadingOverlay.classList.add("show");
    } else {
        loadingOverlay.classList.remove("show");
    }
}

function addMessage(text, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}`;

    const contentDiv = document.createElement("div");
    contentDiv.className = "message-content";
    contentDiv.textContent = text;

    messageDiv.appendChild(contentDiv);
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    if (sender === "user") {
        addToHistory(text);
    }
}

function addToHistory(text) {
    messageHistory.push(text);
    if (messageHistory.length > 8) {
        messageHistory.shift();
    }

    historyList.innerHTML = messageHistory
        .map((entry) => `<div class="history-item">${entry}</div>`)
        .join("");
}

async function handleQuery(e) {
    e.preventDefault();

    const queryText = queryInput.value.trim();
    if (!queryText) return;

    addMessage(queryText, "user");
    queryInput.value = "";

    showLoading(true);
    sendBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/query`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ query: queryText, language: languageSelector.value }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || "Failed to get response");
        }

        const data = await response.json();
        addMessage(data.answer, "assistant");
    } catch (error) {
        addMessage(`Error: ${error.message}`, "assistant");
        console.error("Query error:", error);
    } finally {
        showLoading(false);
        sendBtn.disabled = false;
        queryInput.focus();
    }
}

async function translateQuery(text) {
    const targetLang = languageSelector.value;
    if (targetLang === "en") {
        return text;
    }
    return text; // Placeholder for future translation support
}

function toggleRecording() {
    if (!recognition) {
        alert("Voice recognition is not supported in this browser.");
        return;
    }

    if (isRecording) {
        recognition.stop();
        stopRecognition();
    } else {
        startRecognition();
    }
}

function startRecognition() {
    if (!recognition) {
        alert("Voice recognition is not supported in this browser.");
        return;
    }

    recognition.lang = languageSelector.value === "hi" ? "hi-IN" : languageSelector.value === "kn" ? "kn-IN" : "en-US";
    recognition.start();
    isRecording = true;
    recordBtn.classList.add("recording");
    recordBtn.title = "Stop voice input";
}

function stopRecognition() {
    isRecording = false;
    recordBtn.classList.remove("recording");
    recordBtn.title = "Start voice input";
}

function updatePageLanguage() {
    const lang = languageSelector.value;
    const labels = translations[lang] || translations.en;

    const nodes = document.querySelectorAll("[data-i18n]");
    nodes.forEach((node) => {
        const key = node.getAttribute("data-i18n");
        if (key && labels[key]) {
            node.textContent = labels[key];
        }
    });

    const placeholderNode = document.querySelector("[data-placeholder-i18n]");
    if (placeholderNode) {
        const placeholderKey = placeholderNode.getAttribute("data-placeholder-i18n");
        if (placeholderKey && labels[placeholderKey]) {
            placeholderNode.setAttribute("placeholder", labels[placeholderKey]);
        }
    }
}

function setQuery(query) {
    queryInput.value = query;
    queryInput.focus();
}

function clearChat() {
    messageHistory.length = 0;
    historyList.innerHTML = `
        <div class="history-item empty">No conversation history yet. Your recent questions and answers will appear here.</div>
    `;
    messagesDiv.innerHTML = `
        <div class="message system">
            <div class="message-content">
                <p>Chat cleared. Ask any questions about crimes, rules, and regulations.</p>
            </div>
        </div>
    `;
    queryInput.value = "";
    queryInput.focus();
}
