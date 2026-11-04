import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, ArrowDown, ArrowUp, CheckCircle2, FileDown, Plus, Quote, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import type { Embed, Report, ReportCheck, ReportSection } from '../api/types';
import { VERIFICATION } from '../components/research';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Field, Input, Select, Textarea } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

export function StudioPage() {
  const reports = useAsync(() => api.reports(), []);
  const notes = useAsync(() => api.notes(), []);
  const runs = useAsync(() => api.runs(), []);
  const projects = useAsync(() => api.projects('active'), []);
  const [form, setForm] = useState({ title: '', author: '', project_id: '' });
  const [note, setNote] = useState({ title: '', body: '' });
  const [err, setErr] = useState<string>();
  const navigate = useNavigate();
  const approvedRuns = runs.data?.filter((r) => r.status === 'approved') ?? [];

  return (
    <>
      <PageHeader eyebrow="Modulo G" title="Research Studio" description="Rapporti professionali con citazioni verificabili, grafici, tabelle ed esportazione PDF/DOCX." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card title="Nuovo rapporto">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <Field label="Titolo" className="sm:col-span-3"><Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
              <Field label="Autore"><Input value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} /></Field>
              <Field label="Progetto"><Select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })}><option value="">—</option>{projects.data?.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}</Select></Field>
              <div className="flex items-end"><Button variant="primary" disabled={!form.title.trim()} onClick={async () => {
                setErr(undefined);
                try { const r = await api.createReport({ title: form.title.trim(), author: form.author.trim(), project_id: form.project_id ? Number(form.project_id) : null }); navigate(`/studio/reports/${r.id}`); } catch (e) { setErr(errorText(e)); }
              }}><Plus className="size-4" aria-hidden /> Crea</Button></div>
            </div>
            {approvedRuns.length > 0 && (
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <Field label="Oppure parti da una ricerca approvata" className="min-w-64 flex-1">
                  <Select id="from-run" defaultValue=""><option value="">Seleziona…</option>{approvedRuns.map((r) => <option key={r.id} value={r.id}>#{r.id} {r.question.slice(0, 90)}</option>)}</Select>
                </Field>
                <Button onClick={async () => {
                  const v = (document.getElementById('from-run') as HTMLSelectElement).value;
                  if (!v) return;
                  try { const r = await api.reportFromRun(Number(v)); navigate(`/studio/reports/${r.id}`); } catch (e) { setErr(errorText(e)); }
                }}>Genera bozza</Button>
              </div>
            )}
            {err && <p role="alert" className="mt-2 text-sm text-bad">{err}</p>}
          </Card>
          <Card title="Rapporti">
            {reports.loading && !reports.data && <Loading />}
            {reports.data?.length === 0 && <EmptyState>Nessun rapporto.</EmptyState>}
            <ul className="space-y-2">
              {reports.data?.map((r) => (
                <li key={r.id}><Link to={`/studio/reports/${r.id}`} className="flex flex-wrap items-center gap-2 rounded-md border border-ink-700 p-3 hover:border-gold-500/60">
                  <span className="min-w-0 flex-1 truncate text-paper">{r.title}</span>
                  <Badge tone={r.status === 'approved' ? 'ok' : 'warn'}>{r.status === 'approved' ? 'Approvato' : 'Bozza'}</Badge>
                  <span className="text-[11px] text-steel-500">{formatDateTime(r.updated_at)}</span>
                </Link></li>
              ))}
            </ul>
          </Card>
        </div>
        <Card title="Appunti">
          <div className="space-y-2">
            <Input aria-label="Titolo appunto" placeholder="Titolo" value={note.title} onChange={(e) => setNote({ ...note, title: e.target.value })} />
            <Textarea aria-label="Testo appunto" placeholder="Appunto…" value={note.body} onChange={(e) => setNote({ ...note, body: e.target.value })} />
            <Button disabled={!note.title.trim()} onClick={async () => { await api.createNote(note); setNote({ title: '', body: '' }); await notes.reload(); }}>Salva appunto</Button>
          </div>
          <ul className="mt-4 space-y-3">
            {notes.data?.map((n) => (
              <li key={n.id} className="border-l border-ink-600 pl-3 text-sm">
                <p className="font-medium text-paper">{n.title} <button className="ml-1 text-[11px] text-steel-500 hover:text-bad" onClick={async () => { await api.deleteNote(n.id); await notes.reload(); }} aria-label={`Elimina ${n.title}`}>elimina</button></p>
                <p className="whitespace-pre-line text-steel-300">{n.body}</p>
                <p className="text-[11px] text-steel-500">{formatDateTime(n.updated_at)}</p>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}

function EmbedEditor({ embeds, onChange }: { embeds: Embed[]; onChange: (e: Embed[]) => void }) {
  const series = useAsync(() => api.seriesList(), []);
  const sims = useAsync(() => api.simulations(), []);
  const [tableCsv, setTableCsv] = useState('');
  return (
    <div className="mt-2 space-y-2 rounded-md border border-ink-700 p-2">
      <p className="text-[11px] text-steel-500">Grafici e tabelle della sezione</p>
      {embeds.map((e, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-steel-300">
          <Badge>{e.type === 'series' ? 'Grafico serie' : e.type === 'simulation' ? 'Grafico simulazione' : 'Tabella'}</Badge>
          <span className="min-w-0 flex-1 truncate">{e.type === 'series' ? series.data?.find((s) => s.id === e.series_id)?.name ?? `serie ${e.series_id}` : e.type === 'simulation' ? sims.data?.find((s) => s.id === e.simulation_id)?.title ?? `simulazione ${e.simulation_id}` : `${e.columns.join(', ')} (${e.rows.length} righe)`}</span>
          <button className="text-steel-500 hover:text-bad" onClick={() => onChange(embeds.filter((_, j) => j !== i))} aria-label="Rimuovi">rimuovi</button>
        </div>
      ))}
      <div className="flex flex-wrap gap-2">
        <Select aria-label="Aggiungi grafico di una serie" className="w-auto py-1 text-xs" value="" onChange={(e) => e.target.value && onChange([...embeds, { type: 'series', series_id: Number(e.target.value), caption: '' }])}>
          <option value="">+ grafico serie…</option>{series.data?.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </Select>
        <Select aria-label="Aggiungi grafico di una simulazione" className="w-auto py-1 text-xs" value="" onChange={(e) => e.target.value && onChange([...embeds, { type: 'simulation', simulation_id: Number(e.target.value), caption: '' }])}>
          <option value="">+ simulazione…</option>{sims.data?.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
        </Select>
      </div>
      <Textarea aria-label="Tabella CSV" className="text-xs" placeholder={'Tabella CSV (prima riga intestazione, separatore ;)\nAnno;Valore\n2020;155'} value={tableCsv} onChange={(e) => setTableCsv(e.target.value)} />
      <Button className="text-xs" disabled={!tableCsv.trim()} onClick={() => {
        const lines = tableCsv.trim().split('\n').map((l) => l.split(';').map((c) => c.trim()));
        onChange([...embeds, { type: 'table', caption: '', columns: lines[0], rows: lines.slice(1) }]);
        setTableCsv('');
      }}>+ tabella</Button>
    </div>
  );
}

function SectionEditor({ report, section, onSaved, onError }: { report: Report; section: ReportSection; onSaved: (r: Report) => void; onError: (e: string) => void }) {
  const [body, setBody] = useState(section.body);
  const [title, setTitle] = useState(section.title);
  const [embeds, setEmbeds] = useState<Embed[]>(section.embeds);
  const [showEmbeds, setShowEmbeds] = useState(section.embeds.length > 0);
  const dirty = body !== section.body || title !== section.title || JSON.stringify(embeds) !== JSON.stringify(section.embeds);
  useEffect(() => { setBody(section.body); setTitle(section.title); setEmbeds(section.embeds); }, [section]);
  const chapter = section.key === 'chapter';
  return (
    <section className="rounded-lg border border-ink-700 bg-ink-900 p-4" data-testid={`section-${section.key}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {chapter ? <Input aria-label="Titolo capitolo" className="max-w-md py-1" value={title} onChange={(e) => setTitle(e.target.value)} /> : <h2 className="font-medium text-paper">{section.title}</h2>}
        {chapter && <Badge>Capitolo</Badge>}
        {!section.body.trim() && !chapter && <Badge tone="warn">Da compilare</Badge>}
        <span className="flex-1" />
        {chapter && <>
          <Button variant="ghost" className="px-1.5" aria-label="Sposta su" onClick={async () => onSaved(await api.moveChapter(report.id, section.id, -1))}><ArrowUp className="size-4" /></Button>
          <Button variant="ghost" className="px-1.5" aria-label="Sposta giù" onClick={async () => onSaved(await api.moveChapter(report.id, section.id, 1))}><ArrowDown className="size-4" /></Button>
          <Button variant="ghost" className="px-1.5 hover:text-bad" aria-label="Elimina capitolo" onClick={async () => onSaved(await api.deleteChapter(report.id, section.id))}><Trash2 className="size-4" /></Button>
        </>}
      </div>
      <Textarea aria-label={`Testo: ${section.title}`} className="min-h-32" value={body} onChange={(e) => setBody(e.target.value)} placeholder="Paragrafi separati da una riga vuota; elenchi con «- ». Citazioni: [@id, p. 12]" />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button className="text-xs text-gold-300 hover:underline" onClick={() => setShowEmbeds((v) => !v)}>{showEmbeds ? 'Nascondi grafici e tabelle' : `Grafici e tabelle (${embeds.length})`}</button>
        <span className="flex-1" />
        {dirty && <Button variant="primary" className="text-xs" onClick={async () => {
          try { onSaved(await api.updateSection(report.id, section.id, { body, embeds, ...(chapter ? { title } : {}) })); } catch (e) { onError(errorText(e)); }
        }}>Salva sezione</Button>}
      </div>
      {showEmbeds && <EmbedEditor embeds={embeds} onChange={setEmbeds} />}
    </section>
  );
}

function CheckPanel({ check }: { check?: ReportCheck }) {
  if (!check) return <Loading />;
  return (
    <div className="space-y-2 text-steel-300">
      <p className={`flex items-center gap-1.5 ${check.ready ? 'text-ok' : 'text-warn'}`}>{check.ready ? <CheckCircle2 className="size-4" /> : <AlertTriangle className="size-4" />}{check.ready ? 'Pronto per l\'approvazione' : 'Non ancora approvabile'}</p>
      {check.empty_sections.length > 0 && <p>Sezioni vuote: {check.empty_sections.join(', ')}</p>}
      {check.invalid_citations.length > 0 && <p className="text-bad">Citazioni a fonti inesistenti: {check.invalid_citations.map((i) => `@${i}`).join(', ')}</p>}
      {check.embed_problems.map((p) => <p key={p} className="text-bad">{p}</p>)}
      <p>Bibliografia: {check.bibliography_size} fonti ({check.cited_sources} citate nel testo)</p>
      {check.unverified_sources.length > 0 && <div><p className="text-warn">Fonti non verificate (segnalate nell'export):</p><ul className="list-disc pl-5 text-xs">{check.unverified_sources.map((s) => <li key={s.id}>{s.citation}</li>)}</ul></div>}
      {check.warnings.map((w) => <p key={w} className="text-xs text-warn">{w}</p>)}
    </div>
  );
}

export function ReportEditorPage() {
  const id = Number(useParams().reportId);
  const rep = useAsync(() => api.report(id), [id]);
  const check = useAsync(() => api.checkReport(id), [id, rep.data?.updated_at]);
  const sources = useAsync(() => api.sources(), []);
  const [err, setErr] = useState<string>();
  const [chapter, setChapter] = useState('');
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();
  useContextPanel(
    <div className="space-y-4">
      <div><h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Verifica</h3><CheckPanel check={check.data} /></div>
      <div>
        <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Fonti da citare</h3>
        <p className="mb-2 text-xs text-steel-500">Copia il codice nel testo: <span className="font-mono">[@id]</span> o <span className="font-mono">[@id, p. 12]</span>.</p>
        <ul className="space-y-1.5 text-xs">
          {sources.data?.map((s) => (
            <li key={s.id} className="flex items-start gap-2">
              <button className="shrink-0 font-mono text-gold-300 hover:underline" onClick={() => navigator.clipboard?.writeText(`[@${s.id}]`)} title="Copia codice"><Quote className="inline size-3" /> @{s.id}</button>
              <span className="text-steel-300">{s.citation.slice(0, 120)} <Badge tone={VERIFICATION[s.verification_status].tone}>{VERIFICATION[s.verification_status].label}</Badge></span>
            </li>
          ))}
          {sources.data?.length === 0 && <li className="text-steel-500">Nessuna fonte: aggiungile in <Link to="/bibliography" className="text-gold-300">Bibliografia</Link>.</li>}
        </ul>
      </div>
    </div>,
    [check.data, sources.data],
  );
  if (rep.loading && !rep.data) return <Loading />;
  if (rep.error) return <ErrorBox error={rep.error} onRetry={rep.reload} />;
  const r = rep.data!;
  const saved = (x: Report) => { setErr(undefined); rep.setData(x); };
  return (
    <>
      <PageHeader eyebrow={<Link to="/studio" className="hover:underline">Research Studio</Link>} title={r.title}
        description={`${r.status === 'approved' ? 'Approvato' : 'Bozza'} · aggiornato ${formatDateTime(r.updated_at)}${r.origin.startsWith('research_run') ? ' · da ricerca della War Room' : ''}`}
        actions={<>
          <a href={api.exportUrl(r.id, 'pdf')} className="inline-flex items-center gap-1 rounded-md border border-ink-600 px-3 py-1.5 text-sm text-paper hover:bg-ink-800"><FileDown className="size-4" aria-hidden /> PDF</a>
          <a href={api.exportUrl(r.id, 'docx')} className="inline-flex items-center gap-1 rounded-md border border-ink-600 px-3 py-1.5 text-sm text-paper hover:bg-ink-800"><FileDown className="size-4" aria-hidden /> DOCX</a>
          {r.status === 'draft'
            ? <Button variant="primary" onClick={async () => { try { saved(await api.setReportStatus(r.id, 'approved')); } catch (e) { setErr(errorText(e)); } }}>Approva</Button>
            : <Button onClick={async () => saved(await api.setReportStatus(r.id, 'draft'))}>Riporta in bozza</Button>}
          <Button onClick={() => setDeleting(true)} aria-label="Elimina rapporto"><Trash2 className="size-4" /></Button>
        </>} />
      {r.contains_ai_text && <p className="mb-3 text-sm text-warn">Contiene testo generato o estratto automaticamente: rivedilo prima di approvare.</p>}
      {err && <div className="mb-3"><ErrorBox error={new Error(err)} /></div>}
      <div className="space-y-3">
        {[...r.sections].sort((a, b) => a.ordinal - b.ordinal).map((s) => <SectionEditor key={s.id} report={r} section={s} onSaved={saved} onError={setErr} />)}
      </div>
      <Card className="mt-4">
        <div className="flex flex-wrap items-end gap-2">
          <Field label="Nuovo capitolo (inserito dopo «Analisi»)" className="min-w-64 flex-1"><Input value={chapter} onChange={(e) => setChapter(e.target.value)} /></Field>
          <Button disabled={!chapter.trim()} onClick={async () => { saved(await api.addChapter(r.id, chapter.trim(), 'analysis')); setChapter(''); }}><Plus className="size-4" aria-hidden /> Aggiungi capitolo</Button>
        </div>
        <p className="mt-2 text-xs text-steel-500">La bibliografia è generata automaticamente dalle fonti citate, con lo stato di verifica di ciascuna.</p>
      </Card>
      <ConfirmDialog open={deleting} title="Eliminare il rapporto?" message="Il rapporto e tutte le sue sezioni verranno eliminati." confirmLabel="Elimina definitivamente"
        onCancel={() => setDeleting(false)} onConfirm={async () => { await api.deleteReport(r.id); navigate('/studio'); }} />
    </>
  );
}

export function BriefingPage() {
  const list = useAsync(() => api.briefings(), []);
  const [selected, setSelected] = useState<number>();
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(false);
  const [err, setErr] = useState<string>();
  const b = list.data?.find((x) => x.id === selected) ?? list.data?.[0];
  return (
    <>
      <PageHeader eyebrow="Research Studio" title="Daily Briefing" description="Rapporto periodico sui tuoi dati: ogni voce con data e fonte. Nessuna notizia in tempo reale."
        actions={<>
          <label className="flex items-center gap-1.5 text-sm text-steel-300"><input type="checkbox" checked={refresh} onChange={(e) => setRefresh(e.target.checked)} />Aggiorna prima le serie</label>
          <Button variant="primary" disabled={busy} onClick={async () => { setBusy(true); setErr(undefined); try { const n = await api.generateBriefing(refresh); await list.reload(); setSelected(n.id); } catch (e) { setErr(errorText(e)); } finally { setBusy(false); } }}>{busy ? 'Generazione…' : 'Genera ora'}</Button>
        </>} />
      <p className="mb-4 text-xs text-steel-500">Programmazione: <span className="font-mono">scripts/generate_briefing.py --refresh</span> con cron (vedi documentazione).</p>
      {err && <ErrorBox error={new Error(err)} />}
      {list.loading && !list.data && <Loading />}
      {list.data?.length === 0 && <EmptyState>Nessun briefing generato.</EmptyState>}
      {list.data && list.data.length > 1 && (
        <Select aria-label="Briefing" className="mb-4 max-w-xs" value={b?.id} onChange={(e) => setSelected(Number(e.target.value))}>
          {list.data.map((x) => <option key={x.id} value={x.id}>{x.content.date} · {x.trigger === 'scheduled' ? 'programmato' : 'manuale'} · #{x.id}</option>)}
        </Select>
      )}
      {b && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2" data-testid="briefing">
          {b.content.sections.map((s, i) => (
            <Card key={s.key} title={`${i + 1}. ${s.title}`}>
              {s.items.length === 0 ? <p className="text-sm text-steel-400">{s.empty_reason}</p> : (
                <ul className="space-y-2 text-sm">
                  {s.items.map((it, j) => (
                    <li key={j}>
                      <p className="text-paper">{it.url ? <Link to={it.url} className="hover:text-gold-300">{it.title}</Link> : it.title}
                        {it.value !== undefined && it.value !== null && <span className="ml-2 text-gold-300">{it.value.toLocaleString('it-IT', { maximumSignificantDigits: 6 })} {it.unit}</span>}</p>
                      {it.detail && <p className="text-steel-300">{it.detail}</p>}
                      <p className="text-[11px] text-steel-500">{[it.date && `Data: ${it.date}`, it.source && `Fonte: ${it.source}`, it.kind, it.reason].filter(Boolean).join(' · ')}</p>
                      {it.flags?.map((f) => <p key={f} className="text-[11px] text-warn">{f}</p>)}
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
        </div>
      )}
      {b?.content.refresh && b.content.refresh.length > 0 && <Card title="Aggiornamento delle fonti" className="mt-4"><ul className="text-xs text-steel-300">{b.content.refresh.map((x) => <li key={x.series}>{x.series}: {x.status}</li>)}</ul></Card>}
    </>
  );
}
