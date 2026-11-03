import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Bot, CircleSlash, Cpu, ShieldAlert, XCircle } from 'lucide-react';
import { api } from '../api/client';
import { RELATION_TYPES, type AgentStep, type Claim, type ResearchRun } from '../api/types';
import { CLAIM, SUPPORT } from '../components/research';
import { Badge, type BadgeTone } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Field, Textarea } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useAppState, useContextPanel } from '../state/AppState';

export const AGENT_LABEL: Record<AgentStep['agent'], string> = {
  planner: 'Planner', researcher: 'Ricerca', historian: 'Historian', economist: 'Economist', quant: 'Quant Analyst', skeptic: 'Skeptic', synthesizer: 'Synthesizer',
};
export const RUN_STATUS: Record<ResearchRun['status'], { label: string; tone: BadgeTone }> = {
  queued: { label: 'In coda', tone: 'neutral' }, running: { label: 'In esecuzione', tone: 'gold' },
  awaiting_approval: { label: 'In attesa di approvazione', tone: 'warn' }, approved: { label: 'Approvata', tone: 'ok' },
  rejected: { label: 'Respinta', tone: 'neutral' }, failed: { label: 'Non completata', tone: 'bad' },
};

function ClaimList({ claims, evidenceIds }: { claims: Claim[]; evidenceIds?: Set<string> }) {
  if (!claims.length) return <EmptyState>Nessuna affermazione.</EmptyState>;
  return (
    <ul className="space-y-3">
      {claims.map((c, i) => (
        <li key={i} className="text-sm">
          <div className="mb-1 flex flex-wrap items-center gap-1.5">
            <Badge tone={CLAIM[c.type].tone}>{CLAIM[c.type].label}</Badge>
            {c.evidence.length > 0 && <Badge tone={SUPPORT[c.support].tone}>{SUPPORT[c.support].label}</Badge>}
            {c.evidence.map((e) => <a key={String(e)} href={`#ev-${e}`} className={`font-mono text-[11px] ${evidenceIds?.has(String(e)) ? 'text-gold-300' : 'text-steel-500'}`}>[{e}]</a>)}
          </div>
          <p className="text-paper">{c.text}</p>
          {c.note && <p className="mt-0.5 text-[11px] text-steel-500">{c.note}</p>}
        </li>
      ))}
    </ul>
  );
}

