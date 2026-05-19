import type { PluginVersion } from '../types/plugin';

interface PluginDetailProps {
  plugin?: PluginVersion;
  onInstall: (plugin: PluginVersion) => void;
  busy: boolean;
}

export function PluginDetail({ plugin, onInstall, busy }: PluginDetailProps) {
  if (!plugin) {
    return <section className="panel muted-panel">Select a plugin to inspect versions and capabilities.</section>;
  }

  return (
    <section className="panel detail-panel">
      <div className="panel-heading">
        <div className="plugin-hero">
          <div className="plugin-avatar">RA</div>
          <div>
          <h2>{plugin.manifest.plugin.name}</h2>
          <p>{plugin.manifest.plugin.description}</p>
          <div className="tag-row">
            {plugin.manifest.plugin.tags.map((tag) => (
              <span className="tag-chip" key={tag}>{tag}</span>
            ))}
          </div>
          </div>
        </div>
        <button className="primary-action" disabled={busy} onClick={() => onInstall(plugin)} type="button">
          {busy ? 'Installing...' : 'Install'}
        </button>
      </div>

      <div className="metadata-grid summary">
        <div>
          <span>Plugin ID</span>
          <strong>{plugin.plugin_id}</strong>
        </div>
        <div>
          <span>Version</span>
          <strong>{plugin.version}</strong>
        </div>
        <div>
          <span>Publisher</span>
          <strong>{plugin.manifest.plugin.publisher}</strong>
        </div>
      </div>

      <div className="checksum-row">
        <span>Package checksum</span>
        <code>{plugin.checksum}</code>
      </div>

      <h3>Capabilities</h3>
      <div className="capability-list">
        {plugin.capabilities.map((capability) => (
          <div className="capability-row" key={`${capability.type}:${capability.name}`}>
            <div className="capability-main">
              <div className="capability-heading">
                <strong>{capability.name}</strong>
                <span className={`type-badge ${capability.type}`}>{capability.type}</span>
              </div>
              <p>{capability.description ?? 'No description'}</p>
              <div className="capability-path">
                <span>{capability.type === 'skill' ? 'Context' : 'Invocation'}:</span>
                <code>{String(capability.invocation.path ?? capability.invocation.endpoint ?? 'context')}</code>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
