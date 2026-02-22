document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
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

    // Chat History State
    let conversationHistory = [];

    // --- File Upload Logic ---

    // Update label when file is chosen
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

        // UI Reset
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';
        uploadStatus.classList.add('hidden');
        uploadStatus.className = 'status-msg'; // reset classes

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload/file', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                showStatus(result.message, 'success');
                // Clear file input
                uploadForm.reset();
                fileNameDisplay.textContent = 'No file chosen';
                // Reset chat context context since new data is loaded
                conversationHistory = [];
                addMessageToChat('AI', `I've successfully processed ${result.num_transactions} transactions from your statement. How can I analyze them for you?`);
            } else {
                showStatus(result.detail || 'Upload failed', 'error');
            }
        } catch (error) {
            showStatus('Network error while uploading', 'error');
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload';
        }
    });

    function showStatus(message, type) {
        uploadStatus.textContent = message;
        uploadStatus.classList.add(type);
        uploadStatus.classList.remove('hidden');
    }

    const clearDataBtn = document.getElementById('clear-data-btn');
    if (clearDataBtn) {
        clearDataBtn.addEventListener('click', async () => {
            if (!confirm("Are you sure you want to delete all stored transactions? This cannot be undone.")) {
                return;
            }

            clearDataBtn.disabled = true;
            clearDataBtn.textContent = 'Wiping...';

            try {
                const response = await fetch('/clear', {
                    method: 'POST'
                });

                if (response.ok) {
                    alert("Database cleared successfully! You can now upload a fresh CSV.");
                } else {
                    const error = await response.json();
                    alert("Failed to clear database: " + (error.detail || 'Unknown error'));
                }
            } catch (err) {
                alert("Network error while trying to clear database.");
            } finally {
                clearDataBtn.disabled = false;
                clearDataBtn.textContent = 'Wipe Database (Clear All Data)';
            }
        });
    }

    // --- Chat Logic ---

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const text = chatInput.value.trim();
        if (!text) return;

        // Add user message to UI and history
        addMessageToChat('User', text);
        conversationHistory.push({ role: 'user', content: text });

        // UI Reset
        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;

        const loadingId = addTypingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ messages: conversationHistory })
            });

            const result = await response.json();
            removeTypingIndicator(loadingId);

            if (response.ok) {
                // The backend now returns the updated history including tool calls and responses
                if (result.history) {
                    conversationHistory = result.history;
                } else {
                    conversationHistory.push({ role: 'assistant', content: result.reply });
                }
                addMessageToChat('AI', result.reply);
            } else {
                addMessageToChat('AI', `Error: ${result.detail || 'Failed to process request'}`);
            }

        } catch (error) {
            removeTypingIndicator(loadingId);
            addMessageToChat('AI', 'Network error while calling the AI service.');
        } finally {
            chatInput.disabled = false;
            sendBtn.disabled = false;
            chatInput.focus();
        }
    });

    clearChatBtn.addEventListener('click', () => {
        // Wipe context
        conversationHistory = [];

        // Reset HTML
        chatWindow.innerHTML = `
            <div class="message ai">
                <div class="avatar">AI</div>
                <div class="msg-content">Chat history cleared. What would you like to ask about your finances?</div>
            </div>
        `;
    });

    function addMessageToChat(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender.toLowerCase()}`;

        msgDiv.innerHTML = `
            <div class="avatar">${sender === 'User' ? 'U' : 'AI'}</div>
            <div class="msg-content">${escapeHTML(text)}</div>
        `;

        chatWindow.appendChild(msgDiv);
        scrollToBottom();
    }

    function addTypingIndicator() {
        const id = 'loader-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message ai';
        msgDiv.id = id;

        msgDiv.innerHTML = `
            <div class="avatar">AI</div>
            <div class="typing-indicator">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        `;

        chatWindow.appendChild(msgDiv);
        scrollToBottom();
        return id;
    }

    function removeTypingIndicator(id) {
        const loader = document.getElementById(id);
        if (loader) {
            loader.remove();
        }
    }

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Basic HTML escaping for security
    function escapeHTML(str) {
        if (!str) return "";
        return str.replace(/[&<>'"]/g,
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag)
        );
    }
});
