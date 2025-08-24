/**
 * WebSocket Chat Management
 * Handles real-time chat connections for scene chat functionality.
 *
 * Features:
 * - Automatic connection management with reconnection
 * - Message sending and receiving
 * - Connection status monitoring
 * - Error handling and user feedback
 * - Rate limiting compliance
 * - CSRF token handling for security
 */

class SceneChatWebSocket {
    constructor(sceneId, options = {}) {
        this.sceneId = sceneId;
        this.options = {
            maxReconnectAttempts: 5,
            reconnectInterval: 1000, // Start with 1 second
            maxReconnectInterval: 30000, // Max 30 seconds
            heartbeatInterval: 30000, // 30 seconds
            messageRateLimit: 10, // 10 messages per minute
            rateLimitWindow: 60000, // 1 minute window
            ...options
        };

        // Connection state
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;
        this.heartbeatTimer = null;

        // Rate limiting
        this.messageTimes = [];

        // Event callbacks
        this.onMessage = null;
        this.onStatusChange = null;
        this.onError = null;

        // Get WebSocket URL
        this.websocketUrl = this.getWebSocketUrl();

        // Bind methods to preserve context
        this.handleOpen = this.handleOpen.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.handleClose = this.handleClose.bind(this);
        this.handleError = this.handleError.bind(this);
    }

    /**
     * Get WebSocket URL based on current protocol and host
     */
    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/scenes/${this.sceneId}/chat/`;
    }

    /**
     * Connect to WebSocket
     */
    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        try {
            console.log(`Connecting to WebSocket: ${this.websocketUrl}`);
            this.socket = new WebSocket(this.websocketUrl);

            this.socket.addEventListener('open', this.handleOpen);
            this.socket.addEventListener('message', this.handleMessage);
            this.socket.addEventListener('close', this.handleClose);
            this.socket.addEventListener('error', this.handleError);

        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.notifyError('Failed to create WebSocket connection');
            this.scheduleReconnect();
        }
    }

    /**
     * Handle WebSocket open event
     */
    handleOpen(event) {
        console.log('WebSocket connected successfully');
        this.isConnected = true;
        this.reconnectAttempts = 0;

        this.notifyStatusChange('connected');
        this.startHeartbeat();
    }

    /**
     * Handle incoming WebSocket messages
     */
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);

            switch (data.type) {
                case 'chat_message':
                    if (this.onMessage) {
                        this.onMessage(data.message);
                    }
                    break;

                case 'error':
                    console.error('WebSocket error:', data.error);
                    this.notifyError(data.error);
                    break;

                case 'heartbeat_response':
                    // Heartbeat acknowledged
                    break;

                default:
                    console.warn('Unknown message type:', data.type);
            }

        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    /**
     * Handle WebSocket close event
     */
    handleClose(event) {
        console.log('WebSocket closed:', event.code, event.reason);
        this.isConnected = false;
        this.stopHeartbeat();

        this.notifyStatusChange('disconnected');

        // Attempt reconnection unless explicitly closed
        if (event.code !== 1000) { // 1000 = normal closure
            this.scheduleReconnect();
        }
    }

    /**
     * Handle WebSocket error event
     */
    handleError(event) {
        console.error('WebSocket error:', event);
        this.notifyError('WebSocket connection error');
    }

    /**
     * Send a chat message
     */
    async sendMessage(messageData) {
        if (!this.isConnected) {
            throw new Error('WebSocket not connected');
        }

        // Check rate limit
        if (!this.checkRateLimit()) {
            throw new Error('Rate limit exceeded. Please slow down.');
        }

        // Get CSRF token
        const csrfToken = this.getCSRFToken();
        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }

        // Prepare message with CSRF token
        const message = {
            type: 'chat_message',
            message: {
                ...messageData,
                csrfmiddlewaretoken: csrfToken
            }
        };

        try {
            this.socket.send(JSON.stringify(message));
            this.recordMessageTime();
        } catch (error) {
            console.error('Failed to send message:', error);
            throw new Error('Failed to send message');
        }
    }

    /**
     * Check if we're within rate limits
     */
    checkRateLimit() {
        const now = Date.now();
        const windowStart = now - this.options.rateLimitWindow;

        // Remove old message times
        this.messageTimes = this.messageTimes.filter(time => time > windowStart);

        // Check if we're under the limit
        return this.messageTimes.length < this.options.messageRateLimit;
    }

    /**
     * Record the time of a sent message
     */
    recordMessageTime() {
        this.messageTimes.push(Date.now());
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
     * Start heartbeat to keep connection alive
     */
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                try {
                    this.socket.send(JSON.stringify({ type: 'heartbeat' }));
                } catch (error) {
                    console.error('Failed to send heartbeat:', error);
                }
            }
        }, this.options.heartbeatInterval);
    }

    /**
     * Stop heartbeat timer
     */
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }

    /**
     * Schedule a reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            this.notifyError('Connection lost. Please refresh the page to reconnect.');
            return;
        }

        const delay = Math.min(
            this.options.reconnectInterval * Math.pow(2, this.reconnectAttempts),
            this.options.maxReconnectInterval
        );

        console.log(`Scheduling reconnection attempt ${this.reconnectAttempts + 1} in ${delay}ms`);

        this.reconnectTimer = setTimeout(() => {
            this.reconnectAttempts++;
            this.notifyStatusChange('reconnecting');
            this.connect();
        }, delay);
    }

    /**
     * Manually disconnect WebSocket
     */
    disconnect() {
        console.log('Manually disconnecting WebSocket');

        this.stopHeartbeat();

        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        if (this.socket) {
            this.socket.close(1000, 'Manual disconnect');
            this.socket = null;
        }

        this.isConnected = false;
        this.notifyStatusChange('disconnected');
    }

    /**
     * Notify status change callback
     */
    notifyStatusChange(status) {
        if (this.onStatusChange) {
            this.onStatusChange(status);
        }
    }

    /**
     * Notify error callback
     */
    notifyError(error) {
        if (this.onError) {
            this.onError(error);
        }
    }

    /**
     * Get current connection status
     */
    getStatus() {
        if (this.isConnected) {
            return 'connected';
        } else if (this.reconnectTimer) {
            return 'reconnecting';
        } else {
            return 'disconnected';
        }
    }

    /**
     * Set message callback
     */
    setOnMessage(callback) {
        this.onMessage = callback;
    }

    /**
     * Set status change callback
     */
    setOnStatusChange(callback) {
        this.onStatusChange = callback;
    }

    /**
     * Set error callback
     */
    setOnError(callback) {
        this.onError = callback;
    }
}

// Export for use in other modules
window.SceneChatWebSocket = SceneChatWebSocket;
