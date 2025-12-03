// Configuration
const API_URL = 'http://localhost:8001';
const WS_URL = 'ws://localhost:8001';

// App State
const state = {
    currentUser: null,
    currentRoom: null,
    rooms: [],
    messages: {},
    ws: null
};

// DOM Elements
const landingScreen = document.getElementById('landing-screen');
const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const getStartedBtn = document.getElementById('get-started-btn');
const usernameInput = document.getElementById('username-input');
const loginBtn = document.getElementById('login-btn');
const logoutBtn = document.getElementById('logout-btn');
const currentUserSpan = document.getElementById('current-user');
const roomsList = document.getElementById('rooms-list');
const roomTitle = document.getElementById('room-title');
const roomUsers = document.getElementById('room-users');
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const createRoomBtn = document.getElementById('create-room-btn');
const createFirstRoomBtn = document.querySelector('.create-first-room-btn');
const createRoomModal = document.getElementById('create-room-modal');
const closeModalBtn = document.querySelector('.close-modal-btn');
const cancelBtn = document.querySelector('.cancel-btn');
const confirmCreateRoomBtn = document.getElementById('confirm-create-room-btn');
const roomNameInput = document.getElementById('room-name-input');
const roomDescriptionInput = document.getElementById('room-description-input');
const deleteRoomBtn = document.getElementById('delete-room-btn');
const emptyRooms = document.getElementById('empty-rooms');

// API Helper Functions
async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (body) options.body = JSON.stringify(body);

    const response = await fetch(`${API_URL}${endpoint}`, options);
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return response.json();
}

function connectWebSocket() {
    if (!state.currentUser) return;

    state.ws = new WebSocket(`${WS_URL}/ws/${state.currentUser}`);

    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'message' && data.room_id === state.currentRoom) {
            handleIncomingMessage(data.message);
        }
    };

    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    state.ws.onclose = () => {
        console.log('WebSocket closed');
    };
}

function handleIncomingMessage(message) {
    if (!state.messages[message.room_id]) {
        state.messages[message.room_id] = [];
    }
    state.messages[message.room_id].push(message);
    if (message.room_id === state.currentRoom) {
        renderMessages();
    }
}

// Initialize
async function init() {
    // Load rooms from API
    try {
        state.rooms = await apiRequest('/rooms');
        state.rooms.forEach(room => {
            state.messages[room.id] = [];
        });
        renderRooms();
    } catch (error) {
        console.error('Failed to load rooms:', error);
    }

    // Event Listeners
    getStartedBtn.addEventListener('click', () => {
        landingScreen.classList.remove('active');
        loginScreen.classList.add('active');
    });

    loginBtn.addEventListener('click', handleLogin);
    logoutBtn.addEventListener('click', handleLogout);
    sendBtn.addEventListener('click', sendMessage);
    createRoomBtn.addEventListener('click', openCreateRoomModal);
    createFirstRoomBtn.addEventListener('click', openCreateRoomModal);
    closeModalBtn.addEventListener('click', closeCreateRoomModal);
    cancelBtn.addEventListener('click', closeCreateRoomModal);
    confirmCreateRoomBtn.addEventListener('click', handleCreateRoom);
    deleteRoomBtn.addEventListener('click', handleDeleteRoom);

    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    usernameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleLogin();
    });
    roomNameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleCreateRoom();
    });
}

function handleLogin() {
    const username = usernameInput.value.trim();
    if (!username) {
        alert('Please enter a username');
        return;
    }

    state.currentUser = username;
    currentUserSpan.textContent = username;

    // Set user initial in avatar
    const userInitial = document.getElementById('user-initial');
    if (userInitial) {
        userInitial.textContent = username.charAt(0).toUpperCase();
    }

    loginScreen.classList.remove('active');
    chatScreen.classList.add('active');
    usernameInput.value = '';

    // Connect WebSocket
    connectWebSocket();
}

async function handleLogout() {
    if (state.currentRoom) {
        await leaveRoom(state.currentRoom);
    }

    // Close WebSocket
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }

    state.currentUser = null;
    state.currentRoom = null;
    chatScreen.classList.remove('active');
    loginScreen.classList.add('active');
}

function renderRooms() {
    if (state.rooms.length === 0) {
        roomsList.innerHTML = '';
        emptyRooms.classList.add('active');
        return;
    }

    emptyRooms.classList.remove('active');
    roomsList.innerHTML = state.rooms.map(room => `
        <div class="room-item" data-room-id="${room.id}">
            <h3>${room.name}</h3>
            <p>${room.description}</p>
        </div>
    `).join('');

    document.querySelectorAll('.room-item').forEach(item => {
        item.addEventListener('click', () => {
            const roomId = parseInt(item.dataset.roomId);
            joinRoom(roomId);
        });
    });
}

