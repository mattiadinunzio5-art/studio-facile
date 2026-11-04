import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Plus, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import { ENTITY_TYPES, PROVENANCE, RELATION_TYPES, type EntityType, type GraphData, type Provenance } from '../api/types';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Field, Input, Select, Textarea } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { errorText, toInt } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

const TYPE_COLOR: Record<EntityType, string> = {
  person: '#c6a75e', state: '#6fae8a', company: '#8aa6d2', bank: '#d2a24c', institution: '#b9bcc2',
  event: '#f2f1ed', document: '#9a9ea6', theory: '#c48ac6', indicator: '#6fb5b5',
};
const EDGE_STYLE: Record<Provenance, { stroke: string; dash?: string }> = {
  sourced: { stroke: '#7d818a' },
  user_hypothesis: { stroke: '#a88b47', dash: '5 4' },
  ai_hypothesis: { stroke: '#d26a5c', dash: '2 4' },
};

function useNarrow(breakpoint = 640): boolean {
  const [narrow, setNarrow] = useState(() => typeof window !== 'undefined' && window.innerWidth < breakpoint);
  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < breakpoint);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [breakpoint]);
  return narrow;
}

function GraphCanvas({ data, selected, onSelect }: { data: GraphData; selected?: number; onSelect: (id: number) => void }) {
  // Su schermi stretti lo spazio logico è più piccolo e verticale: il testo resta leggibile.
  const narrow = useNarrow();
  const [W, H, PAD] = narrow ? [400, 520, 36] : [1000, 640, 60];
  const label = narrow ? 12 : 13;
  const maxChars = narrow ? 22 : 28;
  const pos = useMemo(() => {
    const xs = data.nodes.map((n) => n.x), ys = data.nodes.map((n) => n.y);
    const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    const sx = (v: number) => (maxX === minX ? W / 2 : PAD + ((v - minX) / (maxX - minX)) * (W - 2 * PAD));
    const sy = (v: number) => (maxY === minY ? H / 2 : PAD + ((v - minY) / (maxY - minY)) * (H - 2 * PAD));
    return new Map(data.nodes.map((n) => [n.id, { x: sx(n.x), y: sy(n.y) }]));
  }, [data, W, H, PAD]);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full rounded-lg border border-ink-700 bg-ink-950" role="img" aria-label={`Grafo con ${data.nodes.length} entità e ${data.edges.length} relazioni`}>
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#7d818a" /></marker>
      </defs>
      {data.edges.map((e) => {
        const a = pos.get(e.source_entity_id), b = pos.get(e.target_entity_id);
        if (!a || !b) return null;
        const st = EDGE_STYLE[e.provenance];
        return (
          <g key={e.id}>
            <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={st.stroke} strokeDasharray={st.dash} strokeWidth={1.4} markerEnd="url(#arrow)" />
            <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 4} fontSize={narrow ? 10 : 11} fill="#9a9ea6" textAnchor="middle">{RELATION_TYPES[e.relation_type]}</text>
          </g>
        );
      })}
      {data.nodes.map((n) => {
        const p = pos.get(n.id)!;
        const r = 7 + Math.min(10, n.degree * 1.5);
        return (
          <g key={n.id} onClick={() => onSelect(n.id)} className="cursor-pointer" role="button" aria-label={n.name}>
            <circle cx={p.x} cy={p.y} r={r} fill={TYPE_COLOR[n.entity_type]} stroke={n.id === selected || n.is_focus ? '#dcc48e' : '#0d0e10'} strokeWidth={n.id === selected || n.is_focus ? 3 : 1.5} />
            <text x={p.x < W * 0.3 ? p.x - r : p.x > W * 0.7 ? p.x + r : p.x} y={p.y + r + label} fontSize={label} fill="#f2f1ed"
              textAnchor={p.x < W * 0.3 ? 'start' : p.x > W * 0.7 ? 'end' : 'middle'}>{n.name.length > maxChars ? `${n.name.slice(0, maxChars - 1)}…` : n.name}</text>
          </g>
        );
      })}
    </svg>
  );
}

function EntityPanel({ id, onChanged }: { id: number; onChanged: () => void }) {
  const ent = useAsync(() => api.entity(id), [id]);
  const rels = useAsync(() => api.entityRelations(id), [id]);
  const names = useAsync(() => api.entities(), []);
  const nameOf = new Map((names.data ?? []).map((e) => [e.id, e.name]));
  if (!ent.data) return <Loading />;
  const e = ent.data;
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-base font-semibold text-paper">{e.name}</h3>
        <p className="text-xs text-steel-500">{ENTITY_TYPES[e.entity_type]}{e.start_year !== null && ` · ${e.start_year}${e.end_year !== null ? `–${e.end_year}` : ''}`}</p>
      </div>
      {e.description && <p className="text-steel-300">{e.description}</p>}
      {e.event_id && <Link to={`/history/events/${e.event_id}`} className="text-xs text-gold-300 hover:underline">Apri scheda evento</Link>}
      <h4 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Relazioni</h4>
      <ul className="space-y-2">
        {rels.data?.map((r) => (
          <li key={r.id} className="text-steel-300">
            {nameOf.get(r.source_entity_id)} <span className="text-gold-300">{RELATION_TYPES[r.relation_type].toLowerCase()}</span> {nameOf.get(r.target_entity_id)}
            <span className="block text-[11px] text-steel-500">
              <Badge tone={r.provenance === 'sourced' ? 'ok' : r.provenance === 'ai_hypothesis' ? 'bad' : 'warn'}>{PROVENANCE[r.provenance]}</Badge> {r.evidence_label}
              <button className="ml-2 hover:text-bad" onClick={async () => { await api.deleteRelation(r.id); await rels.reload(); onChanged(); }} aria-label="Elimina relazione"><Trash2 className="inline size-3" /></button>
            </span>
          </li>
        ))}
      </ul>
      <Link to={`/graph?focus=${e.id}`} className="text-xs text-gold-300 hover:underline">Centra il grafo su questa entità</Link>
    </div>
  );
}

