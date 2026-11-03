import { api } from '../api/client';
import { CredentialsPanel } from '../components/Credentials';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useState } from 'react';
import { errorText } from '../lib/forms';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Form';

export function SettingsPage() {
  const status = useAsync(() => api.systemStatus(), []);
  const s = status.data;
  return (
    <>
      <PageHeader eyebrow="Workspace" title="Sistema" description="Stato del backend, del database e dei provider AI." />
      {status.loading && !s && <Loading />}
      {status.error && <ErrorBox error={status.error} onRetry={status.reload} />}
      {s && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card title="Backend e database">
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-steel-500">Versione</dt>
              <dd className="text-paper">{s.version}</dd>
              <dt className="text-steel-500">Ambiente</dt>
              <dd className="text-paper">{s.environment}</dd>
              <dt className="text-steel-500">Database</dt>
              <dd className="text-paper">
                {s.database} <Badge tone={s.database_ok ? 'ok' : 'bad'}>{s.database_ok ? 'operativo' : 'errore'}</Badge>
              </dd>
              <dt className="text-steel-500">Ora del server</dt>
              <dd className="text-paper">{formatDateTime(s.server_time)}</dd>
            </dl>
          </Card>
          <Card title="Provider AI">
            <p className="mb-3 text-sm text-steel-300">
              Provider attivo: <span className="text-paper">{s.ai_provider.name}</span>. I provider esterni vengono usati solo
              se configurati da te nelle credenziali qui sotto.
            </p>
            <ProviderSelector current={s.ai_provider.id} onChange={status.reload} />
            <ul className="divide-y divide-ink-700">
              {s.ai_providers.map((p) => (
                <li key={p.id} className="flex flex-wrap items-start gap-2 py-2 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="text-paper">{p.name}</p>
                    <p className="text-xs text-steel-500">{p.notes}</p>
                  </div>
                  <Badge tone={p.id === s.ai_provider.id ? 'ok' : 'neutral'}>{p.id === s.ai_provider.id ? 'In uso' : p.requires_credentials ? 'Richiede credenziali' : 'Disponibile'}</Badge>
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Credenziali dei servizi esterni" className="lg:col-span-2">
            <CredentialsPanel />
          </Card>
        </div>
      )}
    </>
  );
}

function ProviderSelector({ current, onChange }: { current: string; onChange: () => void }) {
  const [provider, setProvider] = useState(current);
  const [effort, setEffort] = useState('medium');
  const [err, setErr] = useState<string>();
  return (
    <div className="mb-3 flex flex-wrap items-end gap-2">
      <Select aria-label="Provider AI" className="w-auto" value={provider} onChange={(e) => setProvider(e.target.value)}>
        <option value="none">Nessuno (modalità locale)</option>
        <option value="ollama">Ollama (locale)</option>
        <option value="openai-compatible">Endpoint compatibile OpenAI</option>
        <option value="anthropic">Anthropic API</option>
      </Select>
      {provider === 'anthropic' && (
        <Select aria-label="Effort" className="w-auto" value={effort} onChange={(e) => setEffort(e.target.value)}>
          {['low', 'medium', 'high', 'xhigh', 'max'].map((x) => <option key={x}>{x}</option>)}
        </Select>
      )}
      <Button onClick={async () => { setErr(undefined); try { await api.selectProvider(provider, effort); onChange(); } catch (e) { setErr(errorText(e)); } }}>Usa</Button>
      {err && <p role="alert" className="w-full text-sm text-bad">{err}</p>}
    </div>
  );
}
