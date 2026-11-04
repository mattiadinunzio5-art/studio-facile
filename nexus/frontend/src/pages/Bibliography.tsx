import { useState, type FormEvent } from 'react';
import { BadgeCheck, Pencil, Plus, Trash2 } from 'lucide-react';
import { api, ApiError } from '../api/client';
import type { Source, SourceInput } from '../api/types';
import { VERIFICATION } from '../components/research';
import { Badge, DemoBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Field, Input, Select, Textarea } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

const TYPES = { book: 'Libro', article: 'Articolo', chapter: 'Capitolo', web: 'Pagina web', dataset: 'Dataset', archive: 'Documento d\'archivio', document: 'Documento', other: 'Altro' };

const empty: Partial<SourceInput> = { source_type: 'book', title: '', authors: [], year: null, publisher: '', container: '', pages: '', doi: '', isbn: '', url: '', accessed_at: '', notes: '' };

export function SourceForm({ initial, onSubmit, onCancel }: { initial?: Partial<SourceInput>; onSubmit: (d: Partial<SourceInput>) => Promise<void>; onCancel: () => void }) {
  const [f, setF] = useState<Partial<SourceInput>>({ ...empty, ...initial });
  const [authors, setAuthors] = useState((initial?.authors ?? []).join('; '));
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const set = (k: keyof SourceInput) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!f.title?.trim()) return setError('Il titolo è obbligatorio.');
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit({ ...f, year: f.year ? Number(f.year) : null, authors: authors.split(';').map((a) => a.trim()).filter(Boolean) });
    } catch (err) {
      const e2 = err as ApiError;
      const details = Array.isArray(e2.details) ? (e2.details as { msg: string }[]).map((d) => d.msg).join('; ') : '';
      setError(`${e2.message}${details ? ` ${details}` : ''}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid grid-cols-1 gap-3 sm:grid-cols-2" noValidate>
      <Field label="Tipo"><Select value={f.source_type} onChange={set('source_type')}>{Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>
      <Field label="Anno"><Input inputMode="numeric" value={f.year ?? ''} onChange={set('year')} /></Field>
      <Field label="Titolo" className="sm:col-span-2"><Input value={f.title} onChange={set('title')} maxLength={500} /></Field>
      <Field label="Autori (separati da ;)" className="sm:col-span-2"><Input value={authors} onChange={(e) => setAuthors(e.target.value)} /></Field>
      <Field label="Editore"><Input value={f.publisher} onChange={set('publisher')} /></Field>
      <Field label="Rivista / volume"><Input value={f.container} onChange={set('container')} /></Field>
      <Field label="Pagine"><Input value={f.pages} onChange={set('pages')} /></Field>
      <Field label="DOI" hint="Verificabile su Crossref"><Input value={f.doi} onChange={set('doi')} placeholder="10.xxxx/…" /></Field>
      <Field label="ISBN"><Input value={f.isbn} onChange={set('isbn')} /></Field>
      <Field label="URL"><Input value={f.url} onChange={set('url')} placeholder="https://…" /></Field>
      <Field label="Data di consultazione"><Input type="date" value={f.accessed_at} onChange={set('accessed_at')} /></Field>
      <Field label="Note" className="sm:col-span-2"><Textarea value={f.notes} onChange={set('notes')} /></Field>
      {error && <p role="alert" className="text-sm text-bad sm:col-span-2">{error}</p>}
      <div className="flex justify-end gap-2 sm:col-span-2">
        <Button onClick={onCancel} disabled={busy}>Annulla</Button>
        <Button type="submit" variant="primary" disabled={busy}>Salva fonte</Button>
      </div>
    </form>
  );
}

export function BibliographyPage() {
  const { data, error, loading, reload } = useAsync(() => api.sources(), []);
  const [editing, setEditing] = useState<Source | 'new'>();
  const [toDelete, setToDelete] = useState<Source>();
  const [actionError, setActionError] = useState<Error>();

  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Citazioni verificabili</h3>
      <p>NEXUS non crea fonti in automatico: ogni scheda è inserita da te. Ogni modifica azzera la verifica.</p>
      <p><strong className="text-paper">Verifica su registro</strong>: controlla il DOI su Crossref e segnala discrepanze di titolo o anno.</p>
      <p><strong className="text-paper">Verifica manuale</strong>: dichiari di aver controllato la fonte originale.</p>
    </div>,
    [],
  );

  async function act(fn: () => Promise<unknown>) {
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
      <PageHeader eyebrow="Archivio" title="Bibliografia" actions={!editing && <Button variant="primary" onClick={() => setEditing('new')}><Plus className="size-4" aria-hidden /> Nuova fonte</Button>} />
      {editing && (
        <Card title={editing === 'new' ? 'Nuova fonte' : 'Modifica fonte'} className="mb-6">
          <SourceForm
            initial={editing === 'new' ? undefined : editing}
            onCancel={() => setEditing(undefined)}
            onSubmit={async (d) => {
              if (editing === 'new') await api.createSource(d);
              else await api.updateSource(editing.id, d);
              setEditing(undefined);
              await reload();
            }}
          />
        </Card>
      )}
      {actionError && <div className="mb-4"><ErrorBox error={actionError} /></div>}
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data?.length === 0 && <EmptyState>Nessuna fonte registrata.</EmptyState>}
      <ul className="space-y-2">
        {data?.map((s) => (
          <li key={s.id} className="rounded-lg border border-ink-700 bg-ink-900 p-3">
            <div className="flex flex-wrap items-start gap-2">
              <p className="min-w-0 flex-1 text-sm text-paper">{s.citation}</p>
              <Badge tone={VERIFICATION[s.verification_status].tone}>{VERIFICATION[s.verification_status].label}</Badge>
              {s.is_demo && <DemoBadge />}
            </div>
            {s.verification_note && <p className="mt-1 text-xs text-steel-500">{s.verification_note}</p>}
            <div className="mt-2 flex flex-wrap gap-1">
              <Button variant="ghost" className="text-xs" onClick={() => act(() => api.verifySource(s.id, 'user'))}><BadgeCheck className="size-3.5" aria-hidden /> Ho verificato l'originale</Button>
              {s.doi && <Button variant="ghost" className="text-xs" onClick={() => act(() => api.verifySource(s.id, 'registry'))}>Verifica DOI su Crossref</Button>}
              <Button variant="ghost" className="px-2" onClick={() => setEditing(s)} aria-label={`Modifica ${s.title}`}><Pencil className="size-4" /></Button>
              <Button variant="ghost" className="px-2 hover:text-bad" onClick={() => setToDelete(s)} aria-label={`Elimina ${s.title}`}><Trash2 className="size-4" /></Button>
            </div>
          </li>
        ))}
      </ul>
      <ConfirmDialog
        open={!!toDelete}
        title="Eliminare la fonte?"
        message="I documenti e le relazioni collegati perderanno il riferimento a questa fonte."
        confirmLabel="Elimina"
        onCancel={() => setToDelete(undefined)}
        onConfirm={async () => {
          if (toDelete) await act(() => api.deleteSource(toDelete.id));
          setToDelete(undefined);
        }}
      />
    </>
  );
}
