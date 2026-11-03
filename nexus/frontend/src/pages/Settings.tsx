import { api } from '../api/client';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';

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
              Provider attivo: <span className="text-paper">{s.ai_provider.name}</span>. La configurazione delle credenziali
              sarà disponibile in Fase 5; i provider esterni verranno usati solo se configurati da te.
            </p>
            <ul className="divide-y divide-ink-700">
              {s.ai_providers.map((p) => (
                <li key={p.id} className="flex flex-wrap items-start gap-2 py-2 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="text-paper">{p.name}</p>
                    <p className="text-xs text-steel-500">{p.notes}</p>
                  </div>
                  <Badge tone={p.implemented ? 'ok' : 'neutral'}>{p.implemented ? 'Attivo' : 'Non implementato'}</Badge>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </>
  );
}
