document.addEventListener('DOMContentLoaded', () => {
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

    let conversationHistory = [];

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
        uploadBtn.textContent = 'Uploading...';
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
                conversationHistory = [];
                addMessageToChat('AI', `I've successfully processed ${result.num_transactions} transactions. How can I analyze them for you?`);
            } else {
                showStatus(result.detail || 'Upload failed', 'error');
            }
        } catch (error) {
            showStatus('Network error during upload', 'error');
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload';
        }
    });

    function showStatus(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.className = `status-msg ${type}`;
    }

    if (clearDataBtn) {
        clearDataBtn.addEventListener('click', async () => {
            if (!confirm("Are you sure you want to delete all your stored transactions?")) return;
            clearDataBtn.disabled = true;
            clearDataBtn.textContent = 'Wiping...';
            try {
                const response = await authFetch('/clear', { method: 'POST' });
                if (!response) return;
                if (response.ok) alert("Data cleared successfully!");
                else {
                    const error = await response.json();
                    alert("Error: " + (error.detail || 'Unknown error'));
                }
            } catch (err) {
                alert("Network error.");
            } finally {
                clearDataBtn.disabled = false;
                clearDataBtn.textContent = 'Wipe Database (Clear All Data)';
            }
        });
    }

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = chatInput.value.trim();
        if (!text) return;

        addMessageToChat('User', text);
        conversationHistory.push({ role: 'user', content: text });

        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;

        const loadingId = addTypingIndicator();

        try {
            const response = await authFetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: conversationHistory })
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
        conversationHistory = [];
        chatWindow.innerHTML = `<div class="message ai"><div class="avatar">AI</div><div class="msg-content"><p>History cleared. What's next?</p></div></div>`;
    });

    function addMessageToChat(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender.toLowerCase()}`;
        msgDiv.innerHTML = `
            <div class="avatar">${sender === 'User' ? 'U' : 'AI'}</div>
            <div class="msg-content">${sender === 'User' ? escapeHTML(text) : marked.parse(text)}</div>
        `;
        chatWindow.appendChild(msgDiv);
        scrollToBottom();
    }

    function addTypingIndicator() {
        const id = 'loader-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai';
        msgDiv.id = id;
        msgDiv.innerHTML = `<div class="avatar">AI</div><div class="typing-indicator"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
        chatWindow.appendChild(msgDiv);
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