function StepRow({ s }: { s: AgentStep }) {
  const icon = s.status === 'skipped' ? <CircleSlash className="size-4 text-steel-500" /> : s.status === 'failed' ? <XCircle className="size-4 text-bad" /> : s.executor === 'ai' ? <Bot className="size-4 text-gold-400" /> : <Cpu className="size-4 text-ok" />;
  return (
    <li className="flex gap-3 border-l border-ink-600 pb-3 pl-3" data-testid={`step-${s.agent}`}>
      <span className="-ml-[22px] mt-0.5 rounded-full bg-ink-950 p-0.5" aria-hidden>{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-medium text-paper">{AGENT_LABEL[s.agent]}</span>
          <Badge tone={s.status === 'executed' ? (s.executor === 'ai' ? 'gold' : 'ok') : s.status === 'failed' ? 'bad' : 'neutral'}>
            {s.status === 'skipped' ? 'Non eseguito' : s.status === 'failed' ? 'Errore' : s.executor === 'ai' ? `AI · ${s.model}` : 'Motore locale'}
          </Badge>
          <span className="text-[11px] text-steel-500">{s.duration_ms} ms{s.output_tokens !== null && ` · ${s.input_tokens}→${s.output_tokens} token`}</span>
        </div>
        <p className="mt-0.5 text-sm text-steel-300">{s.summary}</p>
        {s.error && <p className="text-xs text-bad">{s.error}</p>}
        {s.output.rule_checks && s.output.rule_checks.length > 0 && <ul className="mt-1 list-disc pl-5 text-xs text-warn">{s.output.rule_checks.map((c) => <li key={c}>{c}</li>)}</ul>}
        {s.issues.length > 0 && <ul className="mt-1 text-[11px] text-steel-500">{s.issues.map((x) => <li key={x}>• {x}</li>)}</ul>}
      </div>
    </li>
  );
}

export function WarRoomPage() {
  const runs = useAsync(() => api.runs(), []);
  const series = useAsync(() => api.seriesList(), []);
  const status = useAsync(() => api.systemStatus(), []);
  const [question, setQuestion] = useState('');
  const [seriesIds, setSeriesIds] = useState<number[]>([]);
  const [err, setErr] = useState<string>();
  const navigate = useNavigate();
  const local = status.data?.ai_mode !== 'remote' && status.data?.ai_provider.id === 'none';

  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Flusso</h3>
      <p>Domanda → Pianificazione → Ricerca → Analisi → Controanalisi → Sintesi → <strong className="text-paper">Approvazione</strong>.</p>
      <p>Gli strumenti di ricerca lavorano sempre sui tuoi dati locali. Senza provider AI gli agenti generativi risultano «non eseguiti»: nulla viene simulato.</p>
      <p className="text-xs text-steel-500">NEXUS non pubblica, condivide né modifica l'archivio senza la tua approvazione.</p>
    </div>,
    [],
  );

  return (
    <>
      <PageHeader eyebrow="Modulo E" title="Research War Room" description="Ricerca multi-agente supervisionata con controanalisi e approvazione finale." />
      <Card title="Nuova ricerca" className="mb-6">
        <p className="mb-3 text-xs text-steel-400">
          Modalità: {status.data ? (local ? <span className="text-paper">locale (nessun provider AI)</span> : <span className="text-paper">AI · {status.data.ai_provider.name}</span>) : '…'}
          {' · '}<Link to="/settings" className="text-gold-300 hover:underline">configura provider</Link>
        </p>
        <Field label="Domanda di ricerca"><Textarea value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={2000} placeholder="Es. Quali furono le conseguenze monetarie della fine di Bretton Woods?" /></Field>
        {series.data && series.data.length > 0 && (
          <fieldset className="mt-3">
            <legend className="mb-1 text-xs text-steel-400">Serie per il Quant Analyst (facoltative; altrimenti scelte per pertinenza)</legend>
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {series.data.map((s) => (
                <label key={s.id} className="flex items-center gap-1.5 text-sm text-steel-300">
                  <input type="checkbox" checked={seriesIds.includes(s.id)} onChange={() => setSeriesIds(seriesIds.includes(s.id) ? seriesIds.filter((x) => x !== s.id) : [...seriesIds, s.id].slice(0, 8))} />
                  {s.name}
                </label>
              ))}
            </div>
          </fieldset>
        )}
        {err && <p role="alert" className="mt-2 text-sm text-bad">{err}</p>}
        <div className="mt-3 flex justify-end">
          <Button variant="primary" disabled={question.trim().length < 5} onClick={async () => {
            setErr(undefined);
            try { const r = await api.createRun({ question: question.trim(), series_ids: seriesIds.length ? seriesIds : undefined }); navigate(`/war-room/runs/${r.id}`); } catch (e) { setErr(errorText(e)); }
          }}>Avvia ricerca</Button>
        </div>
      </Card>
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-steel-400">Ricerche</h2>
      {runs.loading && !runs.data && <Loading />}
      {runs.error && <ErrorBox error={runs.error} onRetry={runs.reload} />}
      {runs.data?.length === 0 && <EmptyState>Nessuna ricerca avviata.</EmptyState>}
      <ul className="space-y-2">
        {runs.data?.map((r) => (
          <li key={r.id}>
            <Link to={`/war-room/runs/${r.id}`} className="flex flex-wrap items-center gap-2 rounded-lg border border-ink-700 bg-ink-900 p-3 hover:border-gold-500/60">
              <span className="font-mono text-xs text-steel-500">#{r.id}</span>
              <span className="min-w-0 flex-1 truncate text-sm text-paper">{r.question}</span>
              <Badge tone={RUN_STATUS[r.status].tone}>{RUN_STATUS[r.status].label}</Badge>
              <span className="text-[11px] text-steel-500">{r.mode === 'ai' ? r.provider : 'locale'} · {formatDateTime(r.created_at)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

export function RunDetailPage() {
  const id = Number(useParams().runId);
  const run = useAsync(() => api.run(id), [id]);
  const { refreshUnread } = useAppState();
  const [accepted, setAccepted] = useState<number[]>([]);
  const [note, setNote] = useState('');
  const [err, setErr] = useState<string>();
  const r = run.data;

  useEffect(() => {
    if (!r || !['queued', 'running'].includes(r.status)) return;
    const t = setTimeout(() => void run.reload(), 1500);
    return () => clearTimeout(t);
  }, [r, run]);

  useContextPanel(
    r ? (
      <div className="space-y-2 text-steel-300">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Run #{r.id}</h3>
        <p>Modalità: <span className="text-paper">{r.mode === 'ai' ? `AI (${r.provider}${r.model ? `, ${r.model}` : ''})` : 'locale'}</span></p>
        <p>Avviata: {formatDateTime(r.created_at)}</p>
        {r.finished_at && <p>Terminata: {formatDateTime(r.finished_at)}</p>}
        {r.plan.method && <p>Pianificazione: {r.plan.method}</p>}
      </div>
    ) : null,
    [r?.id, r?.status],
  );

  if (run.loading && !r) return <Loading />;
  if (run.error) return <ErrorBox error={run.error} onRetry={run.reload} />;
  if (!r) return null;
  const evIds = new Set(r.evidence.map((e) => e.id));
  const decide = async (decision: 'approve' | 'reject') => {
    setErr(undefined);
    try { run.setData(await api.decideRun(r.id, { decision, note, accepted_relations: decision === 'approve' ? accepted : [] })); await refreshUnread(); } catch (e) { setErr(errorText(e)); }
  };

  return (
    <>
      <PageHeader eyebrow={<Link to="/war-room" className="hover:underline">Research War Room</Link>} title={r.question}
        actions={<Badge tone={RUN_STATUS[r.status].tone}>{RUN_STATUS[r.status].label}</Badge>} />
      {['queued', 'running'].includes(r.status) && <Loading label="Gli agenti stanno lavorando…" />}
      {r.error && <div className="mb-4"><ErrorBox error={new Error(r.error)} /></div>}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
        <div className="space-y-4 lg:col-span-3">
          {r.result.claims && (
            <Card title="Sintesi">
              {r.result.abstract ? <p className="mb-3 text-sm text-steel-300">{r.result.abstract}</p> : null}
              <p className="mb-3 text-[11px] text-steel-500">{r.result.method}</p>
              <ClaimList claims={r.result.claims} evidenceIds={evIds} />
              {r.result.limitations && r.result.limitations.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Limiti e controanalisi</h3>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-warn">{r.result.limitations.map((l) => <li key={l}>{l}</li>)}</ul>
                </div>
              )}
            </Card>
          )}
          {r.status === 'awaiting_approval' && (
            <Card title="Approvazione">
              {r.result.proposed_relations && r.result.proposed_relations.length > 0 && (
                <fieldset className="mb-3">
                  <legend className="mb-1 text-xs text-steel-400">Relazioni proposte (verranno salvate come «ipotesi AI» da verificare)</legend>
                  {r.result.proposed_relations.map((p, i) => (
                    <label key={i} className="flex items-start gap-2 text-sm text-steel-300">
                      <input type="checkbox" className="mt-1" checked={accepted.includes(i)} onChange={() => setAccepted(accepted.includes(i) ? accepted.filter((x) => x !== i) : [...accepted, i])} />
                      <span>{p.source} <span className="text-gold-300">{RELATION_TYPES[p.relation_type].toLowerCase()}</span> {p.target} <span className="text-[11px] text-steel-500">{p.rationale} {p.evidence.map((e) => `[${e}]`).join(' ')}</span></span>
                    </label>
                  ))}
                </fieldset>
              )}
              <Field label="Nota (facoltativa)"><Textarea value={note} onChange={(e) => setNote(e.target.value)} /></Field>
              {err && <p role="alert" className="mt-2 text-sm text-bad">{err}</p>}
              <div className="mt-3 flex justify-end gap-2">
                <Button onClick={() => decide('reject')}>Respingi</Button>
                <Button variant="primary" onClick={() => decide('approve')}>Approva</Button>
              </div>
            </Card>
          )}
          {r.decided_at && <p className="text-xs text-steel-500">Decisione del {formatDateTime(r.decided_at)}{r.decision_note && `: ${r.decision_note}`}</p>}
          <Card title={`Evidenze (${r.evidence.length})`}>
            {r.evidence.length === 0 && <EmptyState>Nessuna evidenza trovata nell'archivio.</EmptyState>}
            <ol className="space-y-3">
              {r.evidence.map((e) => (
                <li key={e.id} id={`ev-${e.id}`} className="text-sm">
                  <p className="text-xs"><span className="font-mono text-gold-300">[{e.id}]</span> <span className="text-paper">{e.label}</span> <Badge>{e.kind}</Badge> {e.injection_flag && <ShieldAlert className="inline size-3.5 text-warn" aria-label="Possibili istruzioni nel testo" />}</p>
                  <p className="mt-1 text-steel-300">{e.text}</p>
                  <p className="text-[11px] text-steel-500">{e.source}</p>
                </li>
              ))}
            </ol>
          </Card>
        </div>
        <Card title="Agenti" className="lg:col-span-2">
          {r.steps.length === 0 ? <EmptyState>Nessun passo ancora eseguito.</EmptyState> : <ol className="ml-2">{r.steps.map((s) => <StepRow key={s.ordinal} s={s} />)}</ol>}
        </Card>
      </div>
    </>
  );
}