export function GraphPage() {
  const [params, setParams] = useSearchParams();
  const focus = toInt(params.get('focus') ?? '') ?? undefined;
  const [depth, setDepth] = useState(2);
  const [prov, setProv] = useState<string[]>([]);
  const [relTypes, setRelTypes] = useState<string[]>([]);
  const [selected, setSelected] = useState<number | undefined>(focus);
  const graph = useAsync(() => api.graph({ focus, depth, provenance: prov, relation_types: relTypes }), [focus, depth, prov, relTypes]);
  const entities = useAsync(() => api.entities(), []);
  const sources = useAsync(() => api.sources(), []);
  const [form, setForm] = useState<'entity' | 'relation' | 'path'>();
  const [ent, setEnt] = useState({ entity_type: 'person', name: '', description: '', start_year: '', end_year: '' });
  const [rel, setRel] = useState({ source_entity_id: '', target_entity_id: '', relation_type: 'influenced', provenance: 'user_hypothesis', source_id: '', evidence_note: '' });
  const [pathSel, setPathSel] = useState({ a: '', b: '' });
  const [pathResult, setPathResult] = useState<string>();
  const [err, setErr] = useState<string>();

  const reloadAll = async () => { await Promise.all([graph.reload(), entities.reload()]); };
  useContextPanel(
    selected ? <EntityPanel id={selected} onChanged={reloadAll} /> : (
      <div className="space-y-2 text-steel-300">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Legenda</h3>
        <p>Linea continua: relazione documentata. Tratteggio oro: ipotesi dell'utente. Puntinato rosso: ipotesi AI da verificare.</p>
        <p>Seleziona un nodo per aprire la scheda dell'entità.</p>
      </div>
    ),
    [selected],
  );

  async function submit(fn: () => Promise<unknown>) {
    setErr(undefined);
    try {
      await fn();
      setForm(undefined);
      await reloadAll();
    } catch (e) {
      setErr(errorText(e));
    }
  }
  const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const entityOptions = entities.data?.map((e) => <option key={e.id} value={e.id}>{e.name} ({ENTITY_TYPES[e.entity_type]})</option>);

  return (
    <>
      <PageHeader eyebrow="Modulo D" title="Knowledge Graph" description="Entità e relazioni: ogni collegamento ha una fonte o è dichiarato come ipotesi."
        actions={
          <>
            <Button onClick={() => setForm('entity')}><Plus className="size-4" aria-hidden /> Entità</Button>
            <Button onClick={() => setForm('relation')}><Plus className="size-4" aria-hidden /> Relazione</Button>
            <Button onClick={() => setForm('path')}>Percorso</Button>
          </>
        } />
      {form === 'entity' && (
        <Card title="Nuova entità" className="mb-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
            <Field label="Tipo"><Select value={ent.entity_type} onChange={(e) => setEnt({ ...ent, entity_type: e.target.value })}>{Object.entries(ENTITY_TYPES).filter(([k]) => k !== 'event').map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>
            <Field label="Nome" className="sm:col-span-3"><Input value={ent.name} onChange={(e) => setEnt({ ...ent, name: e.target.value })} /></Field>
            <Field label="Da (anno)"><Input inputMode="numeric" value={ent.start_year} onChange={(e) => setEnt({ ...ent, start_year: e.target.value })} /></Field>
            <Field label="A (anno)"><Input inputMode="numeric" value={ent.end_year} onChange={(e) => setEnt({ ...ent, end_year: e.target.value })} /></Field>
            <Field label="Descrizione" className="sm:col-span-4"><Textarea value={ent.description} onChange={(e) => setEnt({ ...ent, description: e.target.value })} /></Field>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button onClick={() => setForm(undefined)}>Annulla</Button>
            <Button variant="primary" disabled={!ent.name.trim()} onClick={() => submit(() => api.createEntity({ ...ent, entity_type: ent.entity_type as EntityType, start_year: toInt(ent.start_year), end_year: toInt(ent.end_year) }))}>Crea entità</Button>
          </div>
        </Card>
      )}
      {form === 'relation' && (
        <Card title="Nuova relazione" className="mb-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Field label="Da"><Select value={rel.source_entity_id} onChange={(e) => setRel({ ...rel, source_entity_id: e.target.value })}><option value="">—</option>{entityOptions}</Select></Field>
            <Field label="Relazione"><Select value={rel.relation_type} onChange={(e) => setRel({ ...rel, relation_type: e.target.value })}>{Object.entries(RELATION_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>
            <Field label="A"><Select value={rel.target_entity_id} onChange={(e) => setRel({ ...rel, target_entity_id: e.target.value })}><option value="">—</option>{entityOptions}</Select></Field>
            <Field label="Provenienza"><Select value={rel.provenance} onChange={(e) => setRel({ ...rel, provenance: e.target.value })}><option value="user_hypothesis">{PROVENANCE.user_hypothesis}</option><option value="sourced">{PROVENANCE.sourced}</option></Select></Field>
            {rel.provenance === 'sourced' && <Field label="Fonte" className="sm:col-span-2"><Select value={rel.source_id} onChange={(e) => setRel({ ...rel, source_id: e.target.value })}><option value="">—</option>{sources.data?.map((s) => <option key={s.id} value={s.id}>{s.citation.slice(0, 100)}</option>)}</Select></Field>}
            <Field label="Nota sull'evidenza" className="sm:col-span-3"><Input value={rel.evidence_note} onChange={(e) => setRel({ ...rel, evidence_note: e.target.value })} /></Field>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button onClick={() => setForm(undefined)}>Annulla</Button>
            <Button variant="primary" disabled={!rel.source_entity_id || !rel.target_entity_id}
              onClick={() => submit(() => api.createRelation({ ...rel, source_entity_id: Number(rel.source_entity_id), target_entity_id: Number(rel.target_entity_id), source_id: rel.source_id ? Number(rel.source_id) : null }))}>Crea relazione</Button>
          </div>
        </Card>
      )}
      {form === 'path' && (
        <Card title="Percorso più breve" className="mb-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Field label="Da"><Select value={pathSel.a} onChange={(e) => setPathSel({ ...pathSel, a: e.target.value })}><option value="">—</option>{entityOptions}</Select></Field>
            <Field label="A"><Select value={pathSel.b} onChange={(e) => setPathSel({ ...pathSel, b: e.target.value })}><option value="">—</option>{entityOptions}</Select></Field>
            <div className="flex items-end"><Button disabled={!pathSel.a || !pathSel.b} onClick={async () => {
              const r = await api.graphPath(Number(pathSel.a), Number(pathSel.b));
              const n = new Map((entities.data ?? []).map((e) => [e.id, e.name]));
              setPathResult(r.found ? r.entity_ids.map((i) => n.get(i)).join(' → ') : 'Nessun percorso tra le due entità.');
            }}>Calcola</Button></div>
          </div>
          {pathResult && <p className="mt-3 text-sm text-paper">{pathResult}</p>}
        </Card>
      )}
      {err && <div className="mb-4"><ErrorBox error={new Error(err)} /></div>}
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-steel-300">
        {focus && <span>Focus: <strong className="text-paper">{entities.data?.find((e) => e.id === focus)?.name}</strong> <button className="text-xs text-gold-300 hover:underline" onClick={() => { setParams({}); setSelected(undefined); }}>rimuovi</button></span>}
        {focus && <label className="flex items-center gap-1">Profondità <Select className="w-16 py-1" value={depth} onChange={(e) => setDepth(Number(e.target.value))}>{[1, 2, 3, 4].map((d) => <option key={d}>{d}</option>)}</Select></label>}
        {(Object.keys(PROVENANCE) as Provenance[]).map((p) => (
          <label key={p} className="flex items-center gap-1.5"><input type="checkbox" checked={prov.length === 0 || prov.includes(p)} onChange={() => setProv(toggle(prov.length === 0 ? Object.keys(PROVENANCE) : prov, p))} />{PROVENANCE[p]}</label>
        ))}
        <Select aria-label="Tipo di relazione" className="w-auto py-1" value={relTypes[0] ?? ''} onChange={(e) => setRelTypes(e.target.value ? [e.target.value] : [])}>
          <option value="">Tutte le relazioni</option>
          {Object.entries(RELATION_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </Select>
      </div>
      {graph.loading && !graph.data && <Loading />}
      {graph.error && <ErrorBox error={graph.error} onRetry={graph.reload} />}
      {graph.data && (graph.data.nodes.length === 0 ? (
        <EmptyState>Il grafo è vuoto. Crea entità ed eventi e collegali con relazioni documentate o ipotesi dichiarate.</EmptyState>
      ) : (
        <>
          <GraphCanvas data={graph.data} selected={selected} onSelect={setSelected} />
          <p className="mt-2 text-xs text-steel-500">
            {graph.data.stats.shown_nodes}/{graph.data.stats.entities} entità · {graph.data.stats.shown_edges} relazioni mostrate · {graph.data.stats.components} componenti ·
            documentate {graph.data.stats.by_provenance.sourced}, ipotesi utente {graph.data.stats.by_provenance.user_hypothesis}, ipotesi AI {graph.data.stats.by_provenance.ai_hypothesis}
          </p>
        </>
      ))}
    </>
  );
}
