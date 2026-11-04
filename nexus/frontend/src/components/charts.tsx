/**
 * Grafici NEXUS (Recharts). Regole: un solo asse y per grafico, palette
 * categoriale validata (CVD) in ordine fisso, legenda con ≥ 2 serie, tooltip,
 * vista tabellare sempre disponibile.
 */
import { useState } from 'react';
import { Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

/** Slot categoriali scuri validati su #121316 (scripts/validate_palette.js: tutti i controlli superati). */
export const SERIES_COLORS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];

const AXIS = { stroke: '#3a3d44', tick: { fill: '#9a9ea6', fontSize: 11 } };
const fmt = (v: number | null | undefined, digits = 4) =>
  v === null || v === undefined || Number.isNaN(v) ? '—' : v.toLocaleString('it-IT', { maximumSignificantDigits: digits });

export interface ChartSeries { key: string; label: string; color?: string; dashed?: boolean }

function TooltipBox({ active, payload, label, unit }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string; unit?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-ink-600 bg-ink-850 px-3 py-2 text-xs shadow-lg">
      <p className="mb-1 text-steel-400">{label}</p>
      {payload.map((p) => (
        <p key={p.name} className="flex items-center gap-2 text-paper">
          <span className="inline-block h-0.5 w-3" style={{ background: p.color }} aria-hidden />
          <span className="text-steel-300">{p.name}:</span> {fmt(p.value, 6)} {unit}
        </p>
      ))}
    </div>
  );
}

export function TimeChart({ data, series, unit, height = 300, zeroLine = false, ariaLabel }: {
  data: Record<string, string | number | null>[];
  series: ChartSeries[];
  unit?: string;
  height?: number;
  zeroLine?: boolean;
  ariaLabel: string;
}) {
  const [table, setTable] = useState(false);
  return (
    <div>
      <div className="mb-1 flex justify-end">
        <button className="text-[11px] text-gold-300 hover:underline" onClick={() => setTable((t) => !t)}>{table ? 'Mostra grafico' : 'Mostra tabella'}</button>
      </div>
      {table ? (
        <div className="max-h-80 overflow-auto rounded border border-ink-700">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-ink-900 text-steel-500"><tr><th className="px-2 py-1">Data</th>{series.map((s) => <th key={s.key} className="px-2 py-1">{s.label}</th>)}</tr></thead>
            <tbody className="divide-y divide-ink-700">
              {data.map((r) => <tr key={String(r.date)}><td className="px-2 py-1 text-steel-400">{r.date}</td>{series.map((s) => <td key={s.key} className="px-2 py-1 text-paper">{fmt(r[s.key] as number | null, 8)}</td>)}</tr>)}
            </tbody>
          </table>
        </div>
      ) : (
        <div role="img" aria-label={ariaLabel} style={{ height }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="#1d1f23" vertical={false} />
              <XAxis dataKey="date" {...AXIS} minTickGap={40} />
              <YAxis {...AXIS} width={64} tickFormatter={(v) => fmt(v, 3)} domain={['auto', 'auto']} />
              {zeroLine && <ReferenceLine y={0} stroke="#7d818a" />}
              <Tooltip content={<TooltipBox unit={unit} />} cursor={{ stroke: '#7d818a' }} />
              {series.length > 1 && <Legend wrapperStyle={{ fontSize: 12, color: '#b9bcc2' }} />}
              {series.map((s, i) => (
                <Line key={s.key} type="linear" dataKey={s.key} name={s.label} stroke={s.color ?? SERIES_COLORS[i % SERIES_COLORS.length]}
                  strokeWidth={2} strokeDasharray={s.dashed ? '5 4' : undefined} dot={false} activeDot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function DrawdownChart({ data, ariaLabel }: { data: { date: string; value: number | null }[]; ariaLabel: string }) {
  return (
    <div role="img" aria-label={ariaLabel} style={{ height: 180 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data.map((d) => ({ date: d.date, drawdown: d.value === null ? null : d.value * 100 }))} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#1d1f23" vertical={false} />
          <XAxis dataKey="date" {...AXIS} minTickGap={40} />
          <YAxis {...AXIS} width={64} tickFormatter={(v) => `${fmt(v, 3)}%`} domain={['auto', 0]} />
          <Tooltip content={<TooltipBox unit="%" />} />
          <Area type="linear" dataKey="drawdown" name="Drawdown" stroke={SERIES_COLORS[0]} fill={SERIES_COLORS[0]} fillOpacity={0.18} strokeWidth={2} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Unisce più serie di punti in righe {date, k1, k2, …} per i grafici. */
export function mergePoints(series: Record<string, { date: string; value: number | null }[]>): Record<string, string | number | null>[] {
  const rows = new Map<string, Record<string, string | number | null>>();
  for (const [key, pts] of Object.entries(series)) {
    for (const p of pts) {
      const r = rows.get(p.date) ?? { date: p.date };
      r[key] = p.value;
      rows.set(p.date, r);
    }
  }
  return [...rows.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

export { fmt as formatNumber };
