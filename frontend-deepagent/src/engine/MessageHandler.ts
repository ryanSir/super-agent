/**
 * A2UI 消息帧处理器（deepagent 版）
 *
 * 新增 Sub-Agent 生命周期事件处理。
 */

// A2UI 事件类型
export type A2UIEvent = {
  event_type: string
  trace_id?: string
  session_id?: string
  timestamp?: number
  [key: string]: any
}

// 执行步骤
export type StepState = {
  stepId: string
  title: string
  status: 'running' | 'completed' | 'failed'
  detail?: string
}

// 工具结果
export type ToolResultState = {
  id: string
  toolType: 'skill' | 'mcp' | 'native_worker' | 'sandbox' | 'builtin'
  toolName: string
  rawToolName: string
  content: string
  status: 'success' | 'failed'
  loading?: boolean
}

// 动态组件
export type WidgetState = {
  id: string
  component: string
  props: Record<string, any>
}

// Sub-Agent 状态
export type SubAgentState = {
  taskId: string
  agentName: string
  status: 'running' | 'completed' | 'failed'
  result?: string
  tokenUsage?: Record<string, number>
  error?: string
}

// 执行阶段
export type ProcessPhase = {
  phase: string
  status: 'pending' | 'running' | 'completed' | 'failed'
}

// 当前正在构建的回答
export type ResponseState = {
  thinking: string
  steps: StepState[]
  toolResults: ToolResultState[]
  widgets: WidgetState[]
  subAgents: SubAgentState[]
  processPhases: ProcessPhase[]
  answer: string
  answerComplete: boolean
}

// 聊天消息
export type ChatItem =
  | { id: string; type: 'user'; content: string; timestamp: string }
  | { id: string; type: 'assistant'; response: ResponseState; timestamp: string }

// 完整 UI 状态
export type UIState = {
  sessionId: string
  isConnected: boolean
  isProcessing: boolean
  messages: ChatItem[]
  currentResponse: ResponseState | null
  error: string | null
}

function emptyResponse(): ResponseState {
  return {
    thinking: '',
    steps: [],
    toolResults: [],
    widgets: [],
    subAgents: [],
    processPhases: [],
    answer: '',
    answerComplete: false,
  }
}

export function createInitialState(sessionId: string): UIState {
  return {
    sessionId,
    isConnected: false,
    isProcessing: false,
    messages: [],
    currentResponse: null,
    error: null,
  }
}

/**
 * 处理 A2UI 事件，返回更新后的 UI 状态
 */
