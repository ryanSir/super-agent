import type { CapabilitySummary, InstallationState, PluginVersion } from '../types/plugin';

const API_BASE = import.meta.env.VITE_PLUGIN_API_BASE ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function listPlugins(): Promise<PluginVersion[]> {
  return request<PluginVersion[]>('/api/registry/plugins');
}

export function installPlugin(workspaceId: string, pluginId: string, version: string): Promise<InstallationState> {
  return request<InstallationState>('/api/manager/installations', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: workspaceId, plugin_id: pluginId, version })
  });
}

export function enablePlugin(workspaceId: string, pluginId: string): Promise<InstallationState> {
  return request<InstallationState>('/api/manager/installations/enable', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: workspaceId, plugin_id: pluginId })
  });
}

export function disablePlugin(workspaceId: string, pluginId: string): Promise<InstallationState> {
  return request<InstallationState>('/api/manager/installations/disable', {
    method: 'POST',
    body: JSON.stringify({ workspace_id: workspaceId, plugin_id: pluginId })
  });
}

export async function listWorkspaceCapabilities(workspaceId: string): Promise<CapabilitySummary[]> {
  const payload = await request<{ capabilities: CapabilitySummary[] }>(`/api/capabilities/workspaces/${workspaceId}`);
  return payload.capabilities;
}
