import { useRef, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Download, FileUp, Library, Trash2 } from 'lucide-react';
import { api, ApiError } from '../api/client';
import type { DocumentInfo } from '../api/types';
import { InjectionWarning } from '../components/research';
import { Badge, DemoBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Field, Input, Select } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

const CATEGORY_LABEL = { source_material: 'Materiale di ricerca', user_work: 'Opera personale', dataset: 'Dataset' } as const;

function formatSize(n: number) {
  return n > 1024 * 1024 ? `${(n / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;
}

function UploadForm({ onDone }: { onDone: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [category, setCategory] = useState<keyof typeof CATEGORY_LABEL>('source_material');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();

  async function submit(e: FormEvent) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return setMsg({ ok: false, text: 'Seleziona un file.' });
    const form = new FormData();
    form.append('file', file);
    if (title.trim()) form.append('title', title.trim());
    form.append('author', author.trim());
    form.append('category', category);
    setBusy(true);
    setMsg(undefined);
    try {
      const d = await api.uploadDocument(form);
      setMsg({ ok: true, text: `Importato «${d.title}»: ${d.chunk_count} segmenti indicizzati.` });
      setTitle('');
      setAuthor('');
      if (fileRef.current) fileRef.current.value = '';
      onDone();
    } catch (err) {
      setMsg({ ok: false, text: err instanceof ApiError ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <Field label="File (PDF, DOCX, CSV, XLSX, TXT, MD — max 25 MB)" className="sm:col-span-2">
        <input ref={fileRef} type="file" accept=".pdf,.docx,.csv,.xlsx,.txt,.md" className="block w-full text-sm text-steel-300 file:mr-3 file:rounded-md file:border file:border-ink-600 file:bg-ink-800 file:px-3 file:py-1.5 file:text-paper" />
      </Field>
      <Field label="Titolo (facoltativo)"><Input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={300} /></Field>
      <Field label="Autore (facoltativo)"><Input value={author} onChange={(e) => setAuthor(e.target.value)} maxLength={300} /></Field>
      <Field label="Categoria">
        <Select value={category} onChange={(e) => setCategory(e.target.value as keyof typeof CATEGORY_LABEL)}>
          {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
      </Field>
      <div className="flex items-end justify-end">
        <Button type="submit" variant="primary" disabled={busy}><FileUp className="size-4" aria-hidden /> {busy ? 'Importazione…' : 'Importa'}</Button>
      </div>
      {msg && <p role={msg.ok ? 'status' : 'alert'} className={`text-sm sm:col-span-2 ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
    </form>
  );
}