export function handleEvent(state: UIState, event: A2UIEvent): UIState {
  switch (event.event_type) {
    case 'connected':
      return { ...state, isConnected: true }

    case 'session_created':
      return {
        ...state,
        isProcessing: true,
        error: null,
        currentResponse: emptyResponse(),
      }

    case 'session_completed': {
      const newMessages = [...state.messages]
      if (state.currentResponse) {
        // 如果 answer 为空但后端返回了 answer，补充
        const cr = state.currentResponse
        const finalAnswer = cr.answer || event.answer || ''
        // 清理仍在 loading 的 toolResults
        const finalToolResults = cr.toolResults.map((tr) =>
          tr.loading ? { ...tr, loading: false, status: 'success' as const } : tr
        )
        newMessages.push({
          id: `msg-${Date.now()}`,
          type: 'assistant',
          response: { ...cr, toolResults: finalToolResults, answer: finalAnswer, answerComplete: true },
          timestamp: new Date().toISOString(),
        })
      }
      return {
        ...state,
        isProcessing: false,
        messages: newMessages,
        currentResponse: null,
      }
    }

    case 'session_failed':
      return {
        ...state,
        isProcessing: false,
        currentResponse: null,
        error: event.error || '任务执行失败',
      }

    case 'thinking': {
      const cr = state.currentResponse || emptyResponse()
      return {
        ...state,
        currentResponse: {
          ...cr,
          thinking: cr.thinking + (event.content || ''),
        },
      }
    }

    case 'step': {
      const cr = state.currentResponse || emptyResponse()
      const existingIdx = cr.steps.findIndex((s) => s.stepId === event.step_id)
      let newSteps: StepState[]

      if (existingIdx >= 0) {
        newSteps = [...cr.steps]
        newSteps[existingIdx] = {
          ...newSteps[existingIdx],
          status: event.status || 'running',
          title: event.title || newSteps[existingIdx].title,
          detail: event.detail,
        }
      } else {
        newSteps = [
          ...cr.steps,
          {
            stepId: event.step_id || `s-${Date.now()}`,
            title: event.title || '',
            status: event.status || 'running',
            detail: event.detail,
          },
        ]
      }

      return {
        ...state,
        currentResponse: { ...cr, steps: newSteps },
      }
    }

    case 'tool_call': {
      const cr = state.currentResponse || emptyResponse()
      const displayName = event.display_name || event.tool_name || 'unknown'
      return {
        ...state,
        currentResponse: {
          ...cr,
          toolResults: [
            ...cr.toolResults,
            {
              id: `tr-loading-${event.tool_name}-${Date.now()}`,
              toolType: (event.tool_type || 'mcp') as ToolResultState['toolType'],
              toolName: displayName,
              rawToolName: event.tool_name || displayName,
              content: '',
              status: 'success' as const,
              loading: true,
            },
          ],
        },
      }
    }

    case 'tool_result': {
      const cr = state.currentResponse || emptyResponse()
      const resultToolName = event.tool_name || 'unknown'
      const loadingIdx = cr.toolResults.findLastIndex(
        (tr) => tr.loading && (tr.rawToolName === resultToolName || tr.toolName === resultToolName)
      )
      const newResult: ToolResultState = {
        id: loadingIdx >= 0 ? cr.toolResults[loadingIdx].id : `tr-${Date.now()}-${cr.toolResults.length}`,
        toolType: event.tool_type || 'skill',
        toolName: loadingIdx >= 0 ? cr.toolResults[loadingIdx].toolName : resultToolName,
        rawToolName: resultToolName,
        content: event.content || '',
        status: event.status || 'success',
        loading: false,
      }
      let newToolResults: ToolResultState[]
      if (loadingIdx >= 0) {
        newToolResults = [...cr.toolResults]
        newToolResults[loadingIdx] = newResult
      } else {
        newToolResults = [...cr.toolResults, newResult]
      }
      const mcpStepIdx = event.tool_type === 'mcp'
        ? cr.steps.findLastIndex(
            (s) => s.status === 'running' && s.title === `调用 ${event.tool_name}`
          )
        : -1
      let newSteps = cr.steps
      if (mcpStepIdx >= 0) {
        newSteps = [...cr.steps]
        newSteps[mcpStepIdx] = { ...newSteps[mcpStepIdx], status: 'completed' }
      }
      return {
        ...state,
        currentResponse: { ...cr, steps: newSteps, toolResults: newToolResults },
      }
    }

    case 'render_widget': {
      const cr = state.currentResponse || emptyResponse()
      return {
        ...state,
        currentResponse: {
          ...cr,
          widgets: [
            ...cr.widgets,
            {
              id: event.widget_id || `w-${Date.now()}`,
              component: event.ui_component,
              props: event.props || {},
            },
          ],
        },
      }
    }

    case 'text_stream': {
      const cr = state.currentResponse || emptyResponse()
      return {
        ...state,
        currentResponse: {
          ...cr,
          answer: cr.answer + (event.delta || ''),
          answerComplete: event.is_final || false,
        },
      }
    }

    case 'process_update': {
      const cr = state.currentResponse || emptyResponse()
      const phaseStatus: ProcessPhase['status'] =
        event.status === 'completed' ? 'completed' : event.status === 'failed' ? 'failed' : 'running'
      const existingIdx = cr.processPhases.findIndex((p) => p.phase === event.phase)
      let newPhases: ProcessPhase[]
      if (existingIdx >= 0) {
        newPhases = [...cr.processPhases]
        newPhases[existingIdx] = { phase: event.phase, status: phaseStatus }
      } else {
        newPhases = [...cr.processPhases, { phase: event.phase, status: phaseStatus }]
      }
      return {
        ...state,
        currentResponse: { ...cr, processPhases: newPhases },
      }
    }

    // ── Sub-Agent 生命周期事件 ──────────────────────────

    case 'sub_agent_started': {
      const cr = state.currentResponse || emptyResponse()
      return {
        ...state,
        currentResponse: {
          ...cr,
          subAgents: [
            ...cr.subAgents,
            {
              taskId: event.task_id || `sa-${Date.now()}`,
              agentName: event.sub_agent_name || 'unknown',
              status: 'running',
            },
          ],
          // 同时添加一个 step 展示
          steps: [
            ...cr.steps,
            {
              stepId: `sa-${event.task_id || Date.now()}`,
              title: `Sub-Agent: ${event.sub_agent_name || 'unknown'} 执行中`,
              status: 'running',
            },
          ],
        },
      }
    }

    case 'sub_agent_progress': {
      const cr = state.currentResponse || emptyResponse()
      const saIdx = cr.subAgents.findIndex((sa) => sa.taskId === event.task_id)
      if (saIdx < 0) return state

      const newSubAgents = [...cr.subAgents]
      newSubAgents[saIdx] = {
        ...newSubAgents[saIdx],
        result: event.progress || '',
      }
      return {
        ...state,
        currentResponse: { ...cr, subAgents: newSubAgents },
      }
    }

    case 'sub_agent_completed': {
      const cr = state.currentResponse || emptyResponse()
      const saIdx = cr.subAgents.findIndex((sa) => sa.taskId === event.task_id)
      if (saIdx < 0) return state

      const newSubAgents = [...cr.subAgents]
      newSubAgents[saIdx] = {
        ...newSubAgents[saIdx],
        status: event.success ? 'completed' : 'failed',
        result: event.answer || '',
        tokenUsage: event.token_usage,
        error: event.error || '',
      }

      // 更新对应 step 状态
      const stepId = `sa-${event.task_id}`
      const stepIdx = cr.steps.findIndex((s) => s.stepId === stepId)
      let newSteps = cr.steps
      if (stepIdx >= 0) {
        newSteps = [...cr.steps]
        newSteps[stepIdx] = {
          ...newSteps[stepIdx],
          status: event.success ? 'completed' : 'failed',
          title: `Sub-Agent: ${newSubAgents[saIdx].agentName} ${event.success ? '完成' : '失败'}`,
        }
      }

      return {
        ...state,
        currentResponse: { ...cr, subAgents: newSubAgents, steps: newSteps },
      }
    }

    // ── 兼容与静默事件 ─────────────────────────────────

    case 'heartbeat':
    case 'middleware_event':
      return state

    default:
      return state
  }
}
