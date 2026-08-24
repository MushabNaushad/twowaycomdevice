/**
 * Commlink Client Application Logic
 * =================================
 * Manages user authentication, manual node addressing, real-time message stream,
 * file attachment validation, multimedia rendering, and drag-and-drop.
 */

// Application State
const state = {
  token: localStorage.getItem('commlink_token') || '',
  user: null,
  activeTargetNode: 2,
  activeTargetName: 'Station Node 2',
  contacts: [],
  messages: [],
  selectedFile: null,
  eventSource: null
};

// Allowed Extensions by Category
const ALLOWED_EXTENSIONS = {
  image: ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'],
  pdf: ['.pdf'],
  audio: ['.wav', '.mp3', '.ogg', '.opus', '.aac', '.pcm'],
  text: ['.txt', '.json', '.csv', '.log']
};

const ALL_ALLOWED = [
  ...ALLOWED_EXTENSIONS.image,
  ...ALLOWED_EXTENSIONS.pdf,
  ...ALLOWED_EXTENSIONS.audio,
  ...ALLOWED_EXTENSIONS.text
];

// ─────────────────────────────────────────────────────────────────────────────
// INITIALIZATION
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  setupDragAndDrop();
  if (state.token) {
    checkAuth();
  } else {
    showAuthOverlay();
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// AUTHENTICATION
// ─────────────────────────────────────────────────────────────────────────────
function showAuthOverlay() {
  document.getElementById('auth-overlay').classList.remove('hidden');
  document.getElementById('main-dashboard').classList.add('hidden');
}

function hideAuthOverlay() {
  document.getElementById('auth-overlay').classList.add('hidden');
  document.getElementById('main-dashboard').classList.remove('hidden');
}

function switchAuthTab(tab) {
  const loginTab = document.getElementById('tab-login');
  const signupTab = document.getElementById('tab-signup');
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');

  if (tab === 'login') {
    loginTab.classList.add('active');
    signupTab.classList.remove('active');
    loginForm.classList.remove('hidden');
    signupForm.classList.add('hidden');
  } else {
    signupTab.classList.add('active');
    loginTab.classList.remove('active');
    signupForm.classList.remove('hidden');
    loginForm.classList.add('hidden');
  }
}

async function checkAuth() {
  try {
    const res = await fetch('/api/me', {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (res.ok) {
      const data = await res.json();
      state.user = data.user;
      initDashboard();
    } else {
      localStorage.removeItem('commlink_token');
      state.token = '';
      showAuthOverlay();
    }
  } catch (err) {
    console.error('Auth verification failed:', err);
    showAuthOverlay();
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errorBanner = document.getElementById('login-error');

  errorBanner.classList.add('hidden');

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok) {
      state.token = data.token;
      state.user = data.user;
      localStorage.setItem('commlink_token', data.token);
      initDashboard();
    } else {
      errorBanner.textContent = data.error || 'Authentication failed.';
      errorBanner.classList.remove('hidden');
    }
  } catch (err) {
    errorBanner.textContent = 'Server connection error.';
    errorBanner.classList.remove('hidden');
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const displayName = document.getElementById('signup-name').value.trim();
  const nodeAddress = parseInt(document.getElementById('signup-node').value, 10);
  const username = document.getElementById('signup-username').value.trim();
  const password = document.getElementById('signup-password').value;
  const errorBanner = document.getElementById('signup-error');

  errorBanner.classList.add('hidden');

  if (isNaN(nodeAddress) || nodeAddress < 1 || nodeAddress > 254) {
    errorBanner.textContent = 'Station Node Address must be between 1 and 254.';
    errorBanner.classList.remove('hidden');
    return;
  }

  try {
    const res = await fetch('/api/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, display_name: displayName, node_address: nodeAddress })
    });
    const data = await res.json();
    if (res.ok) {
      state.token = data.token;
      state.user = data.user;
      localStorage.setItem('commlink_token', data.token);
      initDashboard();
    } else {
      errorBanner.textContent = data.error || 'Registration failed.';
      errorBanner.classList.remove('hidden');
    }
  } catch (err) {
    errorBanner.textContent = 'Server connection error.';
    errorBanner.classList.remove('hidden');
  }
}

async function handleLogout() {
  try {
    await fetch('/api/logout', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
  } catch (err) {}

  if (state.eventSource) {
    state.eventSource.close();
    state.eventSource = null;
  }

  localStorage.removeItem('commlink_token');
  state.token = '';
  state.user = null;
  showAuthOverlay();
}

// ─────────────────────────────────────────────────────────────────────────────
// DASHBOARD INITIALIZATION
// ─────────────────────────────────────────────────────────────────────────────
function initDashboard() {
  hideAuthOverlay();

  // Populate user badge
  document.getElementById('current-node-addr').textContent = `NODE ${state.user.node_address}`;
  document.getElementById('user-display-name').textContent = state.user.display_name;
  document.getElementById('user-avatar').textContent = getInitials(state.user.display_name);

  // Auto-select initial target node (e.g. Node 2 if we are Node 1, or Node 1 if we are Node 2)
  state.activeTargetNode = (state.user.node_address === 1) ? 2 : 1;
  state.activeTargetName = `Station Node ${state.activeTargetNode}`;

  loadContacts();
  loadMessages();
  connectSSE();
}

function getInitials(name) {
  const parts = name.split(' ').filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (name.substring(0, 2) || 'OP').toUpperCase();
}

// ─────────────────────────────────────────────────────────────────────────────
// REAL-TIME SERVER-SENT EVENTS (SSE)
// ─────────────────────────────────────────────────────────────────────────────
function connectSSE() {
  if (state.eventSource) {
    state.eventSource.close();
  }

  state.eventSource = new EventSource('/api/events');

  state.eventSource.addEventListener('status', (e) => {
    try {
      const data = JSON.parse(e.data);
      const tag = document.getElementById('rf-status-text');
      if (data.status === 'ONLINE') {
        tag.textContent = 'RF LINK ACTIVE';
      } else {
        tag.textContent = 'RF STANDBY';
      }
    } catch (err) {}
  });

  state.eventSource.addEventListener('new_message', (e) => {
    try {
      const msg = JSON.parse(e.data);
      
      // Inbound check: Only display incoming messages intended for our station (or broadcasts from others)
      const isForMe = (msg.dst_node === state.user.node_address) || 
                      (msg.dst_node === 0 && msg.src_node !== state.user.node_address);

      if (!isForMe) return;

      // Check if message belongs to the currently active conversation tab
      const isForActiveView = 
        (state.activeTargetNode === 0 && msg.dst_node === 0) ||
        (msg.src_node === state.activeTargetNode);

      if (isForActiveView) {
        state.messages.push(msg);
        renderSingleMessage(msg);
        scrollToBottom();
      }
    } catch (err) {
      console.error('Error parsing live message:', err);
    }
  });

  state.eventSource.onerror = () => {
    console.log('SSE connection lost, reconnecting...');
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// CONTACTS & STATION SELECTION
// ─────────────────────────────────────────────────────────────────────────────
async function loadContacts() {
  try {
    const res = await fetch('/api/contacts', {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (res.ok) {
      const data = await res.json();
      state.contacts = data.contacts || [];
      renderStationsList();
    }
  } catch (err) {
    console.error('Failed to load contacts:', err);
  }
}

function renderStationsList() {
  const container = document.getElementById('stations-list');
  container.innerHTML = '';

  state.contacts.forEach(c => {
    const btn = document.createElement('button');
    const isActive = (c.node_address === state.activeTargetNode);
    btn.className = `station-card ${isActive ? 'active' : ''}`;
    btn.id = `contact-btn-${c.node_address}`;
    btn.onclick = () => selectContact(c.node_address, c.display_name || `Station Node ${c.node_address}`);

    btn.innerHTML = `
      <div class="station-avatar">N${c.node_address}</div>
      <div class="station-details">
        <div class="station-top">
          <span class="station-name">${escapeHtml(c.display_name || `Station ${c.node_address}`)}</span>
          <span class="node-tag">ADDR ${c.node_address}</span>
        </div>
        <span class="station-sub">${escapeHtml(c.username || `Node ${c.node_address}`)}</span>
      </div>
    `;
    container.appendChild(btn);
  });

  // Update active broadcast button state
  const bcastBtn = document.getElementById('contact-btn-0');
  if (bcastBtn) {
    if (state.activeTargetNode === 0) bcastBtn.classList.add('active');
    else bcastBtn.classList.remove('active');
  }
}

function selectContact(nodeAddr, name) {
  state.activeTargetNode = nodeAddr;
  state.activeTargetName = name;

  document.querySelectorAll('.station-card').forEach(c => c.classList.remove('active'));
  const activeBtn = document.getElementById(`contact-btn-${nodeAddr}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update Chat Header
  const avatarText = (nodeAddr === 0) ? '📢' : `N${nodeAddr}`;
  document.getElementById('active-target-avatar').textContent = avatarText;
  document.getElementById('active-target-name').textContent = name;
  document.getElementById('active-target-node').textContent = (nodeAddr === 0) ? 'Target: Broadcast (0)' : `Target: Node ${nodeAddr}`;

  loadMessages();
}

function openAddStationModal() {
  document.getElementById('add-station-modal').classList.remove('hidden');
}

function closeAddStationModal() {
  document.getElementById('add-station-modal').classList.add('hidden');
}

function confirmAddStation() {
  const nodeIdInput = document.getElementById('custom-node-id');
  const nodeNameInput = document.getElementById('custom-node-name');
  const nodeAddr = parseInt(nodeIdInput.value, 10);
  const nodeName = nodeNameInput.value.trim() || `Radio Node ${nodeAddr}`;

  if (isNaN(nodeAddr) || nodeAddr < 1 || nodeAddr > 254) {
    alert('Node Address must be between 1 and 254.');
    return;
  }

  // Check if exists
  if (!state.contacts.find(c => c.node_address === nodeAddr)) {
    state.contacts.push({
      node_address: nodeAddr,
      display_name: nodeName,
      username: `node_${nodeAddr}`
    });
    renderStationsList();
  }

  selectContact(nodeAddr, nodeName);
  closeAddStationModal();
}

// ─────────────────────────────────────────────────────────────────────────────
// MESSAGES STREAM & RENDERING
// ─────────────────────────────────────────────────────────────────────────────
async function loadMessages() {
  try {
    const res = await fetch(`/api/messages?dst=${state.activeTargetNode}`, {
      headers: { 'Authorization': `Bearer ${state.token}` }
    });
    if (res.ok) {
      const data = await res.json();
      state.messages = data.messages || [];
      renderMessagesStream();
    }
  } catch (err) {
    console.error('Failed to load messages:', err);
  }
}

function refreshMessages() {
  loadMessages();
}

function renderMessagesStream() {
  const stream = document.getElementById('messages-stream');
  stream.innerHTML = '';

  if (state.messages.length === 0) {
    stream.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📡</div>
        <h3>No transmissions yet</h3>
        <p>Type a message or drop a file to transmit to ${escapeHtml(state.activeTargetName)}.</p>
      </div>
    `;
    return;
  }

  state.messages.forEach(msg => {
    renderSingleMessage(msg, stream);
  });

  scrollToBottom();
}

function renderSingleMessage(msg, targetStream) {
  const stream = targetStream || document.getElementById('messages-stream');
  
  // Remove empty state if present
  const empty = stream.querySelector('.empty-state');
  if (empty) empty.remove();

  const isOutgoing = msg.is_outgoing;
  const row = document.createElement('div');
  row.className = `message-row ${isOutgoing ? 'outgoing' : 'incoming'}`;

  const timeStr = formatTimestamp(msg.timestamp);
  const senderLabel = isOutgoing ? `You (Node ${msg.src_node})` : `Node ${msg.src_node}`;

  let mediaHtml = '';
  if (msg.media_type === 2) {
    // Image
    mediaHtml = `
      <div class="media-image-card" onclick="openLightbox('/api/media/${msg.id}', '${escapeHtml(msg.filename)}')">
        <img src="/api/media/${msg.id}" alt="${escapeHtml(msg.filename)}" loading="lazy">
      </div>
    `;
  } else if (msg.media_type === 4) {
    // PDF / Document
    const szStr = formatFileSize(msg.file_size);
    mediaHtml = `
      <div class="media-doc-card">
        <div class="doc-icon">📄</div>
        <div class="doc-info">
          <div class="doc-name">${escapeHtml(msg.filename)}</div>
          <div class="doc-size">${szStr} • PDF Document</div>
        </div>
        <a href="/api/media/${msg.id}" target="_blank" class="doc-download-btn" download="${escapeHtml(msg.filename)}">
          Download
        </a>
      </div>
    `;
  } else if (msg.media_type === 3) {
    // Audio
    mediaHtml = `
      <div class="media-audio-card">
        <div class="audio-header">
          <span>🎵 ${escapeHtml(msg.filename)}</span>
        </div>
        <audio controls src="/api/media/${msg.id}"></audio>
      </div>
    `;
  }

  const textHtml = msg.content ? `<div class="msg-text">${escapeHtml(msg.content)}</div>` : '';

  row.innerHTML = `
    <div class="msg-header">
      <span class="msg-sender-tag">${senderLabel}</span>
      <span class="msg-time">${timeStr}</span>
    </div>
    <div class="msg-bubble">
      ${mediaHtml}
      ${textHtml}
    </div>
  `;

  stream.appendChild(row);
}

function scrollToBottom() {
  const stream = document.getElementById('messages-stream');
  stream.scrollTop = stream.scrollHeight;
}

// ─────────────────────────────────────────────────────────────────────────────
// FILE ATTACHMENT & VALIDATION
// ─────────────────────────────────────────────────────────────────────────────
function triggerFileInput() {
  document.getElementById('file-input').click();
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (!file) return;
  validateAndAttachFile(file);
}

function validateAndAttachFile(file) {
  const errorBanner = document.getElementById('composer-error');
  errorBanner.classList.add('hidden');

  const ext = getFileExtension(file.name).toLowerCase();

  // 1. Strict File Type Validation
  if (!ALL_ALLOWED.includes(ext)) {
    errorBanner.textContent = `Unsupported file type "${ext}". Commlink accepts Images (.png, .jpg), PDFs (.pdf), Audio (.wav, .mp3), and Text (.txt).`;
    errorBanner.classList.remove('hidden');
    clearAttachment();
    return;
  }

  // 2. Maximum Size Limit (50 MB)
  if (file.size > 50 * 1024 * 1024) {
    errorBanner.textContent = `File exceeds maximum allowable radio transfer limit (50 MB).`;
    errorBanner.classList.remove('hidden');
    clearAttachment();
    return;
  }

  state.selectedFile = file;

  // Update attachment preview chip
  const previewBar = document.getElementById('attachment-preview-bar');
  const nameLabel = document.getElementById('attachment-name');
  const sizeLabel = document.getElementById('attachment-size');
  const iconSpan = document.getElementById('attachment-icon');
  const textInput = document.getElementById('message-input');

  nameLabel.textContent = file.name;
  sizeLabel.textContent = formatFileSize(file.size);

  if (ALLOWED_EXTENSIONS.image.includes(ext)) iconSpan.textContent = '📷';
  else if (ALLOWED_EXTENSIONS.pdf.includes(ext)) iconSpan.textContent = '📄';
  else if (ALLOWED_EXTENSIONS.audio.includes(ext)) iconSpan.textContent = '🎵';
  else iconSpan.textContent = '📁';

  previewBar.classList.remove('hidden');
  textInput.placeholder = `Attached: ${file.name} (Optional message — press Enter or Send to transmit)`;
  textInput.focus();
}

function clearAttachment() {
  state.selectedFile = null;
  document.getElementById('file-input').value = '';
  document.getElementById('attachment-preview-bar').classList.add('hidden');
  const textInput = document.getElementById('message-input');
  if (textInput) textInput.placeholder = 'Type a message to transmit over radio...';
}

function getFileExtension(fname) {
  const i = fname.lastIndexOf('.');
  return i !== -1 ? fname.substring(i) : '';
}

// ─────────────────────────────────────────────────────────────────────────────
// MESSAGE SENDING
// ─────────────────────────────────────────────────────────────────────────────
async function handleSendMessage(e) {
  if (e) e.preventDefault();

  const textInput = document.getElementById('message-input');
  const text = textInput.value.trim();
  const errorBanner = document.getElementById('composer-error');
  errorBanner.classList.add('hidden');

  // Allow sending if there is text OR an attachment!
  if (!text && !state.selectedFile) return;

  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  try {
    let res;
    if (state.selectedFile) {
      // Multipart Form Data with File
      const formData = new FormData();
      formData.append('dst_node', state.activeTargetNode.toString());
      formData.append('text', text);
      formData.append('file', state.selectedFile);

      res = await fetch('/api/send', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${state.token}` },
        body: formData
      });
    } else {
      // Plain JSON text message
      res = await fetch('/api/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${state.token}`
        },
        body: JSON.stringify({
          dst_node: state.activeTargetNode,
          text: text
        })
      });
    }

    const data = await res.json();
    if (res.ok && data.data) {
      textInput.value = '';
      clearAttachment();
      
      // Render outgoing message immediately
      state.messages.push(data.data);
      renderSingleMessage(data.data);
      scrollToBottom();
    } else {
      errorBanner.textContent = data.error || 'Failed to transmit message.';
      errorBanner.classList.remove('hidden');
    }
  } catch (err) {
    errorBanner.textContent = 'Network communication error.';
    errorBanner.classList.remove('hidden');
  } finally {
    sendBtn.disabled = false;
  }
}

async function clearActiveChat() {
  try {
    const res = await fetch('/api/chat/clear', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${state.token}`
      },
      body: JSON.stringify({ dst_node: state.activeTargetNode })
    });
    if (res.ok) {
      state.messages = [];
      renderMessagesStream();
    }
  } catch (err) {
    console.error('Failed to clear chat channel:', err);
  }
}

function handleTextKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// DRAG AND DROP
// ─────────────────────────────────────────────────────────────────────────────
function setupDragAndDrop() {
  const overlay = document.getElementById('dropzone-overlay');
  const arena = document.querySelector('.chat-container');

  if (!arena) return;

  let dragCounter = 0;

  arena.addEventListener('dragenter', (e) => {
    e.preventDefault();
    dragCounter++;
    overlay.classList.remove('hidden');
  });

  arena.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dragCounter--;
    if (dragCounter <= 0) {
      overlay.classList.add('hidden');
      dragCounter = 0;
    }
  });

  arena.addEventListener('dragover', (e) => {
    e.preventDefault();
  });

  arena.addEventListener('drop', (e) => {
    e.preventDefault();
    dragCounter = 0;
    overlay.classList.add('hidden');

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndAttachFile(e.dataTransfer.files[0]);
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// LIGHTBOX MODAL
// ─────────────────────────────────────────────────────────────────────────────
function openLightbox(src, caption) {
  const modal = document.getElementById('lightbox-modal');
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox-caption').textContent = caption;
  modal.classList.remove('hidden');
}

function closeLightbox() {
  document.getElementById('lightbox-modal').classList.add('hidden');
}

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function formatTimestamp(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
}
