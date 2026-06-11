<script setup>
import { ref, reactive, nextTick, watch, onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import ChatMessage from './components/ChatMessage.vue'
import CodeEditor from './components/CodeEditor.vue'
import { streamChat, uploadFile, getSessions, getSessionMessages } from './api.js'

// 会话管理
const sessions = ref([])
const currentSessionId = ref('')
const currentSession = ref({ id: '', title: '', messages: [] })

// 启动时从后端加载会话列表
onMounted(async () => {
  try {
    const data = await getSessions()
    if (data.sessions?.length) {
      sessions.value = data.sessions.map((s) => ({ ...s, messages: [] }))
      await selectSession(sessions.value[0].id)
    } else {
      newSession()
    }
  } catch {
    newSession()
  }
})

function newSession() {
  const id = `session_${Date.now()}`
  const s = { id, title: `新会话`, messages: [] }
  sessions.value.unshift(s)
  currentSessionId.value = id
  currentSession.value = s
}

async function selectSession(id) {
  currentSessionId.value = id
  let s = sessions.value.find((s) => s.id === id)
  if (!s) return

  // 如果消息为空，从后端加载
  if (!s.messages.length) {
    try {
      const data = await getSessionMessages(id)
      s.messages = data.messages || []
    } catch {}
  }
  currentSession.value = s
  scrollToBottom()
}

// 对话
const inputText = ref('')
const isStreaming = ref(false)
const chatContainer = ref(null)

// 代码编辑器
const showCodeEditor = ref(false)
const codeContent = ref('')
const codeLanguage = ref('python')
const codeLanguages = [
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'csharp', label: 'C#' },
  { value: 'cpp', label: 'C++' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' }
]

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

async function sendMessage() {
  const query = inputText.value.trim()
  if (!query || isStreaming.value) return

  const msgs = currentSession.value.messages
  msgs.push({ role: 'user', content: query })
  inputText.value = ''
  scrollToBottom()

  const aiMsg = reactive({ 
    role: 'assistant', 
    content: '', 
    loading: true,
    thinking: true,
    toolCalls: []
  })
  msgs.push(aiMsg)
  isStreaming.value = true
  scrollToBottom()

  if (msgs.length <= 2) {
    currentSession.value.title = query.slice(0, 20) + (query.length > 20 ? '...' : '')
  }

  await streamChat(
    query,
    currentSessionId.value,
    (event) => {
      // 调试日志
      console.log('Received event:', event)
      
      // 处理不同类型的事件
      switch (event.type) {
        case 'thinking':
          aiMsg.thinking = true
          aiMsg.content = event.content
          console.log('Set thinking:', aiMsg.thinking)
          break
        case 'tool_call':
          aiMsg.thinking = false
          aiMsg.loading = true
          // 添加工具调用记录
          const existingTool = aiMsg.toolCalls.find(t => t.name === event.name)
          if (!existingTool) {
            aiMsg.toolCalls.push({ name: event.name, status: 'calling' })
            console.log('Added tool call:', event.name, 'Total tools:', aiMsg.toolCalls.length)
          }
          break
        case 'tool_result':
          // 更新工具调用状态为已完成
          const tool = aiMsg.toolCalls.find(t => t.name === event.name)
          if (tool) {
            tool.status = 'done'
            console.log('Tool completed:', event.name)
          }
          break
        case 'token':
          aiMsg.thinking = false
          aiMsg.loading = true
          aiMsg.content += event.content
          break
        default:
          // 兼容旧的字符串 token
          if (typeof event === 'string') {
            aiMsg.thinking = false
            aiMsg.loading = true
            aiMsg.content += event
          }
      }
      scrollToBottom()
    },
    () => {
      aiMsg.loading = false
      aiMsg.thinking = false
      isStreaming.value = false
      scrollToBottom()
      console.log('Streaming done')
    }
  )
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

function sendCodeToChat() {
  if (!codeContent.value.trim()) return
  
  // 切换到对话模式
  showCodeEditor.value = false
  
  // 构造代码消息
  const codeMessage = `\`\`\`${codeLanguage.value}\n${codeContent.value}\n\`\`\``
  
  // 发送到对话
  inputText.value = codeMessage
  sendMessage()
}

// 文件上传
const fileInput = ref(null)
const isDragging = ref(false)
const uploadStatus = ref('') // '', 'uploading', 'success', 'error'
const uploadMessage = ref('')
let dragCounter = 0
let statusTimer = null

function clearStatus() {
  if (statusTimer) clearTimeout(statusTimer)
  statusTimer = setTimeout(() => {
    uploadStatus.value = ''
    uploadMessage.value = ''
  }, 3000)
}

async function handleUploadFiles(files) {
  if (!files?.length) return
  uploadStatus.value = 'uploading'
  uploadMessage.value = '上传中...'

  for (const file of files) {
    try {
      const result = await uploadFile(file)
      uploadStatus.value = 'success'
      uploadMessage.value = `✅ ${result.message}`
    } catch (err) {
      uploadStatus.value = 'error'
      uploadMessage.value = `❌ ${err.message}`
    }
  }
  clearStatus()
}

function onFileInputChange(e) {
  handleUploadFiles(e.target.files)
  e.target.value = ''
}

function onInputAreaDragEnter(e) {
  e.preventDefault()
  dragCounter++
  isDragging.value = true
}

function onInputAreaDragLeave(e) {
  e.preventDefault()
  dragCounter--
  if (dragCounter <= 0) {
    dragCounter = 0
    isDragging.value = false
  }
}

function onInputAreaDrop(e) {
  e.preventDefault()
  dragCounter = 0
  isDragging.value = false
  handleUploadFiles(e.dataTransfer?.files)
}
</script>

<template>
  <div class="h-screen flex bg-gray-950 text-gray-200">
    <!-- 侧边栏 -->
    <Sidebar
      :sessions="sessions"
      :currentSession="currentSessionId"
      @selectSession="selectSession"
      @newSession="newSession"
    />

    <!-- 主区域 -->
    <div class="flex-1 flex flex-col">
      <!-- 工具栏 -->
      <div class="border-b border-gray-800 p-2 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <button
            class="px-3 py-1.5 text-sm rounded-lg"
            :class="!showCodeEditor ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'"
            @click="showCodeEditor = false"
          >
            💬 对话
          </button>
          <button
            class="px-3 py-1.5 text-sm rounded-lg"
            :class="showCodeEditor ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400'"
            @click="showCodeEditor = true"
          >
            💻 代码编辑器
          </button>
        </div>
        <div v-if="showCodeEditor" class="flex items-center gap-2">
          <label class="text-xs text-gray-400">语言：</label>
          <select
            v-model="codeLanguage"
            class="bg-gray-800 border border-gray-700 rounded-lg text-sm px-2 py-1 text-gray-200 focus:outline-none focus:border-blue-500"
          >
            <option v-for="lang in codeLanguages" :key="lang.value" :value="lang.value">
              {{ lang.label }}
            </option>
          </select>
        </div>
      </div>

      <!-- 内容区域 -->
      <div class="flex-1 overflow-y-auto">
        <!-- 对话区域 -->
        <div v-if="!showCodeEditor" ref="chatContainer" class="h-full">
          <!-- 空状态 -->
          <div
            v-if="!currentSession.messages.length"
            class="h-full flex flex-col items-center justify-center text-gray-500"
          >
            <div class="text-5xl mb-4">🔍</div>
            <div class="text-lg font-medium mb-2">代码分析助手</div>
            <div class="text-sm max-w-md text-center">
              粘贴代码让我帮你审查，或上传文档构建知识库。<br />
              支持代码审查、安全分析、性能诊断、重构建议。
            </div>
          </div>

          <!-- 消息列表 -->
          <div v-else class="py-4">
            <ChatMessage
              v-for="(msg, i) in currentSession.messages"
              :key="i"
              :role="msg.role"
              :content="msg.content"
              :loading="msg.loading"
              :thinking="msg.thinking"
              :tool-calls="msg.toolCalls"
            />
          </div>
        </div>

        <!-- 代码编辑器区域 -->
        <div v-else class="h-full p-4">
          <div class="h-full">
            <CodeEditor
              v-model="codeContent"
              :language="codeLanguage"
            />
          </div>
          <div class="mt-4 flex gap-2">
            <button
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
              @click="sendCodeToChat"
            >
              📤 发送代码到对话
            </button>
            <button
              class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm transition-colors"
              @click="codeContent = ''"
            >
              🗑️ 清空
            </button>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div
        class="border-t border-gray-800 p-4 relative"
        @dragenter="onInputAreaDragEnter"
        @dragover.prevent
        @dragleave="onInputAreaDragLeave"
        @drop="onInputAreaDrop"
      >
        <!-- 拖拽遮罩 -->
        <div
          v-if="isDragging"
          class="absolute inset-0 z-10 bg-blue-600/10 border-2 border-dashed
                 border-blue-500 rounded-xl flex items-center justify-center
                 pointer-events-none"
        >
          <span class="text-blue-400 text-sm font-medium">
            📎 松开鼠标上传文件
          </span>
        </div>

        <!-- 上传状态提示 -->
        <div
          v-if="uploadMessage"
          class="max-w-4xl mx-auto mb-2 text-xs px-2"
          :class="uploadStatus === 'error' ? 'text-red-400' : 'text-green-400'"
        >
          {{ uploadMessage }}
        </div>

        <div class="max-w-4xl mx-auto flex gap-2 items-center">
          <!-- 上传按钮图标 -->
          <input
            ref="fileInput"
            type="file"
            accept=".md,.txt,.pdf,.docx"
            multiple
            class="hidden"
            @change="onFileInputChange"
          />
          <button
            class="w-9 h-9 shrink-0 flex items-center justify-center rounded-lg
                   text-gray-400 hover:text-white hover:bg-gray-800
                   transition-colors relative group"
            title="上传文档（支持 .md / .txt / .pdf / .docx）"
            @click="fileInput?.click()"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
            </svg>
            <!-- Tooltip -->
            <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5
                        bg-gray-800 text-xs text-gray-300 rounded-lg whitespace-nowrap
                        opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none
                        border border-gray-700 shadow-lg">
              支持 .md / .txt / .pdf / .docx
            </div>
          </button>

          <!-- 输入框 -->
          <textarea
            v-model="inputText"
            rows="1"
            placeholder="输入代码或问题... (Enter 发送, Shift+Enter 换行)"
            class="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2
                   text-sm text-gray-200 resize-none focus:outline-none
                   focus:border-blue-500 placeholder-gray-500 leading-5
                   min-h-[36px] max-h-[200px]"
            style="field-sizing: content;"
            @keydown="handleKeydown"
          />

          <!-- 发送按钮 -->
          <button
            class="w-9 h-9 shrink-0 flex items-center justify-center rounded-lg
                   bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700
                   disabled:cursor-not-allowed text-white transition-colors"
            :disabled="!inputText.trim() || isStreaming"
            @click="sendMessage"
          >
            <svg v-if="!isStreaming" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
            <span v-else class="text-xs">⏳</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
