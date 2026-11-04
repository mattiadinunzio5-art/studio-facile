import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, Network, Pencil, Plus, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import {
  CATEGORIES, KNOWLEDGE_KINDS, PROVENANCE, RELATION_TYPES, RELIABILITY,
  type Category, type EventInput, type HistoricalEvent, type Reliability,
} from '../api/types';
import { VERIFICATION } from '../components/research';
import { Badge, DemoBadge, type BadgeTone } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Field, Input, Select, Textarea } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { errorText, fromList, toInt, toList } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

export const RELIABILITY_TONE: Record<Reliability, BadgeTone> = { established: 'ok', probable: 'gold', disputed: 'warn', unverified: 'neutral' };

const blank: EventInput = {
  title: '', start_year: 1900, start_month: null, start_day: null, end_year: null, end_month: null, end_day: null, period: '', region: '',
  countries: [], categories: [], description: '', causes: '', consequences: '', people: [], institutions: [], economic_implications: '',
  reliability: 'unverified', reliability_note: '',
};

export function EventForm({ initial, onSubmit, onCancel }: { initial?: EventInput; onSubmit: (d: EventInput) => Promise<void>; onCancel: () => void }) {
  const init = initial ?? blank;
  const [f, setF] = useState<Record<string, string>>({
    title: init.title, start_year: String(init.start_year ?? ''), start_month: String(init.start_month ?? ''), start_day: String(init.start_day ?? ''),
    end_year: String(init.end_year ?? ''), end_month: String(init.end_month ?? ''), end_day: String(init.end_day ?? ''),
    period: init.period, region: init.region, countries: fromList(init.countries), people: fromList(init.people), institutions: fromList(init.institutions),
    description: init.description, causes: init.causes, consequences: init.consequences, economic_implications: init.economic_implications,
    reliability: init.reliability, reliability_note: init.reliability_note,
  });
  const [cats, setCats] = useState<Category[]>(init.categories);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const bind = (k: string) => ({ value: f[k], onChange: (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value }) });

  async function submit(e: FormEvent) {
    e.preventDefault();
    const start = toInt(f.start_year);
    if (!f.title.trim()) return setError('Il titolo è obbligatorio.');
    if (start === null) return setError("L'anno iniziale è obbligatorio (negativo per a.C.).");
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit({
        title: f.title.trim(), start_year: start, start_month: toInt(f.start_month), start_day: toInt(f.start_day),
        end_year: toInt(f.end_year), end_month: toInt(f.end_month), end_day: toInt(f.end_day), period: f.period, region: f.region,
        countries: toList(f.countries), categories: cats, description: f.description, causes: f.causes, consequences: f.consequences,
        people: toList(f.people), institutions: toList(f.institutions), economic_implications: f.economic_implications,
        reliability: f.reliability as Reliability, reliability_note: f.reliability_note,
      });
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="grid grid-cols-1 gap-3 sm:grid-cols-6">
      <Field label="Titolo" className="sm:col-span-6"><Input {...bind('title')} maxLength={300} /></Field>
      <Field label="Anno inizio" hint="Negativo = a.C." className="sm:col-span-2"><Input inputMode="numeric" {...bind('start_year')} /></Field>
      <Field label="Mese"><Input inputMode="numeric" {...bind('start_month')} /></Field>
      <Field label="Giorno"><Input inputMode="numeric" {...bind('start_day')} /></Field>
      <div className="hidden sm:col-span-2 sm:block" />
      <Field label="Anno fine" className="sm:col-span-2"><Input inputMode="numeric" {...bind('end_year')} /></Field>
      <Field label="Mese"><Input inputMode="numeric" {...bind('end_month')} /></Field>
      <Field label="Giorno"><Input inputMode="numeric" {...bind('end_day')} /></Field>
      <div className="hidden sm:col-span-2 sm:block" />
      <Field label="Periodo storico" className="sm:col-span-2"><Input {...bind('period')} /></Field>
      <Field label="Area geografica" className="sm:col-span-2"><Input {...bind('region')} /></Field>
      <Field label="Paesi (separati da virgola)" className="sm:col-span-2"><Input {...bind('countries')} /></Field>
      <fieldset className="sm:col-span-6">
        <legend className="mb-1 text-xs text-steel-400">Categorie</legend>
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          {(Object.keys(CATEGORIES) as Category[]).map((c) => (
            <label key={c} className="flex items-center gap-1.5 text-sm text-steel-300">
              <input type="checkbox" checked={cats.includes(c)} onChange={() => setCats(cats.includes(c) ? cats.filter((x) => x !== c) : [...cats, c])} />
              {CATEGORIES[c]}
            </label>
          ))}
        </div>
      </fieldset>
      <Field label="Descrizione" className="sm:col-span-6"><Textarea {...bind('description')} /></Field>
      <Field label="Cause" className="sm:col-span-3"><Textarea {...bind('causes')} /></Field>
      <Field label="Conseguenze" hint="Considerate conoscenza retrospettiva nella Time Machine" className="sm:col-span-3"><Textarea {...bind('consequences')} /></Field>
      <Field label="Personaggi coinvolti" className="sm:col-span-3"><Input {...bind('people')} /></Field>
      <Field label="Istituzioni coinvolte" className="sm:col-span-3"><Input {...bind('institutions')} /></Field>
      <Field label="Implicazioni economiche" className="sm:col-span-6"><Textarea {...bind('economic_implications')} /></Field>
      <Field label="Attendibilità" className="sm:col-span-2">
        <Select {...bind('reliability')}>{Object.entries(RELIABILITY).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select>
      </Field>
      <Field label="Nota sull'attendibilità" className="sm:col-span-4"><Input {...bind('reliability_note')} /></Field>
      {error && <p role="alert" className="text-sm text-bad sm:col-span-6">{error}</p>}
      <div className="flex justify-end gap-2 sm:col-span-6">
        <Button onClick={onCancel} disabled={busy}>Annulla</Button>
        <Button type="submit" variant="primary" disabled={busy}>Salva evento</Button>
      </div>
    </form>
  );
}

