import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { Badge } from '../components/ui/Badge';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { useAsync } from '../lib/useAsync';

const HIT_LABEL = { project: 'Progetto', module: 'Modulo', document: 'Documento', event: 'Evento', entity: 'Entità', series: 'Serie', report: 'Rapporto' } as const;

export function SearchPage() {
  const [params] = useSearchParams();
  const q = (params.get('q') ?? '').trim();
  const valid = q.length >= 2;
  const { data, error, loading, reload } = useAsync(
    () => (valid ? api.search(q) : Promise.resolve(undefined)),
    [q],
  );

  return (
    <>
      <PageHeader eyebrow="Ricerca globale" title={valid ? `«${q}»` : 'Ricerca'} />
      {!valid && <EmptyState>Inserisci almeno 2 caratteri nella barra di ricerca.</EmptyState>}
      {valid && loading && <Loading label="Ricerca in corso…" />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data && (
        <>
          <p className="mb-4 text-xs text-steel-500">
            Ambiti cercati: {data.searched_scopes.join(', ')}. Non ancora ricercabili: {data.unavailable_scopes.join(', ')}.
          </p>
          {data.hits.length === 0 ? (
            <EmptyState>Nessun risultato.</EmptyState>
          ) : (
            <ul className="space-y-2">
              {data.hits.map((h) => (
                <li key={`${h.type}-${h.id}`}>
                  <Link to={h.url} className="block rounded-lg border border-ink-700 bg-ink-900 p-3 hover:border-gold-500/60">
                    <div className="flex items-center gap-2">
                      <Badge>{HIT_LABEL[h.type]}</Badge>
                      <span className="min-w-0 truncate font-medium text-paper">{h.title}</span>
                    </div>
                    {h.snippet && <p className="mt-1 text-sm text-steel-400">{h.snippet}</p>}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}
