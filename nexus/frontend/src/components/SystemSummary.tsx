import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Activity } from '../api/types';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { Loading } from './ui/States';

/** Contenuto del pannello contestuale: stato del sistema e attività recenti. */
export function SystemSummary({ activity }: { activity?: Activity[] }) {
  const status = useAsync(() => api.systemStatus(), []);
  return (
    <>
      <div>
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Sistema</h3>
        {status.loading && <Loading />}
        {status.error && <p className="text-bad">{status.error.message}</p>}
        {status.data && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-steel-300">
            <dt className="text-steel-500">Versione</dt>
            <dd>{status.data.version}</dd>
            <dt className="text-steel-500">Database</dt>
            <dd>
              {status.data.database} · {status.data.database_ok ? 'operativo' : 'errore'}
            </dd>
            <dt className="text-steel-500">AI</dt>
            <dd>{status.data.ai_mode === 'local' ? 'Modalità locale (nessun provider)' : status.data.ai_provider.name}</dd>
            <dt className="text-steel-500">Ambiente</dt>
            <dd>{status.data.environment}</dd>
          </dl>
        )}
      </div>
      {activity && (
        <div>
          <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Attività recenti</h3>
          <ul className="space-y-2.5">
            {activity.map((a) => (
              <li key={a.id} className="border-l border-ink-600 pl-3">
                <p className="text-steel-300">{a.summary}</p>
                <p className="text-[11px] text-steel-500">
                  {formatDateTime(a.created_at)} · {a.actor}
                </p>
              </li>
            ))}
          </ul>
          <Link to="/activity" className="mt-3 inline-block text-xs text-gold-300 hover:underline">
            Registro completo
          </Link>
        </div>
      )}
    </>
  );
}
