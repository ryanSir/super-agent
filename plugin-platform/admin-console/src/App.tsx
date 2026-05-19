import { useEffect, useMemo, useState } from 'react';

import {
  disablePlugin,
  enablePlugin,
  installPlugin,
  listPlugins,
  listWorkspaceCapabilities
} from './api/client';
import { InstallStatePanel } from './components/InstallStatePanel';
import { PluginDetail } from './components/PluginDetail';
import { PluginList } from './components/PluginList';
import type { CapabilitySummary, InstallationState, PluginVersion } from './types/plugin';
import './styles.css';

const WORKSPACE_ID = 'workspace-1';
type ThemeMode = 'light' | 'dark';

export default function App() {
  const [plugins, setPlugins] = useState<PluginVersion[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [installation, setInstallation] = useState<InstallationState>();
  const [capabilities, setCapabilities] = useState<CapabilitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [query, setQuery] = useState('');
  const [theme, setTheme] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') return 'light';
    const stored = window.localStorage.getItem('plugin-platform-theme');
    if (stored === 'light' || stored === 'dark') return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    void refreshPlugins();
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('plugin-platform-theme', theme);
  }, [theme]);

  const selectedPlugin = useMemo(
    () => plugins.find((plugin) => plugin.plugin_id === selectedId) ?? plugins[0],
    [plugins, selectedId]
  );

  const filteredPlugins = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return plugins;
    return plugins.filter((plugin) => {
      const metadata = plugin.manifest.plugin;
      return [metadata.name, plugin.plugin_id, metadata.publisher, metadata.description ?? '', ...metadata.tags]
        .join(' ')
        .toLowerCase()
        .includes(normalized);
    });
  }, [plugins, query]);

  const capabilityTotal = useMemo(
    () => plugins.reduce((total, plugin) => total + plugin.capabilities.length, 0),
    [plugins]
  );

  useEffect(() => {
    if (selectedPlugin && !selectedId) {
      setSelectedId(selectedPlugin.plugin_id);
    }
  }, [selectedPlugin, selectedId]);

  async function refreshPlugins() {
    try {
      setLoading(true);
      setError(undefined);
      const payload = await listPlugins();
      setPlugins(payload);
      setSelectedId((current) => current ?? payload[0]?.plugin_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load plugins');
    } finally {
      setLoading(false);
    }
  }

  async function refreshCapabilities() {
    const payload = await listWorkspaceCapabilities(WORKSPACE_ID);
    setCapabilities(payload);
  }

  async function installSelected(plugin: PluginVersion) {
    await runOperation(async () => {
      const state = await installPlugin(WORKSPACE_ID, plugin.plugin_id, plugin.version);
      setInstallation(state);
      await refreshCapabilities();
    });
  }

  async function enableSelected() {
    if (!selectedPlugin) return;
    await runOperation(async () => {
      const state = await enablePlugin(WORKSPACE_ID, selectedPlugin.plugin_id);
      setInstallation(state);
      await refreshCapabilities();
    });
  }

  async function disableSelected() {
    if (!selectedPlugin) return;
    await runOperation(async () => {
      const state = await disablePlugin(WORKSPACE_ID, selectedPlugin.plugin_id);
      setInstallation(state);
      await refreshCapabilities();
    });
  }

  async function runOperation(operation: () => Promise<void>) {
    try {
      setBusy(true);
      setError(undefined);
      await operation();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-block">
          <span className="product-mark">PP</span>
          <div>
            <h1>Plugin Platform</h1>
            <p>Registry operations, workspace enablement, and capability governance.</p>
          </div>
        </div>
        <div className="topbar-actions">
          <span className="env-pill">Local Dev</span>
          <button
            className="secondary-action"
            onClick={() => setTheme((current) => (current === 'light' ? 'dark' : 'light'))}
            title="Toggle theme"
            type="button"
          >
            {theme === 'light' ? 'Dark' : 'Light'}
          </button>
          <button className="secondary-action" onClick={refreshPlugins} title="Refresh plugins" type="button">
            Sync Registry
          </button>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <section className="overview-grid">
        <div className="metric-card">
          <span>Published Versions</span>
          <strong>{plugins.length}</strong>
          <small>Registry records</small>
        </div>
        <div className="metric-card">
          <span>Declared Capabilities</span>
          <strong>{capabilityTotal}</strong>
          <small>Across all plugins</small>
        </div>
        <div className="metric-card">
          <span>Workspace</span>
          <strong>{WORKSPACE_ID}</strong>
          <small>Current scope</small>
        </div>
        <div className="metric-card">
          <span>Active Index</span>
          <strong>{capabilities.length}</strong>
          <small>Enabled capabilities</small>
        </div>
      </section>

      <section className="workspace-grid">
        <aside className="panel list-panel">
          <div className="panel-heading compact">
            <div>
              <h2>Registry</h2>
              <p>{loading ? 'Loading' : `${filteredPlugins.length} of ${plugins.length} versions`}</p>
            </div>
          </div>
          <label className="search-box">
            <span>Search plugins</span>
            <input
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Name, id, publisher, tag"
              value={query}
            />
          </label>
          {loading ? (
            <div className="empty-state">Loading plugins...</div>
          ) : (
            <PluginList plugins={filteredPlugins} selectedPluginId={selectedId} onSelect={(plugin) => setSelectedId(plugin.plugin_id)} />
          )}
        </aside>

        <PluginDetail plugin={selectedPlugin} onInstall={installSelected} busy={busy} />

        <InstallStatePanel
          installation={installation}
          capabilities={capabilities}
          onEnable={enableSelected}
          onDisable={disableSelected}
          busy={busy}
        />
      </section>
    </main>
  );
}
