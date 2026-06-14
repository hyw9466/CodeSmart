const BASE = '/api'

// 用户ID管理：从 localStorage 获取或创建
function getUserId() {
  let userId = localStorage.getItem('user_id')
  if (!userId) {
    // 生成唯一用户ID
    userId = 'user_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36)
    localStorage.setItem('user_id', userId)
  }
  return userId
}

// 带用户ID的请求头
function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-User-ID': getUserId()
  }
}

export async function checkHealth() {
  const res = await fetch('/health')
  return res.json()
}

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, {
    method: 'POST',
    body: form,
    headers: { 'X-User-ID': getUserId() }
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '上传失败')
  }
  return res.json()
}

export async function getDocuments() {
  const res = await fetch(`${BASE}/documents`, {
    headers: { 'X-User-ID': getUserId() }
  })
  return res.json()
}

export async function deleteDocument(filename) {
  const res = await fetch(`${BASE}/documents/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
    headers: { 'X-User-ID': getUserId() }
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '删除失败')
  }
  return res.json()
}

export async function deleteAllDocuments() {
  const res = await fetch(`${BASE}/documents`, {
    method: 'DELETE',
    headers: { 'X-User-ID': getUserId() }
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '清空失败')
  }
  return res.json()
}

export async function getSessions() {
  const res = await fetch(`${BASE}/sessions`, {
    headers: { 'X-User-ID': getUserId() }
  })
  return res.json()
}

export async function getSessionMessages(sessionId) {
  const res = await fetch(`${BASE}/sessions/${sessionId}/messages`, {
    headers: { 'X-User-ID': getUserId() }
  })
  return res.json()
}

/**
 * 流式 Agent 对话，通过 SSE 逐 token 回调
 * @param {string} query
 * @param {string} sessionId
 * @param {(event: { type: string, content: string, name?: string }) => void} onEvent
 * @param {() => void} onDone
 */
export async function streamChat(query, sessionId, onEvent, onDone) {
  const res = await fetch(`${BASE}/agent/chat/stream`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ query, session_id: sessionId, user_id: getUserId() }),
  })

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // 保留不完整的行

    for (const line of lines) {
      if (line.startsWith('event: done')) {
        onDone?.()
        return
      }
      if (line.startsWith('data: ')) {
        const payload = line.slice(6)
        if (payload === '[DONE]') {
          onDone?.()
          return
        }
        try {
          const event = JSON.parse(payload)
          onEvent?.(event)
        } catch {}
      }
    }
  }
  onDone?.()
}

export async function getCodeCompletion(code, language, line, column) {
  const res = await fetch(`${BASE}/code/completion`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ code, language, line, column }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || '代码补全失败')
  }
  return res.json()
}

// 导出获取用户ID的函数（供其他组件使用）
export { getUserId }
