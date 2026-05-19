export type CapabilityType = 'skill' | 'openapi' | 'mcp';

export interface CapabilitySummary {
  plugin_id: string;
  plugin_version: string;
  type: CapabilityType;
  name: string;
  description?: string | null;
  invocation: Record<string, unknown>;
}

export interface PluginMetadata {
  id: string;
  name: string;
  version: string;
  publisher: string;
  description?: string | null;
  tags: string[];
}

export interface PluginVersion {
  plugin_id: string;
  version: string;
  checksum: string;
  status: string;
  created_at: string;
  package_path: string;
  manifest: {
    plugin: PluginMetadata;
  };
  capabilities: CapabilitySummary[];
}

export interface InstallationState {
  workspace_id: string;
  plugin_id: string;
  version: string;
  enabled: boolean;
  agent_ids: string[];
}
