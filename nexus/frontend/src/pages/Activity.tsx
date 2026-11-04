import { useState } from 'react';
import { api } from '../api/client';
import type { Activity } from '../api/types';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';

const PAGE = 50;

export function ActivityPage() {
  const { data, error, loading, reload, setData } = useAsync(() => api.activity(PAGE, 0), []);
  const [more, setMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filter, setFilter] = useState('');

  async function loadMore() {
    if (!data) return;
    setLoadingMore(true);
    try {
      const next = await api.activity(PAGE, data.length);
      setData([...data, ...next]);
      if (next.length < PAGE) setMore(false);
    } finally {
      setLoadingMore(false);
    }
  }

  const rows: Activity[] = (data ?? []).filter((a) => {
    const f = filter.trim().toLowerCase();
    return !f || a.summary.toLowerCase().includes(f) || a.action.toLowerCase().includes(f) || a.actor.includes(f);
  });

  return (
    <>
      <PageHeader eyebrow="Workspace" title="Registro attività" description="Tutte le operazioni rilevanti eseguite dall'utente o dal sistema, in ordine cronologico inverso." />
      <input
        type="search"
        aria-label="Filtra attività"
        placeholder="Filtra per testo, azione o attore…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="mb-4 w-full max-w-sm rounded-md border border-ink-700 bg-ink-900 px-3 py-1.5 text-sm text-paper placeholder:text-steel-500 focus:border-gold-500 focus:outline-none"
      />
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data && rows.length === 0 && <EmptyState>Nessuna attività corrispondente.</EmptyState>}
      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-ink-700">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="bg-ink-900 text-[11px] uppercase tracking-wider text-steel-500">
              <tr>
                <th className="px-3 py-2 font-medium">Data</th>
                <th className="px-3 py-2 font-medium">Attore</th>
                <th className="px-3 py-2 font-medium">Azione</th>
                <th className="px-3 py-2 font-medium">Descrizione</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {rows.map((a) => (
                <tr key={a.id}>
                  <td className="whitespace-nowrap px-3 py-2 text-steel-400">{formatDateTime(a.created_at)}</td>
                  <td className="px-3 py-2 text-steel-300">{a.actor}</td>
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-steel-400">{a.action}</td>
                  <td className="px-3 py-2 text-paper">{a.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && more && data.length >= PAGE && (
        <Button className="mt-4" onClick={loadMore} disabled={loadingMore}>Carica altre</Button>
      )}
    </>
  );
}
