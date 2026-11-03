import { useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import type { AskResult, RetrievalResult } from '../api/types';
import { CLAIM, PassageCard, SUPPORT } from '../components/research';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Field, Input, Select, Textarea } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { useContextPanel } from '../state/AppState';

export function AskResultView({ result }: { result: AskResult }) {
  const index = new Map(result.passages.map((p, i) => [p.chunk_id, i + 1]));
  return (
    <div className="space-y-4" data-testid="ask-result">
      <p className="rounded-md border border-ink-700 bg-ink-850 p-3 text-xs text-steel-400">{result.disclaimer}</p>
      {result.issues && result.issues.length > 0 && <ul className="text-xs text-warn">{result.issues.map((i) => <li key={i}>• {i}</li>)}</ul>}
      <Card title="Affermazioni">
        <ul className="space-y-3">
          {result.claims.map((c, i) => (
            <li key={i} className="text-sm">
              <div className="mb-1 flex flex-wrap gap-1.5">
                <Badge tone={CLAIM[c.type].tone}>{CLAIM[c.type].label}</Badge>
                <Badge tone={SUPPORT[c.support].tone}>{SUPPORT[c.support].label}</Badge>
                {c.evidence.map((e) => <span key={e} className="font-mono text-[11px] text-steel-500">[{index.get(e) ?? '?'}]</span>)}
              </div>
              <p className={c.type === 'documented_fact' ? 'text-paper' : 'text-steel-300'}>
                {c.type === 'documented_fact' ? `«${c.text}»` : c.text}
              </p>
              {c.note && <p className="mt-0.5 text-[11px] text-steel-500">{c.note}</p>}
            </li>
          ))}
        </ul>
      </Card>
      {result.passages.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-steel-400">Passaggi recuperati</h2>
          {result.passages.map((p, i) => <PassageCard key={p.chunk_id} hit={p} index={i + 1} />)}
        </div>
      )}
    </div>
  );
}

export function ResearchArchivePage() {
  const [tab, setTab] = useState<'ask' | 'search'>('ask');
  const [question, setQuestion] = useState('');
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [useAi, setUseAi] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError>();
  const [ask, setAsk] = useState<AskResult>();
  const [search, setSearch] = useState<RetrievalResult>();

  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Come leggere i risultati</h3>
      <p><strong className="text-paper">Fatto documentato</strong>: frase riportata alla lettera da un documento. Indica cosa afferma il documento, non che sia vero.</p>
      <p><strong className="text-paper">Supporto</strong>: quota dei termini della domanda presenti nel passaggio.</p>
      <p><strong className="text-paper">Dato mancante</strong>: l'archivio non contiene passaggi pertinenti.</p>
    </div>,
    [],
  );

  async function run(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      if (tab === 'ask') setAsk(await api.ask(question.trim(), undefined, useAi));
      else setSearch(await api.researchSearch(query.trim(), mode, 20));
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader eyebrow="Archivio" title="Interroga l'archivio" description="Domande e ricerche sui documenti importati, con collocazione precisa delle fonti." />
      <div className="mb-4 flex gap-1" role="tablist">
        {(['ask', 'search'] as const).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={`rounded-md px-3 py-1.5 text-sm ${tab === t ? 'bg-ink-800 text-paper' : 'text-steel-400 hover:text-paper'}`}>
            {t === 'ask' ? 'Domanda' : 'Ricerca'}
          </button>
        ))}
      </div>
      <form onSubmit={run} className="mb-6 space-y-3">
        {tab === 'ask' ? (
          <>
            <Field label="Domanda"><Textarea value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={1000} placeholder="Es. Quando terminò la convertibilità del dollaro in oro?" /></Field>
            <label className="flex items-center gap-2 text-sm text-steel-300">
              <input type="checkbox" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} />
              Risposta con il provider AI configurato (basata solo sui passaggi recuperati)
            </label>
          </>
        ) : (
          <div className="flex flex-wrap gap-3">
            <Field label="Termini" className="min-w-60 flex-1"><Input value={query} onChange={(e) => setQuery(e.target.value)} /></Field>
            <Field label="Metodo">
              <Select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="hybrid">Ibrida (testuale + semantica)</option>
                <option value="text">Testuale (BM25)</option>
                <option value="semantic">Semantica</option>
              </Select>
            </Field>
          </div>
        )}
        <Button type="submit" variant="primary" disabled={busy || (tab === 'ask' ? question.trim().length < 3 : query.trim().length < 2)}>
          {tab === 'ask' ? 'Rispondi dai documenti' : 'Cerca'}
        </Button>
      </form>
      {busy && <Loading label="Ricerca nell'archivio…" />}
      {error && <ErrorBox error={error} />}
      {tab === 'ask' && ask && !busy && <AskResultView result={ask} />}
      {tab === 'search' && search && !busy && (
        <>
          <p className="mb-3 text-xs text-steel-500">Metodo: {search.mode} · motore semantico: {search.semantic_engine} · {search.hits.length} risultati</p>
          {search.hits.length === 0 ? <EmptyState>Nessun passaggio trovato.</EmptyState> : (
            <div className="space-y-2">{search.hits.map((h, i) => <PassageCard key={h.chunk_id} hit={h} index={i + 1} />)}</div>
          )}
        </>
      )}
    </>
  );
}
