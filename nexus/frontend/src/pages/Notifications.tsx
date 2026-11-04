import { api } from '../api/client';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useAppState } from '../state/AppState';

export function NotificationsPage() {
  const { data, error, loading, reload } = useAsync(() => api.notifications(), []);
  const { refreshUnread } = useAppState();

  async function after(fn: () => Promise<unknown>) {
    await fn();
    await Promise.all([reload(), refreshUnread()]);
  }

  const unread = data?.filter((n) => !n.read_at).length ?? 0;

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Notifiche"
        actions={unread > 0 && <Button onClick={() => after(api.markAllRead)}>Segna tutte come lette</Button>}
      />
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data && data.length === 0 && <EmptyState>Nessuna notifica.</EmptyState>}
      {data && data.length > 0 && (
        <ul className="space-y-3">
          {data.map((n) => (
            <li key={n.id} className={`rounded-lg border bg-ink-900 p-4 ${n.read_at ? 'border-ink-700' : 'border-gold-500/40'}`}>
              <div className="flex flex-wrap items-start gap-2">
                <h2 className={`min-w-0 flex-1 ${n.read_at ? 'text-steel-300' : 'font-medium text-paper'}`}>{n.title}</h2>
                <Badge tone={n.level === 'error' ? 'bad' : n.level === 'warning' ? 'warn' : 'neutral'}>{n.level}</Badge>
              </div>
              {n.body && <p className="mt-1 text-sm text-steel-400">{n.body}</p>}
              <div className="mt-2 flex items-center gap-3 text-[11px] text-steel-500">
                <span>{formatDateTime(n.created_at)}</span>
                {!n.read_at && (
                  <button className="text-gold-300 hover:underline" onClick={() => after(() => api.markRead(n.id))}>
                    Segna come letta
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
