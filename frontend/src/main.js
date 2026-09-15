import { marked } from 'marked';

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
});

// App State
const state = {
  currentModel: 'models/gemini-3.8-flash',
  modelLabel: 'Flash',
  modelBadge: '3.8 Flash',
  messages: [], // Array of { role: 'user' | 'model', content: string }
  currentInteractionId: null, // Track interaction session for multi-turn
  isGenerating: false,
  isRecording: false,
  recognition: null,
};

// DOM Elements
const welcomeScreen = document.getElementById('welcome-screen');
const chatHistory = document.getElementById('chat-history');
const messagesContainer = document.getElementById('messages-container');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const recordingPulse = document.getElementById('recording-pulse');
const modelDropdownBtn = document.getElementById('model-dropdown-btn');
const modelSelectorWrapper = document.getElementById('model-selector-wrapper');
const modelMenu = document.getElementById('model-menu');
const selectedModelLabel = document.getElementById('selected-model-label');
const headerModelBadge = document.getElementById('header-model-badge');
const newChatBtn = document.getElementById('new-chat-btn');
const addBtn = document.getElementById('add-btn');
const plusMenu = document.getElementById('plus-menu');
const menuClearChat = document.getElementById('menu-clear-chat');
const menuSystemPrompt = document.getElementById('menu-system-prompt');
const statusIndicator = document.getElementById('status-indicator');
const suggestionChips = document.querySelectorAll('.chip');

// Initialize
function init() {
  setupEventListeners();
  setupSpeechRecognition();
  autoResizeTextarea();
}

// Event Listeners
function setupEventListeners() {
  // Input changes
  chatInput.addEventListener('input', () => {
    autoResizeTextarea();
    toggleSendButton();
  });

  // Enter to send (Shift+Enter for newline)
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!state.isGenerating && chatInput.value.trim().length > 0) {
        sendMessage(chatInput.value.trim());
      }
    }
  });

  // Send button
  sendBtn.addEventListener('click', () => {
    const text = chatInput.value.trim();
    if (!state.isGenerating && text.length > 0) {
      sendMessage(text);
    }
  });

  // Model Dropdown toggle
  modelDropdownBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = !modelMenu.classList.contains('hidden');
    closeAllMenus();
    if (!isOpen) {
      modelMenu.classList.remove('hidden');
      modelSelectorWrapper.classList.add('open');
    }
  });

  // Model Option Select
  document.querySelectorAll('.model-option').forEach((option) => {
    option.addEventListener('click', () => {
      const modelId = option.dataset.model;
      const badge = option.dataset.badge;
      selectModel(modelId, badge);
      closeAllMenus();
    });
  });

  // Plus Menu toggle
  addBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = !plusMenu.classList.contains('hidden');
    closeAllMenus();
    if (!isOpen) {
      plusMenu.classList.remove('hidden');
    }
  });

  // Menu items
  menuClearChat.addEventListener('click', () => {
    resetChat();
    closeAllMenus();
  });

  menuSystemPrompt.addEventListener('click', () => {
    alert(`현재 모델: ${state.currentModel}\n상태: 정상 작동 중 (API Key 연결됨)`);
    closeAllMenus();
  });

  // Global click to close menus
  document.addEventListener('click', () => {
    closeAllMenus();
  });

  // New Chat
  newChatBtn.addEventListener('click', resetChat);

  // Suggestion Chips
  suggestionChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      const prompt = chip.dataset.prompt;
      if (prompt && !state.isGenerating) {
        sendMessage(prompt);
      }
    });
  });

  // Mic Button
  micBtn.addEventListener('click', toggleSpeechRecognition);
}

function closeAllMenus() {
  modelMenu.classList.add('hidden');
  modelSelectorWrapper.classList.remove('open');
  plusMenu.classList.add('hidden');
}

function selectModel(modelId, badge) {
  state.currentModel = modelId;
  state.modelLabel = badge;
  state.modelBadge = modelId.includes('3.8') ? '3.8 Flash' : '3.7 Flash';
  state.currentInteractionId = null; // 모델 변경 시 새 세션

  selectedModelLabel.textContent = badge;
  headerModelBadge.textContent = state.modelBadge;

  document.querySelectorAll('.model-option').forEach((opt) => {
    opt.classList.toggle('active', opt.dataset.model.endsWith(modelId.replace('models/', '')) || opt.dataset.model === modelId);
  });
}

function autoResizeTextarea() {
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + 'px';
}

function toggleSendButton() {
  const hasText = chatInput.value.trim().length > 0;
  sendBtn.disabled = !hasText || state.isGenerating;
}

function resetChat() {
  if (state.isGenerating) return;
  state.messages = [];
  state.currentInteractionId = null; // 대화 초기화 시 세션 ID 리셋
  messagesContainer.innerHTML = '';
  chatHistory.classList.add('hidden');
  welcomeScreen.classList.remove('hidden');
  chatInput.value = '';
  autoResizeTextarea();
  toggleSendButton();
}

// Web Speech API for voice recognition
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    micBtn.title = '이 브라우저는 음성 인식을 지원하지 않습니다.';
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.lang = 'ko-KR';
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.onstart = () => {
    state.isRecording = true;
    micBtn.classList.add('recording');
    recordingPulse.classList.remove('hidden');
    chatInput.placeholder = '말씀해 주세요...';
  };

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map((r) => r[0].transcript)
      .join('');
    chatInput.value = transcript;
    autoResizeTextarea();
    toggleSendButton();
  };

  recognition.onerror = (event) => {
    console.warn('Speech recognition error:', event.error);
    stopRecording();
  };

  recognition.onend = () => {
    stopRecording();
  };

  state.recognition = recognition;
}

