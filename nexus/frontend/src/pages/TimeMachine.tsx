import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { EyeOff, History } from 'lucide-react';
import { api } from '../api/client';
import { CATEGORIES, KNOWLEDGE_KINDS, RELIABILITY } from '../api/types';
import { Badge, DemoBadge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { Field, Input, Select } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { toInt } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';
import { RELIABILITY_TONE } from './History';

export function TimeMachinePage() {
  const [params, setParams] = useSearchParams();
  const year = params.get('year') ?? '';
  const [draftYear, setDraftYear] = useState(year);
  const hindsight = params.get('hindsight') === '1';
  const country = params.get('country') ?? '';
  const category = params.get('category') ?? '';
  const eventId = params.get('event') ?? '';
  const update = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) (v ? next.set(k, v) : next.delete(k));
    setParams(next, { replace: true });
  };
  const { data, error, loading, reload } = useAsync(
    () => api.timeline({ as_of_year: toInt(year) ?? undefined, hindsight, country: country || undefined, category: category || undefined, event_id: eventId ? Number(eventId) : undefined }),
    [year, hindsight, country, category, eventId],
  );

  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Filtro anti-senno-di-poi</h3>
      <p>Alla data scelta vengono nascosti: eventi successivi, conseguenze (conoscenza retrospettiva) e informazioni emerse dopo.</p>
      <p>Attiva «senno di poi» per confrontare con ciò che sappiamo oggi: le informazioni successive restano evidenziate.</p>
    </div>,
    [],
  );

  return (
    <>
      <PageHeader eyebrow="Modulo C" title="Historical Time Machine" description="Cronologia interattiva: cosa si sapeva in un dato momento." />
      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Field label="Anno (negativo = a.C.)">
            <form onSubmit={(e) => { e.preventDefault(); update({ year: draftYear.trim() }); }}>
              <Input inputMode="numeric" value={draftYear} onChange={(e) => setDraftYear(e.target.value)} onBlur={() => update({ year: draftYear.trim() })} placeholder="es. 1931" />
            </form>
          </Field>
          <Field label="Paese / area"><Input value={country} onChange={(e) => update({ country: e.target.value })} /></Field>
          <Field label="Categoria">
            <Select value={category} onChange={(e) => update({ category: e.target.value })}>
              <option value="">Tutte</option>
              {Object.entries(CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </Select>
          </Field>
          <label className="col-span-2 flex items-end gap-2 pb-2 text-sm text-steel-300 md:col-span-2">
            <input type="checkbox" checked={hindsight} onChange={(e) => update({ hindsight: e.target.checked ? '1' : '' })} />
            Senno di poi (mostra conoscenze successive)
          </label>
        </div>
        {eventId && <p className="mt-2 text-xs text-steel-400">Filtrato su un solo evento. <button className="text-gold-300 hover:underline" onClick={() => update({ event: '' })}>Mostra tutti</button></p>}
      </Card>
      {loading && !data && <Loading />}
      {error && <ErrorBox error={error} onRetry={reload} />}
      {data && (
        <>
          {data.notes.map((n) => <p key={n} className="mb-2 flex items-start gap-2 text-xs text-steel-400"><History className="mt-0.5 size-3.5 shrink-0 text-gold-400" aria-hidden />{n}</p>)}
          {data.hidden_future_events > 0 && <p className="mb-4 text-xs text-steel-500">{data.hidden_future_events} eventi successivi alla data sono nascosti.</p>}
          {data.indicators.length > 0 && (
            <Card title={`Indicatori disponibili al ${year}`} className="mb-4">
              <ul className="space-y-1 text-sm">
                {data.indicators.map((i) => (
                  <li key={i.series_id} className="flex flex-wrap justify-between gap-2">
                    <Link to={`/financial/series/${i.series_id}`} className="text-steel-300 hover:text-paper">{i.name}</Link>
                    <span className="text-paper">{i.last_value.toLocaleString('it-IT')} {i.unit} <span className="text-[11px] text-steel-500">({i.last_date}, {i.source})</span></span>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-steel-500">{data.indicators[0].caveat}</p>
            </Card>
          )}
          {data.events.length === 0 ? <EmptyState>Nessun evento noto alla data selezionata.</EmptyState> : (
            <ol className="relative space-y-4 border-l border-ink-600 pl-5">
              {data.events.map((e) => (
                <li key={e.id} className="relative">
                  <span className="absolute -left-[25px] top-1.5 size-2.5 rounded-full border border-gold-400 bg-ink-950" aria-hidden />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-gold-300">{e.date_label}</span>
                    <Link to={`/history/events/${e.id}`} className="font-medium text-paper hover:text-gold-300">{e.title}</Link>
                    {e.status_at_date === 'ongoing' && <Badge tone="gold">In corso alla data</Badge>}
                    <Badge tone={RELIABILITY_TONE[e.reliability]}>{RELIABILITY[e.reliability]}</Badge>
                    {e.is_demo && <DemoBadge />}
                  </div>
                  {e.description && <p className="mt-1 text-sm text-steel-300">{e.description}</p>}
                  {e.known_then.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {e.known_then.map((k) => <li key={k.id} className="text-sm text-steel-300"><span className="text-[11px] text-steel-500">[{KNOWLEDGE_KINDS[k.kind]}, {k.known_since_year}]</span> {k.content}</li>)}
                    </ul>
                  )}
                  {e.consequences && <p className="mt-2 text-sm text-steel-400"><span className="text-[11px] uppercase tracking-wider text-warn">Conseguenze (senno di poi)</span> {e.consequences}</p>}
                  {e.known_later.length > 0 && (
                    <ul className="mt-2 space-y-1 rounded-md border border-warn/30 bg-warn/5 p-2">
                      {e.known_later.map((k) => <li key={k.id} className="text-sm text-steel-300"><span className="text-[11px] text-warn">[Emersa nel {k.known_since_year} · {KNOWLEDGE_KINDS[k.kind]}]</span> {k.content}</li>)}
                    </ul>
                  )}
                  {(e.consequences_hidden || e.hidden_later_count > 0) && (
                    <p className="mt-1 flex items-center gap-1 text-[11px] text-steel-500"><EyeOff className="size-3" aria-hidden />
                      Nascosto: {[e.consequences_hidden && 'conseguenze', e.hidden_later_count > 0 && `${e.hidden_later_count} informazioni successive`].filter(Boolean).join(', ')}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </>
  );
}
