/**
 * Scene Chat UI Component
 * Manages the chat interface for scene communication.
 *
 * Features:
 * - Message display with formatting
 * - Real-time message updates
 * - Character selection for IC messages
 * - Message type switching (IC/OOC/Private)
 * - Markdown rendering
 * - Rate limiting feedback
 * - Connection status indicators
 * - Message history loading
 */

class SceneChatUI {
    constructor(containerId, sceneId, options = {}) {
        this.containerId = containerId;
        this.sceneId = sceneId;
        this.options = {
            maxMessageHistory: 100,
            markdownEnabled: true,
            autoScroll: true,
            showTimestamps: true,
            showCharacterAvatars: false, // Future feature
            ...options
        };

        // State
        this.messages = [];
        this.characters = [];
        this.currentUser = null;
        this.selectedCharacter = null;
        this.messageType = 'PUBLIC';
        this.isLoading = false;
        this.rateLimitStatus = {
            remaining: 10,
            resetTime: 0,
            isLimited: false
        };

        // WebSocket connection
        this.websocket = null;

        // DOM elements
        this.container = null;
        this.messagesContainer = null;
        this.messageInput = null;
        this.characterSelect = null;
        this.messageTypeSelect = null;
        this.sendButton = null;
        this.connectionStatus = null;

        // Initialize
        this.init();
    }

    /**
     * Initialize the chat UI
     */
    async init() {
        try {
            await this.setupDOM();
            await this.loadUserData();
            await this.loadCharacters();
            await this.loadMessageHistory();
            this.setupWebSocket();
            this.setupEventListeners();

            console.log('Scene chat UI initialized successfully');
        } catch (error) {
            console.error('Failed to initialize scene chat UI:', error);
            this.showError('Failed to initialize chat');
        }
    }

