// web_app.js - JavaScript for SMTP Web Client

let ws = null;
let attachments = [];
let selectedRecipient = null;
let selectedEmail = null;

// DOM Elements
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const statusMessage = document.getElementById('statusMessage');
const emailForm = document.getElementById('emailForm');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const refreshBtn = document.getElementById('refreshBtn');
const fileInput = document.getElementById('fileInput');
const attachmentCount = document.getElementById('attachmentCount');
const attachmentList = document.getElementById('attachmentList');
const recipientsList = document.getElementById('recipientsList');
const emailsList = document.getElementById('emailsList');
const emailContent = document.getElementById('emailContent');

// Initialize
window.addEventListener('load', () => {
    connectWebSocket();
    setupEventListeners();
});

// WebSocket Connection
function connectWebSocket() {
    ws = new WebSocket('ws://localhost:8787');

    ws.onopen = () => {
        console.log('Connected to WebSocket server');
        updateConnectionStatus(true);
        showStatus('Connected to SMTP server', 'success');
        loadInbox();
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showStatus('Connection error', 'error');
    };

    ws.onclose = () => {
        console.log('Disconnected from WebSocket server');
        updateConnectionStatus(false);
        showStatus('Disconnected from server', 'error');

        // Try to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
}

function updateConnectionStatus(connected) {
    if (connected) {
        statusIndicator.classList.add('connected');
        statusText.textContent = 'Connected';
        sendBtn.disabled = false;
    } else {
        statusIndicator.classList.remove('connected');
        statusText.textContent = 'Disconnected';
        sendBtn.disabled = true;
    }
}

function handleMessage(data) {
    switch (data.type) {
        case 'connected':
            console.log(data.message);
            break;

        case 'send_success':
            showStatus(data.message, 'success');
            clearForm();
            loadInbox();
            break;

        case 'recipients':
            displayRecipients(data.data);
            break;

        case 'emails':
            displayEmails(data.data, data.recipient);
            break;

        case 'email_content':
            displayEmailContent(data.content, data.is_binary);
            break;

        case 'inbox_updated':
            loadInbox();
            break;

        case 'error':
            showStatus(data.message, 'error');
            break;
    }
}

// Event Listeners
function setupEventListeners() {
    emailForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendEmail();
    });

    clearBtn.addEventListener('click', clearForm);
    refreshBtn.addEventListener('click', loadInbox);

    fileInput.addEventListener('change', handleFileSelect);
}

// File Handling
function handleFileSelect(e) {
    const files = Array.from(e.target.files);

    files.forEach(file => {
        const reader = new FileReader();
        reader.onload = (event) => {
            attachments.push({
                name: file.name,
                data: event.target.result
            });
            updateAttachmentDisplay();
        };
        reader.readAsDataURL(file);
    });

    // Clear file input
    fileInput.value = '';
}

function updateAttachmentDisplay() {
    if (attachments.length === 0) {
        attachmentCount.textContent = 'No attachments';
        attachmentList.innerHTML = '';
    } else {
        attachmentCount.textContent = `${attachments.length} file(s) attached`;
        attachmentList.innerHTML = attachments.map((att, index) => `
            <div class="attachment-item">
                <span>📎 ${att.name}</span>
                <button onclick="removeAttachment(${index})">×</button>
            </div>
        `).join('');
    }
}

function removeAttachment(index) {
    attachments.splice(index, 1);
    updateAttachmentDisplay();
}

// Send Email
function sendEmail() {
    const sender = document.getElementById('sender').value.trim();
    const recipientsText = document.getElementById('recipients').value.trim();
    const subject = document.getElementById('subject').value.trim();
    const body = document.getElementById('body').value.trim();

    if (!sender || !recipientsText) {
        showStatus('Sender and recipients are required', 'error');
        return;
    }

    const recipients = recipientsText.split(',').map(r => r.trim()).filter(r => r);

    if (recipients.length === 0) {
        showStatus('At least one recipient is required', 'error');
        return;
    }

    const emailData = {
        type: 'send_email',
        sender: sender,
        recipients: recipients,
        subject: subject,
        body: body,
        attachments: attachments
    };

    sendBtn.disabled = true;
    showStatus('Sending email...', '');

    ws.send(JSON.stringify(emailData));

    // Re-enable button after 2 seconds
    setTimeout(() => {
        sendBtn.disabled = false;
    }, 2000);
}

function clearForm() {
    document.getElementById('sender').value = '';
    document.getElementById('recipients').value = '';
    document.getElementById('subject').value = '';
    document.getElementById('body').value = '';
    attachments = [];
    updateAttachmentDisplay();
}

// Inbox Functions
function loadInbox() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'get_recipients' }));
    }
}

function displayRecipients(recipients) {
    if (recipients.length === 0) {
        recipientsList.innerHTML = '<div class="empty-state">No emails yet</div>';
        return;
    }

    recipientsList.innerHTML = recipients.map(recipient => `
        <div class="list-item ${selectedRecipient === recipient.name ? 'active' : ''}" 
             onclick="selectRecipient('${recipient.name}')">
            <div class="list-item-name">${recipient.name.replace(/_at_/g, '@').replace(/_/g, '.')}</div>
            <div class="list-item-count">${recipient.count} email(s)</div>
        </div>
    `).join('');
}

function selectRecipient(recipient) {
    selectedRecipient = recipient;
    selectedEmail = null;

    // Update UI
    document.querySelectorAll('#recipientsList .list-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.list-item').classList.add('active');

    // Load emails for this recipient
    ws.send(JSON.stringify({
        type: 'get_emails',
        recipient: recipient
    }));

    // Clear email content
    emailContent.innerHTML = '<div class="empty-state">Select an email to view</div>';
}

function displayEmails(emails, recipient) {
    if (emails.length === 0) {
        emailsList.innerHTML = '<div class="empty-state">No emails</div>';
        return;
    }

    emailsList.innerHTML = emails.map(email => {
        const icon = email.isAttachment ? '📎' : '📧';
        return `
            <div class="list-item ${selectedEmail === email.filename ? 'active' : ''}" 
                 onclick="selectEmail('${recipient}', '${email.filename}')">
                <div class="list-item-name">${icon} ${email.display}</div>
                ${email.isAttachment ? '<div class="list-item-attachment">Attachment</div>' : ''}
            </div>
        `;
    }).join('');
}

function selectEmail(recipient, filename) {
    selectedEmail = filename;

    // Update UI
    document.querySelectorAll('#emailsList .list-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.list-item').classList.add('active');

    // Load email content
    ws.send(JSON.stringify({
        type: 'get_email_content',
        recipient: recipient,
        filename: filename
    }));
}

function displayEmailContent(content, isBinary) {
    if (isBinary) {
        emailContent.innerHTML = `<div style="color: #667eea;">${content}</div>`;
    } else {
        emailContent.textContent = content;
    }
}

// Status Messages
function showStatus(message, type = '') {
    statusMessage.textContent = message;
    statusMessage.className = type;

    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            statusMessage.textContent = '';
            statusMessage.className = '';
        }, 5000);
    }

}