export function EventsPage() {
  const [filters, setFilters] = useState({ q: '', category: '', country: '', from_year: '', to_year: '' });
  const { data, error, loading, reload } = useAsync(
    () => api.events({ ...filters, from_year: toInt(filters.from_year) ?? undefined, to_year: toInt(filters.to_year) ?? undefined }),
    [filters],
  );
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const set = (k: keyof typeof filters) => (e: { target: { value: string } }) => setFilters({ ...filters, [k]: e.target.value });

  return (
    <>
      <PageHeader eyebrow="Modulo A" title="Historical Intelligence" description="Archivio strutturato di eventi storici con cause, conseguenze, fonti e attendibilità."
        actions={!creating && <Button variant="primary" onClick={() => setCreating(true)}><Plus className="size-4" aria-hidden /> Nuovo evento</Button>} />
      {creating && (
        <Card title="Nuovo evento" className="mb-6">
          <EventForm onCancel={() => setCreating(false)} onSubmit={async (d) => { const e = await api.createEvent(d); navigate(`/history/events/${e.id}`); }} />
        </Card>
      )}
      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        <Input aria-label="Cerca" placeholder="Cerca…" value={filters.q} onChange={set('q')} className="col-span-2 md:col-span-1" />
        <Select aria-label="Categoria" value={filters.category} onChange={set('category')}>
          <option value="">Tutte le categorie</option>
          {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
        <Input aria-label="Paese" placeholder="Paese o area" value={filters.country} onChange={set('country')} />
        <Input aria-label="Dall'anno" placeholder="Dall'anno" inputMode="numeric" value={filters.from_year} onChange={set('from_year')} />
        <Input aria-label="All'anno" placeholder="All'anno" inputMode="numeric" value={filters.to_year} onChange={set('to_year')} />
      </div>
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data?.length === 0 && <EmptyState>Nessun evento corrispondente.</EmptyState>}
      <ul className="space-y-2">
        {data?.map((e) => (
          <li key={e.id}>
            <Link to={`/history/events/${e.id}`} className="block rounded-lg border border-ink-700 bg-ink-900 p-3 hover:border-gold-500/60">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-gold-300">{e.date_label}</span>
                <span className="font-medium text-paper">{e.title}</span>
                <Badge tone={RELIABILITY_TONE[e.reliability]}>{RELIABILITY[e.reliability]}</Badge>
                {e.is_demo && <DemoBadge />}
                {e.source_warning && <AlertTriangle className="size-3.5 text-warn" aria-label={e.source_warning} />}
              </div>
              <p className="mt-1 text-xs text-steel-500">{[e.countries.join(', '), e.categories.map((c) => CATEGORIES[c]).join(', ')].filter(Boolean).join(' · ')}</p>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

function Section({ title, text }: { title: string; text: string }) {
  if (!text) return null;
  return (
    <div>
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">{title}</h3>
      <p className="mt-1 whitespace-pre-line text-sm text-steel-300">{text}</p>
    </div>
  );
}

export function EventDetailPage() {
  const id = Number(useParams().eventId);
  const ev = useAsync(() => api.event(id), [id]);
  const sources = useAsync(() => api.sources(), []);
  const others = useAsync(() => api.events(), []);
  const rels = useAsync(async () => (ev.data?.entity_id ? api.entityRelations(ev.data.entity_id) : []), [ev.data?.entity_id]);
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [err, setErr] = useState<string>();
  const [srcSel, setSrcSel] = useState('');
  const [srcPages, setSrcPages] = useState('');
  const [k, setK] = useState({ content: '', known_since_year: '', kind: 'contemporary' });
  const [link, setLink] = useState({ target: '', relation_type: 'caused', provenance: 'user_hypothesis', source_id: '' });
  const navigate = useNavigate();

  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Informazioni datate</h3>
      <p>Registra ciò che era noto e quando: la Time Machine mostra solo le informazioni note alla data selezionata.</p>
      <p className="text-xs text-steel-500">Le relazioni con altri eventi vanno nel Knowledge Graph: servono una fonte oppure l'etichetta di ipotesi.</p>
    </div>,
    [],
  );

  async function act(fn: () => Promise<HistoricalEvent | unknown>) {
    setErr(undefined);
    try {
      const r = await fn();
      if (r && typeof r === 'object' && 'knowledge' in r) ev.setData(r as HistoricalEvent);
      await rels.reload();
    } catch (e) {
      setErr(errorText(e));
    }
  }

  if (ev.loading && !ev.data) return <Loading />;
  if (ev.error) return <ErrorBox error={ev.error} onRetry={ev.reload} />;
  const e = ev.data!;
  const titleOf = new Map((others.data ?? []).map((o) => [o.entity_id, o.title]));

  return (
    <>
      <PageHeader eyebrow={<Link to="/history" className="hover:underline">Historical Intelligence</Link>} title={e.title} description={e.date_label}
        actions={!editing && (
          <>
            <Link to={`/time-machine?event=${e.id}&year=${e.start_year}`} className="inline-flex items-center rounded-md border border-ink-600 px-3 py-1.5 text-sm text-paper hover:bg-ink-800">Apri nella Time Machine</Link>
            {e.entity_id && <Link to={`/graph?focus=${e.entity_id}`} className="inline-flex items-center gap-1 rounded-md border border-ink-600 px-3 py-1.5 text-sm text-paper hover:bg-ink-800"><Network className="size-4" aria-hidden /> Grafo</Link>}
            <Button onClick={() => setEditing(true)}><Pencil className="size-4" aria-hidden /> Modifica</Button>
            <Button onClick={() => setDeleting(true)} aria-label="Elimina evento"><Trash2 className="size-4" /></Button>
          </>
        )} />
      {editing ? (
        <Card title="Modifica evento"><EventForm initial={e} onCancel={() => setEditing(false)} onSubmit={async (d) => { ev.setData(await api.updateEvent(e.id, d)); setEditing(false); }} /></Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Card title="Scheda" className="lg:col-span-2">
            <div className="mb-3 flex flex-wrap gap-1.5">
              <Badge tone={RELIABILITY_TONE[e.reliability]}>Attendibilità: {RELIABILITY[e.reliability]}</Badge>
              {e.categories.map((c) => <Badge key={c}>{CATEGORIES[c]}</Badge>)}
              {e.is_demo && <DemoBadge />}
            </div>
            {e.source_warning && <p className="mb-3 flex items-start gap-2 text-sm text-warn"><AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />{e.source_warning}</p>}
            <div className="space-y-4">
              <p className="text-xs text-steel-500">{[e.period, e.region, e.countries.join(', ')].filter(Boolean).join(' · ')}</p>
              <Section title="Descrizione" text={e.description} />
              <Section title="Cause" text={e.causes} />
              <Section title="Conseguenze" text={e.consequences} />
              <Section title="Implicazioni economiche" text={e.economic_implications} />
              <Section title="Personaggi" text={e.people.join(', ')} />
              <Section title="Istituzioni" text={e.institutions.join(', ')} />
              <Section title="Nota sull'attendibilità" text={e.reliability_note} />
            </div>
          </Card>
          <div className="space-y-4">
            <Card title="Fonti">
              {e.sources.length === 0 && <EmptyState>Nessuna fonte collegata.</EmptyState>}
              <ul className="space-y-2 text-sm">
                {e.sources.map((s) => (
                  <li key={s.source_id}>
                    <p className="text-steel-300">{s.citation}{s.pages && ` — pp. ${s.pages}`}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <Badge tone={VERIFICATION[s.verification_status].tone}>{VERIFICATION[s.verification_status].label}</Badge>
                      <button className="text-[11px] text-steel-500 hover:text-bad" onClick={() => act(() => api.unlinkEventSource(e.id, s.source_id))}>Scollega</button>
                    </div>
                  </li>
                ))}
              </ul>
              <div className="mt-3 space-y-2">
                <Select aria-label="Fonte da collegare" value={srcSel} onChange={(x) => setSrcSel(x.target.value)}>
                  <option value="">Seleziona una fonte…</option>
                  {sources.data?.map((s) => <option key={s.id} value={s.id}>{s.citation.slice(0, 90)}</option>)}
                </Select>
                <div className="flex gap-2">
                  <Input aria-label="Pagine" placeholder="Pagine" value={srcPages} onChange={(x) => setSrcPages(x.target.value)} />
                  <Button disabled={!srcSel} onClick={() => act(() => api.linkEventSource(e.id, Number(srcSel), srcPages))}>Collega</Button>
                </div>
                <Link to="/bibliography" className="text-xs text-gold-300 hover:underline">Nuova fonte in bibliografia</Link>
              </div>
            </Card>
            <Card title="Informazioni datate">
              <ul className="space-y-2 text-sm">
                {e.knowledge.map((ki) => (
                  <li key={ki.id} className="border-l border-ink-600 pl-2">
                    <p className="text-[11px] text-steel-500">Nota dal {ki.known_since_year} · {KNOWLEDGE_KINDS[ki.kind]} <button className="ml-2 hover:text-bad" onClick={() => act(() => api.deleteKnowledge(e.id, ki.id))}>rimuovi</button></p>
                    <p className="text-steel-300">{ki.content}</p>
                  </li>
                ))}
              </ul>
              <div className="mt-3 space-y-2">
                <Textarea aria-label="Informazione" placeholder="Cosa era noto…" value={k.content} onChange={(x) => setK({ ...k, content: x.target.value })} />
                <div className="flex gap-2">
                  <Input aria-label="Nota dall'anno" placeholder="Anno" inputMode="numeric" value={k.known_since_year} onChange={(x) => setK({ ...k, known_since_year: x.target.value })} />
                  <Select aria-label="Tipo" value={k.kind} onChange={(x) => setK({ ...k, kind: x.target.value })}>
                    {Object.entries(KNOWLEDGE_KINDS).map(([kk, v]) => <option key={kk} value={kk}>{v}</option>)}
                  </Select>
                </div>
                <Button disabled={!k.content.trim() || toInt(k.known_since_year) === null}
                  onClick={() => act(async () => { const r = await api.addKnowledge(e.id, { content: k.content, known_since_year: toInt(k.known_since_year)!, kind: k.kind as never, source_id: null }); setK({ ...k, content: '' }); return r; })}>
                  Aggiungi
                </Button>
              </div>
            </Card>
            <Card title="Collegamenti">
              <ul className="space-y-1.5 text-sm">
                {rels.data?.map((r) => (
                  <li key={r.id} className="text-steel-300">
                    {r.source_entity_id === e.entity_id ? '' : `${titleOf.get(r.source_entity_id) ?? 'Entità'} → `}
                    <span className="text-gold-300">{RELATION_TYPES[r.relation_type]}</span>
                    {r.source_entity_id === e.entity_id ? ` → ${titleOf.get(r.target_entity_id) ?? 'entità'}` : ' questo evento'}
                    <span className="block text-[11px] text-steel-500">{PROVENANCE[r.provenance]} · {r.evidence_label}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-3 space-y-2">
                <Select aria-label="Evento collegato" value={link.target} onChange={(x) => setLink({ ...link, target: x.target.value })}>
                  <option value="">Collega a evento…</option>
                  {others.data?.filter((o) => o.id !== e.id).map((o) => <option key={o.id} value={o.id}>{o.date_label} · {o.title}</option>)}
                </Select>
                <Select aria-label="Tipo di relazione" value={link.relation_type} onChange={(x) => setLink({ ...link, relation_type: x.target.value })}>
                  {Object.entries(RELATION_TYPES).map(([kk, v]) => <option key={kk} value={kk}>{v}</option>)}
                </Select>
                <Select aria-label="Provenienza" value={link.provenance} onChange={(x) => setLink({ ...link, provenance: x.target.value })}>
                  <option value="user_hypothesis">{PROVENANCE.user_hypothesis}</option>
                  <option value="sourced">{PROVENANCE.sourced} (richiede fonte)</option>
                </Select>
                {link.provenance === 'sourced' && (
                  <Select aria-label="Fonte della relazione" value={link.source_id} onChange={(x) => setLink({ ...link, source_id: x.target.value })}>
                    <option value="">Seleziona fonte…</option>
                    {sources.data?.map((s) => <option key={s.id} value={s.id}>{s.citation.slice(0, 90)}</option>)}
                  </Select>
                )}
                <Button disabled={!link.target} onClick={() => act(() => api.linkEvents(e.id, {
                  target_event_id: Number(link.target), relation_type: link.relation_type, provenance: link.provenance,
                  source_id: link.source_id ? Number(link.source_id) : null,
                }))}>Collega</Button>
              </div>
            </Card>
            {err && <ErrorBox error={new Error(err)} />}
          </div>
        </div>
      )}
      <ConfirmDialog open={deleting} title="Eliminare l'evento?" message="L'evento, le informazioni datate e le sue relazioni nel grafo verranno eliminati definitivamente."
        confirmLabel="Elimina definitivamente" onCancel={() => setDeleting(false)}
        onConfirm={async () => { await api.deleteEvent(e.id); navigate('/history'); }} />
    </>
  );
}
