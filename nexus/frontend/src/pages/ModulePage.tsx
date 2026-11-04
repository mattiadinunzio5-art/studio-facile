import { Link, useParams } from 'react-router-dom';
import { Check, Hourglass } from 'lucide-react';
import { api } from '../api/client';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorBox, Loading } from '../components/ui/States';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

const STATUS_LABEL = { in_preparation: 'In preparazione', partial: 'Parziale', available: 'Disponibile' } as const;

export function ModulePage() {
  const { moduleId = '' } = useParams();
  const { data: m, error, loading, reload } = useAsync(() => api.module(moduleId), [moduleId]);

  useContextPanel(
    m ? (
      <div>
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Modulo {m.code}</h3>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-steel-300">
          <dt className="text-steel-500">Stato</dt>
          <dd>{STATUS_LABEL[m.status]}</dd>
          <dt className="text-steel-500">Fase prevista</dt>
          <dd>{m.phase}</dd>
        </dl>
        <p className="mt-3 text-xs text-steel-500">
          Le fasi vengono sviluppate in sequenza e ciascuna richiede l'approvazione prima di iniziare la successiva.
        </p>
      </div>
    ) : null,
    [m],
  );

  if (loading && !m) return <Loading />;
  if (error) return <ErrorBox error={error} onRetry={reload} />;
  if (!m) return null;

  return (
    <>
      <PageHeader
        eyebrow={`Modulo ${m.code}`}
        title={m.name}
        description={m.summary}
        actions={<Badge tone="gold">{STATUS_LABEL[m.status]} · Fase {m.phase}</Badge>}
      />
      <div
        role="note"
        className="mb-6 flex items-start gap-3 rounded-lg border border-gold-500/30 bg-gold-400/5 p-4 text-sm"
      >
        <Hourglass className="mt-0.5 size-4 shrink-0 text-gold-400" aria-hidden />
        <p className="text-steel-300">
          Questo modulo è <strong className="text-paper">in preparazione</strong> e sarà sviluppato nella Fase {m.phase}.
          Nessuna funzione, dato o risultato viene simulato in questa pagina.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Funzionalità previste">
          <ul className="space-y-2 text-sm text-steel-300">
            {m.planned_features.map((f) => (
              <li key={f} className="flex gap-2">
                <span className="mt-2 size-1 shrink-0 rounded-full bg-steel-500" aria-hidden />
                {f}
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Già disponibile">
          {m.implemented_features.length === 0 ? (
            <p className="text-sm text-steel-400">Nessuna funzionalità di questo modulo è ancora implementata.</p>
          ) : (
            <ul className="space-y-2 text-sm text-steel-300">
              {m.implemented_features.map((f) => (
                <li key={f} className="flex gap-2">
                  <Check className="mt-0.5 size-4 shrink-0 text-ok" aria-hidden />
                  {f}
                </li>
              ))}
            </ul>
          )}
          {m.id === 'research-studio' && (
            <Link to="/projects" className="mt-3 inline-block text-xs text-gold-300 hover:underline">
              Vai ai progetti
            </Link>
          )}
        </Card>
      </div>
    </>
  );
}
