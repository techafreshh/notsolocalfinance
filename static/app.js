document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // --- Auth State & Elements ---
    let token = localStorage.getItem('finance_ai_token');
    let username = localStorage.getItem('finance_ai_username');

    const authOverlay = document.getElementById('auth-overlay');
    const appMain = document.getElementById('app-main');
    const authError = document.getElementById('auth-error');
    const displayUsername = document.getElementById('display-username');
    const logoutBtn = document.getElementById('logout-btn');

    // --- Core UI Elements ---
    const fileInput = document.getElementById('file-input');
    const fileNameDisplay = document.getElementById('file-name');
    const uploadForm = document.getElementById('upload-form');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadStatus = document.getElementById('upload-status');

    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatWindow = document.getElementById('chat-window');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    const clearDataBtn = document.getElementById('clear-data-btn');
    const themeToggle = document.getElementById('theme-toggle');
    const sampleQuestions = document.getElementById('sample-questions');

    // --- Theme Management ---
    let currentTheme = localStorage.getItem('finance_ai_theme') || 'light';
    
    function applyTheme(theme) {
        if (theme === 'light') {
            document.body.classList.add('light-theme');
        } else {
            document.body.classList.remove('light-theme');
        }
        localStorage.setItem('finance_ai_theme', theme);
        updateThemeIcons(theme);
    }

    function updateThemeIcons(theme) {
        const moonIcon = themeToggle.querySelector('.dark-icon');
        const sunIcon = themeToggle.querySelector('.light-icon');
        if (theme === 'light') {
            moonIcon.classList.add('hidden');
            sunIcon.classList.remove('hidden');
        } else {
            moonIcon.classList.remove('hidden');
            sunIcon.classList.add('hidden');
        }
    }

    themeToggle.addEventListener('click', () => {
        currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(currentTheme);
    });

    // Initialize theme
    applyTheme(currentTheme);

    function generateSessionId() {
        return (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : 'session-' + Date.now() + '-' + Math.random().toString(36).substring(2);
    }

    let conversationHistory = [];
    const savedHistory = sessionStorage.getItem('finance_ai_history');
    if (savedHistory) {
        try { conversationHistory = JSON.parse(savedHistory); } catch(e) {}
    }

    let sessionId = sessionStorage.getItem('finance_ai_session_id');
    if (!sessionId) {
        sessionId = generateSessionId();
        sessionStorage.setItem('finance_ai_session_id', sessionId);
    }
    
    function saveSession() {
        sessionStorage.setItem('finance_ai_session_id', sessionId);
        sessionStorage.setItem('finance_ai_history', JSON.stringify(conversationHistory));
    }

    console.log("Finance AI Initialized with Session ID:", sessionId);

    function enableChat() {
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.placeholder = "Ask about your finances...";
        sampleQuestions.classList.remove('hidden');
    }

    function disableChat() {
        chatInput.disabled = true;
        sendBtn.disabled = true;
        chatInput.placeholder = "Upload a statement to start chatting...";
        sampleQuestions.classList.add('hidden');
    }

    // Handle sample question clicks
    sampleQuestions.addEventListener('click', (e) => {
        const badge = e.target.closest('.sample-badge');
        if (badge) {
            chatInput.value = badge.dataset.query;
            chatInput.focus();
        }
    });

    // Restore UI from history
    if (conversationHistory.length > 0) {
        chatWindow.innerHTML = ''; // Clear default greeting
        for (const msg of conversationHistory) {
            addMessageToChat(msg.role === 'assistant' ? 'AI' : 'User', msg.content, false);
        }
        enableChat();
        // Defer scroll to bottom to ensure elements are rendered
        setTimeout(() => { chatWindow.scrollTop = chatWindow.scrollHeight; }, 100);
    }

    // --- Authentication Logic ---

    function checkAuth() {
        if (token) {
            authOverlay.classList.add('hidden');
            appMain.classList.remove('hidden');
            displayUsername.textContent = username || 'User';
        } else {
            authOverlay.classList.remove('hidden');
            appMain.classList.add('hidden');
        }
    }

    checkAuth();

    logoutBtn.addEventListener('click', () => {
        localStorage.removeItem('finance_ai_token');
        localStorage.removeItem('finance_ai_username');
        location.reload();
    });

    function showAuthError(msg) {
        authError.textContent = msg;
        authError.classList.remove('hidden');
    }

    // --- Authorized Fetch Wrapper ---

    async function authFetch(url, options = {}) {
        if (!token) return;
        
        const headers = options.headers || {};
        headers['Authorization'] = `Bearer ${token}`;
        
        const response = await fetch(url, { ...options, headers });
        
        if (response.status === 401) {
            // Token expired or invalid
            logoutBtn.click();
            return;
        }
        
        return response;
    }

    // --- App Features (File Upload, Chat, etc.) ---

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            fileNameDisplay.textContent = e.target.files[0].name;
            uploadStatus.classList.add('hidden');
        } else {
            fileNameDisplay.textContent = 'No file chosen';
        }
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const file = fileInput.files[0];
        if (!file) return;

        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Processing...';
        uploadStatus.className = 'status-msg hidden';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await authFetch('/upload/file', {
                method: 'POST',
                body: formData
            });

            if (!response) return;
            const result = await response.json();

            if (response.ok) {
                showStatus(result.message, 'success');
                uploadForm.reset();
                fileNameDisplay.textContent = 'No file chosen';
                const replyText = `I've successfully processed ${result.num_transactions} transactions. How can I analyze them for you?`;
                conversationHistory.push({ role: 'assistant', content: replyText });
                saveSession();
                addMessageToChat('AI', replyText);
                enableChat();
            } else {
                showStatus(result.detail || 'Upload failed', 'error');
            }
        } catch (error) {
            showStatus('Network error during upload', 'error');
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Analyze Data';
        }
    });

    function showStatus(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.className = `status-msg ${type}`;
    }

    if (clearDataBtn) {
        clearDataBtn.addEventListener('click', async () => {
            if (!confirm("Are you sure you want to delete all your stored transactions? This action cannot be undone.")) return;
            clearDataBtn.disabled = true;
            clearDataBtn.textContent = 'Wiping...';
            try {
                const response = await authFetch('/clear', { method: 'POST' });
                if (!response) return;
                if (response.ok) {
                    showStatus("Data cleared successfully!", 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    const error = await response.json();
                    showStatus("Error: " + (error.detail || 'Unknown error'), 'error');
                }
            } catch (err) {
                showStatus("Network error.", 'error');
            } finally {
                clearDataBtn.disabled = false;
                clearDataBtn.textContent = 'Wipe All Records';
            }
        });
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;

        addMessageToChat('User', text);
        conversationHistory.push({ role: 'user', content: text });
        saveSession();

        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;

        const loadingId = addTypingIndicator();

        console.log("Sending chat request with session_id:", sessionId);
        try {
            const response = await authFetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: conversationHistory, session_id: sessionId })
            });

            if (!response) {
                removeTypingIndicator(loadingId);
                return;
            }

            const result = await response.json();
            removeTypingIndicator(loadingId);

            if (response.ok) {
                if (result.history) conversationHistory = result.history;
                else conversationHistory.push({ role: 'assistant', content: result.reply });
                saveSession();
                addMessageToChat('AI', result.reply);
            } else {
                addMessageToChat('AI', `Error: ${result.detail || 'Failed to process'}`);
            }
        } catch (error) {
            removeTypingIndicator(loadingId);
            addMessageToChat('AI', 'Network error.');
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    });

    clearChatBtn.addEventListener('click', () => {
        if (conversationHistory.length === 0) return;
        conversationHistory = [];
        sessionId = generateSessionId();
        saveSession();
        console.log("New chat started with session_id:", sessionId);
        chatWindow.innerHTML = '';
        addMessageToChat('AI', 'Session reset. I\'m ready for new questions.');
        disableChat();
    });

    function addMessageToChat(sender, text, scroll = true) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender.toLowerCase()}`;
        
        const iconName = sender === 'User' ? 'user' : 'bot';
        
        msgDiv.innerHTML = `
            <div class="avatar"><i data-lucide="${iconName}" size="18"></i></div>
            <div class="msg-content">${sender === 'User' ? escapeHTML(text) : marked.parse(text)}</div>
        `;
        chatWindow.appendChild(msgDiv);
        
        // Render new icons
        lucide.createIcons();
        
        if (scroll) scrollToBottom();
    }

    function addTypingIndicator() {
        const id = 'loader-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai';
        msgDiv.id = id;
        msgDiv.innerHTML = `
            <div class="avatar"><i data-lucide="bot" size="18"></i></div>
            <div class="typing-indicator">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;
        chatWindow.appendChild(msgDiv);
        lucide.createIcons();
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const loader = document.getElementById(id);
        if (loader) loader.remove();
    }

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function escapeHTML(str) {
        if (!str) return "";
        return str.replace(/[&<>'"]/g, tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag));
    }
});
