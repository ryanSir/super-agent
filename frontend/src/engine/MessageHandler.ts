/**
 * A2UI 消息帧处理器
 *
 * 根据 event_type 路由到对应处理逻辑，维护 UI 状态。
 */

// A2UI 事件类型
export type A2UIEvent = {
  event_type: string
  trace_id?: string
  session_id?: string
  timestamp?: string
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
  toolType: 'skill' | 'mcp' | 'native_worker' | 'sandbox'
  toolName: string
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

// 当前正在构建的回答
export type ResponseState = {
  thinking: string
  steps: StepState[]
  toolResults: ToolResultState[]
  widgets: WidgetState[]
  answer: string
  answerComplete: boolean
}

// 聊天消息（用户消息 or 归档的回答）
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
      // 归档 currentResponse 到 messages
      const newMessages = [...state.messages]
      if (state.currentResponse) {
        newMessages.push({
          id: `msg-${Date.now()}`,
          type: 'assistant',
          response: state.currentResponse,
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
        // 更新已有步骤的状态
        newSteps = [...cr.steps]
        newSteps[existingIdx] = {
          ...newSteps[existingIdx],
          status: event.status || 'running',
          title: event.title || newSteps[existingIdx].title,
          detail: event.detail,
        }
      } else {
        // 新步骤
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
      const stepId = `mcp-${event.tool_name}-${Date.now()}`
      const newSteps: StepState[] =
        event.tool_type === 'mcp'
          ? [
              ...cr.steps,
              {
                stepId,
                title: `调用 ${event.tool_name}`,
                status: 'running' as const,
              },
            ]
          : cr.steps
      return {
        ...state,
        currentResponse: {
          ...cr,
          steps: newSteps,
          toolResults: [
            ...cr.toolResults,
            {
              id: `tr-loading-${event.tool_name}-${Date.now()}`,
              toolType: (event.tool_type || 'mcp') as ToolResultState['toolType'],
              toolName: event.tool_name || 'unknown',
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
      // 替换同名 loading 占位，若无则直接追加
      const loadingIdx = cr.toolResults.findLastIndex(
        (tr) => tr.loading && tr.toolName === (event.tool_name || 'unknown')
      )
      const newResult: ToolResultState = {
        id: loadingIdx >= 0 ? cr.toolResults[loadingIdx].id : `tr-${Date.now()}-${cr.toolResults.length}`,
        toolType: event.tool_type || 'skill',
        toolName: event.tool_name || 'unknown',
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
      // 将对应 MCP step 标记为 completed
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

    // 兼容旧事件
    case 'process_update':
      return handleEvent(state, {
        ...event,
        event_type: 'step',
        step_id: event.phase || `pu-${Date.now()}`,
        title: event.message || event.phase || '',
        status: event.status === 'in_progress' ? 'running' : event.status,
      })

    case 'skill_result':
      return handleEvent(state, {
        ...event,
        event_type: 'tool_result',
        tool_type: 'skill',
        tool_name: event.skill_name || 'unknown',
      })

    case 'heartbeat':
      return state

    // 记忆系统更新事件（静默处理，不影响 UI）
    case 'memory_update':
      return state

    // Middleware 事件（静默处理，可用于调试面板）
    case 'middleware_event':
      return state

    default:
      // 向后兼容：忽略未知事件类型，不抛出错误
      return state
  }
}
