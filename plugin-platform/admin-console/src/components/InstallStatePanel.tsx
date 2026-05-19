import type { CapabilitySummary, InstallationState } from '../types/plugin';

interface InstallStatePanelProps {
  installation?: InstallationState;
  capabilities: CapabilitySummary[];
  onEnable: () => void;
  onDisable: () => void;
  busy: boolean;
}

export function InstallStatePanel({
  installation,
  capabilities,
  onEnable,
  onDisable,
  busy
}: InstallStatePanelProps) {
  return (
    <section className="panel state-panel">
      <div className="panel-heading compact">
        <div>
          <h2>Workspace State</h2>
          <p>workspace-1</p>
        </div>
        {installation?.enabled ? (
          <button className="secondary-action" disabled={busy} onClick={onDisable} type="button">
            {busy ? 'Updating...' : 'Disable'}
          </button>
        ) : (
          <button className="secondary-action" disabled={!installation || busy} onClick={onEnable} type="button">
            {busy ? 'Updating...' : 'Enable'}
          </button>
        )}
      </div>

      <div className="status-line">
        <span className={`status-dot ${installation?.enabled ? 'active' : ''}`} />
        <strong>{installation ? (installation.enabled ? 'Enabled' : 'Installed, disabled') : 'Not installed'}</strong>
      </div>
      <p className="state-note">
        {installation
          ? `Version ${installation.version} is installed for this workspace.`
          : 'Install the selected plugin before enabling its capabilities.'}
      </p>

      <div className="lifecycle-list">
        <div className="lifecycle-item done">
          <span />
          <strong>Published</strong>
        </div>
        <div className={`lifecycle-item ${installation ? 'done' : ''}`}>
          <span />
          <strong>Installed</strong>
        </div>
        <div className={`lifecycle-item ${installation?.enabled ? 'done' : ''}`}>
          <span />
          <strong>Enabled</strong>
        </div>
        <div className={`lifecycle-item ${capabilities.length > 0 ? 'done' : ''}`}>
          <span />
          <strong>Indexed</strong>
        </div>
      </div>

      <h3>Indexed Capabilities</h3>
      {capabilities.length === 0 ? (
        <div className="empty-state small">No active capabilities indexed for this workspace.</div>
      ) : (
        <ul className="indexed-list">
          {capabilities.map((capability) => (
            <li key={`${capability.type}:${capability.name}`}>
              <span>{capability.type}</span>
              <strong>{capability.name}</strong>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
