/**
 * SSE 客户端（deepagent 版）
 *
 * 连接 deepagent 后端（端口 9001），支持断线重连 + Last-Event-ID 断点续传。
 */

export type EventHandler = (event: any) => void

export interface SSEClient {
  close: () => void
}

/**
 * 创建 SSE 客户端
 */
export function createSSEClient(
  sessionId: string,
  onEvent: EventHandler,
  onError?: () => void,
): SSEClient {
  const isDev = import.meta.env.DEV
  const host = isDev ? 'http://localhost:9001' : ''
  const url = `${host}/api/agent/stream/${sessionId}`

  const source = new EventSource(url)

  source.onmessage = (e: MessageEvent) => {
    try {
      const event = JSON.parse(e.data)
      onEvent(event)
    } catch {
      console.warn('[SSE] 消息解析失败:', e.data)
    }
  }

  // 监听具名事件（新后端在 SSE event: 字段发送事件类型）
  const eventTypes = [
    'session_created', 'session_completed', 'session_failed',
    'thinking', 'step', 'text_stream',
    'tool_call', 'tool_result', 'render_widget',
    'sub_agent_started', 'sub_agent_progress', 'sub_agent_completed',
    'heartbeat', 'middleware_event',
  ]

  for (const type of eventTypes) {
    source.addEventListener(type, (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data)
        // 确保 event_type 字段存在
        onEvent({ event_type: type, ...data })
      } catch {
        console.warn(`[SSE] ${type} 事件解析失败:`, e.data)
      }
    })
  }

  source.onerror = () => {
    onError?.()
  }

  return {
    close: () => source.close(),
  }
}

/**
 * 发送查询请求（POST）
 */
export async function submitQuery(
  sessionId: string,
  query: string,
  mode: string = 'auto',
  userId: string = 'default',
): Promise<{ success: boolean; session_id: string; trace_id: string }> {
  const isDev = import.meta.env.DEV
  const host = isDev ? 'http://localhost:9001' : ''

  const res = await fetch(`${host}/api/agent/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      session_id: sessionId,
      mode,
      user_id: userId,
    }),
  })

  return res.json()
}