function toggleSpeechRecognition() {
  if (!state.recognition) {
    alert('현재 브라우저 환경에서 음성 인식을 지원하지 않거나 마이크 권한이 필요합니다.');
    return;
  }

  if (state.isRecording) {
    state.recognition.stop();
  } else {
    try {
      state.recognition.start();
    } catch (err) {
      console.warn('Recognition start failed:', err);
    }
  }
}

function stopRecording() {
  state.isRecording = false;
  micBtn.classList.remove('recording');
  recordingPulse.classList.add('hidden');
  chatInput.placeholder = 'Gemini에게 물어보기';
}

// Send Message Flow
async function sendMessage(text) {
  // Show chat history if first message
  if (welcomeScreen && !welcomeScreen.classList.contains('hidden')) {
    welcomeScreen.classList.add('hidden');
    chatHistory.classList.remove('hidden');
  }

  // Clear input
  chatInput.value = '';
  autoResizeTextarea();
  toggleSendButton();

  // Add User Message
  state.messages.push({ role: 'user', content: text });
  renderUserMessage(text);

  // Scroll
  scrollToBottom();

  // Prepare Gemini response placeholder
  state.isGenerating = true;
  updateStatus(true);
  toggleSendButton();

  const modelRow = createModelMessageElement();
  messagesContainer.appendChild(modelRow);
  const bubble = modelRow.querySelector('.model-bubble');
  const cursor = modelRow.querySelector('.streaming-cursor');

  let fullResponse = '';

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        input: text,
        messages: state.messages,
        model: state.currentModel,
        previous_interaction_id: state.currentInteractionId,
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`서버 응답 오류 (${response.status}): ${errText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;
        
        const dataStr = trimmed.slice(6);
        if (dataStr === '[DONE]') {
          break;
        }

        try {
          const parsed = JSON.parse(dataStr);
          if (parsed.interaction_id) {
            state.currentInteractionId = parsed.interaction_id;
          }
          if (parsed.error) {
            fullResponse += `\n\n> ⚠️ **오류:** ${parsed.error}`;
          } else if (parsed.text) {
            fullResponse += parsed.text;
          }
          bubble.innerHTML = marked.parse(fullResponse);
          attachCodeCopyButtons(bubble);
          scrollToBottom();
        } catch (e) {
          console.warn('Chunk parse error:', e, dataStr);
        }
      }
    }

    // Finished streaming
    if (cursor) cursor.remove();
    state.messages.push({ role: 'model', content: fullResponse });

  } catch (error) {
    if (cursor) cursor.remove();
    bubble.innerHTML = `<p style="color: #f87171;">⚠️ 요청 처리 중 문제가 발생했습니다: ${error.message}</p>`;
  } finally {
    state.isGenerating = false;
    updateStatus(false);
    toggleSendButton();
    scrollToBottom();
  }
}

// Render User Message
function renderUserMessage(text) {
  const row = document.createElement('div');
  row.className = 'message-row user-row';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble user-bubble';
  bubble.textContent = text;

  row.appendChild(bubble);
  messagesContainer.appendChild(row);
}

// Create Model Message Shell
function createModelMessageElement() {
  const row = document.createElement('div');
  row.className = 'message-row model-row';

  const avatar = document.createElement('div');
  avatar.className = 'avatar-icon model-avatar';
  avatar.innerHTML = '✨';

  const contentCol = document.createElement('div');
  contentCol.style.flex = '1';

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble model-bubble';

  const cursor = document.createElement('span');
  cursor.className = 'streaming-cursor';

  const meta = document.createElement('div');
  meta.className = 'model-meta-info';
  meta.textContent = `${state.modelBadge} • ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;

  contentCol.appendChild(bubble);
  contentCol.appendChild(cursor);
  contentCol.appendChild(meta);

  row.appendChild(avatar);
  row.appendChild(contentCol);

  return row;
}

// Attach Copy Buttons to Code Blocks
function attachCodeCopyButtons(container) {
  const preElements = container.querySelectorAll('pre');
  preElements.forEach((pre) => {
    if (pre.querySelector('.code-header')) return;

    const code = pre.querySelector('code');
    let lang = 'code';
    if (code && code.className) {
      const match = code.className.match(/language-(\w+)/);
      if (match) lang = match[1];
    }

    const header = document.createElement('div');
    header.className = 'code-header';

    const langSpan = document.createElement('span');
    langSpan.textContent = lang;

    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-btn';
    copyBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      <span>복사</span>
    `;

    copyBtn.addEventListener('click', async () => {
      if (code) {
        await navigator.clipboard.writeText(code.innerText);
        copyBtn.innerHTML = `
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34a853" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span style="color: #34a853;">완료!</span>
        `;
        setTimeout(() => {
          copyBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            <span>복사</span>
          `;
        }, 2000);
      }
    });

    header.appendChild(langSpan);
    header.appendChild(copyBtn);
    pre.insertBefore(header, pre.firstChild);
  });
}

function updateStatus(busy) {
  if (busy) {
    statusIndicator.classList.add('busy');
    statusIndicator.querySelector('.status-text').textContent = '답변 생성 중...';
  } else {
    statusIndicator.classList.remove('busy');
    statusIndicator.querySelector('.status-text').textContent = '준비 완료';
  }
}

function scrollToBottom() {
  const mainContent = document.getElementById('main-content');
  if (mainContent) {
    mainContent.scrollTop = mainContent.scrollHeight;
  }
}

// Start
document.addEventListener('DOMContentLoaded', init);
