import { useState } from 'react';
import { ExternalLink, KeyRound, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { ErrorBox, Loading } from '../components/ui/States';
import { CONNECTOR_STATUS_LABEL, StatusDot } from '../components/ui/StatusDot';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

export function SourcesPage() {
  const { data, error, loading, reload, setData } = useAsync(() => api.connectors(), []);
  const [checking, setChecking] = useState<Set<string>>(new Set());
  const [checkError, setCheckError] = useState<Error>();

  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Come funziona</h3>
      <p>La verifica invia una sola richiesta all'host della fonte e registra esito, codice HTTP e latenza. Nessun dato viene scaricato.</p>
      <p>L'importazione delle serie sarà attivata con il modulo Financial Intelligence (Fase 4).</p>
      <p className="text-xs text-steel-500">
        Licenze e limiti d'uso vanno verificati sulle pagine ufficiali dei termini prima di qualsiasi uso, in particolare commerciale.
      </p>
    </div>,
    [],
  );

  async function check(ids: string[]) {
    setCheckError(undefined);
    setChecking(new Set(ids));
    for (const id of ids) {
      try {
        const updated = await api.checkConnector(id);
        setData((prev) => prev?.map((c) => (c.id === updated.id ? updated : c)));
      } catch (e) {
        setCheckError(e as Error);
      } finally {
        setChecking((s) => {
          const n = new Set(s);
          n.delete(id);
          return n;
        });
      }
    }
  }

  const busy = checking.size > 0;

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Fonti e connettori"
        description="Fonti aperte dichiarate, con stato osservato, termini d'uso e fase di attivazione. Nessun connettore importa ancora dati."
        actions={
          data && (
            <Button onClick={() => check(data.map((c) => c.id))} disabled={busy}>
              <RefreshCw className={`size-4 ${busy ? 'animate-spin' : ''}`} aria-hidden /> Verifica tutte
            </Button>
          )
        }
      />
      {checkError && <div className="mb-4"><ErrorBox error={checkError} /></div>}
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data && (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {data.map((c) => (
            <article key={c.id} className="min-w-0 rounded-lg border border-ink-700 bg-ink-900 p-4" data-testid={`connector-${c.id}`}>
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <h2 className="font-medium text-paper">{c.name}</h2>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    <Badge>{c.category}</Badge>
                    <Badge tone="gold">Importazione: Fase {c.planned_phase}</Badge>
                    {c.requires_api_key && (
                      <Badge tone="neutral">
                        <KeyRound className="mr-1 size-3" aria-hidden /> Richiede chiave
                      </Badge>
                    )}
                  </div>
                </div>
                <Button
                  className="shrink-0"
                  onClick={() => check([c.id])}
                  disabled={checking.has(c.id)}
                  aria-label={`Verifica ${c.name}`}
                >
                  <RefreshCw className={`size-4 ${checking.has(c.id) ? 'animate-spin' : ''}`} aria-hidden />
                  <span className="hidden sm:inline">Verifica</span>
                </Button>
              </div>
              <div className="mt-3 flex items-center gap-2 text-sm">
                <StatusDot status={c.last_status} />
                <span className="text-steel-300">{CONNECTOR_STATUS_LABEL[c.last_status]}</span>
                {c.last_http_status !== null && <span className="text-xs text-steel-500">HTTP {c.last_http_status}</span>}
                {c.last_latency_ms !== null && <span className="text-xs text-steel-500">{c.last_latency_ms} ms</span>}
              </div>
              <p className="mt-1 text-xs text-steel-500">Ultima verifica: {formatDateTime(c.last_checked_at)}</p>
              {c.last_error && <p className="mt-1 break-words font-mono text-[11px] text-bad">{c.last_error}</p>}
              <p className="mt-3 text-sm text-steel-400">{c.notes}</p>
              <div className="mt-3 flex flex-wrap gap-4 text-xs">
                <a href={c.homepage} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-gold-300 hover:underline">
                  Sito <ExternalLink className="size-3" aria-hidden />
                </a>
                <a href={c.terms_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-gold-300 hover:underline">
                  Termini d'uso e licenza <ExternalLink className="size-3" aria-hidden />
                </a>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
