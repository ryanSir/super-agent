import type { CapabilitySummary, InstallationState, PluginVersion } from '../types/plugin';

const API_BASE = import.meta.env.VITE_PLUGIN_API_BASE ?? '';

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(detail || `Request failed: ${response.status}`, response.status);
  }
  return response.json() as Promise<T>;
}

export function listPlugins(): Promise<PluginVersion[]> {
  return request<PluginVersion[]>('/api/registry/plugins');
}

export function getInstallation(pluginId: string): Promise<InstallationState | undefined> {
  return request<InstallationState>(`/api/manager/installations/${pluginId}`).catch((error) => {
    if (error instanceof ApiError && error.status === 404) return undefined;
    throw error;
  });
}

export function installPlugin(pluginId: string, version: string): Promise<InstallationState> {
  return request<InstallationState>('/api/manager/installations', {
    method: 'POST',
    body: JSON.stringify({ plugin_id: pluginId, version })
  });
}

export function enablePlugin(pluginId: string): Promise<InstallationState> {
  return request<InstallationState>('/api/manager/installations/enable', {
    method: 'POST',
    body: JSON.stringify({ plugin_id: pluginId })
  });
}

export function disablePlugin(pluginId: string): Promise<InstallationState> {
  return request<InstallationState>('/api/manager/installations/disable', {
    method: 'POST',
    body: JSON.stringify({ plugin_id: pluginId })
  });
}

export async function listCapabilities(): Promise<CapabilitySummary[]> {
  const payload = await request<{ capabilities: CapabilitySummary[] }>('/api/capabilities');
  return payload.capabilities;
}
