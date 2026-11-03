import { useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Archive, ArchiveRestore, Pencil, Plus, Trash2 } from 'lucide-react';
import { api, ApiError } from '../api/client';
import type { Project, ProjectStatus } from '../api/types';
import { DemoBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

const inputCls =
  'w-full rounded-md border border-ink-700 bg-ink-950 px-3 py-2 text-sm text-paper placeholder:text-steel-500 focus:border-gold-500 focus:outline-none';

export function ProjectForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial?: Pick<Project, 'title' | 'description'>;
  submitLabel: string;
  onSubmit: (data: { title: string; description: string }) => Promise<void>;
  onCancel?: () => void;
}) {
  const [title, setTitle] = useState(initial?.title ?? '');
  const [description, setDescription] = useState(initial?.description ?? '');
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const t = title.trim();
    if (!t) return setError('Il titolo è obbligatorio.');
    if (t.length > 200) return setError('Il titolo non può superare 200 caratteri.');
    if (description.length > 5000) return setError('La descrizione non può superare 5000 caratteri.');
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit({ title: t, description: description.trim() });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-3">
      <label className="block">
        <span className="mb-1 block text-xs text-steel-400">Titolo</span>
        <input className={inputCls} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} placeholder="Es. Il sistema di Bretton Woods" />
      </label>
      <label className="block">
        <span className="mb-1 block text-xs text-steel-400">Descrizione (facoltativa)</span>
        <textarea className={`${inputCls} min-h-20`} value={description} onChange={(e) => setDescription(e.target.value)} maxLength={5000} />
      </label>
      {error && <p role="alert" className="text-sm text-bad">{error}</p>}
      <div className="flex justify-end gap-2">
        {onCancel && <Button onClick={onCancel} disabled={busy}>Annulla</Button>}
        <Button type="submit" variant="primary" disabled={busy}>{submitLabel}</Button>
      </div>
    </form>
  );
}

export function ProjectsPage() {
  const [params, setParams] = useSearchParams();
  const [filter, setFilter] = useState<ProjectStatus>('active');
  const [creating, setCreating] = useState(params.get('new') === '1');
  const [editingId, setEditingId] = useState<number>();
  const [toDelete, setToDelete] = useState<Project>();
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState<Error>();
  const highlight = Number(params.get('id')) || undefined;
  const { data, error, loading, reload } = useAsync(() => api.projects(filter), [filter]);

  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Progetti</h3>
      <p>I progetti raccoglieranno documenti, fonti, appunti e rapporti man mano che i moduli verranno sviluppati.</p>
      <p className="text-xs text-steel-500">L'eliminazione è irreversibile e richiede sempre una conferma esplicita. Ogni operazione è registrata.</p>
    </div>,
    [],
  );

  useEffect(() => {
    if (highlight) document.getElementById(`project-${highlight}`)?.scrollIntoView({ block: 'center' });
  }, [highlight, data]);

  async function run(fn: () => Promise<unknown>) {
    setActionError(undefined);
    try {
      await fn();
      await reload();
    } catch (e) {
      setActionError(e as Error);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Progetti di ricerca"
        actions={!creating && (
          <Button variant="primary" onClick={() => setCreating(true)}>
            <Plus className="size-4" aria-hidden /> Nuovo progetto
          </Button>
        )}
      />
      {creating && (
        <Card title="Nuovo progetto" className="mb-6">
          <ProjectForm
            submitLabel="Crea progetto"
            onCancel={() => {
              setCreating(false);
              params.delete('new');
              setParams(params, { replace: true });
            }}
            onSubmit={async (d) => {
              await api.createProject(d);
              setCreating(false);
              setFilter('active');
              await reload();
            }}
          />
        </Card>
      )}
      <div className="mb-4 flex gap-1" role="tablist" aria-label="Filtro stato">
        {(['active', 'archived'] as const).map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={filter === s}
            onClick={() => setFilter(s)}
            className={`rounded-md px-3 py-1.5 text-sm ${filter === s ? 'bg-ink-800 text-paper' : 'text-steel-400 hover:text-paper'}`}
          >
            {s === 'active' ? 'Attivi' : 'Archiviati'}
          </button>
        ))}
      </div>
      {actionError && <div className="mb-4"><ErrorBox error={actionError} /></div>}
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data && data.length === 0 && (
        <EmptyState>{filter === 'active' ? 'Nessun progetto attivo. Crea il primo progetto.' : 'Nessun progetto archiviato.'}</EmptyState>
      )}
      {data && data.length > 0 && (
        <ul className="space-y-3">
          {data.map((p) => (
            <li
              key={p.id}
              id={`project-${p.id}`}
              className={`rounded-lg border bg-ink-900 p-4 ${highlight === p.id ? 'border-gold-500/70' : 'border-ink-700'}`}
            >
              {editingId === p.id ? (
                <ProjectForm
                  initial={p}
                  submitLabel="Salva"
                  onCancel={() => setEditingId(undefined)}
                  onSubmit={async (d) => {
                    await api.updateProject(p.id, d);
                    setEditingId(undefined);
                    await reload();
                  }}
                />
              ) : (
                <div className="flex flex-wrap items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="min-w-0 break-words font-medium text-paper">{p.title}</h2>
                      {p.is_demo && <DemoBadge />}
                    </div>
                    {p.description && <p className="mt-1 whitespace-pre-line text-sm text-steel-400">{p.description}</p>}
                    <p className="mt-2 text-[11px] text-steel-500">
                      Creato {formatDateTime(p.created_at)} · Aggiornato {formatDateTime(p.updated_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button variant="ghost" className="px-2" onClick={() => setEditingId(p.id)} aria-label={`Modifica ${p.title}`}>
                      <Pencil className="size-4" />
                    </Button>
                    {p.status === 'active' ? (
                      <Button variant="ghost" className="px-2" onClick={() => run(() => api.updateProject(p.id, { status: 'archived' }))} aria-label={`Archivia ${p.title}`}>
                        <Archive className="size-4" />
                      </Button>
                    ) : (
                      <Button variant="ghost" className="px-2" onClick={() => run(() => api.updateProject(p.id, { status: 'active' }))} aria-label={`Ripristina ${p.title}`}>
                        <ArchiveRestore className="size-4" />
                      </Button>
                    )}
                    <Button variant="ghost" className="px-2 hover:text-bad" onClick={() => setToDelete(p)} aria-label={`Elimina ${p.title}`}>
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <ConfirmDialog
        open={!!toDelete}
        title="Eliminare il progetto?"
        message={`«${toDelete?.title ?? ''}» verrà eliminato definitivamente. L'operazione non è reversibile. In alternativa puoi archiviarlo.`}
        confirmLabel="Elimina definitivamente"
        busy={deleting}
        onCancel={() => setToDelete(undefined)}
        onConfirm={async () => {
          if (!toDelete) return;
          setDeleting(true);
          await run(() => api.deleteProject(toDelete.id));
          setDeleting(false);
          setToDelete(undefined);
        }}
      />
    </>
  );
}
