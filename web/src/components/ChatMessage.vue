<script setup>
import { computed, ref } from 'vue'
import { renderMarkdown } from '../markdown.js'

const props = defineProps({
  role: { type: String, required: true }, // 'user' | 'assistant'
  content: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  thinking: { type: Boolean, default: false },
  toolCalls: { type: Array, default: () => [] },
})

const html = computed(() => renderMarkdown(props.content))

// 使用 computed 确保工具调用列表被正确追踪
const hasToolCalls = computed(() => props.toolCalls && props.toolCalls.length > 0)

const toolNames = {
  document_qa: '文档问答',
  document_summary: '文档总结',
  code_security_analysis: '代码安全分析',
  code_optimization: '代码优化',
  error_log_analysis: '错误日志分析',
}

function getToolDisplayName(name) {
  return toolNames[name] || name
}
</script>

<template>
  <div class="flex gap-3 px-4 py-3" :class="role === 'user' ? 'justify-end' : ''">
    <!-- 头像 -->
    <div
      v-if="role === 'assistant'"
      class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white text-sm shrink-0"
    >
      🤖
    </div>

    <!-- 消息体 -->
    <div
      class="max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed"
      :class="
        role === 'user'
          ? 'bg-blue-600 text-white rounded-br-sm'
          : 'bg-gray-800 text-gray-200 rounded-bl-sm'
      "
    >
      <!-- 用户消息纯文本 -->
      <div v-if="role === 'user'" class="whitespace-pre-wrap">{{ content }}</div>

      <!-- AI 消息 -->
      <div v-else>
        <!-- 思考状态 -->
        <div v-if="thinking" class="flex items-center gap-2 py-1 text-gray-400">
          <svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
          </svg>
          <span>{{ content || '正在思考...' }}</span>
        </div>

        <!-- 工具调用列表 -->
        <div v-if="hasToolCalls" class="space-y-2 mb-2">
          <div
            v-for="(tool, index) in props.toolCalls"
            :key="index"
            class="flex items-center gap-2 px-3 py-2 bg-gray-700/50 rounded-lg text-xs"
          >
            <span class="text-blue-400">{{ tool.status === 'calling' ? '🔧' : tool.status === 'done' ? '✅' : '⏳' }}</span>
            <span class="text-gray-300">{{ tool.status === 'calling' ? '调用中' : '已完成' }}：</span>
            <span class="text-green-400 font-medium">{{ getToolDisplayName(tool.name) }}</span>
          </div>
        </div>

        <!-- 加载动画 -->
        <div v-if="loading && !content && !thinking" class="flex gap-1 py-1">
          <span class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0ms" />
          <span class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 150ms" />
          <span class="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style="animation-delay: 300ms" />
        </div>

        <!-- Markdown 内容 -->
        <div v-if="content" class="markdown-body" v-html="html" />
      </div>
    </div>

    <!-- 用户头像 -->
    <div
      v-if="role === 'user'"
      class="w-8 h-8 rounded-lg bg-gray-600 flex items-center justify-center text-white text-sm shrink-0"
    >
      👤
    </div>
  </div>
</template>
