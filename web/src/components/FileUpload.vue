<script setup>
import { ref } from 'vue'
import { uploadFile } from '../api.js'

const emit = defineEmits(['uploaded'])
const uploading = ref(false)
const lastResult = ref(null)

async function handleFiles(e) {
  const files = e.target.files || e.dataTransfer?.files
  if (!files?.length) return

  uploading.value = true
  lastResult.value = null

  for (const file of files) {
    try {
      const result = await uploadFile(file)
      lastResult.value = result
      emit('uploaded', result)
    } catch (err) {
      lastResult.value = { status: 'error', message: err.message }
    }
  }
  uploading.value = false
  e.target.value = ''
}

function onDrop(e) {
  e.preventDefault()
  handleFiles(e)
}
</script>

<template>
  <div
    class="border border-dashed border-gray-600 rounded-lg p-4 text-center
           hover:border-blue-500 transition-colors cursor-pointer"
    @drop="onDrop"
    @dragover.prevent
  >
    <label class="cursor-pointer">
      <input
        type="file"
        accept=".md,.txt,.pdf,.docx"
        multiple
        class="hidden"
        @change="handleFiles"
      />
      <div class="text-gray-400 text-sm">
        <span v-if="uploading">⏳ 上传中...</span>
        <span v-else>📎 点击或拖拽上传文档（.md / .txt / .pdf / .docx）</span>
      </div>
    </label>

    <!-- 上传结果详情 -->
    <div v-if="lastResult" class="mt-3 text-sm text-left">
      <div v-if="lastResult.status === 'success'" class="text-green-400 space-y-1">
        <div class="font-medium">✅ {{ lastResult.filename }}</div>
        <div class="text-xs text-gray-400 ml-2">
          <span>📄 {{ lastResult.chunks }} 个片段</span>
          <span class="ml-2">📝 {{ lastResult.char_count }} 个字符</span>
        </div>
        <div class="text-xs text-green-500 mt-1">{{ lastResult.message }}</div>
      </div>
      <div v-else-if="lastResult.status === 'error'" class="text-red-400">
        <div class="font-medium">❌ {{ lastResult.filename || '上传失败' }}</div>
        <div class="text-xs text-red-400 mt-1">{{ lastResult.message }}</div>
      </div>
    </div>
  </div>
</template>
