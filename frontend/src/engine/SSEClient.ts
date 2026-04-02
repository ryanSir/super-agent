/**
 * SSE 客户端
 *
 * 基于原生 EventSource，自动断线重连 + Last-Event-ID 断点续传。
 */

export type EventHandler = (event: any) => void

export interface SSEClient {
  close: () => void
}

/**
 * 创建 SSE 客户端
 *
 * EventSource 断线后浏览器自动重连，并携带 Last-Event-ID 请求头，
 * 后端从该位置开始重放，实现零代码断点续传。
 */
export function createSSEClient(
  sessionId: string,
  onEvent: EventHandler,
  onError?: () => void,
): SSEClient {
  const isDev = import.meta.env.DEV
  const host = isDev ? 'http://localhost:9000' : ''
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

  source.onerror = () => {
    // EventSource 自动重连，带 Last-Event-ID，无需手动处理
    // 仅通知上层用于 UI 状态更新
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
): Promise<{ success: boolean; session_id: string; trace_id: string }> {
  const isDev = import.meta.env.DEV
  const host = isDev ? 'http://localhost:9000' : ''

  const res = await fetch(`${host}/api/agent/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId }),
  })

  return res.json()
}