    /**
     * Setup DOM structure
     */
    setupDOM() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            throw new Error(`Container element '${this.containerId}' not found`);
        }

        this.container.innerHTML = `
            <div class="scene-chat">
                <div class="chat-header">
                    <h5 class="mb-0">Scene Chat</h5>
                    <div class="connection-status" id="connection-status">
                        <span class="status-indicator disconnected"></span>
                        <span class="status-text">Connecting...</span>
                    </div>
                </div>

                <div class="chat-messages" id="chat-messages">
                    <div class="loading-indicator d-none">
                        <div class="spinner-border spinner-border-sm" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <span class="ms-2">Loading messages...</span>
                    </div>
                </div>

                <div class="chat-input">
                    <div class="input-controls mb-2">
                        <div class="row g-2">
                            <div class="col-md-4">
                                <select class="form-select form-select-sm" id="message-type">
                                    <option value="PUBLIC">Public (IC)</option>
                                    <option value="OOC">Out of Character</option>
                                    <option value="PRIVATE">Private Message</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <select class="form-select form-select-sm" id="character-select" disabled>
                                    <option value="">Select Character...</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <select class="form-select form-select-sm d-none" id="recipient-select">
                                    <option value="">Select Recipient...</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div class="input-group">
                        <textarea
                            class="form-control"
                            id="message-input"
                            placeholder="Type your message..."
                            rows="2"
                            maxlength="2000"
                        ></textarea>
                        <button class="btn btn-primary" type="button" id="send-button" disabled>
                            <i class="fas fa-paper-plane"></i>
                            Send
                        </button>
                    </div>

                    <div class="input-help">
                        <small class="text-muted">
                            <span id="char-count">0/2000</span> |
                            <span id="rate-limit-status"></span>
                            Markdown supported
                        </small>
                    </div>
                </div>

                <div class="alert alert-danger d-none" id="chat-error" role="alert">
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    <div class="error-message"></div>
                </div>
            </div>
        `;

        // Cache DOM elements
        this.messagesContainer = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.characterSelect = document.getElementById('character-select');
        this.messageTypeSelect = document.getElementById('message-type');
        this.recipientSelect = document.getElementById('recipient-select');
        this.sendButton = document.getElementById('send-button');
        this.connectionStatus = document.getElementById('connection-status');
    }

    /**
     * Load current user data
     */
    async loadUserData() {
        try {
            const response = await fetch('/api/profile/current-user/', {
                method: 'GET',
                credentials: 'include', // Include cookies for session auth
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load user data');
            }

            this.currentUser = await response.json();
            console.log('Current user loaded:', this.currentUser);
        } catch (error) {
            console.error('Failed to load user data:', error);
            // Continue without user data for now
        }
    }

    /**
     * Load available characters for this scene
     */
    async loadCharacters() {
        try {
            const response = await fetch(`/api/scenes/${this.sceneId}/`, {
                method: 'GET',
                credentials: 'include', // Include cookies for session auth
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load scene data');
            }

            const sceneData = await response.json();
            this.characters = sceneData.participants || [];

            console.log('Scene data loaded:', sceneData);
            console.log('Characters found:', this.characters);
            console.log('Current user:', this.currentUser);

            this.updateCharacterSelect();
        } catch (error) {
            console.error('Failed to load characters:', error);
            this.showError('Failed to load characters');
        }
    }

    /**
     * Update character select dropdown
     */
    updateCharacterSelect() {
        this.characterSelect.innerHTML = '<option value="">Select Character...</option>';

        // Add user's characters - note: currentUser has nested structure { user: {...} }
        const userId = this.currentUser && this.currentUser.user ? this.currentUser.user.id : null;
        const userCharacters = this.characters.filter(char =>
            userId && char.player_owner && char.player_owner.id === userId
        );

        console.log('Filtered user characters:', userCharacters);
        console.log('User ID comparison:', userId,
                    'vs character owners:', this.characters.map(c => c.player_owner ? c.player_owner.id : 'no owner'));

        userCharacters.forEach(character => {
            const option = document.createElement('option');
            option.value = character.id;
            option.textContent = character.name;
            option.dataset.npc = character.npc;
            this.characterSelect.appendChild(option);
        });

        // Auto-select first character if only one
        if (userCharacters.length === 1) {
            this.characterSelect.value = userCharacters[0].id;
            this.selectedCharacter = userCharacters[0];
        }

        // Enable/disable character select based on availability
        this.characterSelect.disabled = userCharacters.length === 0;

        // Update send button state
        this.updateSendButtonState();
    }

    /**
     * Load message history from API
     */
    async loadMessageHistory() {
        this.showLoading(true);

        try {
            const response = await fetch(`/api/scenes/${this.sceneId}/messages/?limit=50`, {
                method: 'GET',
                credentials: 'include', // Include cookies for session auth
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load message history');
            }

            const data = await response.json();
            this.messages = data.results || data; // Handle both paginated and non-paginated responses

            this.renderMessages();
        } catch (error) {
            console.error('Failed to load message history:', error);
            this.showError('Failed to load message history');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Setup WebSocket connection
     */
    setupWebSocket() {
        this.websocket = new SceneChatWebSocket(this.sceneId);

        this.websocket.setOnMessage((message) => {
            this.addMessage(message);
        });

        this.websocket.setOnRateLimitUpdate((status) => {
            this.updateRateLimitStatus(status);
        });

        this.websocket.setOnStatusChange((status) => {
            this.updateConnectionStatus(status);
            this.updateSendButtonState();
        });

        this.websocket.setOnError((error) => {
            this.showError(error);
        });

        this.websocket.connect();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => {
            this.sendMessage();
        });

        // Enter key to send (Shift+Enter for new line)
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Character count and send button state
        this.messageInput.addEventListener('input', () => {
            this.updateCharacterCount();
            this.updateSendButtonState();
        });

        // Message type change
        this.messageTypeSelect.addEventListener('change', () => {
            this.onMessageTypeChange();
        });

        // Character selection
        this.characterSelect.addEventListener('change', () => {
            this.onCharacterChange();
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.autoResizeTextarea();
        });
    }

    /**
     * Handle message type change
     */
    onMessageTypeChange() {
        const messageType = this.messageTypeSelect.value;
        this.messageType = messageType;

        // Show/hide character select for IC messages
        if (messageType === 'PUBLIC') {
            this.characterSelect.closest('.col-md-4').classList.remove('d-none');
            this.recipientSelect.closest('.col-md-4').classList.add('d-none');
        } else if (messageType === 'PRIVATE') {
            this.characterSelect.closest('.col-md-4').classList.remove('d-none');
            this.recipientSelect.closest('.col-md-4').classList.remove('d-none');
            this.loadRecipients();
        } else {
            this.characterSelect.closest('.col-md-4').classList.add('d-none');
            this.recipientSelect.closest('.col-md-4').classList.add('d-none');
        }

        this.updateSendButtonState();
    }

    /**
     * Handle character selection change
     */
    onCharacterChange() {
        const characterId = this.characterSelect.value;
        this.selectedCharacter = this.characters.find(c => c.id == characterId) || null;
        this.updateSendButtonState();
    }

    /**
     * Update send button state based on current conditions
     */
    updateSendButtonState() {
        let canSend = true;

        // Check if message input has content
        const hasContent = this.messageInput && this.messageInput.value.trim().length > 0;

        // Check character requirements based on message type
        if (this.messageType === 'PUBLIC' && !this.selectedCharacter) {
            canSend = false;
        }

        if (this.messageType === 'PRIVATE' && (!this.selectedCharacter || !this.recipientSelect.value)) {
            canSend = false;
        }

        // Check if WebSocket is connected
        const isConnected = this.websocket && this.websocket.getStatus() === 'connected';

        this.sendButton.disabled = !canSend || !hasContent || !isConnected;
    }

    /**
     * Load recipients for private messages
     */
    loadRecipients() {
        this.recipientSelect.innerHTML = '<option value="">Select Recipient...</option>';

        // Add all other users in the scene
        const userId = this.currentUser && this.currentUser.user ? this.currentUser.user.id : null;
        const otherUsers = new Set();
        this.characters.forEach(character => {
            if (character.player_owner &&
                (!userId || character.player_owner.id !== userId)) {
                otherUsers.add(JSON.stringify({
                    id: character.player_owner.id,
                    username: character.player_owner.username
                }));
            }
        });

        Array.from(otherUsers).forEach(userStr => {
            const user = JSON.parse(userStr);
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.username;
            this.recipientSelect.appendChild(option);
        });
    }

    /**
     * Send a message
     */
    async sendMessage() {
        const content = this.messageInput.value.trim();
        if (!content) {
            return;
        }

        // Validate message based on type
        if (this.messageType === 'PUBLIC' && !this.selectedCharacter) {
            this.showError('Please select a character for in-character messages');
            return;
        }

        if (this.messageType === 'PRIVATE' && !this.recipientSelect.value) {
            this.showError('Please select a recipient for private messages');
            return;
        }

        try {
            const messageData = {
                content: content,
                message_type: this.messageType,
                character: this.selectedCharacter ? this.selectedCharacter.id : null,
                recipients: this.messageType === 'PRIVATE' ? [this.recipientSelect.value] : []
            };

            await this.websocket.sendMessage(messageData);

            // Clear input on successful send
            this.messageInput.value = '';
            this.updateCharacterCount();
            this.autoResizeTextarea();

        } catch (error) {
            console.error('Failed to send message:', error);
            this.showError(error.message || 'Failed to send message');
        }
    }

    /**
     * Add a new message to the display
     */
    addMessage(message) {
        this.messages.push(message);

        // Keep only recent messages
        if (this.messages.length > this.options.maxMessageHistory) {
            this.messages = this.messages.slice(-this.options.maxMessageHistory);
        }

        const messageElement = this.createMessageElement(message);
        this.messagesContainer.appendChild(messageElement);

        // Auto-scroll to bottom
        if (this.options.autoScroll) {
            this.scrollToBottom();
        }

        // Show new message indicator if not scrolled to bottom
        this.showNewMessageIndicator();
    }

    /**
     * Render all messages
     */
    renderMessages() {
        // Clear existing messages (keep loading indicator)
        const loadingIndicator = this.messagesContainer.querySelector('.loading-indicator');
        this.messagesContainer.innerHTML = '';
        if (loadingIndicator) {
            this.messagesContainer.appendChild(loadingIndicator);
        }

        // Render each message
        this.messages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            this.messagesContainer.appendChild(messageElement);
        });

        // Scroll to bottom
        this.scrollToBottom();
    }

    /**
     * Create a message element
     */
    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message message-${message.message_type.toLowerCase()}`;
        messageDiv.dataset.messageId = message.id;

        // Message header
        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';

        let senderName = 'Unknown';
        if (message.message_type === 'PUBLIC' && message.character) {
            senderName = message.character.name;
        } else if (message.sender) {
            senderName = message.sender.display_name || message.sender.username;
        }

        const senderSpan = document.createElement('span');
        senderSpan.className = 'sender-name';
        senderSpan.textContent = senderName;
        headerDiv.appendChild(senderSpan);

        // Message type badge
        if (message.message_type !== 'PUBLIC') {
            const typeBadge = document.createElement('span');
            typeBadge.className = `badge bg-secondary ms-2 message-type-${message.message_type.toLowerCase()}`;
            typeBadge.textContent = message.message_type;
            headerDiv.appendChild(typeBadge);
        }

        // Timestamp
        if (this.options.showTimestamps && message.created_at) {
            const timeSpan = document.createElement('span');
            timeSpan.className = 'message-time text-muted ms-auto';
            timeSpan.textContent = this.formatTimestamp(message.created_at);
            headerDiv.appendChild(timeSpan);
        }

        messageDiv.appendChild(headerDiv);

        // Message content
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        if (this.options.markdownEnabled) {
            contentDiv.innerHTML = this.renderMarkdown(message.content);
        } else {
            contentDiv.textContent = message.content;
        }

        messageDiv.appendChild(contentDiv);

        // Private message recipients
        if (message.message_type === 'PRIVATE' && message.recipients && message.recipients.length > 0) {
            const recipientsDiv = document.createElement('div');
            recipientsDiv.className = 'message-recipients text-muted';
            recipientsDiv.innerHTML = `<small>To: ${message.recipients.map(r => r.username).join(', ')}</small>`;
            messageDiv.appendChild(recipientsDiv);
        }

        return messageDiv;
    }

    /**
     * Basic markdown rendering
     */
    renderMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    /**
     * Format timestamp
     */
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();

        if (date.toDateString() === now.toDateString()) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } else {
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(status) {
        const indicator = this.connectionStatus.querySelector('.status-indicator');
        const text = this.connectionStatus.querySelector('.status-text');

        indicator.className = `status-indicator ${status}`;

        switch (status) {
            case 'connected':
                text.textContent = 'Connected';
                break;
            case 'connecting':
            case 'reconnecting':
                text.textContent = 'Connecting...';
                break;
            case 'disconnected':
                text.textContent = 'Disconnected';
                break;
        }

        // Update send button state
        this.updateSendButtonState();
    }

    /**
     * Update character count and rate limit status
     */
    updateCharacterCount() {
        const count = this.messageInput.value.length;
        const charCountElement = document.getElementById('char-count');
        if (charCountElement) {
            charCountElement.textContent = `${count}/2000`;
            charCountElement.className = count > 1800 ? 'text-warning' : '';
        }

        // Update send button state based on rate limit
        this.updateSendButtonState();
    }

    /**
     * Update rate limit status display
     */
    updateRateLimitStatus(status) {
        this.rateLimitStatus = status;
        const rateLimitElement = document.getElementById('rate-limit-status');

        if (rateLimitElement) {
            if (status.remaining <= 0) {
                rateLimitElement.textContent = `Rate limited - try again in ${Math.ceil(status.retryAfter)}s | `;
                rateLimitElement.className = 'text-danger';
                this.rateLimitStatus.isLimited = true;
            } else if (status.remaining <= 2) {
                rateLimitElement.textContent = `${status.remaining} messages remaining | `;
                rateLimitElement.className = 'text-warning';
                this.rateLimitStatus.isLimited = false;
            } else {
                rateLimitElement.textContent = '';
                rateLimitElement.className = '';
                this.rateLimitStatus.isLimited = false;
            }
        }

        this.updateSendButtonState();
    }

    /**
     * Update send button state based on connection and rate limits
     */
    updateSendButtonState() {
        const isConnected = this.websocket && this.websocket.getStatus() === 'connected';
        const hasContent = this.messageInput && this.messageInput.value.trim().length > 0;
        const notRateLimited = !this.rateLimitStatus.isLimited;

        if (this.sendButton) {
            this.sendButton.disabled = !isConnected || !hasContent || !notRateLimited;
        }
    }

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    /**
     * Scroll to bottom of messages
     */
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    /**
     * Show new message indicator
     */
    showNewMessageIndicator() {
        const isScrolledToBottom = this.messagesContainer.scrollTop + this.messagesContainer.clientHeight >=
                                  this.messagesContainer.scrollHeight - 5;

        if (!isScrolledToBottom) {
            // Could add a "new messages" indicator here
            console.log('New message received while not at bottom');
        }
    }

    /**
     * Show loading indicator
     */
    showLoading(show) {
        const loadingIndicator = this.messagesContainer.querySelector('.loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.classList.toggle('d-none', !show);
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const errorAlert = document.getElementById('chat-error');
        if (errorAlert) {
            const errorMessage = errorAlert.querySelector('.error-message');
            errorMessage.textContent = message;
            errorAlert.classList.remove('d-none');

            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorAlert.classList.add('d-none');
            }, 5000);
        }
    }

    /**
     * Get CSRF token from page
     */
    getCSRFToken() {
        // Try to get from meta tag first
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            return metaToken.getAttribute('content');
        }

        // Try to get from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }

        // Try to get from form
        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfInput) {
            return csrfInput.value;
        }

        return null;
    }

    /**
     * Refresh character list (public method)
     */
    async refreshCharacters() {
        try {
            await this.loadCharacters();
            console.log('Character list refreshed');
        } catch (error) {
            console.error('Failed to refresh characters:', error);
        }
    }

    /**
     * Cleanup resources
     */
    destroy() {
        if (this.websocket) {
            this.websocket.disconnect();
        }
    }
}

// Export for use
window.SceneChatUI = SceneChatUI;
