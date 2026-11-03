import { useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, FlaskConical, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import type { SimulationEnvelope } from '../api/types';
import { formatNumber, TimeChart } from '../components/charts';
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

const KINDS = {
  monte_carlo: 'Monte Carlo',
  monte_carlo_bootstrap: 'Monte Carlo su dati storici',
  debt: 'Debito pubblico e tassi',
  sensitivity: 'Sensitività',
  inflation: 'Inflazione',
  monetary_policy: 'Politiche monetarie',
  regression: 'Regressione',
  backtest: 'Backtesting',
} as const;
type Kind = keyof typeof KINDS;

const pct = (v: unknown) => (typeof v === 'number' ? `${formatNumber(v * 100, 4)}%` : '—');
const num = (s: string) => (s.trim() === '' ? undefined : Number(s.replace(',', '.')));
const list = (s: string) => s.split(/[;\s]+/).filter(Boolean).map((x) => Number(x.replace(',', '.')));

type FormState = Record<string, string>;
const DEFAULTS: Record<Kind, FormState> = {
  monte_carlo: { s0: '100', mu: '0.05', sigma: '0.2', years: '5', steps_per_year: '12', n_paths: '2000', seed: '42', threshold: '' },
  monte_carlo_bootstrap: { series_id: '', years: '3', n_paths: '2000', block: '6', seed: '42' },
  debt: { d0: '135', r_eff0: '0.03', r_market: '0.04', avg_maturity: '7', g: '0.03', pb: '1', years: '15', rate_shock: '0.01', shock_start: '1',
          crisis_start: '', crisis_years: '2', crisis_g: '-0.06', crisis_r: '0.01', stochastic: '', counterfactual: '' },
  sensitivity: { d0: '135', r_eff0: '0.03', r_market: '0.04', avg_maturity: '7', g: '0.03', pb: '1', years: '15', g_lo: '0.01', g_hi: '0.05', r_lo: '0.02', r_hi: '0.06', pb_lo: '-1', pb_hi: '3' },
  inflation: { amount: '10000', nominal_rate: '0.03', years: '20', inflation_levels: '0.02 0.05 0.10' },
  monetary_policy: { labels: '2021 2022 2023', inflation: '0.026 0.084 0.054', output_gap: '-0.01 0.005 0.0', actual_rate: '', r_star: '0.005', pi_target: '0.02' },
  regression: { y_series_id: '', x_series_ids: '', transform: 'diff', lags: '0', target_frequency: '', method: 'mean' },
  backtest: { series_id: '', strategy: 'ma_cross', fast: '10', slow: '50', lookback: '12', cost_bps: '10', rf: '0' },
};

function payload(kind: Kind, f: FormState): Record<string, unknown> {
  switch (kind) {
    case 'monte_carlo':
      return { s0: num(f.s0), mu: num(f.mu), sigma: num(f.sigma), years: num(f.years), steps_per_year: num(f.steps_per_year), n_paths: num(f.n_paths), seed: num(f.seed), threshold: num(f.threshold) ?? null };
    case 'monte_carlo_bootstrap':
      return { series_id: num(f.series_id), years: num(f.years), n_paths: num(f.n_paths), block: num(f.block), seed: num(f.seed) };
    case 'debt':
      return {
        d0: num(f.d0), r_eff0: num(f.r_eff0), r_market: num(f.r_market), avg_maturity: num(f.avg_maturity), g: num(f.g), pb: num(f.pb), years: num(f.years),
        rate_shock: num(f.rate_shock) ?? 0, shock_start: num(f.shock_start) ?? 1, counterfactual: f.counterfactual === '1',
        crisis: f.crisis_start ? { start: num(f.crisis_start), years: num(f.crisis_years), g_shock: num(f.crisis_g) ?? 0, r_shock: num(f.crisis_r) ?? 0 } : null,
        stochastic: f.stochastic === '1' ? { n_paths: 2000, sd_r: 0.005, sd_g: 0.02, corr: -0.3 } : null,
      };
    case 'sensitivity':
      return { base: { d0: num(f.d0), r_eff0: num(f.r_eff0), r_market: num(f.r_market), avg_maturity: num(f.avg_maturity), g: num(f.g), pb: num(f.pb), years: num(f.years) },
               ranges: { g: [num(f.g_lo), num(f.g_hi)], r_market: [num(f.r_lo), num(f.r_hi)], pb: [num(f.pb_lo), num(f.pb_hi)] } };
    case 'inflation':
      return { amount: num(f.amount), nominal_rate: num(f.nominal_rate), years: num(f.years), inflation_levels: list(f.inflation_levels) };
    case 'monetary_policy':
      return { labels: f.labels.split(/\s+/).filter(Boolean), inflation: list(f.inflation), output_gap: list(f.output_gap), actual_rate: f.actual_rate.trim() ? list(f.actual_rate) : null,
               r_star: num(f.r_star), pi_target: num(f.pi_target),
               rules: [{ name: 'Taylor (1993): a=0,5 b=0,5', a: 0.5, b: 0.5 }, { name: 'Più restrittiva: a=1 b=0,5', a: 1, b: 0.5 }, { name: 'Attenta alla crescita: a=0,5 b=1', a: 0.5, b: 1 }] };
    case 'regression':
      return { y_series_id: num(f.y_series_id), x_series_ids: f.x_series_ids.split(',').filter(Boolean).map(Number), transform: f.transform, lags: num(f.lags),
               target_frequency: f.target_frequency || null, method: f.method };
    case 'backtest':
      return { series_id: num(f.series_id), strategy: f.strategy, fast: num(f.fast), slow: num(f.slow), lookback: num(f.lookback), cost_bps: num(f.cost_bps), rf: num(f.rf) };
  }
}

function SimForm({ kind, onDone }: { kind: Kind; onDone: (id: number) => void }) {
  const [f, setF] = useState<FormState>(DEFAULTS[kind]);
  const [err, setErr] = useState<string>();
  const [busy, setBusy] = useState(false);
  const series = useAsync(() => api.seriesList(), []);
  const b = (k: string) => ({ value: f[k] ?? '', onChange: (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value }) });
  const seriesSelect = (k: string, label: string) => (
    <Field label={label}><Select {...b(k)}><option value="">Seleziona…</option>{series.data?.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.frequency})</option>)}</Select></Field>
  );
  // Solo i campi del tipo selezionato vengono costruiti (lo stato contiene solo le sue chiavi).
  const fields: Record<Kind, () => ReactNode> = {
    monte_carlo: () => <>
      <Field label="Valore iniziale"><Input {...b('s0')} /></Field><Field label="Drift annuo μ (decimale)"><Input {...b('mu')} /></Field>
      <Field label="Volatilità annua σ"><Input {...b('sigma')} /></Field><Field label="Anni"><Input {...b('years')} /></Field>
      <Field label="Passi per anno"><Input {...b('steps_per_year')} /></Field><Field label="Traiettorie (max 20000)"><Input {...b('n_paths')} /></Field>
      <Field label="Seed"><Input {...b('seed')} /></Field><Field label="Soglia (facoltativa)"><Input {...b('threshold')} /></Field></>,
    monte_carlo_bootstrap: () => <>{seriesSelect('series_id', 'Serie (prezzi o indici)')}<Field label="Anni"><Input {...b('years')} /></Field>
      <Field label="Traiettorie"><Input {...b('n_paths')} /></Field><Field label="Lunghezza blocco"><Input {...b('block')} /></Field></>,
    debt: () => <>
      <Field label="Debito iniziale (% PIL)"><Input {...b('d0')} /></Field><Field label="Costo medio iniziale del debito"><Input {...b('r_eff0')} /></Field>
      <Field label="Tasso di mercato"><Input {...b('r_market')} /></Field><Field label="Vita media del debito (anni)"><Input {...b('avg_maturity')} /></Field>
      <Field label="Crescita PIL nominale"><Input {...b('g')} /></Field><Field label="Saldo primario (% PIL)"><Input {...b('pb')} /></Field>
      <Field label="Anni"><Input {...b('years')} /></Field><Field label="Shock sui tassi (es. 0.01 = +1 p.p.)"><Input {...b('rate_shock')} /></Field>
      <Field label="Crisi: anno di inizio (vuoto = nessuna)"><Input {...b('crisis_start')} /></Field><Field label="Crisi: durata"><Input {...b('crisis_years')} /></Field>
      <Field label="Crisi: shock crescita"><Input {...b('crisis_g')} /></Field><Field label="Crisi: shock tassi"><Input {...b('crisis_r')} /></Field>
      <label className="flex items-center gap-2 text-sm text-steel-300"><input type="checkbox" checked={f.stochastic === '1'} onChange={(e) => setF({ ...f, stochastic: e.target.checked ? '1' : '' })} />Incertezza su r e g (Monte Carlo)</label>
      <label className="flex items-center gap-2 text-sm text-steel-300"><input type="checkbox" checked={f.counterfactual === '1'} onChange={(e) => setF({ ...f, counterfactual: e.target.checked ? '1' : '' })} />Scenario controfattuale (storia alternativa)</label></>,
    sensitivity: () => <>
      {['d0', 'r_eff0', 'r_market', 'avg_maturity', 'g', 'pb', 'years'].map((k) => <Field key={k} label={`Base: ${k}`}><Input {...b(k)} /></Field>)}
      <Field label="Crescita: min"><Input {...b('g_lo')} /></Field><Field label="Crescita: max"><Input {...b('g_hi')} /></Field>
      <Field label="Tasso di mercato: min"><Input {...b('r_lo')} /></Field><Field label="Tasso di mercato: max"><Input {...b('r_hi')} /></Field>
      <Field label="Saldo primario: min"><Input {...b('pb_lo')} /></Field><Field label="Saldo primario: max"><Input {...b('pb_hi')} /></Field></>,
    inflation: () => <>
      <Field label="Importo"><Input {...b('amount')} /></Field><Field label="Tasso nominale annuo"><Input {...b('nominal_rate')} /></Field>
      <Field label="Anni"><Input {...b('years')} /></Field><Field label="Livelli di inflazione (separati da spazio)"><Input {...b('inflation_levels')} /></Field></>,
    monetary_policy: () => <>
      <Field label="Periodi (separati da spazio)" className="sm:col-span-2"><Input {...b('labels')} /></Field>
      <Field label="Inflazione per periodo (decimali)" className="sm:col-span-2"><Input {...b('inflation')} /></Field>
      <Field label="Output gap per periodo" className="sm:col-span-2"><Input {...b('output_gap')} /></Field>
      <Field label="Tasso effettivo (facoltativo)" className="sm:col-span-2"><Input {...b('actual_rate')} /></Field>
      <Field label="r* (tasso neutrale reale)"><Input {...b('r_star')} /></Field><Field label="Obiettivo d'inflazione"><Input {...b('pi_target')} /></Field>
      <p className="text-xs text-steel-500 sm:col-span-2">Inserisci tu i dati (con la loro fonte nella nota del progetto): il confronto è controfattuale.</p></>,
    regression: () => <>{seriesSelect('y_series_id', 'Variabile dipendente (y)')}
      <Field label="Regressori (x)"><Select multiple value={f.x_series_ids.split(',').filter(Boolean)} onChange={(e) => setF({ ...f, x_series_ids: [...e.target.selectedOptions].map((o) => o.value).join(',') })} className="h-28">
        {series.data?.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.frequency})</option>)}</Select></Field>
      <Field label="Trasformazione"><Select {...b('transform')}><option value="diff">Differenze</option><option value="pct">Variazioni %</option><option value="levels">Livelli (rischio spurio)</option></Select></Field>
      <Field label="Ritardo dei regressori"><Input {...b('lags')} /></Field>
      <Field label="Frequenza comune (se diverse)"><Select {...b('target_frequency')}><option value="">—</option><option value="M">Mensile</option><option value="Q">Trimestrale</option><option value="A">Annuale</option></Select></Field>
      <Field label="Aggregazione"><Select {...b('method')}><option value="mean">Media</option><option value="last">Ultimo</option><option value="sum">Somma</option></Select></Field></>,
    backtest: () => <>{seriesSelect('series_id', 'Serie di prezzi')}
      <Field label="Strategia"><Select {...b('strategy')}><option value="buy_hold">Buy & hold</option><option value="ma_cross">Incrocio medie mobili</option><option value="momentum">Momentum</option></Select></Field>
      {f.strategy === 'ma_cross' && <><Field label="Media veloce"><Input {...b('fast')} /></Field><Field label="Media lenta"><Input {...b('slow')} /></Field></>}
      {f.strategy === 'momentum' && <Field label="Lookback (periodi)"><Input {...b('lookback')} /></Field>}
      <Field label="Costi (punti base per operazione)"><Input {...b('cost_bps')} /></Field><Field label="Tasso privo di rischio annuo"><Input {...b('rf')} /></Field></>,
  };
  return (
    <div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">{fields[kind]()}</div>
      {err && <p role="alert" className="mt-3 text-sm text-bad">{err}</p>}
      <div className="mt-3 flex justify-end">
        <Button variant="primary" disabled={busy} onClick={async () => {
          setBusy(true); setErr(undefined);
          try { onDone((await api.runSimulation(kind, payload(kind, f))).id); } catch (e) { setErr(errorText(e)); } finally { setBusy(false); }
        }}><FlaskConical className="size-4" aria-hidden /> Esegui</Button>
      </div>
    </div>
  );
}

