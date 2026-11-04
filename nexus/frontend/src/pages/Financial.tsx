import { useMemo, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, ExternalLink, RefreshCw, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import { FREQUENCY_LABEL, SERIES_CATEGORIES, type Comparison, type Preset, type SeriesDetail } from '../api/types';
import { DrawdownChart, formatNumber, mergePoints, SERIES_COLORS, TimeChart } from '../components/charts';
import { Badge, DemoBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { Field, Input, Select } from '../components/ui/Form';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorBox, Loading } from '../components/ui/States';
import { formatDateTime } from '../lib/format';
import { errorText } from '../lib/forms';
import { useAsync } from '../lib/useAsync';
import { useContextPanel } from '../state/AppState';

const CONNECTORS = { 'world-bank': 'World Bank', eurostat: 'Eurostat', owid: 'Our World in Data', fred: 'FRED' } as const;
const pct = (v: unknown) => (typeof v === 'number' ? `${formatNumber(v * 100, 4)}%` : '—');

function ImportPanel({ onDone }: { onDone: (id: number) => void }) {
  const presets = useAsync(() => api.presets(), []);
  const [mode, setMode] = useState<'preset' | 'custom' | 'csv'>('preset');
  const [preset, setPreset] = useState('');
  const [c, setC] = useState({ connector: 'world-bank', category: 'other', indicator: '', country: '', series_id: '', slug: '', entity: '', dataset: '', filters: '' });
  const [csv, setCsv] = useState({ name: '', source_label: '', source_url: '', unit: '', category: 'other' });
  const [file, setFile] = useState<File>();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string }>();

  async function run(fn: () => Promise<SeriesDetail>) {
    setBusy(true);
    setMsg(undefined);
    try {
      const s = await fn();
      setMsg({ ok: true, text: `Importata «${s.name}»: ${s.observation_count} osservazioni${s.from_cache ? ' (dalla cache: fonte non raggiungibile)' : ''}.${s.import_warnings?.length ? ` Avvisi: ${s.import_warnings.join('; ')}` : ''}` });
      onDone(s.id);
    } catch (e) {
      setMsg({ ok: false, text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (mode === 'preset') {
      const p = presets.data?.[Number(preset)] as Preset | undefined;
      if (p) void run(() => api.importSeries({ connector: p.connector, category: p.category, ...p.params }));
    } else if (mode === 'custom') {
      const filters: Record<string, string> = {};
      for (const pair of c.filters.split(/[&,\s]+/).filter(Boolean)) {
        const [k, v] = pair.split('=');
        if (k && v) filters[k.trim()] = v.trim();
      }
      void run(() => api.importSeries({ ...c, filters }));
    } else {
      if (!file) return setMsg({ ok: false, text: 'Seleziona un file CSV.' });
      const f = new FormData();
      f.append('file', file);
      for (const [k, v] of Object.entries(csv)) f.append(k, v);
      void run(() => api.uploadSeries(f));
    }
  }

  const bind = (k: keyof typeof c) => ({ value: c[k], onChange: (e: { target: { value: string } }) => setC({ ...c, [k]: e.target.value }) });
  const bindCsv = (k: keyof typeof csv) => ({ value: csv[k], onChange: (e: { target: { value: string } }) => setCsv({ ...csv, [k]: e.target.value }) });
  const categoryOptions = Object.entries(SERIES_CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>);

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="flex gap-1" role="tablist">
        {([['preset', 'Serie suggerite'], ['custom', 'Da fonte aperta'], ['csv', 'Da CSV']] as const).map(([k, v]) => (
          <button type="button" key={k} role="tab" aria-selected={mode === k} onClick={() => setMode(k)} className={`rounded-md px-3 py-1.5 text-sm ${mode === k ? 'bg-ink-800 text-paper' : 'text-steel-400 hover:text-paper'}`}>{v}</button>
        ))}
      </div>
      {mode === 'preset' && (
        <Field label="Serie" hint="Codici reali delle fonti. Le serie FRED richiedono una chiave gratuita (Sistema → Credenziali).">
          <Select value={preset} onChange={(e) => setPreset(e.target.value)}>
            <option value="">Seleziona…</option>
            {presets.data?.map((p, i) => <option key={i} value={i}>{CONNECTORS[p.connector as keyof typeof CONNECTORS]} · {p.label}</option>)}
          </Select>
        </Field>
      )}
      {mode === 'custom' && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="Fonte"><Select {...bind('connector')}>{Object.entries(CONNECTORS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>
          <Field label="Categoria"><Select {...bind('category')}>{categoryOptions}</Select></Field>
          {c.connector === 'world-bank' && <><Field label="Codice indicatore" hint="es. FP.CPI.TOTL.ZG"><Input {...bind('indicator')} /></Field><Field label="Paese (ISO3)" hint="es. ITA, DEU, USA"><Input {...bind('country')} /></Field></>}
          {c.connector === 'fred' && <Field label="ID serie FRED" hint="es. UNRATE"><Input {...bind('series_id')} /></Field>}
          {c.connector === 'owid' && <><Field label="Slug del grafico" hint="dall'URL ourworldindata.org/grapher/…"><Input {...bind('slug')} /></Field><Field label="Paese / entità" hint="es. Italy"><Input {...bind('entity')} /></Field></>}
          {c.connector === 'eurostat' && <><Field label="Codice dataset" hint="es. prc_hicp_aind"><Input {...bind('dataset')} /></Field><Field label="Filtri" hint="es. geo=IT coicop=CP00 unit=RCH_A_AVG"><Input {...bind('filters')} /></Field></>}
        </div>
      )}
      {mode === 'csv' && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Field label="File CSV (data, valore)" className="sm:col-span-3"><input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0])} className="block w-full text-sm text-steel-300" /></Field>
          <Field label="Nome"><Input {...bindCsv('name')} /></Field>
          <Field label="Fonte (obbligatoria)"><Input {...bindCsv('source_label')} /></Field>
          <Field label="URL della fonte"><Input {...bindCsv('source_url')} /></Field>
          <Field label="Unità di misura"><Input {...bindCsv('unit')} /></Field>
          <Field label="Categoria"><Select {...bindCsv('category')}>{categoryOptions}</Select></Field>
        </div>
      )}
      {msg && <p role={msg.ok ? 'status' : 'alert'} className={`text-sm ${msg.ok ? 'text-ok' : 'text-bad'}`}>{msg.text}</p>}
      <div className="flex justify-end"><Button type="submit" variant="primary" disabled={busy}>{busy ? 'Importazione…' : 'Importa serie'}</Button></div>
    </form>
  );
}

