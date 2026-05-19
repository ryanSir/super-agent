import type { PluginVersion } from '../types/plugin';

interface PluginListProps {
  plugins: PluginVersion[];
  selectedPluginId?: string;
  onSelect: (plugin: PluginVersion) => void;
}

export function PluginList({ plugins, selectedPluginId, onSelect }: PluginListProps) {
  if (plugins.length === 0) {
    return <div className="empty-state">No plugins published yet.</div>;
  }

  return (
    <div className="plugin-list">
      {plugins.map((plugin) => (
        <button
          className={`plugin-row ${selectedPluginId === plugin.plugin_id ? 'selected' : ''}`}
          key={`${plugin.plugin_id}@${plugin.version}`}
          onClick={() => onSelect(plugin)}
          type="button"
        >
          <span className="plugin-row-main">
            <span className="plugin-title-line">
              <strong>{plugin.manifest.plugin.name}</strong>
              <span className="version-chip">{plugin.version}</span>
            </span>
            <span>{plugin.manifest.plugin.description ?? 'No description'}</span>
          </span>
          <span className="plugin-row-meta">
            <span>{plugin.capabilities.length}</span>
            <span>caps</span>
          </span>
        </button>
      ))}
    </div>
  );
}
