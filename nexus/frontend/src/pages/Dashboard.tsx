import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, ChevronUp, Cpu, Eye, EyeOff, Plus, SlidersHorizontal } from 'lucide-react';
import { api } from '../api/client';
import type { Dashboard as DashboardData, DashboardLayout, WidgetId } from '../api/types';
import { SystemSummary } from '../components/SystemSummary';
import { Badge, DemoBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading, NotAvailable } from '../components/ui/States';
import { CONNECTOR_STATUS_LABEL, StatusDot } from '../components/ui/StatusDot';
import { formatDateTime } from '../lib/format';
import { MODULE_NAV } from '../lib/nav';
import { useAsync } from '../lib/useAsync';
import { useAppState, useContextPanel } from '../state/AppState';

export const WIDGET_LABELS: Record<WidgetId, string> = {
  modules: 'Aree di NEXUS',
  sources: 'Stato delle fonti',
  searches: 'Ultime ricerche',
  projects: 'Progetti attivi',
  indicators: 'Indicatori economici',
  events: 'Eventi storici',
  reports: 'Rapporti recenti',
  ai: 'Attività AI',
  notifications: 'Notifiche',
};

const WIDE: WidgetId[] = ['modules'];

function renderWidget(id: WidgetId, d: DashboardData, onRead: (nid: number) => void): ReactNode {
  switch (id) {
    case 'modules':
      return (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(15.5rem,1fr))] gap-2">
          {d.modules.map((m) => {
            const nav = MODULE_NAV.find((n) => n.to === `/modules/${m.id}`);
            const Icon = nav?.icon;
            return (
              <Link
                key={m.id}
                to={`/modules/${m.id}`}
                className="group flex min-w-0 flex-col gap-2 rounded-md border border-ink-700 bg-ink-850 p-3 hover:border-gold-500/60"
              >
                <div className="flex items-center gap-2">
                  {Icon && <Icon className="size-4 text-gold-400" aria-hidden />}
                  <span className="font-mono text-[11px] text-steel-500">{m.code}</span>
                  <span className="min-w-0 truncate text-sm font-medium text-paper">{m.name}</span>
                </div>
                <p className="line-clamp-2 text-xs text-steel-400">{m.summary}</p>
                <div>
                  <Badge tone="gold">In preparazione · Fase {m.phase}</Badge>
                </div>
              </Link>
            );
          })}
        </div>
      );
    case 'sources':
      return (
        <>
          <p className="mb-3 text-xs text-steel-400">
            {d.sources.total} fonti dichiarate · {d.sources.implemented} con importazione dati attiva
          </p>
          <ul className="space-y-1.5">
            {d.sources.items.map((c) => (
              <li key={c.id} className="flex items-center gap-2 text-sm">
                <StatusDot status={c.last_status} />
                <span className="min-w-0 flex-1 truncate text-steel-300">{c.name}</span>
                <span className="shrink-0 text-[11px] text-steel-500">{CONNECTOR_STATUS_LABEL[c.last_status]}</span>
              </li>
            ))}
          </ul>
          <Link to="/sources" className="mt-3 inline-block text-xs text-gold-300 hover:underline">
            Verifica disponibilità
          </Link>
        </>
      );
    case 'searches':
      return d.recent_searches.length === 0 ? (
        <EmptyState>Nessuna ricerca eseguita. Usa la barra in alto.</EmptyState>
      ) : (
        <ul className="space-y-1.5">
          {d.recent_searches.map((s) => (
            <li key={s.id} className="flex items-center gap-2 text-sm">
              <Link to={`/search?q=${encodeURIComponent(s.query)}`} className="min-w-0 flex-1 truncate text-steel-300 hover:text-paper">
                {s.query}
              </Link>
              <span className="shrink-0 text-[11px] text-steel-500">
                {s.results_count} risultati · {formatDateTime(s.created_at)}
              </span>
            </li>
          ))}
        </ul>
      );
    case 'projects':
      return (
        <>
          {d.projects.items.length === 0 ? (
            <EmptyState>Nessun progetto attivo.</EmptyState>
          ) : (
            <ul className="space-y-2">
              {d.projects.items.map((p) => (
                <li key={p.id} className="flex items-center gap-2 text-sm">
                  <Link to={`/projects?id=${p.id}`} className="min-w-0 flex-1 truncate text-steel-300 hover:text-paper">
                    {p.title}
                  </Link>
                  {p.is_demo && <DemoBadge />}
                  <span className="shrink-0 text-[11px] text-steel-500">{formatDateTime(p.updated_at)}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-3 flex items-center justify-between text-xs text-steel-500">
            <span>
              {d.projects.active_count} attivi · {d.projects.archived_count} archiviati
            </span>
            <Link to="/projects?new=1" className="inline-flex items-center gap-1 text-gold-300 hover:underline">
              <Plus className="size-3" aria-hidden /> Nuovo progetto
            </Link>
          </div>
        </>
      );
    case 'indicators':
      return <NotAvailable reason={d.indicators.reason} phase={d.indicators.planned_phase} />;
    case 'events':
      return <NotAvailable reason={d.events.reason} phase={d.events.planned_phase} />;
    case 'reports':
      return <NotAvailable reason={d.reports.reason} phase={d.reports.planned_phase} />;
    case 'ai':
      return (
        <div className="flex items-start gap-3 text-sm">
          <Cpu className="mt-0.5 size-4 shrink-0 text-steel-400" aria-hidden />
          <div>
            <p className="font-medium text-paper">
              {d.ai.mode === 'local' ? 'Modalità locale' : 'Provider remoto'} · {d.ai.provider}
            </p>
            <p className="mt-1 text-steel-400">{d.ai.note}</p>
            <p className="mt-2 text-xs text-steel-500">Esecuzioni AI registrate: {d.ai.runs.length}</p>
          </div>
        </div>
      );
    case 'notifications':
      return d.notifications.items.length === 0 ? (
        <EmptyState>Nessuna notifica.</EmptyState>
      ) : (
        <ul className="space-y-3">
          {d.notifications.items.map((n) => (
            <li key={n.id} className="text-sm">
              <div className="flex items-start gap-2">
                <p className={`min-w-0 flex-1 ${n.read_at ? 'text-steel-400' : 'font-medium text-paper'}`}>{n.title}</p>
                {!n.read_at && (
                  <button onClick={() => onRead(n.id)} className="shrink-0 text-[11px] text-gold-300 hover:underline">
                    Segna letta
                  </button>
                )}
              </div>
              <p className="mt-0.5 text-xs text-steel-500">{formatDateTime(n.created_at)}</p>
            </li>
          ))}
        </ul>
      );
  }
}

function LayoutEditor({ layout, onSave, onCancel }: { layout: DashboardLayout; onSave: (l: DashboardLayout) => Promise<void>; onCancel: () => void }) {
  const [draft, setDraft] = useState(layout);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Error>();

  const move = (i: number, dir: -1 | 1) => {
    const order = [...draft.order];
    const j = i + dir;
    if (j < 0 || j >= order.length) return;
    [order[i], order[j]] = [order[j], order[i]];
    setDraft({ ...draft, order });
  };
  const toggle = (id: WidgetId) =>
    setDraft({ ...draft, hidden: draft.hidden.includes(id) ? draft.hidden.filter((h) => h !== id) : [...draft.hidden, id] });

  return (
    <Card title="Personalizza dashboard" className="mb-6" testId="layout-editor">
      <ul className="divide-y divide-ink-700">
        {draft.order.map((id, i) => {
          const hidden = draft.hidden.includes(id);
          return (
            <li key={id} className="flex items-center gap-2 py-2 text-sm">
              <span className={`min-w-0 flex-1 truncate ${hidden ? 'text-steel-500 line-through' : 'text-paper'}`}>{WIDGET_LABELS[id]}</span>
              <Button variant="ghost" className="px-1.5" onClick={() => move(i, -1)} disabled={i === 0} aria-label={`Sposta su ${WIDGET_LABELS[id]}`}>
                <ChevronUp className="size-4" />
              </Button>
              <Button variant="ghost" className="px-1.5" onClick={() => move(i, 1)} disabled={i === draft.order.length - 1} aria-label={`Sposta giù ${WIDGET_LABELS[id]}`}>
                <ChevronDown className="size-4" />
              </Button>
              <Button variant="ghost" className="px-1.5" onClick={() => toggle(id)} aria-label={`${hidden ? 'Mostra' : 'Nascondi'} ${WIDGET_LABELS[id]}`}>
                {hidden ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </Button>
            </li>
          );
        })}
      </ul>
      {error && <div className="mt-3"><ErrorBox error={error} /></div>}
      <div className="mt-4 flex justify-end gap-2">
        <Button onClick={onCancel} disabled={saving}>Annulla</Button>
        <Button
          variant="primary"
          disabled={saving}
          onClick={async () => {
            setSaving(true);
            setError(undefined);
            try {
              await onSave(draft);
            } catch (e) {
              setError(e as Error);
              setSaving(false);
            }
          }}
        >
          Salva layout
        </Button>
      </div>
    </Card>
  );
}

export function DashboardPage() {
  const { data, error, loading, reload, setData } = useAsync(() => api.dashboard(), []);
  const { refreshUnread } = useAppState();
  const [editing, setEditing] = useState(false);

  useContextPanel(<SystemSummary activity={data?.recent_activity} />, [data?.recent_activity]);

  useEffect(() => {
    if (data) void refreshUnread();
  }, [data, refreshUnread]);

  async function markRead(id: number) {
    await api.markRead(id);
    await reload();
  }

  return (
    <>
      <PageHeader
        eyebrow="Panoramica"
        title="Dashboard"
        description="Stato reale della piattaforma. Le sezioni che dipendono da moduli non ancora sviluppati lo dichiarano esplicitamente."
        actions={
          data && !editing ? (
            <Button onClick={() => setEditing(true)}>
              <SlidersHorizontal className="size-4" aria-hidden /> Personalizza
            </Button>
          ) : undefined
        }
      />
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data && editing && (
        <LayoutEditor
          layout={data.layout}
          onCancel={() => setEditing(false)}
          onSave={async (l) => {
            const saved = await api.saveLayout(l);
            setData({ ...data, layout: saved });
            setEditing(false);
          }}
        />
      )}
      {data && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {data.layout.order
            .filter((id) => !data.layout.hidden.includes(id))
            .map((id) => (
              <Card
                key={id}
                title={WIDGET_LABELS[id]}
                testId={`widget-${id}`}
                className={WIDE.includes(id) ? 'md:col-span-2 2xl:col-span-3' : ''}
              >
                {renderWidget(id, data, markRead)}
              </Card>
            ))}
        </div>
      )}
    </>
  );
}