export function FinancialPage() {
  const [category, setCategory] = useState('');
  const list = useAsync(() => api.seriesList(category || undefined), [category]);
  const [showImport, setShowImport] = useState(false);
  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Dati</h3>
      <p>Ogni serie riporta fonte, unità, frequenza, periodo, data di aggiornamento dichiarata dalla fonte e dati mancanti.</p>
      <p>Non ci sono quotazioni in tempo reale: l'ultimo valore è l'ultima osservazione pubblicata.</p>
      <p className="text-xs text-steel-500">IMF, OECD e BIS non sono ancora collegati.</p>
    </div>,
    [],
  );
  return (
    <>
      <PageHeader eyebrow="Modulo B" title="Financial Intelligence" description="Serie storiche da fonti aperte documentate e analisi quantitative."
        actions={<><Link to="/financial/compare" className="inline-flex items-center rounded-md border border-ink-600 px-3 py-1.5 text-sm text-paper hover:bg-ink-800">Confronta serie</Link><Button variant="primary" onClick={() => setShowImport((v) => !v)}>Importa serie</Button></>} />
      {showImport && <Card title="Importa serie" className="mb-6"><ImportPanel onDone={() => list.reload()} /></Card>}
      <Select aria-label="Categoria" className="mb-4 max-w-64" value={category} onChange={(e) => setCategory(e.target.value)}>
        <option value="">Tutte le categorie</option>
        {Object.entries(SERIES_CATEGORIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </Select>
      {list.loading && !list.data && <Loading />}
      {list.error && <ErrorBox error={list.error} onRetry={list.reload} />}
      {list.data?.length === 0 && <EmptyState>Nessuna serie importata.</EmptyState>}
      {list.data && list.data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-ink-700">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-ink-900 text-[11px] uppercase tracking-wider text-steel-500">
              <tr><th className="px-3 py-2">Serie</th><th className="px-3 py-2">Ultimo valore</th><th className="px-3 py-2">Periodo</th><th className="px-3 py-2">Freq.</th><th className="px-3 py-2">Fonte</th></tr>
            </thead>
            <tbody className="divide-y divide-ink-700">
              {list.data.map((s) => (
                <tr key={s.id}>
                  <td className="px-3 py-2"><Link to={`/financial/series/${s.id}`} className="text-paper hover:text-gold-300">{s.name}</Link> {s.is_demo && <DemoBadge />}<span className="block text-[11px] text-steel-500">{SERIES_CATEGORIES[s.category]}</span></td>
                  <td className="whitespace-nowrap px-3 py-2 text-paper">{formatNumber(s.last_value ?? undefined, 6)} <span className="text-xs text-steel-500">{s.unit}</span><span className="block text-[11px] text-steel-500">{s.last_date}</span></td>
                  <td className="whitespace-nowrap px-3 py-2 text-steel-400">{s.start_date?.slice(0, 7)} → {s.end_date?.slice(0, 7)}{s.missing_count > 0 && <span className="block text-[11px] text-warn">{s.missing_count} mancanti</span>}</td>
                  <td className="px-3 py-2 text-steel-400">{FREQUENCY_LABEL[s.frequency]}</td>
                  <td className="px-3 py-2 text-xs text-steel-400">{s.source_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div><dt className="text-[11px] text-steel-500">{label}</dt><dd className="text-sm text-paper">{value}</dd></div>;
}

export function SeriesDetailPage() {
  const id = Number(useParams().seriesId);
  const s = useAsync(() => api.series(id), [id]);
  const [maText, setMaText] = useState('');
  const ma = useMemo(() => maText.split(/[,\s]+/).map(Number).filter((n) => Number.isInteger(n) && n >= 2).slice(0, 3), [maText]);
  const [returns, setReturns] = useState('simple');
  const [metrics, setMetrics] = useState<string>('');
  const a = useAsync(() => api.analysis(id, ma, returns, metrics || undefined), [id, ma.join(','), returns, metrics]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string>();
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();

  useContextPanel(
    s.data ? (
      <div className="space-y-3">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Provenienza</h3>
        <dl className="space-y-2 text-steel-300">
          <Stat label="Fonte" value={s.data.source_label} />
          <Stat label="Unità" value={s.data.unit || '—'} />
          <Stat label="Frequenza" value={FREQUENCY_LABEL[s.data.frequency]} />
          <Stat label="Periodo" value={`${s.data.start_date} → ${s.data.end_date}`} />
          <Stat label="Aggiornamento dichiarato dalla fonte" value={s.data.source_last_updated || 'non indicato'} />
          <Stat label="Scaricata il" value={formatDateTime(s.data.retrieved_at)} />
          <Stat label="Osservazioni / mancanti" value={`${s.data.observation_count} / ${s.data.missing_count}`} />
        </dl>
        {s.data.from_cache && <p className="text-xs text-warn">Ultimo aggiornamento servito dalla cache: la fonte non era raggiungibile.</p>}
        <p className="text-xs text-steel-500">{s.data.license_note}</p>
        {s.data.source_url && <a href={s.data.source_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-xs text-gold-300 hover:underline">Pagina della fonte <ExternalLink className="size-3" aria-hidden /></a>}
      </div>
    ) : null,
    [s.data],
  );

  if (s.loading && !s.data) return <Loading />;
  if (s.error) return <ErrorBox error={s.error} onRetry={s.reload} />;
  const d = s.data!;
  const chartData = mergePoints({ value: d.observations, ...Object.fromEntries(Object.entries(a.data?.moving_averages ?? {}).map(([w, pts]) => [`ma${w}`, pts])) });
  const chartSeries = [{ key: 'value', label: d.name.length > 40 ? 'Serie' : d.name }, ...Object.keys(a.data?.moving_averages ?? {}).map((w) => ({ key: `ma${w}`, label: `Media mobile ${w}`, dashed: true }))];

  return (
    <>
      <PageHeader eyebrow={<Link to="/financial" className="hover:underline">Financial Intelligence</Link>} title={d.name}
        description={`${d.unit || 'unità non indicata'} · ${FREQUENCY_LABEL[d.frequency]} · ultimo dato ${d.last_date ?? '—'}`}
        actions={<>
          {d.connector !== 'upload' && <Button disabled={busy} onClick={async () => { setBusy(true); setErr(undefined); try { s.setData(await api.refreshSeries(id)); await a.reload(); } catch (e) { setErr(errorText(e)); } finally { setBusy(false); } }}><RefreshCw className={`size-4 ${busy ? 'animate-spin' : ''}`} aria-hidden /> Aggiorna dalla fonte</Button>}
          <Button onClick={() => setDeleting(true)} aria-label="Elimina serie"><Trash2 className="size-4" /></Button>
        </>} />
      {d.is_demo && <p className="mb-3"><DemoBadge /> <span className="text-xs text-steel-400">Serie dimostrativa: non sono dati reali.</span></p>}
      {err && <div className="mb-4"><ErrorBox error={new Error(err)} /></div>}
      <Card title="Serie storica" className="mb-4">
        <div className="mb-3 flex flex-wrap gap-3">
          <Field label="Medie mobili (periodi, max 3)"><Input value={maText} onChange={(e) => setMaText(e.target.value)} placeholder="es. 5, 10" className="w-40" /></Field>
        </div>
        <TimeChart data={chartData} series={chartSeries} unit={d.unit} ariaLabel={`Andamento di ${d.name}`} />
      </Card>
      {a.error && <ErrorBox error={a.error} />}
      {a.data && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Card title="Statistiche">
            <div className="mb-3 flex flex-wrap gap-3">
              <Field label="Base di calcolo">
                <Select value={metrics || a.data.metrics_basis} onChange={(e) => setMetrics(e.target.value)}>
                  <option value="levels">Livelli (rendimenti %, drawdown)</option>
                  <option value="rates">Tassi/percentuali (variazioni assolute)</option>
                </Select>
              </Field>
              {a.data.metrics_basis === 'levels' && <Field label="Rendimenti"><Select value={returns} onChange={(e) => setReturns(e.target.value)}><option value="simple">Semplici</option><option value="log">Logaritmici</option></Select></Field>}
            </div>
            <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              <Stat label="Osservazioni valide" value={String(a.data.summary.valid)} />
              <Stat label="Mancanti" value={String(a.data.summary.missing)} />
              <Stat label="Media" value={formatNumber(a.data.summary.mean as number)} />
              <Stat label="Minimo" value={formatNumber(a.data.summary.min as number)} />
              <Stat label="Massimo" value={formatNumber(a.data.summary.max as number)} />
              <Stat label="Deviazione std." value={formatNumber(a.data.summary.std as number)} />
              {a.data.returns && <>
                <Stat label="Variazione totale" value={pct(a.data.returns.total_change)} />
                <Stat label="CAGR" value={pct(a.data.returns.cagr)} />
                <Stat label="Volatilità annualizzata" value={pct(a.data.returns.volatility_annualized)} />
                <Stat label="Rendimento medio per periodo" value={pct(a.data.returns.mean_per_period)} />
                <Stat label="Migliore / peggiore" value={`${pct(a.data.returns.best)} / ${pct(a.data.returns.worst)}`} />
              </>}
              {a.data.changes && <>
                <Stat label="Variazione media per periodo" value={formatNumber(a.data.changes.mean as number)} />
                <Stat label="Dev. std. variazioni" value={formatNumber(a.data.changes.std as number)} />
              </>}
              {a.data.drawdown && <Stat label="Max drawdown" value={`${pct(a.data.drawdown.max_drawdown)} (${a.data.drawdown.peak_date.slice(0, 7)} → ${a.data.drawdown.trough_date.slice(0, 7)})`} />}
            </dl>
            {a.data.warnings.map((w) => <p key={w} className="mt-2 flex items-start gap-1.5 text-xs text-warn"><AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />{w}</p>)}
          </Card>
          <Card title="Analisi della serie temporale">
            <dl className="space-y-2">
              {a.data.timeseries.linear_trend && <Stat label="Trend lineare (per periodo)" value={formatNumber(a.data.timeseries.linear_trend.slope_per_period)} />}
              {a.data.timeseries.adf && <Stat label={`Test ADF (n=${a.data.timeseries.adf.nobs})`} value={`stat. ${formatNumber(a.data.timeseries.adf.statistic)}, p = ${formatNumber(a.data.timeseries.adf.p_value, 3)} — ${a.data.timeseries.adf.interpretation}`} />}
              {a.data.timeseries.acf && <Stat label="Autocorrelazione (lag 1–3)" value={a.data.timeseries.acf.slice(1, 4).map((x) => formatNumber(x, 3)).join(' · ')} />}
              {a.data.timeseries.note && <p className="text-xs text-steel-500">{a.data.timeseries.note}</p>}
            </dl>
            {a.data.anomalies.length > 0 && (
              <div className="mt-3">
                <h4 className="text-[11px] uppercase tracking-wider text-steel-500">Variazioni anomale</h4>
                <ul className="text-xs text-steel-300">{a.data.anomalies.slice(0, 8).map((x) => <li key={x.date}>{x.date}: {formatNumber(x.change)} (z {formatNumber(x.z, 3)})</li>)}</ul>
              </div>
            )}
          </Card>
          {a.data.drawdown_series && <Card title="Drawdown" className="lg:col-span-2"><DrawdownChart data={a.data.drawdown_series} ariaLabel="Drawdown dal massimo precedente" /></Card>}
        </div>
      )}
      <ConfirmDialog open={deleting} title="Eliminare la serie?" message="La serie e tutte le sue osservazioni verranno eliminate." confirmLabel="Elimina"
        onCancel={() => setDeleting(false)} onConfirm={async () => { await api.deleteSeries(id); navigate('/financial'); }} />
    </>
  );
}

export function ComparePage() {
  const list = useAsync(() => api.seriesList(), []);
  const [selected, setSelected] = useState<number[]>([]);
  const [freq, setFreq] = useState('');
  const [method, setMethod] = useState('last');
  const [mode, setMode] = useState('returns');
  const [res, setRes] = useState<Comparison>();
  const [err, setErr] = useState<string>();
  const [busy, setBusy] = useState(false);
  const nameOf = (id: string) => res?.series.find((s) => String(s.id) === id)?.name ?? id;

  async function run() {
    setBusy(true);
    setErr(undefined);
    try {
      setRes(await api.compare({ series_ids: selected, target_frequency: freq || null, method, mode }));
    } catch (e) {
      setErr(errorText(e));
      setRes(undefined);
    } finally {
      setBusy(false);
    }
  }
  const rebasedOk = res && Object.values(res.rebased_100).every(Boolean);

  return (
    <>
      <PageHeader eyebrow={<Link to="/financial" className="hover:underline">Financial Intelligence</Link>} title="Confronto tra serie" description="Allineamento sulle date comuni, ribasamento a 100 e correlazioni. Le frequenze diverse richiedono un ricampionamento esplicito." />
      <Card className="mb-4">
        <fieldset className="mb-3">
          <legend className="mb-1 text-xs text-steel-400">Serie (da 2 a 8)</legend>
          <div className="grid grid-cols-1 gap-1 sm:grid-cols-2">
            {list.data?.map((s) => (
              <label key={s.id} className="flex items-center gap-2 text-sm text-steel-300">
                <input type="checkbox" checked={selected.includes(s.id)} disabled={!selected.includes(s.id) && selected.length >= 8}
                  onChange={() => setSelected(selected.includes(s.id) ? selected.filter((x) => x !== s.id) : [...selected, s.id])} />
                <span className="min-w-0 truncate">{s.name}</span><Badge>{s.frequency}</Badge>
              </label>
            ))}
          </div>
          {list.data?.length === 0 && <EmptyState>Importa almeno due serie.</EmptyState>}
        </fieldset>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <Field label="Frequenza comune"><Select value={freq} onChange={(e) => setFreq(e.target.value)}><option value="">Nessun ricampionamento</option>{Object.entries(FREQUENCY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select></Field>
          <Field label="Metodo di aggregazione"><Select value={method} onChange={(e) => setMethod(e.target.value)}><option value="last">Ultimo valore del periodo</option><option value="mean">Media del periodo</option><option value="sum">Somma del periodo</option></Select></Field>
          <Field label="Correlazione su"><Select value={mode} onChange={(e) => setMode(e.target.value)}><option value="returns">Variazioni (consigliato)</option><option value="levels">Livelli</option></Select></Field>
          <div className="flex items-end"><Button variant="primary" disabled={selected.length < 2 || busy} onClick={run}>Confronta</Button></div>
        </div>
      </Card>
      {err && <ErrorBox error={new Error(err)} />}
      {res && (
        <div className="space-y-4">
          <Card title={`Procedura (${res.common_observations} date comuni, ${res.period.start} → ${res.period.end})`}>
            <ul className="list-disc space-y-1 pl-5 text-sm text-steel-300">{[...res.procedure, ...res.notes].map((p) => <li key={p}>{p}</li>)}</ul>
          </Card>
          {rebasedOk && (
            <Card title="Andamento ribasato (primo valore comune = 100)">
              <TimeChart data={mergePoints(Object.fromEntries(Object.entries(res.rebased_100).map(([k, v]) => [k, v ?? []])))}
                series={Object.keys(res.rebased_100).map((k, i) => ({ key: k, label: nameOf(k), color: SERIES_COLORS[i] }))} ariaLabel="Serie ribasate a 100" />
            </Card>
          )}
          <Card title="Matrice di correlazione (Pearson)">
            <div className="overflow-x-auto">
              <table className="text-sm">
                <thead><tr><th />{Object.keys(res.correlation).map((k) => <th key={k} className="max-w-40 truncate px-2 py-1 text-left text-xs font-normal text-steel-400">{nameOf(k)}</th>)}</tr></thead>
                <tbody>
                  {Object.entries(res.correlation).map(([a, row]) => (
                    <tr key={a}><th className="max-w-48 truncate px-2 py-1 text-left text-xs font-normal text-steel-400">{nameOf(a)}</th>
                      {Object.entries(row).map(([b, v]) => <td key={b} className="px-2 py-1 text-paper">{v === null ? 'n.d.' : v.toFixed(3)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[11px] text-steel-500">n.d.: correlazione non definita (variazioni costanti o dati insufficienti).</p>
          </Card>
        </div>
      )}
    </>
  );
}
