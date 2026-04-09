/**
 * A2UI 组件注册中心
 *
 * 根据后端下发的 ui_component 字段，动态映射到 React 组件。
 * 前端不再是写死路由的静态页面，而是一个"组件渲染引擎"。
 */

import React from 'react'
import DataWidget from '../components/DataWidget'
import ArtifactPreview from '../components/ArtifactPreview'
import ChatMessage from '../components/ChatMessage'
import TerminalView from '../components/TerminalView'

// 组件注册表：ui_component → React 组件
const registry: Record<string, React.ComponentType<any>> = {
  DataChart: DataWidget,
  DataWidget,
  ArtifactPreview,
  ChatMessage,
  TerminalView,
}

/**
 * 根据组件名称获取 React 组件
 */
export function getComponent(name: string): React.ComponentType<any> | null {
  return registry[name] || null
}

/**
 * 注册自定义组件
 */
export function registerComponent(name: string, component: React.ComponentType<any>): void {
  registry[name] = component
}

/**
 * 获取所有已注册的组件名称
 */
export function getRegisteredComponents(): string[] {
  return Object.keys(registry)
}

/**
 * 动态渲染组件
 */
export function renderWidget(
  componentName: string,
  props: Record<string, any>,
  key?: string,
): React.ReactElement | null {
  const Component = getComponent(componentName)
  if (!Component) {
    console.warn(`[ComponentRegistry] 未注册的组件: ${componentName}`)
    return null
  }
  return <Component key={key} {...props} />
}