// Modal functions
function openCreateRoomModal() {
    createRoomModal.classList.add('active');
    roomNameInput.value = '';
    roomDescriptionInput.value = '';
    roomNameInput.focus();
}

function closeCreateRoomModal() {
    createRoomModal.classList.remove('active');
}

async function handleCreateRoom() {
    const name = roomNameInput.value.trim();
    const description = roomDescriptionInput.value.trim();

    if (!name) {
        alert('Please enter a room name');
        return;
    }

    try {
        const result = await apiRequest('/rooms/create', 'POST', { name, description });
        state.rooms.push(result.room);
        state.messages[result.room.id] = [];
        renderRooms();
        closeCreateRoomModal();
    } catch (error) {
        console.error('Failed to create room:', error);
        alert('Failed to create room');
    }
}

async function handleDeleteRoom() {
    if (!state.currentRoom) return;

    const room = state.rooms.find(r => r.id === state.currentRoom);
    if (!room) return;

    if (!confirm(`Are you sure you want to delete "${room.name}"?`)) {
        return;
    }

    try {
        await apiRequest(`/rooms/${state.currentRoom}`, 'DELETE');

        // Remove from state
        state.rooms = state.rooms.filter(r => r.id !== state.currentRoom);
        delete state.messages[state.currentRoom];

        // Clear current room
        state.currentRoom = null;
        roomTitle.textContent = 'Select a room';
        roomUsers.textContent = '';
        messagesDiv.innerHTML = '';
        deleteRoomBtn.style.display = 'none';

        renderRooms();
    } catch (error) {
        console.error('Failed to delete room:', error);
        alert('Failed to delete room');
    }
}

async function joinRoom(roomId) {
    const room = state.rooms.find(r => r.id === roomId);
    if (!room) return;

    // Leave previous room
    if (state.currentRoom) {
        await leaveRoom(state.currentRoom);
    }

    // Join new room via API
    try {
        await apiRequest('/rooms/join', 'POST', {
            username: state.currentUser,
            room_id: roomId
        });

        state.currentRoom = roomId;

        // Load existing messages
        const roomMessages = await apiRequest(`/rooms/${roomId}/messages`);
        state.messages[roomId] = roomMessages;

        // Update UI
        document.querySelectorAll('.room-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-room-id="${roomId}"]`).classList.add('active');

        roomTitle.textContent = room.name;
        updateRoomUsers();
        renderMessages();
        deleteRoomBtn.style.display = 'flex';
    } catch (error) {
        console.error('Failed to join room:', error);
        alert('Failed to join room');
    }
}

async function leaveRoom(roomId) {
    try {
        await apiRequest('/rooms/leave', 'POST', {
            username: state.currentUser,
            room_id: roomId
        });
    } catch (error) {
        console.error('Failed to leave room:', error);
    }
}

function updateRoomUsers() {
    const room = state.rooms.find(r => r.id === state.currentRoom);
    if (room) {
        roomUsers.textContent = `👥 ${room.users.length} user${room.users.length !== 1 ? 's' : ''}: ${room.users.join(', ')}`;
    }
}

async function sendMessage() {
    if (!state.currentRoom) {
        alert('Please select a room first');
        return;
    }

    const content = messageInput.value.trim();
    if (!content) return;

    messageInput.value = '';

    try {
        await apiRequest('/messages/send', 'POST', {
            username: state.currentUser,
            room_id: state.currentRoom,
            content: content
        });
    } catch (error) {
        console.error('Failed to send message:', error);
        alert('Failed to send message');
    }
}

function renderMessages() {
    if (!state.currentRoom) return;

    const messages = state.messages[state.currentRoom];
    messagesDiv.innerHTML = messages.map(msg => {
        const isOwn = msg.author === state.currentUser;
        const isAI = msg.message_type === 'ai';
        const classes = ['message'];
        if (isAI) classes.push('ai');
        if (isOwn) classes.push('own');

        return `
            <div class="${classes.join(' ')}">
                <div class="message-header">
                    <span class="message-author ${isAI ? 'ai' : ''}">${msg.author}</span>
                    <span class="message-time">${formatTime(msg.timestamp)}</span>
                </div>
                <div class="message-content">${escapeHtml(msg.content)}</div>
            </div>
        `;
    }).join('');

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Start the app
init();