function GutenbergForm({ onDone }: { onDone: () => void }) {
  const [id, setId] = useState('');
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();
  async function submit(e: FormEvent) {
    e.preventDefault();
    const n = Number(id);
    if (!Number.isInteger(n) || n < 1 || !title.trim()) return setMsg({ ok: false, text: 'Indica ID numerico e titolo.' });
    setBusy(true);
    setMsg(undefined);
    try {
      const d = await api.importGutenberg({ ebook_id: n, title: title.trim(), author: author.trim() });
      setMsg({ ok: true, text: `Importato «${d.title}».` });
      onDone();
    } catch (err) {
      setMsg({ ok: false, text: err instanceof ApiError ? err.message : String(err) });
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Field label="ID ebook" hint="Il numero nell'indirizzo gutenberg.org/ebooks/N"><Input inputMode="numeric" value={id} onChange={(e) => setId(e.target.value)} /></Field>
      <Field label="Titolo"><Input value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
      <Field label="Autore"><Input value={author} onChange={(e) => setAuthor(e.target.value)} /></Field>
      <p className="text-[11px] text-steel-500 sm:col-span-2">Scarica un solo testo su tua richiesta. Lo status di pubblico dominio va verificato nel tuo paese.</p>
      <div className="flex justify-end"><Button type="submit" disabled={busy}>{busy ? 'Download…' : 'Importa da Gutenberg'}</Button></div>
      {msg && <p role={msg.ok ? 'status' : 'alert'} className={`text-sm sm:col-span-3 ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
    </form>
  );
}

export function DocumentsPage() {
  const [category, setCategory] = useState('');
  const { data, error, loading, reload } = useAsync(() => api.documents({ category }), [category]);
  const [toDelete, setToDelete] = useState<DocumentInfo>();
  const [showGutenberg, setShowGutenberg] = useState(false);

  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Archivio</h3>
      <p>Ogni documento viene estratto, suddiviso in segmenti con pagina o collocazione e indicizzato per la ricerca testuale (BM25) e semantica.</p>
      <p>I documenti sono trattati come dati: frasi che sembrano istruzioni per un'AI vengono segnalate e mai eseguite.</p>
      <p className="text-xs text-steel-500">Le opere personali (es. «L'Atlante del Digitale») vanno importate con categoria «Opera personale».</p>
    </div>,
    [],
  );

  return (
    <>
      <PageHeader eyebrow="Archivio" title="Documenti" description="Importazione, estrazione del testo e indicizzazione per la ricerca nell'archivio." />
      <Card title="Importa documento" className="mb-4"><UploadForm onDone={reload} /></Card>
      <div className="mb-6">
        <button className="text-xs text-gold-300 hover:underline" onClick={() => setShowGutenberg((v) => !v)}>
          <Library className="mr-1 inline size-3.5" aria-hidden />{showGutenberg ? 'Nascondi' : 'Importa da Project Gutenberg'}
        </button>
        {showGutenberg && <Card className="mt-2"><GutenbergForm onDone={reload} /></Card>}
      </div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Select aria-label="Filtra per categoria" value={category} onChange={(e) => setCategory(e.target.value)} className="max-w-60">
          <option value="">Tutte le categorie</option>
          {Object.entries(CATEGORY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
        <Link to="/research" className="text-sm text-gold-300 hover:underline">Interroga l'archivio →</Link>
      </div>
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data?.length === 0 && <EmptyState>Nessun documento importato.</EmptyState>}
      {data && data.length > 0 && (
        <ul className="space-y-2">
          {data.map((d) => (
            <li key={d.id} className="flex flex-wrap items-start gap-3 rounded-lg border border-ink-700 bg-ink-900 p-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Link to={`/documents/${d.id}`} className="font-medium text-paper hover:text-gold-300">{d.title}</Link>
                  <Badge>{d.kind.toUpperCase()}</Badge>
                  <Badge tone={d.category === 'user_work' ? 'gold' : 'neutral'}>{CATEGORY_LABEL[d.category]}</Badge>
                  {d.is_demo && <DemoBadge />}
                  {d.source_id === null && <Badge tone="warn">Senza scheda bibliografica</Badge>}
                </div>
                <p className="mt-1 text-xs text-steel-500">
                  {d.author && `${d.author} · `}{d.page_count ? `${d.page_count} pagine · ` : ''}{d.chunk_count} segmenti · {formatSize(d.size_bytes)} · {formatDateTime(d.created_at)}
                </p>
                {d.flagged_chunks > 0 && <InjectionWarning />}
              </div>
              <a href={api.documentFileUrl(d.id)} className="rounded p-1.5 text-steel-400 hover:bg-ink-800 hover:text-paper" aria-label={`Scarica ${d.title}`}><Download className="size-4" /></a>
              <Button variant="ghost" className="px-2 hover:text-bad" onClick={() => setToDelete(d)} aria-label={`Elimina ${d.title}`}><Trash2 className="size-4" /></Button>
            </li>
          ))}
        </ul>
      )}
      <ConfirmDialog
        open={!!toDelete}
        title="Eliminare il documento?"
        message={`«${toDelete?.title ?? ''}» e il suo indice verranno eliminati definitivamente dall'archivio.`}
        confirmLabel="Elimina definitivamente"
        onCancel={() => setToDelete(undefined)}
        onConfirm={async () => {
          if (toDelete) await api.deleteDocument(toDelete.id);
          setToDelete(undefined);
          await reload();
        }}
      />
    </>
  );
}

export function DocumentDetailPage() {
  const id = Number(useParams().documentId);
  const doc = useAsync(() => api.document(id), [id]);
  const sources = useAsync(() => api.sources(), []);
  const [offset, setOffset] = useState(0);
  const chunks = useAsync(() => api.chunks(id, offset, 30), [id, offset]);
  const [saveError, setSaveError] = useState<Error>();

  if (doc.loading && !doc.data) return <Loading />;
  if (doc.error) return <ErrorBox error={doc.error} onRetry={doc.reload} />;
  const d = doc.data!;
  return (
    <>
      <PageHeader eyebrow="Documento" title={d.title} description={`${d.filename} · ${d.kind.toUpperCase()} · ${d.chunk_count} segmenti`} />
      <Card title="Collegamento bibliografico" className="mb-4">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Scheda bibliografica" className="min-w-60 flex-1">
            <Select
              value={d.source_id ?? ''}
              onChange={async (e) => {
                setSaveError(undefined);
                try {
                  doc.setData(await api.updateDocument(d.id, { source_id: e.target.value ? Number(e.target.value) : null }));
                } catch (err) {
                  setSaveError(err as Error);
                }
              }}
            >
              <option value="">— nessuna (le citazioni useranno solo titolo e autore) —</option>
              {sources.data?.map((s) => <option key={s.id} value={s.id}>{s.citation.slice(0, 120)}</option>)}
            </Select>
          </Field>
          <Link to="/bibliography" className="text-xs text-gold-300 hover:underline">Gestisci bibliografia</Link>
        </div>
        {d.license_note && <p className="mt-3 text-xs text-steel-500">Licenza: {d.license_note}</p>}
        {saveError && <div className="mt-2"><ErrorBox error={saveError} /></div>}
      </Card>
      <Card title="Testo estratto">
        {chunks.loading && <Loading />}
        {chunks.error && <ErrorBox error={chunks.error} />}
        <ol className="space-y-3">
          {chunks.data?.map((c) => (
            <li key={c.id} className="border-l border-ink-600 pl-3">
              <p className="text-[11px] text-steel-500">#{c.ordinal + 1} · {c.locator || '—'} {c.injection_flag && <InjectionWarning />}</p>
              <p className="whitespace-pre-line text-sm text-steel-300">{c.text}</p>
            </li>
          ))}
        </ol>
        <div className="mt-4 flex justify-between">
          <Button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 30))}>Precedenti</Button>
          <Button disabled={(chunks.data?.length ?? 0) < 30} onClick={() => setOffset(offset + 30)}>Successivi</Button>
        </div>
      </Card>
    </>
  );
}