export function LabPage() {
  const [kind, setKind] = useState<Kind>('debt');
  const sims = useAsync(() => api.simulations(), []);
  const navigate = useNavigate();
  useContextPanel(
    <div className="space-y-2 text-steel-300">
      <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Regole del laboratorio</h3>
      <p>Ogni risultato dichiara ipotesi, variabili, parametri, metodo, dati usati e limiti.</p>
      <p>Le simulazioni non sono previsioni; gli scenari controfattuali sono marcati come tali.</p>
      <p>Nel backtest il segnale di oggi agisce domani: nessun uso di dati futuri.</p>
    </div>,
    [],
  );
  return (
    <>
      <PageHeader eyebrow="Modulo F" title="Economic Laboratory" description="Simulazioni, scenari, regressioni e backtesting con ipotesi esplicite." />
      <Card className="mb-6">
        <Field label="Tipo di analisi" className="mb-4 max-w-sm">
          <Select value={kind} onChange={(e) => setKind(e.target.value as Kind)}>{Object.entries(KINDS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select>
        </Field>
        <SimForm key={kind} kind={kind} onDone={(id) => navigate(`/lab/simulations/${id}`)} />
      </Card>
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-steel-400">Simulazioni salvate</h2>
      {sims.loading && !sims.data && <Loading />}
      {sims.data?.length === 0 && <EmptyState>Nessuna simulazione.</EmptyState>}
      <ul className="space-y-2">
        {sims.data?.map((s) => (
          <li key={s.id}><Link to={`/lab/simulations/${s.id}`} className="flex flex-wrap items-center gap-2 rounded-lg border border-ink-700 bg-ink-900 p-3 hover:border-gold-500/60">
            <span className="min-w-0 flex-1 truncate text-sm text-paper">{s.title}</span>
            <Badge>{KINDS[s.kind as Kind] ?? s.kind}</Badge>{s.counterfactual && <Badge tone="warn">Controfattuale</Badge>}
            <span className="text-[11px] text-steel-500">{formatDateTime(s.created_at)}</span>
          </Link></li>
        ))}
      </ul>
    </>
  );
}

type Row = Record<string, string | number | null>;

function ResultsView({ r }: { r: SimulationEnvelope }) {
  const res = r.results as Record<string, any>;
  const fanChart = (fan: Row[], label: string, unit = '') => (
    <TimeChart data={fan.map((p) => ({ date: String(p.t), p5: p.p5, p50: p.p50, p95: p.p95 }))} unit={unit} ariaLabel={label}
      series={[{ key: 'p95', label: '95° percentile', dashed: true }, { key: 'p50', label: 'Mediana' }, { key: 'p5', label: '5° percentile', dashed: true }]} />
  );
  switch (r.kind) {
    case 'monte_carlo':
    case 'monte_carlo_bootstrap':
      return <>{fanChart(res.fan, 'Distribuzione delle traiettorie')}
        <dl className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">{Object.entries(res.final).map(([k, v]) => <div key={k}><dt className="text-[11px] text-steel-500">{k}</dt><dd className="text-paper">{formatNumber(v as number, 6)}</dd></div>)}</dl></>;
    case 'debt': {
      const rows = (res.years as number[]).map((y, i) => ({ date: String(y), base: res.baseline.debt[i], shock: res.rate_shock?.debt[i] ?? null, crisis: res.crisis?.debt[i] ?? null }));
      const series = [{ key: 'base', label: 'Scenario base' }, ...(res.rate_shock ? [{ key: 'shock', label: 'Shock sui tassi' }] : []), ...(res.crisis ? [{ key: 'crisis', label: 'Crisi' }] : [])];
      return <>
        <TimeChart data={rows} series={series} unit="% PIL" ariaLabel="Debito/PIL per scenario" />
        <p className="mt-2 text-sm text-steel-300">Saldo primario che stabilizza il debito: <span className="text-paper">{formatNumber(res.debt_stabilizing_primary_balance)}% del PIL</span>
          {res.rate_shock_delta_final !== undefined && <> · Effetto dello shock a fine orizzonte: <span className="text-paper">{formatNumber(res.rate_shock_delta_final)} p.p.</span></>}</p>
        {res.fan && <div className="mt-4"><h4 className="mb-1 text-xs text-steel-400">Incertezza (scenario base)</h4>{fanChart(res.fan, 'Ventaglio di incertezza del debito', '% PIL')}<p className="text-xs text-steel-500">Probabilità che il debito finale superi quello iniziale: {pct(res.prob_final_above_start)}</p></div>}
      </>;
    }
    case 'sensitivity':
      return <table className="w-full text-left text-sm"><thead className="text-[11px] text-steel-500"><tr><th>Parametro</th><th>Intervallo</th><th>Risultato</th><th>Escursione</th></tr></thead>
        <tbody>{res.tornado.map((t: Row) => <tr key={String(t.parameter)} className="border-t border-ink-700"><td className="py-1 text-paper">{t.parameter}</td><td>{t.low} → {t.high}</td><td>{formatNumber(t.result_low as number)} → {formatNumber(t.result_high as number)}</td><td className="text-paper">{formatNumber(t.swing as number)}</td></tr>)}</tbody></table>;
    case 'inflation': {
      const keys = Object.keys(res.paths);
      const rows = (res.years as number[]).map((y, i) => Object.fromEntries([['date', String(y)], ...keys.map((k) => [k, res.paths[k].purchasing_power[i]])]));
      return <><TimeChart data={rows} series={keys.map((k) => ({ key: k, label: `Inflazione ${pct(Number(k))}` }))} ariaLabel="Potere d'acquisto" />
        <table className="mt-3 w-full text-left text-sm"><thead className="text-[11px] text-steel-500"><tr><th>Inflazione</th><th>Tasso reale</th><th>Potere d'acquisto finale</th><th>Investimento in termini reali</th><th>Dimezzamento</th></tr></thead>
          <tbody>{res.summary.map((s: Row) => <tr key={String(s.inflation)} className="border-t border-ink-700"><td>{pct(s.inflation)}</td><td>{pct(s.real_rate)}</td><td>{formatNumber(s.purchasing_power_end as number)}</td><td>{formatNumber(s.real_investment_end as number)}</td><td>{s.halving_years ?? '—'} anni</td></tr>)}</tbody></table></>;
    }
    case 'monetary_policy': {
      const rules = Object.keys(res.prescribed);
      const rows = (res.labels as string[]).map((l, i) => Object.fromEntries([['date', l], ...rules.map((k, j) => [`r${j}`, res.prescribed[k][i]]), ...(res.actual ? [['actual', res.actual[i]]] : [])]));
      return <TimeChart data={rows} ariaLabel="Tassi prescritti" series={[...rules.map((k, j) => ({ key: `r${j}`, label: k })), ...(res.actual ? [{ key: 'actual', label: 'Tasso effettivo', dashed: true }] : [])]} />;
    }
    case 'regression':
      return <>
        <p className="mb-2 text-sm text-steel-300">n = {res.n} · R² = {formatNumber(res.r2, 4)} · R² corretto = {formatNumber(res.r2_adj, 4)} · Durbin-Watson = {res.durbin_watson}</p>
        <table className="mb-3 w-full text-left text-sm"><thead className="text-[11px] text-steel-500"><tr><th>Variabile</th><th>Coefficiente</th><th>Err. std (HAC)</th><th>t</th><th>p</th><th>IC 95%</th></tr></thead>
          <tbody>{res.coefficients.map((c: Row) => <tr key={String(c.name)} className="border-t border-ink-700"><td className="text-paper">{c.name}</td><td>{formatNumber(c.coef as number)}</td><td>{formatNumber(c.std_err as number)}</td><td>{c.t}</td><td>{c.p_value}</td><td>{formatNumber(c.ci_low as number)} – {formatNumber(c.ci_high as number)}</td></tr>)}</tbody></table>
        <TimeChart data={res.fitted.map((f: Row) => ({ date: f.date, actual: f.actual, fitted: f.fitted }))} series={[{ key: 'actual', label: 'Osservato' }, { key: 'fitted', label: 'Stimato', dashed: true }]} ariaLabel="Valori osservati e stimati" />
      </>;
    case 'backtest':
      return <>
        <TimeChart data={res.equity} series={[{ key: 'strategy', label: 'Strategia' }, { key: 'benchmark', label: 'Buy & hold' }]} ariaLabel="Valore della strategia e del benchmark" />
        <table className="mt-3 w-full text-left text-sm"><thead className="text-[11px] text-steel-500"><tr><th /><th>Rendimento totale</th><th>CAGR</th><th>Volatilità</th><th>Sharpe</th><th>Max drawdown</th></tr></thead>
          <tbody>{[['Strategia', res.strategy], ['Buy & hold', res.benchmark_buy_hold]].map(([n, m]) => <tr key={n as string} className="border-t border-ink-700"><td className="text-paper">{n as string}</td><td>{pct(m.total_return)}</td><td>{pct(m.cagr)}</td><td>{pct(m.volatility)}</td><td>{formatNumber(m.sharpe, 3)}</td><td>{pct(m.max_drawdown)}</td></tr>)}</tbody></table>
        <p className="mt-2 text-xs text-steel-500">Operazioni: {res.trades} · Esposizione media: {pct(res.exposure)}</p>
      </>;
    default:
      return <pre className="overflow-auto text-xs text-steel-300">{JSON.stringify(res, null, 2)}</pre>;
  }
}

export function SimulationPage() {
  const id = Number(useParams().simId);
  const sim = useAsync(() => api.simulation(id), [id]);
  const [deleting, setDeleting] = useState(false);
  const navigate = useNavigate();
  if (sim.loading && !sim.data) return <Loading />;
  if (sim.error) return <ErrorBox error={sim.error} onRetry={sim.reload} />;
  const s = sim.data!;
  const r = s.result;
  const Section = ({ title, items }: { title: string; items: string[] }) => items.length ? <div><h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">{title}</h3><ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-steel-300">{items.map((i) => <li key={i}>{i}</li>)}</ul></div> : null;
  return (
    <>
      <PageHeader eyebrow={<Link to="/lab" className="hover:underline">Economic Laboratory</Link>} title={r.title} description={formatDateTime(s.created_at)}
        actions={<Button onClick={() => setDeleting(true)} aria-label="Elimina simulazione"><Trash2 className="size-4" /></Button>} />
      <p role="note" className={`mb-4 rounded-md border p-3 text-sm ${r.counterfactual ? 'border-warn/40 bg-warn/5 text-warn' : 'border-ink-700 bg-ink-850 text-steel-300'}`}>{r.label}</p>
      {r.warnings.map((w) => <p key={w} className="mb-2 flex items-start gap-2 text-sm text-warn"><AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden />{w}</p>)}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Risultati" className="lg:col-span-2"><ResultsView r={r} /></Card>
        <Card title="Scheda metodologica">
          <div className="space-y-4">
            <Section title="Ipotesi" items={r.hypotheses} />
            <div><h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Variabili</h3><dl className="mt-1 text-sm">{Object.entries(r.variables).map(([k, v]) => <div key={k}><dt className="inline font-mono text-paper">{k}</dt>: <dd className="inline text-steel-300">{v}</dd></div>)}</dl></div>
            <div><h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Metodo</h3><p className="mt-1 text-sm text-steel-300">{r.method}</p></div>
            <Section title="Dati utilizzati" items={r.data_used} />
            <div><h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-steel-500">Parametri</h3><Textarea readOnly className="mt-1 font-mono text-xs" value={JSON.stringify(r.parameters, null, 1)} /></div>
            <Section title="Limiti del modello" items={r.limitations} />
          </div>
        </Card>
      </div>
      <ConfirmDialog open={deleting} title="Eliminare la simulazione?" message="Il risultato salvato verrà eliminato." confirmLabel="Elimina"
        onCancel={() => setDeleting(false)} onConfirm={async () => { await api.deleteSimulation(id); navigate('/lab'); }} />
    </>
  );
}
