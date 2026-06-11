<script setup>
import { ref, onMounted, watch } from 'vue'
import { getCodeCompletion } from '../api.js'

// 全局变量，用于存储monaco编辑器实例
let monaco = null
let editor = null
let completionProvider = null

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'python'
  }
})

const emit = defineEmits(['update:modelValue'])

const editorContainer = ref(null)

onMounted(() => {
  if (!editorContainer.value) return

  // 检查monaco是否已加载
  if (window.monaco) {
    monaco = window.monaco
    initEditor()
  } else {
    // 动态加载monaco-editor
    loadMonacoEditor().then(() => {
      monaco = window.monaco
      initEditor()
    }).catch(err => {
      console.error('Failed to load Monaco Editor:', err)
    })
  }
})

function loadMonacoEditor() {
  return new Promise((resolve, reject) => {
    // 检查是否已经加载
    if (window.monaco) {
      resolve()
      return
    }

    // 创建样式标签
    const style = document.createElement('link')
    style.rel = 'stylesheet'
    style.href = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/editor/editor.main.min.css'
    document.head.appendChild(style)

    // 创建脚本标签
    const script = document.createElement('script')
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs/loader.min.js'
    script.onload = () => {
      // 配置monaco加载
      window.require.config({
        paths: {
          'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.52.2/min/vs'
        }
      })
      
      // 加载monaco编辑器
      window.require(['vs/editor/editor.main'], () => {
        resolve()
      }, reject)
    }
    script.onerror = reject
    document.head.appendChild(script)
  })
}

function initEditor() {
  if (!monaco || !editorContainer.value) return

  // 初始化编辑器
  editor = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: props.language,
    theme: 'vs-dark',
    minimap: { enabled: false },
    automaticLayout: true,
    scrollBeyondLastLine: false,
    fontSize: 14,
    lineNumbers: 'on',
    roundedSelection: false,
    scrollbar: {
      vertical: 'visible',
      horizontal: 'visible'
    }
  })

  // 监听编辑器内容变化
  editor.onDidChangeModelContent(() => {
    emit('update:modelValue', editor.getValue())
  })

  // 注册代码补全提供者
  registerCompletionProvider()
}

function registerCompletionProvider() {
  if (!editor) return

  const model = editor.getModel()
  if (!model) return

  // 清除现有的补全提供者，避免重复注册
  if (completionProvider) {
    completionProvider.dispose()
    completionProvider = null
  }

  // 注册新的补全提供者
  completionProvider = monaco.languages.registerCompletionItemProvider(props.language, {
    provideCompletionItems: async (model, position) => {
      try {
        const code = model.getValue()
        const line = position.lineNumber
        const column = position.column

        // 调用后端API获取补全建议
        const response = await getCodeCompletion(code, props.language, line, column)
        const completions = response.completions || []

        // 转换为Monaco Editor的补全项格式
        const items = completions.map(item => ({
          label: item.label,
          kind: getCompletionKind(item.kind || 'Text'),
          documentation: item.documentation,
          insertText: item.insertText,
          range: {
            startLineNumber: position.lineNumber,
            startColumn: position.column,
            endLineNumber: position.lineNumber,
            endColumn: position.column
          }
        }))

        return {
          suggestions: items
        }
      } catch (error) {
        console.error('补全请求失败:', error)
        return { suggestions: [] }
      }
    },
    triggerCharacters: ['.', ':', '(', '[', '"', "'", ' ']
  })
}

function getCompletionKind(kind) {
  const kindMap = {
    'Text': monaco.languages.CompletionItemKind.Text,
    'Method': monaco.languages.CompletionItemKind.Method,
    'Function': monaco.languages.CompletionItemKind.Function,
    'Constructor': monaco.languages.CompletionItemKind.Constructor,
    'Field': monaco.languages.CompletionItemKind.Field,
    'Variable': monaco.languages.CompletionItemKind.Variable,
    'Class': monaco.languages.CompletionItemKind.Class,
    'Interface': monaco.languages.CompletionItemKind.Interface,
    'Module': monaco.languages.CompletionItemKind.Module,
    'Property': monaco.languages.CompletionItemKind.Property,
    'Unit': monaco.languages.CompletionItemKind.Unit,
    'Value': monaco.languages.CompletionItemKind.Value,
    'Enum': monaco.languages.CompletionItemKind.Enum,
    'Keyword': monaco.languages.CompletionItemKind.Keyword,
    'Snippet': monaco.languages.CompletionItemKind.Snippet,
    'Color': monaco.languages.CompletionItemKind.Color,
    'File': monaco.languages.CompletionItemKind.File,
    'Reference': monaco.languages.CompletionItemKind.Reference
  }
  return kindMap[kind] || monaco.languages.CompletionItemKind.Text
}

// 监听语言变化
watch(() => props.language, (newLanguage) => {
  if (editor) {
    monaco.editor.setModelLanguage(editor.getModel(), newLanguage)
    registerCompletionProvider()
  }
})

// 监听模型值变化
watch(() => props.modelValue, (newValue) => {
  if (editor && editor.getValue() !== newValue) {
    editor.setValue(newValue)
  }
})
</script>

<template>
  <div 
    ref="editorContainer"
    class="w-full h-full min-h-[300px] border border-gray-700 rounded-lg overflow-hidden"
  ></div>
</template>

<style scoped>
/* Monaco Editor 容器样式 */
:deep(.monaco-editor) {
  height: 100% !important;
}

:deep(.monaco-editor .margin) {
  background-color: #1e1e1e;
}

:deep(.monaco-editor .monaco-editor-background) {
  background-color: #1e1e1e;
}

:deep(.monaco-editor .line-numbers) {
  color: #858585;
}

:deep(.monaco-editor .cursor) {
  border-left-color: #ffffff;
}
</style>